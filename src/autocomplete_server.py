#!/usr/bin/env python3
"""
Flask microservice port of the provided JavaScript module that talks to
`pyright-langserver --stdio` using the Language Server Protocol (LSP).

Endpoints (POST JSON):
 - /config/set_project_root  { "path": "/path/to/project" }
 - /config/set_python_path  { "path": "/path/to/python" }
 - /initialize              {}
 - /open_file               { "filePath": "/path/to/file.py", fileContent: "import numpy as..." }
 - /change_file             { "filePath": "/path/to/file.py", fileContent: "from pandas import..." }
 - /complete               { "filePath": "...", "line": 0, "character": 0 }
 - /hover                  { "filePath": "...", "line": 0, "character": 0 }
 - /definition             { "filePath": "...", "line": 0, "character": 0 }
 - /dispose                {}
 - /diagnostics            {}

PORT — 5000
"""
if 1 == 1:
    pass

from flask import Flask, request, jsonify
import subprocess
import threading
import json
import os
from pathlib import Path
import shutil
import logging

# Setup logger
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
log = logging.getLogger("pyright_flask")

app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin")
    response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS, GET"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

# LSP / Pyright symbol kind -> human-readable mapping (unchanged)
LSP_KIND = {
    1: "File",
    2: "Module",
    3: "Namespace",
    4: "Package",
    5: "Class",
    6: "Variable",
    7: "Method",
    8: "Function",
    9: "Property",
    10: "Field",
    11: "Constructor",
    12: "Enum",
    13: "Interface",
    14: "Function Type",
    15: "Constant",
    16: "String",
    17: "Number",
    18: "Boolean",
    19: "Array",
    20: "Object",
    21: "Key",
    22: "Null",
    23: "EnumMember",
    24: "Struct",
    25: "Event",
    26: "Operator",
    27: "TypeParameter",
}

# configuration
class Config:
    def __init__(self):
        self.projectRootPath = ''
        self.pythonPath = ''

    def setProjectRootPath(self, path: str):
        self.projectRootPath = path or ''

    def setPythonPath(self, path: str):
        self.pythonPath = path or ''

config = Config()

# encapsulated state

class ServerState:
    def __init__(self):
        self._lock = threading.Lock()
        self._response_cond = threading.Condition(self._lock)
        self.latestRequestId = 1
        self.responseLog = {}   # id -> response
        self.filesLog = {}      # uri -> {'latestVersion': int, 'fileContent': str}
        self.diagnosticsLog = []

    def next_request_id(self):
        with self._lock:
            rid = self.latestRequestId
            self.latestRequestId += 1
            return rid

    def store_response(self, response: dict):
        # classify publishDiagnostics vs id'd responses
        with self._response_cond:
            if response.get('method') == 'textDocument/publishDiagnostics':
                # keep a shallow copy to avoid mutations from other threads
                self.diagnosticsLog.append(response.copy())
            elif 'id' in response:
                self.responseLog[response['id']] = response
                self._response_cond.notify_all()

    def pop_response(self, request_id: int, timeout=None):
        """Wait (blocking) until response for request_id is available, then pop and return it."""
        with self._response_cond:
            found = self._response_cond.wait_for(lambda: request_id in self.responseLog, timeout=timeout)
            if not found:
                raise TimeoutError(f"Timeout waiting for response id {request_id}")
            return self.responseLog.pop(request_id)

    def add_file(self, uri: str, content: str, version: int = 1):
        with self._lock:
            self.filesLog[uri] = {'latestVersion': version, 'fileContent': content}

    def change_file(self, uri: str, content: str):
        with self._lock:
            if uri not in self.filesLog:
                self.filesLog[uri] = {'latestVersion': 0, 'fileContent': ''}
            self.filesLog[uri]['latestVersion'] += 1
            self.filesLog[uri]['fileContent'] = content
            return self.filesLog[uri]['latestVersion']

    def get_diagnostics_snapshot(self):
        with self._lock:
            return list(self.diagnosticsLog)

state = ServerState()

# process management
_server_proc = None
_stdout_thread = None
_stderr_thread = None
_running = False
_buffer = bytearray()
_buffer_lock = threading.Lock()  # to protect _buffer since stdout reader may modify it

# helper utilities

