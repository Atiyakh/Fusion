// Editor.jsx
import { useEffect, useRef, useCallback, forwardRef, useImperativeHandle } from 'react';
import { CodeiumEditor } from '@codeium/react-code-editor';
import styles from '../NotebookCell/NotebookCell.module.css';
import lspClient from './lspClient.js';

// helpers
function mapTypeToMonacoKind(monaco, typeStr) {
  if (!monaco || !typeStr) return monaco?.languages?.CompletionItemKind?.Text || 0;
  const t = typeStr.toLowerCase();
  const K = monaco.languages.CompletionItemKind;
  if (t.includes('function') || t.includes('method')) return K.Function || K.Method || K.Text;
  if (t.includes('variable') || t.includes('field') || t.includes('constant')) return K.Variable || K.Field || K.Text;
  if (t.includes('class')) return K.Class || K.Struct || K.Text;
  if (t.includes('module') || t.includes('package')) return K.Module || K.File || K.Text;
  if (t.includes('property')) return K.Property || K.Field || K.Text;
  if (t.includes('enum')) return K.Enum || K.Text;
  if (t.includes('interface')) return K.Interface || K.Text;
  return K.Text;
}

// --- improved signature help provider (paste in registerLanguageProvidersSingleton) ---
const lastSignatureByUri = new Map(); // uri -> { result, openOffset, timestamp }

/**
 * Helpers: offset/position conversions
 */

const lastHoverByUri = new Map();

function posToOffset(model, position) {
  return model.getOffsetAt(position);
}
function offsetToPos(model, offset) {
  return model.getPositionAt(offset);
}

/**
 * Find the offset of the unmatched '(' that starts the call nearest before `cursorOffset`.
 * Attempts to ignore parentheses inside strings and nested parens.
 * Returns the offset of '(' or null if not found.
 */
function findCallOpenOffset(model, cursorOffset) {
  const text = model.getValue();
  let depth = 0;
  let inString = null;
  let escapeNext = false;

  for (let i = cursorOffset - 1; i >= 0; i--) {
    const ch = text[i];

    if (escapeNext) {
      escapeNext = false;
      continue;
    }

    if (inString) {
      if (ch === '\\') {
        escapeNext = true;
        continue;
      }
      // naive string close detection: match quote type
      if (ch === inString) {
        inString = null;
      }
      continue;
    }

    if (ch === '"' || ch === "'") {
      // enter string
      inString = ch;
      continue;
    }

    if (ch === ')') {
      depth += 1;
      continue;
    }
    if (ch === '(') {
      if (depth === 0) {
        return i;
      } else {
        depth -= 1;
        continue;
      }
    }

    // ignore other chars
  }
  return null;
}

/**
 * Determine whether the call that starts at openOffset has a matching closing ')' BEFORE cursorOffset.
 * If yes, the call is already closed (so we should hide hints).
 */
function isCallClosedBeforeCursor(model, openOffset, cursorOffset) {
  const text = model.getValue();
  let depth = 0;
  let inString = null;
  let escapeNext = false;

  for (let i = openOffset + 1; i < Math.min(text.length, cursorOffset); i++) {
    const ch = text[i];
    if (escapeNext) {
      escapeNext = false;
      continue;
    }
    if (inString) {
      if (ch === '\\') {
        escapeNext = true;
        continue;
      }
      if (ch === inString) {
        inString = null;
      }
      continue;
    }
    if (ch === '"' || ch === "'") {
      inString = ch;
      continue;
    }
    if (ch === '(') {
      depth += 1;
      continue;
    }
    if (ch === ')') {
      if (depth === 0) {
        // found the matching close for the openOffset before cursor
        return true;
      } else {
        depth -= 1;
      }
    }
  }
  return false;
}

/**
 * Count top-level commas between openOffset+1 and cursorOffset to get active parameter index.
 * Ignores commas inside nested parentheses or strings.
 */
