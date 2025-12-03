// lspClient.js
// LSP client wrapper for the Flask microservice.

import axios from 'axios';

/**
 * @typedef {Object} LspClientOptions
 * @property {string} [baseUrl] - Base URL of the Flask LSP server (default: http://localhost:5000)
 * @property {(msg: string, ...args: any[]) => void} [logger] - Optional logger
 * @property {number} [defaultDebounceMs] - Default debounce ms for typing updates (default: 250)
 */

class LspClient {
  constructor(opts = {}) {
    const { baseUrl = 'http://localhost:5000', logger = console, defaultDebounceMs = 250 } = opts;

    if (typeof baseUrl !== 'string') throw new TypeError('baseUrl must be a string');

    this.baseUrl = baseUrl.replace(/\/+$/, ''); // normalize no trailing slash
    this._logger = logger;
    this._defaultDebounceMs = Number(defaultDebounceMs) || 250;

    this._openedFiles = new Map();
    this._inflight = new Map();
    this._debouncers = new Map();

    // bind public methods
    this.openFile = this.openFile.bind(this);
    this.changeFile = this.changeFile.bind(this);
    this.changeFileDebounced = this.changeFileDebounced.bind(this);
    this.complete = this.complete.bind(this);
    this.hover = this.hover.bind(this);
    this.definition = this.definition.bind(this);
    this.signature = this.signature.bind(this);
    this.diagnostics = this.diagnostics.bind(this);
    this.ensureOpenAndSync = this.ensureOpenAndSync.bind(this);
    this.getOpenedFiles = this.getOpenedFiles.bind(this);
  }

  // Internal helpers
  _url(path) {
    if (!path.startsWith('/')) path = '/' + path;
    return this.baseUrl + path;
  }

  async _jsonRequest(path, opts = {}) {
    const url = this._url(path);
    const config = {
      url,
      method: opts.method || 'GET',
      headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
      data: opts.body || undefined,
    };

    try {
      const res = await axios(config);
      return res.data || {};
    } catch (err) {
      let message = err.message || 'Unknown error';
      if (err.response) {
        message = `Server error ${err.response.status}: ${JSON.stringify(err.response.data)}`;
        const e = new Error(message);
        e.status = err.response.status;
        throw e;
      } else {
        throw new Error(`Network error: ${message}`);
      }
    }
  }

  _validateFileArgs(filePath, fileContent) {
    if (typeof filePath !== 'string' || !filePath) throw new TypeError('filePath must be a non-empty string');
    if (typeof fileContent !== 'string') throw new TypeError('fileContent must be a string');
  }

  _getDebouncedChangeFn(delayMs) {
    const key = Number(delayMs) || this._defaultDebounceMs;
    if (this._debouncers.has(key)) return this._debouncers.get(key);

    let timer = null;
    const fn = (filePath, fileContent) => {
      this.changeFile(filePath, fileContent).catch((err) => this._logger.error('debounced changeFile failed', err));
    };

    const debounced = (filePath, fileContent) => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => {
        timer = null;
        fn(filePath, fileContent);
      }, key);
    };

    this._debouncers.set(key, debounced);
    return debounced;
  }

  // Public API
  async openFile(filePath, fileContent) {
    this._validateFileArgs(filePath, fileContent);
    const res = await this._jsonRequest('/open_file', {
      method: 'POST',
      body: { filePath, fileContent },
    });

    const prev = this._openedFiles.get(filePath) || { version: 0 };
    this._openedFiles.set(filePath, { ...prev, version: 1, uri: res.uri });
    return res;
  }

  async changeFile(filePath, fileContent) {
    this._validateFileArgs(filePath, fileContent);
    const res = await this._jsonRequest('/change_file', {
      method: 'POST',
      body: { filePath, fileContent },
    });

    const prev = this._openedFiles.get(filePath) || { version: 0 };
    this._openedFiles.set(filePath, { ...prev, version: res.version || prev.version + 1, uri: res.uri || prev.uri });
    return res;
  }

  changeFileDebounced(delayMs) {
    return this._getDebouncedChangeFn(delayMs);
  }

  async complete(filePath, line, character) {
    if (typeof filePath !== 'string') throw new TypeError('filePath must be a string');
    const body = { filePath, line: Number(line), character: Number(character) };
    const res = await this._jsonRequest('/complete', { method: 'POST', body });
    return Array.isArray(res.results) ? res.results : [];
  }

  async hover(filePath, line, character) {
    const body = { filePath, line: Number(line), character: Number(character) };
    return this._jsonRequest('/hover', { method: 'POST', body });
  }

  async definition(filePath, line, character) {
    const body = { filePath, line: Number(line), character: Number(character) };
    return this._jsonRequest('/definition', { method: 'POST', body });
  }

  async signature(filePath, line, character) {
    const body = {filePath, line: Number(line), character: Number(character) };
    return this._jsonRequest('/signature', { method: 'POST', body });
  }


  async diagnostics() {
    return this._jsonRequest('/diagnostics', { method: 'GET' });
  }

  async ensureOpenAndSync(filePath, fileContent) {
    this._validateFileArgs(filePath, fileContent);

    const key = filePath;
    if (this._inflight.has(key)) return this._inflight.get(key);

    const p = (async () => {
      if (!this._openedFiles.has(filePath)) {
        await this.openFile(filePath, fileContent);
      } else {
        await this.changeFile(filePath, fileContent);
      }
    })();

    this._inflight.set(key, p);
    p.finally(() => this._inflight.delete(key)).catch(() => {});
    return p;
  }

  getOpenedFiles() {
    return new Map(this._openedFiles);
  }
}

// unified connection to all editor instances
export default new LspClient({
  baseUrl: 'http://localhost:5000/',
  defaultDebounceMs: 200,
});