def pathToFileUri(p: str) -> str:
    """Return a file URI similar to JS's behavior. Uses pathlib.as_uri where possible."""
    try:
        pth = Path(p)
        # Use resolve(strict=False) so it doesn't fail on non-existent paths
        return pth.resolve(strict=False).as_uri()
    except Exception:
        # fallback to manual behavior (mimic original)
        fixed = p.replace('\\', '/')
        pth = Path(fixed)
        try:
            abs_p = pth.resolve(strict=False).as_posix()
        except Exception:
            abs_p = str(pth)
        if abs_p.startswith('/'):
            return 'file://' + abs_p
        else:
            return 'file:///' + abs_p

# LSP message parsing / reader threads

def _read_stdout_loop(pipe):
    global _buffer
    try:
        while True:
            chunk = pipe.read(4096)
            if not chunk:
                break
            if isinstance(chunk, str):
                chunk = chunk.encode('utf-8')
            with _buffer_lock:
                _buffer.extend(chunk)
                # parse messages as in LSP: headers + \r\n\r\n + body
                while True:
                    sep = b"\r\n\r\n"
                    header_end = _buffer.find(sep)
                    if header_end == -1:
                        break
                    header = _buffer[:header_end].decode('ascii', errors='ignore')
                    content_length = None
                    for line in header.split('\r\n'):
                        if line.lower().startswith('content-length:'):
                            try:
                                content_length = int(line.split(':', 1)[1].strip())
                            except Exception:
                                content_length = None
                            break
                    if content_length is None:
                        # malformed header: drop header and continue
                        _buffer = _buffer[header_end + 4:]
                        continue
                    total_len = header_end + 4 + content_length
                    if len(_buffer) < total_len:
                        break  # wait for full body
                    body = bytes(_buffer[header_end + 4: total_len]).decode('utf-8', errors='ignore')
                    # remove parsed message
                    _buffer = _buffer[total_len:]
                    try:
                        obj = json.loads(body)
                        state.store_response(obj)
                    except Exception:
                        log.warning('Malformed JSON from language server (ignored)')
                        continue
    except Exception as e:
        log.exception('stdout reader loop error: %s', e)


def _read_stderr_loop(pipe):
    try:
        while True:
            data = pipe.readline()
            if not data:
                break
            if isinstance(data, bytes):
                s = data.decode('utf-8', errors='ignore')
            else:
                s = data
            log.error('SERVER STDERR: %s', s.strip())
    except Exception as e:
        log.exception('stderr reader loop error: %s', e)

# server control

def _find_pyright_executable():
    # 1) environment override
    env_path = os.environ.get('PYRIGHT_SERVER')
    if env_path:
        return env_path
    # 2) look on PATH
    whiched = shutil.which('pyright-langserver') or shutil.which('pyright')
    if whiched:
        return whiched
    # 3) fallback to possible npm global location on Windows if present
    possible = os.path.expanduser(r"~/.node_modules_global/bin/pyright-langserver")
    if os.path.exists(possible):
        return possible
    # 4) original hard-coded path (kept as a last resort but not recommended)
    fallback = r'C:/Users/dell/AppData/Roaming/npm/pyright-langserver'
    if os.path.exists(fallback):
        return fallback
    return None


def _start_server():
    global _server_proc, _stdout_thread, _stderr_thread, _running
    if _server_proc is not None:
        return
    exe = _find_pyright_executable()
    if not exe:
        raise FileNotFoundError('pyright-langserver not found; set PYRIGHT_SERVER env var or install pyright')
    cmd = [exe, '--stdio']
    log.info('Starting language server: %s', cmd)
    print("STARTED!!!")
    _server_proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        bufsize=0
    )
    _running = True
    _stdout_thread = threading.Thread(target=_read_stdout_loop, args=(_server_proc.stdout,), daemon=True)
    _stderr_thread = threading.Thread(target=_read_stderr_loop, args=(_server_proc.stderr,), daemon=True)
    _stdout_thread.start()
    _stderr_thread.start()


def sendMessage(obj: dict):
    if _server_proc is None or _server_proc.stdin is None:
        raise RuntimeError('server not started')
    json_text = json.dumps(obj, separators=(',', ':'))
    content_bytes = json_text.encode('utf-8')
    content_length = len(content_bytes)
    header = f"Content-Length: {content_length}\r\n\r\n".encode('ascii')
    msg = header + content_bytes
    try:
        _server_proc.stdin.write(msg)
        _server_proc.stdin.flush()
    except Exception as e:
        log.exception('error writing to server stdin: %s', e)


def dispose():
    global _server_proc, _running
    if _server_proc is not None:
        try:
            _server_proc.terminate()
            try:
                _server_proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                _server_proc.kill()
        except Exception:
            pass
    _server_proc = None
    with state._response_cond:
        state.responseLog.clear()
    with state._lock:
        state.diagnosticsLog.clear()
        state.filesLog.clear()
    _running = False