function countTopLevelCommas(model, openOffset, cursorOffset) {
  const text = model.getValue();
  let depth = 0;
  let inString = null;
  let escapeNext = false;
  let commas = 0;

  for (let i = openOffset + 1; i < cursorOffset; i++) {
    const ch = text[i];
    if (escapeNext) {
      escapeNext = false;
      continue;
    }
    if (inString) {
      if (ch === '\\') {
        escapeNext = true;
      } else if (ch === inString) {
        inString = null;
      }
      continue;
    }
    if (ch === '"' || ch === "'") {
      inString = ch;
      continue;
    }
    if (ch === '(') {
      depth += 1;
      continue;
    }
    if (ch === ')') {
      if (depth > 0) depth -= 1;
      continue;
    }
    if (ch === ',' && depth === 0) {
      commas += 1;
      continue;
    }
  }
  return commas;
}

/**
 * Build a sanitized Monaco SignatureHelp using LSP `result`.
 * Also tries to compute activeParameter from local parsing if result doesn't provide it.
 */
async function buildSignatureHelp(monaco, model, position, lspResult, openOffset) {
  const result = lspResult || {};
  const rawSignatures = Array.isArray(result.signatures) ? result.signatures : [];
  const signatures = rawSignatures.map((s) => {
    const params = (s.parameters || []).map((p) => {
      const label = (typeof p.label === 'string')
        ? p.label
        : (Array.isArray(p.label) ? `${p.label[0]},${p.label[1]}` : String(p.label));
      return { label, documentation: p.documentation || '' };
    });
    return {
      label: s.label || (typeof s.documentation === 'string' ? s.documentation : (s.documentation && s.documentation.value) || ''),
      documentation: s.documentation || '',
      parameters: params,
    };
  });

  // Compute activeParam: prefer LSP-provided, fall back to local comma-count heuristic
  let activeParameter = (typeof result.activeParameter === 'number') ? result.activeParameter : null;
  if (activeParameter === null && openOffset !== null) {
    try {
      const cursorOffset = posToOffset(model, position);
      activeParameter = countTopLevelCommas(model, openOffset, cursorOffset);
    } catch (e) {
      activeParameter = 0;
    }
  }
  if (activeParameter === null) activeParameter = 0;

  // clamp
  const activeSignature = Math.min(Math.max(typeof result.activeSignature === 'number' ? result.activeSignature : 0, 0), Math.max(0, signatures.length - 1));
  const sig = signatures[activeSignature] || { label: '', parameters: [] };
  const paramCount = sig.parameters ? sig.parameters.length : 0;
  const activeParameterClamped = Math.min(Math.max(activeParameter, 0), Math.max(0, paramCount - 1));

  return {
    value: {
      signatures,
      activeSignature,
      activeParameter: activeParameterClamped,
    },
    dispose: () => {}
  };
}

function diagnosticsToMarkers(monaco, diagnosticsArray) {
  const byUri = new Map();
  if (!Array.isArray(diagnosticsArray)) return byUri;

  for (const entry of diagnosticsArray) {
    try {
      const params = entry.params || {};
      const uri = params.uri;
      const diagnostics = params.diagnostics || [];
      if (!uri) continue;

      const markers = diagnostics.map((d) => {
        const r = d.range || {};
        const start = r.start || {};
        const end = r.end || {};

        const severity = (d.severity === 1)
          ? monaco.MarkerSeverity.Error
          : (d.severity === 2)
            ? monaco.MarkerSeverity.Warning
            : (d.severity === 3)
              ? monaco.MarkerSeverity.Info
              : monaco.MarkerSeverity.Hint;

        return {
          severity,
          message: d.message || String(d),
          startLineNumber: (typeof start.line === 'number' ? start.line : 0) + 1,
          startColumn: (typeof start.character === 'number' ? start.character : 0) + 1,
          endLineNumber: (typeof end.line === 'number' ? end.line : 0) + 1,
          endColumn: (typeof end.character === 'number' ? end.character : 0) + 1,
          code: d.code,
          source: d.source || 'pyright',
        };
      });

      byUri.set(uri, markers);
    } catch (e) {
      // ignore parse errors per entry
      // eslint-disable-next-line no-console
      console.warn('Failed to parse diagnostic entry', e, entry);
    }
  }

  return byUri;
}

