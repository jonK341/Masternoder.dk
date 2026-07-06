'use strict';

// IPC handler registration + owner API client. Shared by the app entrypoint
// (main.js) and the headless smoke test so both exercise the same wiring.
// The admin key lives only in the main process and is injected here.

const { ipcMain, safeStorage } = require('electron');
const http = require('http');
const https = require('https');
const { URL } = require('url');
const store = require('./store');
const daemon = require('./daemon');

const ADMIN_KEY_HEADER = 'X-Exchange-Admin-Key';
const REQUEST_TIMEOUT_MS = 15000;

function baseUrl() {
  const cfg = store.getConfig();
  return String(cfg.serverUrl || '').replace(/\/+$/, '');
}

// Node http/https client. Electron's main-process fetch hangs on localhost in
// some environments (proxy / happy-eyeballs), so we use the core modules for a
// deterministic, dependency-free request path.
function apiRequest(method, apiPath, body) {
  return new Promise((resolve) => {
    const base = baseUrl();
    if (!base) return resolve({ ok: false, status: 0, data: { error: 'server URL not set' } });
    const key = store.getAdminKey();
    if (!key) return resolve({ ok: false, status: 0, data: { error: 'admin key not set' } });

    let url;
    try { url = new URL(base + apiPath); } catch (e) {
      return resolve({ ok: false, status: 0, data: { error: 'bad server URL' } });
    }
    const payload = body !== undefined ? JSON.stringify(body) : null;
    // Connection: close keeps each request independent — some single-threaded
    // dev servers (Werkzeug) stall on keep-alive sockets.
    const headers = { [ADMIN_KEY_HEADER]: key, 'Accept': 'application/json', 'Connection': 'close' };
    if (payload !== null) {
      headers['Content-Type'] = 'application/json';
      headers['Content-Length'] = Buffer.byteLength(payload);
    }
    const lib = url.protocol === 'https:' ? https : http;
    const req = lib.request(
      {
        hostname: url.hostname,
        port: url.port || (url.protocol === 'https:' ? 443 : 80),
        path: url.pathname + url.search,
        method,
        headers,
      },
      (res) => {
        let raw = '';
        res.on('data', (c) => { raw += c; });
        res.on('end', () => {
          let data;
          try { data = JSON.parse(raw); } catch (_) { data = {}; }
          const status = res.statusCode || 0;
          resolve({ ok: status >= 200 && status < 300, status, data });
        });
      }
    );
    req.setTimeout(REQUEST_TIMEOUT_MS, () => req.destroy(new Error('request timed out')));
    req.on('error', (err) => resolve({ ok: false, status: 0, data: { error: String(err && err.message || err) } }));
    if (payload !== null) req.write(payload);
    req.end();
  });
}

// getWindow() returns the current BrowserWindow (for streaming daemon logs), or
// null in headless contexts.
function registerIpc(getWindow) {
  const send = (channel, payload) => {
    const w = typeof getWindow === 'function' ? getWindow() : null;
    if (w && !w.isDestroyed()) w.webContents.send(channel, payload);
  };

  ipcMain.handle('config:get', () => ({
    serverUrl: store.getConfig().serverUrl || '',
    hasKey: store.hasAdminKey(),
    encryptionAvailable: safeStorage.isEncryptionAvailable(),
    daemonScript: store.getConfig().daemonScript || '',
    repoRoot: store.getConfig().repoRoot || '',
  }));

  ipcMain.handle('config:setServerUrl', (_e, url) => {
    store.setConfig({ serverUrl: String(url || '').trim() });
    return { ok: true };
  });

  ipcMain.handle('config:setDaemon', (_e, opts) => {
    store.setConfig({
      repoRoot: String((opts && opts.repoRoot) || '').trim(),
      daemonScript: String((opts && opts.daemonScript) || '').trim(),
    });
    return { ok: true };
  });

  ipcMain.handle('key:set', (_e, key) => {
    const k = String(key || '').trim();
    if (!k) return { ok: false, error: 'empty key' };
    store.setAdminKey(k);
    return { ok: true };
  });

  ipcMain.handle('key:clear', () => {
    store.clearAdminKey();
    return { ok: true };
  });

  ipcMain.handle('api:status', () => apiRequest('GET', '/api/profit-daemon/status'));
  ipcMain.handle('api:instances', () => apiRequest('GET', '/api/profit-daemon/instances'));
  ipcMain.handle('api:controlOverview', () => apiRequest('GET', '/api/exchange/control-board/overview'));
  ipcMain.handle('api:killSwitch', (_e, on) => apiRequest('POST', '/api/exchange/control-board/kill-switch', { on: !!on }));
  ipcMain.handle('api:runAll', (_e, force) => apiRequest('POST', '/api/exchange/control-board/run', { force: !!force }));
  ipcMain.handle('api:payoutStatus', () => apiRequest('GET', '/api/exchange/payout/status'));
  ipcMain.handle('api:payoutSweep', (_e, minUsd) => {
    const body = {};
    if (minUsd !== undefined && minUsd !== null && minUsd !== '') body.min_sweep_usd = Number(minUsd);
    return apiRequest('POST', '/api/exchange/payout/sweep', body);
  });

  ipcMain.handle('daemon:status', () => daemon.status());
  ipcMain.handle('daemon:start', async (_e, opts) => {
    const cfg = store.getConfig();
    if (opts && opts.mode === 'live') {
      const inst = await apiRequest('GET', '/api/profit-daemon/instances');
      if (inst.ok && inst.data && inst.data.live_active_count > 0) {
        return { ok: false, error: 'live instance already active on server — refusing to start (double-tick risk)' };
      }
    }
    return daemon.start({
      repoRoot: cfg.repoRoot,
      daemonScript: cfg.daemonScript,
      serverUrl: baseUrl(),
      adminKey: store.getAdminKey(),
      mode: opts && opts.mode,
      profile: opts && opts.profile,
      onLog: (line) => send('daemon:log', line),
      onExit: (code) => send('daemon:exit', code),
    });
  });
  ipcMain.handle('daemon:stop', () => daemon.stop());
}

module.exports = { registerIpc, apiRequest, baseUrl };