# high-level LSP helpers (preserve behavior & JSON responses)

from typing import List, Dict, Optional, Tuple

def sort_completions(
    raw_items: List[Dict],
    prefix: str = "",
    limit: Optional[int] = None,
    case_sensitive: bool = False
) -> List[Dict]:
    """
    Sort LSP completion items to mimic editor behavior (VS Code / JetBrains-ish).
    - Primary: use item['sortText'] if present, else label fallback.
    - Grouping: public (no _), protected (_name), dunder (__name__).
    - Fuzzy boosts: strong boost if startswith(prefix), medium if contains prefix,
      weak subsequence boost if characters of prefix appear in order.
    - Stable: original order preserved when keys tie.
    Returns the sorted list of items (same dicts, new order).
    
    Parameters:
      raw_items: list of LSP completion item dicts (pyright-style)
      prefix: the text the user has typed before the cursor (used for fuzzy boosts)
      limit: optionally slice the top-N results
      case_sensitive: whether matching should be case-sensitive (default False)
    """
    if not raw_items:
        return []

    # small helpers
    def _label_of(it: Dict) -> str:
        # common fallbacks for label text
        return (
            it.get("label")
            or it.get("name")  # some servers
            or it.get("insertText")
            or ""
        )

    def _normalize(s: str) -> str:
        return s if case_sensitive else s.lower()

    norm_prefix = _normalize(prefix or "")

    def _group(label: str) -> int:
        # lower is better (public first)
        if label.startswith("__") and label.endswith("__") and len(label) > 4:
            return 2
        if label.startswith("_"):
            return 1
        return 0

    def _subsequence_score(needle: str, haystack: str) -> Optional[float]:
        # returns a score where lower is better; None if not a subsequence
        # score is average index of matched chars; earlier matches -> smaller score
        if not needle:
            return 0.0
        i = 0
        total_idx = 0
        for ch in needle:
            pos = haystack.find(ch, i)
            if pos == -1:
                return None
            total_idx += pos
            i = pos + 1
        return total_idx / len(needle)

    def fuzzy_boost(label: str, norm_label: str) -> int:
        # produce an integer where lower is better (more boost)
        if not norm_prefix:
            return 0
        # startswith -> strongest boost
        if norm_label.startswith(norm_prefix):
            return -1000
        # contains -> medium boost; earlier occurrence better
        pos = norm_label.find(norm_prefix)
        if pos != -1:
            return -500 + pos  # earlier pos slightly better
        # subsequence match -> smaller boost based on average positions
        subs = _subsequence_score(norm_prefix, norm_label)
        if subs is not None:
            # convert to integer; earlier average index => more negative
            # clamp so it doesn't outrank startswith/contains
            val = int(-250 + min(subs, 200))
            return val
        # no match -> neutral
        return 0

    # Build sort keys for each item (stable by original index)
    keyed: List[Tuple[Tuple, int, Dict]] = []
    for idx, item in enumerate(raw_items):
        label = _label_of(item)
        norm_label = _normalize(label)
        # primary sort text (prefer server-provided sortText)
        sort_text = _normalize(item.get("sortText") or label or "")
        grp = _group(label)
        boost = fuzzy_boost(label, norm_label)
        # final key: (fuzzy_boost, group, sort_text, label) -> ascending sort
        key = (boost, grp, sort_text, norm_label)
        keyed.append((key, idx, item))

    # sort using the computed tuple; Python's sort is stable so `idx` keeps original order when keys tie
    keyed.sort(key=lambda x: x[0] + (x[1],))  # append index as final tiebreaker

    sorted_items = [t[2] for t in keyed]
    if limit is not None:
        return sorted_items[:limit]
    return sorted_items


def handle_df_response(response: dict):
    # TODO: talk to ipython and load df inspection if loaded
    return response


def initializeRequest():
    _start_server()
    responseId_ = state.next_request_id()
    sendMessage({
        'jsonrpc': '2.0',
        'id': responseId_,
        'method': 'initialize',
        'params': {
            'processId': os.getpid(),
            'rootUri': pathToFileUri(config.projectRootPath),
            'capabilities': {
                'textDocument': {
                    'completion': { 'completionItem': { 'snippetSupport': False } },
                    'hover': { 'contentFormat': ['markdown', 'plaintext'] },
                    'signatureHelp': { 'signatureInformation': { 'parameterInformation': { 'labelOffsetSupport': False } } }
                },
                'workspace': { 'workspaceEdit': { 'documentChanges': True } }
            },
            'initializationOptions': {
                'basedpyright': {
                    'analysis': { 'diagnosticMode': 'workspace', 'autoImportCompletions': True }
                },
                'pythonPath': config.pythonPath
            }
        }
    })
    # wait for response using condition variable (no busy-wait)
    _ = state.pop_response(responseId_)
    initializedNotification()
    return {'status': 'initialized'}