function normalizeToFileUri(uriOrPath) {
  if (!uriOrPath) return uriOrPath;
  if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(uriOrPath)) return uriOrPath;
  if (/^[A-Za-z]:\\|^\\\\/.test(uriOrPath)) {
    return 'file:///' + uriOrPath.replace(/\\/g, '/');
  }
  return 'file://' + uriOrPath;
}

// global provider singleton per monaco
/**
 * Use a WeakMap keyed by the monaco object so different monaco instances
 * (if any) get distinct provider sets. Each entry contains a refCount so
 * multiple Cells can "acquire" the same set and "release" it on unmount.
 */
const monacoProvidersMap = new WeakMap();

function registerLanguageProvidersSingleton(monaco) {
  if (!monaco) return null;

  // return existing + bump refCount
  const existing = monacoProvidersMap.get(monaco);
  if (existing) {
    existing.refCount += 1;
    return existing;
  }

  // create new provider set
  let diagnosticsTimer = null;
  let diagnosticsStopped = false;

  // Poll diagnostics and set markers on models
  async function pollDiagnosticsOnce() {
    try {
      const snapshot = await lspClient.diagnostics();
      const byUri = diagnosticsToMarkers(monaco, snapshot);
      const models = monaco.editor.getModels();
      for (const model of models) {
        try {
          const uri = model.uri.toString();
          const markers = byUri.get(uri) || [];
          monaco.editor.setModelMarkers(model, 'pyright', markers);
        } catch (e) {
          // eslint-disable-next-line no-console
          console.warn('Failed to set model markers', e);
        }
      }
    } catch (e) {
      // eslint-disable-next-line no-console
      console.debug('diagnostics poll failed', e);
    }
  }

  function startDiagnosticsLoop() {
    diagnosticsStopped = false;
    async function loop() {
      if (diagnosticsStopped) return;
      await pollDiagnosticsOnce();
      if (diagnosticsStopped) return;
      diagnosticsTimer = setTimeout(loop, 1500);
    }
    loop();
    return () => {
      diagnosticsStopped = true;
      if (diagnosticsTimer) {
        clearTimeout(diagnosticsTimer);
        diagnosticsTimer = null;
      }
    };
  }

  // Helper to get file identifier for lspClient from the model
  const modelToFileId = (model) => {
    try {
      // prefer model.uri.toString() which is a file://... URI; lspClient should accept it
      return model && model.uri ? model.uri.toString() : undefined;
    } catch (_) {
      return undefined;
    }
  };

  // providers use model.uri at runtime (no stale closures)
  const completionDisposable = monaco.languages.registerCompletionItemProvider('python', {
    triggerCharacters: ['.', '['],
    provideCompletionItems: async (model, position) => {
      try {
        const fileId = modelToFileId(model);
        const line0 = position.lineNumber - 1;
        const col0 = position.column - 1;
        const content = model.getValue();
        try {
          await lspClient.ensureOpenAndSync(fileId, content);
        } catch (syncErr) {
          // eslint-disable-next-line no-console
          console.error('ensureOpenAndSync failed (completion)', syncErr);
        }
        const results = await lspClient.complete(fileId, line0, col0);
        const suggestions = (Array.isArray(results) ? results : []).map((item) => ({
          label: item.name,
          kind: mapTypeToMonacoKind(monaco, item.type),
          documentation: item.description || '',
          insertText: item.name,
          range: undefined,
        }));
        return { suggestions };
      } catch (e) {
        // eslint-disable-next-line no-console
        console.error('completion provider failed', e);
        return { suggestions: [] };
      }
    },
  });

  const hoverDisposable = monaco.languages.registerHoverProvider('python', {
    // signature: (model, position, token)
    provideHover: async (model, position, token) => {
      try {
        const fileId = modelToFileId(model);
        const line0 = position.lineNumber - 1;
        const col0 = position.column - 1;
        const content = model.getValue();

        // fire-and-forget sync so hover isn't blocked by ensureOpenAndSync
        lspClient.ensureOpenAndSync(fileId, content).catch((err) => {
          // eslint-disable-next-line no-console
          console.debug('ensureOpenAndSync (hover) failed (non-blocking)', err);
        });

        // compute a tight anchor range (word under cursor) to avoid the popup losing its anchor
        let range;
        try {
          const word = model.getWordAtPosition(position);
          if (word && word.startColumn && word.endColumn) {
            range = new monaco.Range(position.lineNumber, word.startColumn, position.lineNumber, word.endColumn);
          } else {
            // fallback: use the single character at cursor
            range = new monaco.Range(position.lineNumber, position.column, position.lineNumber, position.column);
          }
        } catch (e) {
          range = undefined;
        }

        // quick-return cached hover if position/uri matches and cache is recent
        const cacheKey = `${fileId}:${posToOffset(model, position)}`;
        const cached = lastHoverByUri.get(cacheKey);
        if (cached && (Date.now() - cached.ts) < 250) {
          return { contents: cached.contents, range };
        }

        // call server for hover info
        let resp;
        try {
          resp = await lspClient.hover(fileId, line0, col0);
        } catch (e) {
          // server failed — avoid returning nothing; use cached or empty
          if (cached) return { contents: cached.contents, range };
          return { contents: [], range };
        }

        // bail if the request was cancelled while awaiting server
        if (token && token.isCancellationRequested && typeof token.isCancellationRequested === 'boolean' && token.isCancellationRequested) {
          return { contents: [], range };
        }

        const result = resp && (resp.result || resp);
        const rawContents = result ? result.contents || result : [];

        // normalize helper -> returns array of { value: string } (Monaco accepts objects with `value`)
        function normalizeContents(contents) {
          if (!contents) return [];
          // handle array / single string / object
          if (typeof contents === 'string') return [{ value: contents }];
          if (Array.isArray(contents)) {
            return contents.flatMap((c) => normalizeContents(c));
          }
          if (typeof contents === 'object') {
            // common LSP variants: { value }, { language, value }, MarkedString, etc.
            if (typeof contents.value === 'string') return [{ value: contents.value }];
            if (typeof contents.markup === 'string') return [{ value: contents.markup }];
            if (contents.language && contents.value) {
              return [{ value: '```' + (contents.language || '') + '\n' + contents.value + '\n```' }];
            }
            // fallback
            return [{ value: JSON.stringify(contents) }];
          }
          return [{ value: String(contents) }];
        }

        const markdownStrings = normalizeContents(rawContents);

        // cache small-window
        lastHoverByUri.set(cacheKey, { ts: Date.now(), contents: markdownStrings });

        return { contents: markdownStrings, range };
      } catch (e) {
        // eslint-disable-next-line no-console
        console.debug('hover failed', e);
        return { contents: [], range: undefined };
      }
    },
  });

  const defDisposable = monaco.languages.registerDefinitionProvider('python', {
    provideDefinition: async (model, position) => {
      try {
        const fileId = modelToFileId(model);
        const line0 = position.lineNumber - 1;
        const col0 = position.column - 1;
        const content = model.getValue();
        try {
          await lspClient.ensureOpenAndSync(fileId, content);
        } catch (syncErr) {
          // eslint-disable-next-line no-console
          console.error('ensureOpenAndSync failed (definition)', syncErr);
        }
        const resp = await lspClient.definition(fileId, line0, col0);
        const result = resp.result || resp;
        const locs = Array.isArray(result) ? result : (result ? [result] : []);
        const monacoLocs = locs.map((loc) => {
          const rawUri = loc.uri || loc.targetUri || loc.target || '';
          const uriStr = normalizeToFileUri(rawUri);
          const range = loc.range || loc.targetSelectionRange || loc.targetRange || {};
          const start = range.start || {};
          const end = range.end || {};
          try {
            return {
              uri: monaco.Uri.parse(uriStr),
              range: new monaco.Range(
                (typeof start.line === 'number' ? start.line : 0) + 1,
                (typeof start.character === 'number' ? start.character : 0) + 1,
                (typeof end.line === 'number' ? end.line : 0) + 1,
                (typeof end.character === 'number' ? end.character : 0) + 1
              ),
            };
          } catch (e) {
            // eslint-disable-next-line no-console
            console.warn('Invalid definition URI/range from server', uriStr, e);
            return null;
          }
        }).filter(Boolean);
        return monacoLocs;
      } catch (e) {
        // eslint-disable-next-line no-console
        console.debug('definition failed', e);
        return [];
      }
    },
  });

  const signatureDisposable = monaco.languages.registerSignatureHelpProvider('python', {
    signatureHelpTriggerCharacters: ['(', ','],
    signatureHelpRetriggerCharacters: [')', ','],
    provideSignatureHelp: async (model, position, token, context) => {
      try {
        const fileId = modelToFileId(model);
        if (!fileId) {
          return { value: { signatures: [], activeSignature: 0, activeParameter: 0 }, dispose: () => {} };
        }

        const cursorOffset = posToOffset(model, position);
        const openOffset = findCallOpenOffset(model, cursorOffset);
        // if no open paren found, bail
        if (openOffset === null) {
          return { value: { signatures: [], activeSignature: 0, activeParameter: 0 }, dispose: () => {} };
        }

        // if call is already closed before the cursor, hide the hints (user finished)
        if (isCallClosedBeforeCursor(model, openOffset, cursorOffset)) {
          return { value: { signatures: [], activeSignature: 0, activeParameter: 0 }, dispose: () => {} };
        }

        // Use cache to reduce flicker on quick typing (only reuse if same openOffset)
        const cacheKey = fileId;
        const cached = lastSignatureByUri.get(cacheKey);
        const now = Date.now();

        // ensure server has latest content (best-effort)
        try { await lspClient.ensureOpenAndSync(fileId, model.getValue()); } catch (_) {}

        // Decide whether to call server:
        // - call server on initial trigger (no cache) OR if cache is stale (>1s) OR openOffset changed
        const shouldCallServer = !cached || (cached.openOffset !== openOffset) || (now - (cached.timestamp || 0) > 1000);

        let lspResult = null;
        if (shouldCallServer) {
          try {
            const resp = await lspClient.signature(fileId, position.lineNumber - 1, position.column - 1);
            // backend returns either { result: {...} } or {...}
            lspResult = resp && (resp.result || resp);
          } catch (e) {
            // network/server failure: fall back to cached or local heuristic
            lspResult = null;
          }
          // update cache (even if lspResult is null we update timestamp so we don't hammer)
          lastSignatureByUri.set(cacheKey, { result: lspResult, openOffset, timestamp: Date.now() });
        } else {
          lspResult = cached ? cached.result : null;
        }

        // build a Monaco-friendly signatureHelp (will use local comma-count if needed)
        const sigHelp = await buildSignatureHelp(monaco, model, position, lspResult, openOffset);
        return sigHelp;
      } catch (e) {
        console.error('signature provider failed', e);
        return { value: { signatures: [], activeSignature: 0, activeParameter: 0 }, dispose: () => {} };
      }
    }
  });

  // Start diagnostics loop once for this monaco instance
  const stopDiagnostics = startDiagnosticsLoop();

  const record = {
    completionDisposable,
    hoverDisposable,
    defDisposable,
    stopDiagnostics,
    refCount: 1,
    disposeAll: () => {
      try { completionDisposable && completionDisposable.dispose(); } catch (_) {}
      try { hoverDisposable && hoverDisposable.dispose(); } catch (_) {}
      try { defDisposable && defDisposable.dispose(); } catch (_) {}
      try { signatureDisposable && signatureDisposable.dispose(); } catch (_) {}
      try { stopDiagnostics && stopDiagnostics(); } catch (_) {}
    },
    acquire: function () {
      this.refCount += 1;
    },
    release: function () {
      this.refCount = Math.max(0, this.refCount - 1);
      if (this.refCount === 0) {
        this.disposeAll();
        monacoProvidersMap.delete(monaco);
      }
    }
  };

  monacoProvidersMap.set(monaco, record);
  return record;
}

