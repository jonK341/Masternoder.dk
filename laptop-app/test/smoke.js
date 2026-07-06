'use strict';

// Headless integration smoke test: boots the real main process wiring (IPC +
// preload + store + daemon), loads the actual renderer offscreen, drives the
// connect flow programmatically through window.pdc, and asserts the dashboard
// renders with live data from a running server.
//
// Requires the Flask dev server on SERVER_URL with EXCHANGE_ADMIN_KEY=ADMIN_KEY.
// Run: SERVER_URL=http://127.0.0.1:5000 ADMIN_KEY=demo-admin-key-123 \
//        xvfb-run -a electron test/smoke.js   (or with a display: electron test/smoke.js)

const { app, BrowserWindow } = require('electron');
const path = require('path');

const SERVER_URL = process.env.SERVER_URL || 'http://127.0.0.1:5000';
const ADMIN_KEY = process.env.ADMIN_KEY || 'demo-admin-key-123';

const store = require('../src/store');
const { registerIpc } = require('../src/ipc');

function fail(msg) {
  console.log('SMOKE_RESULT ' + JSON.stringify({ ok: false, error: msg }));
  app.exit(1);
}

let smokeWin = null;

app.whenReady().then(async () => {
  // Fresh config each run.
  store.setConfig({ serverUrl: '', repoRoot: '', daemonScript: '' });
  store.clearAdminKey();

  // Register the exact IPC handlers the real app uses.
  registerIpc(() => smokeWin);

  const win = new BrowserWindow({
    show: false,
    webPreferences: {
      preload: path.join(__dirname, '..', 'src', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });
  smokeWin = win;

  win.webContents.on('console-message', (_e, level, message, line, sourceId) => {
    console.log('[renderer:' + level + ']', message, '(' + (sourceId || '') + ':' + line + ')');
  });
  win.webContents.on('preload-error', (_e, p, err) => console.log('[preload-error]', p, String(err)));

  await win.loadFile(path.join(__dirname, '..', 'src', 'renderer', 'index.html'));

  const results = {};

  // 1. preload bridge exposed?
  results.hasBridge = await win.webContents.executeJavaScript('typeof window.pdc === "object" && !!window.pdc.api');

  // 2. gate visible, app hidden initially
  results.gateVisibleInitial = await win.webContents.executeJavaScript(
    '!document.getElementById("gate").hidden && document.getElementById("app").hidden'
  );

  // 2b. Exercise the bridge methods directly to localize any failure.
  results.direct = await win.webContents.executeJavaScript(`(async () => {
    try {
      const su = await window.pdc.config.setServerUrl(${JSON.stringify(SERVER_URL)});
      const sk = await window.pdc.key.set(${JSON.stringify(ADMIN_KEY)});
      const st = await window.pdc.api.status();
      return { setUrl: su, setKey: sk, statusOk: st.ok, view: st.data && st.data.view, err: st.data && st.data.error };
    } catch (e) { return { threw: String(e && e.message || e) }; }
  })()`);

  // 3. drive connect the same way the button handler does.
  win.webContents.on('console-message', (_e, level, message) => {
    console.log('[renderer]', message);
  });
  await win.webContents.executeJavaScript(`window.__err=''; window.addEventListener('error', e => { window.__err = String(e.message); }); window.addEventListener('unhandledrejection', e => { window.__err = 'reject: ' + String(e.reason); }); true;`);
  const connectOutcome = await win.webContents.executeJavaScript(`(async () => {
    document.getElementById('gate-url').value = ${JSON.stringify(SERVER_URL)};
    document.getElementById('gate-key').value = ${JSON.stringify(ADMIN_KEY)};
    document.getElementById('gate-connect').click();
    // wait for async connect + enterApp + first refresh
    await new Promise(r => setTimeout(r, 5000));
    const gateHidden = document.getElementById('gate').hidden;
    const appVisible = !document.getElementById('app').hidden;
    const pill = document.getElementById('status-pill').textContent;
    const kpiCount = document.querySelectorAll('#status-kpis .kpi').length;
    const instRows = document.querySelectorAll('#instances .inst-row').length;
    const payoutKpis = document.querySelectorAll('#payout-kpis .kpi').length;
    const conflictShown = !document.getElementById('conflict-bar').hidden;
    const conflictText = document.getElementById('conflict-bar').textContent;
    const gateErr = document.getElementById('gate-err').hidden ? '' : document.getElementById('gate-err').textContent;
    return { gateHidden, appVisible, pill, kpiCount, instRows, payoutKpis, conflictShown, conflictText, gateErr, jsErr: window.__err };
  })()`);
  results.connect = connectOutcome;

  // 4. toggle kill-switch and read the message
  const killOutcome = await win.webContents.executeJavaScript(`(async () => {
    const t = document.getElementById('kill-toggle');
    t.checked = true; t.dispatchEvent(new Event('change'));
    await new Promise(r => setTimeout(r, 1500));
    const onMsg = document.getElementById('control-msg').textContent;
    t.checked = false; t.dispatchEvent(new Event('change'));
    await new Promise(r => setTimeout(r, 1500));
    const offMsg = document.getElementById('control-msg').textContent;
    return { onMsg, offMsg };
  })()`);
  results.killSwitch = killOutcome;

  const ok = !!(results.hasBridge && results.gateVisibleInitial &&
    connectOutcome.appVisible && connectOutcome.gateHidden &&
    connectOutcome.kpiCount > 0 && connectOutcome.payoutKpis > 0);
  console.log('SMOKE_RESULT ' + JSON.stringify({ ok, results }, null, 2));
  app.exit(ok ? 0 : 2);
}).catch((e) => fail(String(e && e.stack || e)));