def initializedNotification():
    sendMessage({
        'jsonrpc': '2.0',
        'method': 'initialized',
        'params': {}
    })


def openFileNotification(filePath, fileContent):
    fileURI = pathToFileUri(filePath)
    state.add_file(fileURI, fileContent, version=1)
    sendMessage({
        'jsonrpc': '2.0',
        'method': 'textDocument/didOpen',
        'params': {
            'textDocument': {
                'uri': fileURI,
                'languageId': 'python',
                'version': 1,
                'text': fileContent
            }
        }
    })
    return {'status': 'opened', 'uri': fileURI}


def changeFileNotification(filePath, fileContent):
    fileURI = pathToFileUri(filePath)
    latestVersion = state.change_file(fileURI, fileContent)
    sendMessage({
        'jsonrpc': '2.0',
        'method': 'textDocument/didChange',
        'params': {
            'textDocument': { 'uri': fileURI, 'version': latestVersion },
            'contentChanges': [{ 'text': fileContent }]
        }
    })
    return {'status': 'changed', 'uri': fileURI, 'version': latestVersion}


def completeRequest(filePath, line, character):
    fileURI = pathToFileUri(filePath)
    requestId_ = state.next_request_id()
    sendMessage({
        'jsonrpc': '2.0',
        'id': requestId_,
        'method': 'textDocument/completion',
        'params': {
            'textDocument': { 'uri': fileURI },
            'position': { 'line': line, 'character': character },
            'context': { 'triggerKind': 1 }
        }
    })
    resp = state.pop_response(requestId_)
    result = resp.get('result', {})
    raw_items = result.get('items', result)

    items = []
    for item in sort_completions(raw_items):
        items.append({
            "name": item.get("label", ""),
            "type": LSP_KIND.get(item.get("kind"), "Unknown")
        })
    return {"results": items}


def hoverRequest(filePath, line, character):
    fileURI = pathToFileUri(filePath)
    requestId_ = state.next_request_id()
    sendMessage({
        'jsonrpc': '2.0',
        'id': requestId_,
        'method': 'textDocument/hover',
        'params': {
            'textDocument': { 'uri': fileURI },
            'position': { 'line': line, 'character': character }
        }
    })
    response = state.pop_response(requestId_)
    print("TESTING", response)
    if "DataFrame" in response.get("result", {}).get("contents", {}).get("value", None):
        return handle_df_response(response)
    return response


def definitionRequest(filePath, line, character):
    fileURI = pathToFileUri(filePath)
    requestId_ = state.next_request_id()
    sendMessage({
        'jsonrpc': '2.0',
        'id': requestId_,
        'method': 'textDocument/definition',
        'params': {
            'textDocument': { 'uri': fileURI },
            'position': { 'line': line, 'character': character }
        }
    })
    return state.pop_response(requestId_)


def signatureRequest(filePath, line, character, timeout=2.0):
    fileURI = pathToFileUri(filePath)
    requestId_ = state.next_request_id()
    sendMessage({
        'jsonrpc': '2.0',
        'id': requestId_,
        'method': 'textDocument/signatureHelp',
        'params': {
            'textDocument': { 'uri': fileURI },
            'position': { 'line': line, 'character': character }
        }
    })
    resp = state.pop_response(requestId_, timeout=timeout)
    # resp is the raw LSP signatureHelp object; just return it
    return resp

# Flask endpoints

@app.route('/config/set_project_root', methods=['POST', 'OPTIONS'])
def set_project_root():
    if request.method == "OPTIONS":
        return jsonify({})
    data = request.get_json() or {}
    path = data.get('path', '')
    config.setProjectRootPath(path)
    return jsonify({'projectRootPath': config.projectRootPath})


@app.route('/config/set_python_path', methods=['POST', 'OPTIONS'])
def set_python_path():
    if request.method == "OPTIONS":
        return jsonify({})
    data = request.get_json() or {}
    path = data.get('path', '')
    config.setPythonPath(path)
    return jsonify({'pythonPath': config.pythonPath})