// Editor component
export default forwardRef(function Editor({
  ParentNotebookFile = '/tmp/example.py',
  initialValue = 'Test', // NOTE:DEPRECATED, remove when stable
  minHeight = 16,
  maxHeight = 10000,
  debounceMs = 200,
  onWidthChange = () => {},
}, cellRef) {
  // refs
  const monacoRef = useRef(null);
  const editorRef = useRef(null);
  const modelRef = useRef(null);
  const providersInstanceRef = useRef(null); // holds the singleton record for this monaco
  const disposerRef = useRef(null);
  const diagnosticsTimerRef = useRef(null); // fallback, not used when singleton active
  const mountedRef = useRef(false);
  const debouncedChangeRef = useRef(null);
  const wrapperRef = useRef(null);
  const resizeObserverRef = useRef(null);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  useEffect(() => {
    try {
      debouncedChangeRef.current = lspClient.changeFileDebounced(Number(debounceMs) || undefined);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('Failed to get debounced change function', err);
      debouncedChangeRef.current = null;
    }
  }, [debounceMs]);

  const getEditorDom = useCallback((editor) => {
    if (!editor) return null;
    return (typeof editor.getDomNode === 'function')
      ? editor.getDomNode()
      : (typeof editor.getContainerDomNode === 'function')
        ? editor.getContainerDomNode()
        : null;
  }, []);

  const computeContentHeight = useCallback((editor, monaco) => {
    try {
      if (typeof editor.getContentHeight === 'function') {
        const h = editor.getContentHeight();
        if (typeof h === 'number' && Number.isFinite(h) && h > 0) return Math.ceil(h);
      }
    } catch (e) { /* fallthrough */ }

    try {
      if (typeof editor.getScrollHeight === 'function') {
        const s = editor.getScrollHeight();
        if (typeof s === 'number' && Number.isFinite(s) && s > 0) return Math.ceil(s);
      }
    } catch (e) { /* fallthrough */ }

    try {
      const model = editor.getModel && editor.getModel();
      const lines = model ? model.getLineCount() : 1;
      try {
        const EditorOption = monaco?.editor?.EditorOption;
        if (EditorOption) {
          const maybe = editor.getOption ? editor.getOption(EditorOption.lineHeight) : undefined;
          const lineHeightVal = (typeof maybe === 'number' && maybe > 0) ? maybe : 18;
          return Math.ceil(lines * lineHeightVal);
        }
      } catch (e) { /* ignore */ }
      return Math.ceil(lines * 18);
    } catch (e) {
      return minHeight;
    }
  }, [minHeight]);

  const doUpdateHeight = useCallback(() => {
    const editor = editorRef.current;
    const wrapper = wrapperRef.current;
    const monaco = monacoRef.current;
    if (!editor || !wrapper) return;

    const rawHeight = computeContentHeight(editor, monaco);
    const clamped = Math.max(minHeight, Math.min(maxHeight, Math.ceil(rawHeight)));

    wrapper.style.height = `${clamped}px`;
    const editorDom = getEditorDom(editor);
    if (editorDom) editorDom.style.height = `${clamped}px`;

    requestAnimationFrame(() => {
      try {
        const widthPx = (wrapper.clientWidth || (editorDom && editorDom.clientWidth) || 0);
        onWidthChange(widthPx);
        if (typeof editor.layout === 'function') {
          editor.layout({ width: widthPx, height: clamped });
        } else if (typeof editor.layout === 'function') {
          editor.layout();
        }
      } catch (e) {
        // eslint-disable-next-line no-console
        console.debug('editor.layout failed', e);
      }
    });
  }, [computeContentHeight, getEditorDom, minHeight, maxHeight]);

  const handleEditorMount = useCallback((editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;

    // Create/get model using unique file URI for this cell
    const uriStr = ParentNotebookFile.startsWith('file://') ? ParentNotebookFile : normalizeToFileUri(ParentNotebookFile);
    const uri = monaco.Uri.parse(uriStr);
    let model = monaco.editor.getModel(uri);
    if (!model) {
      model = monaco.editor.createModel(initialValue, 'python', uri);
    }
    modelRef.current = model;

    // Initial open/sync
    lspClient.ensureOpenAndSync(uri.toString(), model.getValue()).catch((err) => {
      // eslint-disable-next-line no-console
      console.error('initial open/sync failed', err);
    });

    // wire change listener for LSP
    const disposable = model.onDidChangeContent(() => {
      const content = model.getValue();
      const debounced = debouncedChangeRef.current;
      if (typeof debounced === 'function') {
        try {
          debounced(uri.toString(), content);
        } catch (e) {
          // eslint-disable-next-line no-console
          console.error('debounced change invoke failed', e);
        }
      } else {
        lspClient.changeFile(uri.toString(), content).catch((e) => {
          // eslint-disable-next-line no-console
          console.error('changeFile failed', e);
        });
      }
      doUpdateHeight();
    });

    disposerRef.current = () => {
      try { disposable.dispose(); } catch (_) {}
    };

    // Acquire/register shared language providers + diagnostics for this monaco instance
    try {
      const providersRecord = registerLanguageProvidersSingleton(monaco);
      providersInstanceRef.current = providersRecord;
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('registerLanguageProviders failed', e);
    }

    // configure editor options
    editor.updateOptions({
      minimap: { enabled: false },
      parameterHints: { enabled: true },
      hover: { enabled: true, delay: 300 },
      scrollbar: { vertical: 'hidden', alwaysConsumeMouseWheel: false },
      scrollBeyondLastLine: false,
      wordWrap: 'off',
      lineNumbersMinChars: 2,
      automaticLayout: false,
      padding: { bottom: 6, top: 6 },
    });

    // content-size change subscription (if available)
    let sizeDisposable = null;
    try {
      if (typeof editor.onDidContentSizeChange === 'function') {
        sizeDisposable = editor.onDidContentSizeChange(() => {
          doUpdateHeight();
        });
      }
    } catch (e) {
      // eslint-disable-next-line no-console
      console.debug('onDidContentSizeChange not supported', e);
    }

    // initial layout after mount
    setTimeout(() => doUpdateHeight(), 0);

    // resize observer to watch wrapper width
    try {
      if (wrapperRef.current && typeof ResizeObserver !== 'undefined') {
        resizeObserverRef.current = new ResizeObserver(() => {
          doUpdateHeight();
        });
        resizeObserverRef.current.observe(wrapperRef.current);
      }
    } catch (e) {
      // ignore
    }

    // cleanup for this mount
    return () => {
      try { sizeDisposable && sizeDisposable.dispose(); } catch (_) {}
      try { if (disposerRef.current) disposerRef.current(); } catch (_) {}
      try { if (resizeObserverRef.current) { resizeObserverRef.current.disconnect(); resizeObserverRef.current = null; } } catch (_) {}

      // release the shared providers instance (decrement refCount and maybe dispose)
      try {
        if (providersInstanceRef.current && typeof providersInstanceRef.current.release === 'function') {
          providersInstanceRef.current.release();
          providersInstanceRef.current = null;
        }
      } catch (_) {}

      // clear markers for our model only (safer)
      try {
        const mon = monacoRef.current;
        const m = modelRef.current;
        if (mon && m) {
          mon.editor.setModelMarkers(m, 'pyright', []);
        }
      } catch (_) {}
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ParentNotebookFile, initialValue, doUpdateHeight]);

  // handle forwarded ref
  useImperativeHandle(cellRef, () => ({
    focus: () => editorRef.current?.focus()
  }));

  // cleanup on unmount
  useEffect(() => {
    return () => {
      try { if (disposerRef.current) disposerRef.current(); } catch (_) {}
      try {
        if (providersInstanceRef.current && typeof providersInstanceRef.current.release === 'function') {
          providersInstanceRef.current.release();
          providersInstanceRef.current = null;
        }
      } catch (_) {}
      try {
        const monaco = monacoRef.current;
        const m = modelRef.current;
        if (monaco && m) {
          monaco.editor.setModelMarkers(m, 'pyright', []);
        }
      } catch (_) {}
      try { if (resizeObserverRef.current) { resizeObserverRef.current.disconnect(); resizeObserverRef.current = null; } } catch (_) {}
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  // render
  return (
    <div
      className={styles.cellEditorWrapper}
      ref={wrapperRef}
    >
      <CodeiumEditor
        className="editor"
        language="python"
        height="18px"
        theme={"customTheme"}
        defaultValue={initialValue}
        beforeMount={(monaco) => {
          // define custom theme
          monaco.editor.defineTheme('customTheme', {
            base: 'vs',
            inherit: true,
            rules: [
                { token: 'comment', foreground: '#69707D' },       // adjusted
                { token: 'keyword', foreground: '#2874A3', fontStyle: 'bold' }, // adjusted
                { token: 'string', foreground: '#1b6643ff' },
                { token: 'number', foreground: '#B45309' },
                { token: 'type', foreground: '#7C3AED' },
                { token: 'variable', foreground: '#7C3AED' }, // consider changing to avoid same color as type
                { token: 'identifier', foreground: '#1F2937' },
                { token: 'function', foreground: '#0B5EA6' }
            ],
            colors: {
                'editor.background': '#F8F8F8',
                // REFACTOR 'editor.foldBackground': '#90b7de',
                'editor.foreground': '#0F1722',
                'editorLineNumber.foreground': '#7B8794',
                'editorCursor.foreground': '#0F1722',
                'editor.selectionBackground': '#4EA8DE2E',
                'editor.inactiveSelectionBackground': '#4EA8DE12',
                'editor.lineHighlightBackground': '#4EA8DE0F',
                'editorIndentGuide.background': '#E6EEF6',
            }
          });
          monaco.editor.setTheme('customTheme');
        }}
        onMount={(editor, monaco) => {
          const disposer = handleEditorMount(editor, monaco);
          return disposer;
        }}
        style={{ height: '100%' }}
        options={{
          fontSize: 16,
          automaticLayout: true,
          minimap: { enabled: false },
          // REFACTOR folding: true,               // hides the folding arrows
          // REFACTOR foldingHighlight: true,
          glyphMargin: false,           // hides the gutter margin (used for breakpoints/markers)
          lineHeight: 18,
          renderLineHighlight: 'none',
          lineNumbers: "off",
          suggestOnTriggerCharacters: true,
          quickSuggestions: true,
          scrollBeyondLastLine: false,
          overflow: "visible",
          scrollbar: { vertical: 'hidden', horizontal: 'hidden' },
          overviewRulerLanes: 0,
        }}
      />
    </div>
  );
});