@app.route('/initialize', methods=['POST', 'OPTIONS'])
def http_initialize():
    if request.method == "OPTIONS":
        return jsonify({})
    try:
        res = initializeRequest()
        return jsonify(res)
    except Exception as e:
        log.exception('initialize failed')
        return jsonify({'error': str(e)}), 500


@app.route('/open_file', methods=['POST', 'OPTIONS'])
def http_open_file():
    if request.method == "OPTIONS":
        return jsonify({})
    data = request.get_json() or {}
    filePath = data.get('filePath')
    fileContent = data.get('fileContent')
    if not filePath:
        return jsonify({'error': 'filePath required'}), 400
    if not isinstance(fileContent, str):
        return jsonify({'error': 'fileContent required'}), 400
    try:
        res = openFileNotification(filePath, fileContent)
        return jsonify(res)
    except Exception as e:
        log.exception('open_file failed')
        return jsonify({'error': str(e)}), 500


@app.route('/change_file', methods=['POST', 'OPTIONS'])
def http_change_file():
    if request.method == "OPTIONS":
        return jsonify({})
    data = request.get_json() or {}
    filePath = data.get('filePath')
    fileContent = data.get('fileContent')
    if not filePath:
        return jsonify({'error': 'filePath required'}), 400
    if not isinstance(fileContent, str):
        return jsonify({'error': 'fileContent required'}), 400
    try:
        res = changeFileNotification(filePath, fileContent)
        return jsonify(res)
    except Exception as e:
        log.exception('change_file failed')
        return jsonify({'error': str(e)}), 500


@app.route('/complete', methods=['POST', 'OPTIONS'])
def http_complete():
    if request.method == "OPTIONS":
        return jsonify({})
    data = request.get_json() or {}
    filePath = data.get('filePath')
    line = data.get('line', 0)
    character = data.get('character', 0)
    if not filePath:
        return jsonify({'error': 'filePath required'}), 400
    try:
        res = completeRequest(filePath, line, character)
        return jsonify(res)
    except Exception as e:
        log.exception('complete failed')
        return jsonify({'error': str(e)}), 500


@app.route('/hover', methods=['POST', 'OPTIONS'])
def http_hover():
    if request.method == "OPTIONS":
        return jsonify({})
    data = request.get_json() or {}
    filePath = data.get('filePath')
    line = data.get('line', 0)
    character = data.get('character', 0)
    if not filePath:
        return jsonify({'error': 'filePath required'}), 400
    try:
        res = hoverRequest(filePath, line, character)
        return jsonify(res)
    except Exception as e:
        log.exception('hover failed')
        return jsonify({'error': str(e)}), 500


@app.route('/signature', methods=['POST', 'OPTIONS'])
def http_signature():
    print("TESTING")
    if request.method == "OPTIONS":
        return jsonify({})
    data = request.get_json() or {}
    filePath = data.get('filePath')
    line = data.get('line', 0)
    character = data.get('character', 0)
    if not filePath:
        return jsonify({'error': 'filePath required'}), 400
    try:
        res = signatureRequest(filePath, line, character)
        return jsonify(res)
    except Exception as e:
        log.exception('signature failed')
        return jsonify({'error': str(e)}), 500


@app.route('/definition', methods=['POST', 'OPTIONS'])
def http_definition():
    if request.method == "OPTIONS":
        return jsonify({})
    data = request.get_json() or {}
    filePath = data.get('filePath')
    line = data.get('line', 0)
    character = data.get('character', 0)
    if not filePath:
        return jsonify({'error': 'filePath required'}), 400
    try:
        res = definitionRequest(filePath, line, character)
        return jsonify(res)
    except Exception as e:
        log.exception('definition failed')
        return jsonify({'error': str(e)}), 500


@app.route('/dispose', methods=['POST', 'OPTIONS'])
def http_dispose():
    if request.method == "OPTIONS":
        return jsonify({})
    dispose()
    return jsonify({'status': 'disposed'})


@app.route('/diagnostics', methods=['GET', 'OPTIONS'])
def http_diagnostics():
    if request.method == "OPTIONS":
        return jsonify({})
    return jsonify(state.get_diagnostics_snapshot())


if __name__ == '__main__':
    # attempt initialization before starting Flask
    try:
        initializeRequest()
    except Exception as e:
        log.warning('initial initializeRequest failed: %s', e)
    port = int(os.environ.get('PORT', 5000)) # REFACTOR: pump port through env vars or fall back to 5000 | spin server with PORT in env
    try:
        app.run(host='localhost', port=port)
    finally:
        dispose()
