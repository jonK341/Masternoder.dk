'use strict';

const $ = (id) => document.getElementById(id);
// window.pdc is injected by the preload contextBridge; alias under a local
// name (declaring `const pdc` would clash with the global binding).
const api = window.pdc;

let pollTimer = null;

function money(n) {
  const v = Number(n || 0);
  return (v < 0 ? '-$' : '$') + Math.abs(v).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function kpi(label, value, cls) {
  return `<div class="kpi ${cls || ''}"><div class="k-label">${label}</div><div class="k-value">${value}</div></div>`;
}

// --------------------------------------------------------------------------
// Gate / connection
// --------------------------------------------------------------------------
async function initGate() {
  const cfg = await api.config.get();
  $('gate-url').value = cfg.serverUrl || '';
  const encMsg = cfg.encryptionAvailable
    ? 'OS keychain encryption available — key stored securely.'
    : 'OS keychain unavailable — key kept in memory for this session only.';
  $('gate-enc').textContent = encMsg;
  if (cfg.serverUrl && cfg.hasKey) {
    enterApp();
  }
}

$('gate-connect').addEventListener('click', async () => {
  const url = $('gate-url').value.trim();
  const key = $('gate-key').value.trim();
  const err = $('gate-err');
  err.hidden = true;
  if (!url) { err.textContent = 'Server URL required'; err.hidden = false; return; }
  if (!key) { err.textContent = 'Admin key required'; err.hidden = false; return; }
  await api.config.setServerUrl(url);
  await api.key.set(key);
  // Validate against the owner API before entering.
  const res = await api.api.status();
  if (!res.ok || (res.data && res.data.view !== 'owner')) {
    err.textContent = res.status === 401 || (res.data && res.data.view === 'public')
      ? 'Key rejected by server (not owner).'
      : ('Cannot reach server: ' + ((res.data && res.data.error) || res.status));
    err.hidden = false;
    return;
  }
  $('gate-key').value = '';
  enterApp();
});

$('disconnect-btn').addEventListener('click', async () => {
  await api.key.clear();
  if (pollTimer) clearInterval(pollTimer);
  $('app').hidden = true;
  $('gate').hidden = false;
  initGate();
});

async function enterApp() {
  $('gate').hidden = true;
  $('app').hidden = false;
  const cfg = await api.config.get();
  $('server-label').textContent = cfg.serverUrl || '';
  if (cfg.repoRoot) $('repo-root').value = cfg.repoRoot;
  refreshAll();
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(refreshAll, 15000);
  syncRunner();
}

// --------------------------------------------------------------------------
// Status + instances
// --------------------------------------------------------------------------
async function refreshAll() {
  await Promise.all([loadStatus(), loadInstances(), loadControls(), loadPayout()]);
}

async function loadStatus() {
  const res = await api.api.status();
  const pill = $('status-pill');
  const dot = $('conn-dot');
  if (!res.ok) {
    pill.textContent = 'unreachable';
    pill.className = 'pill off';
    dot.className = 'dot off';
    return;
  }
  const d = res.data;
  const online = !!d.running;
  pill.textContent = online ? ('online · ' + (d.mode || '?')) : 'stale / offline';
  pill.className = 'pill ' + (online ? 'on' : 'off');
  dot.className = 'dot ' + (online ? 'on' : 'off');

  const kpis = [];
  kpis.push(kpi('Daemon', online ? 'online' : 'offline', online ? 'good' : 'bad'));
  kpis.push(kpi('Mode', d.mode || '?', d.mode === 'live' ? 'good' : 'warn'));
  kpis.push(kpi('Profile', d.profile || 'max'));
  kpis.push(kpi('Readiness', (d.profit_readiness_pct != null ? d.profit_readiness_pct + '%' : '—')));
  if (d.payout) kpis.push(kpi('Auto sweep', d.payout.auto_sweep ? 'on' : 'off', d.payout.auto_sweep ? 'good' : 'warn'));
  $('status-kpis').innerHTML = kpis.join('');

  const loops = Array.isArray(d.loops) ? d.loops : [];
  $('status-loops').innerHTML = loops.map((r) => {
    const age = r.age_sec != null ? Math.round(r.age_sec) + 's ago' : '—';
    return `<div class="loop-row ${r.stale ? 'stale' : ''}"><strong>${r.loop}</strong> · ${age}<br><span class="muted">${r.summary || ''}</span></div>`;
  }).join('') || '<span class="muted small">No loop data.</span>';
}

async function loadInstances() {
  const res = await api.api.instances();
  const bar = $('conflict-bar');
  if (!res.ok) {
    $('instances').innerHTML = '<span class="muted small">Instances unavailable.</span>';
    bar.hidden = true;
    return;
  }
  const d = res.data;
  $('inst-count').textContent = '· ' + (d.active_count || 0) + ' active';
  if (d.conflict) {
    bar.hidden = false;
    bar.textContent = '⚠ ' + (d.conflict_reason || 'Multiple daemon instances active');
  } else {
    bar.hidden = true;
  }
  const rows = Array.isArray(d.instances) ? d.instances : [];
  $('instances').innerHTML = rows.map((r) => {
    const badges = [];
    if (r.active) badges.push('<span class="badge active">active</span>');
    if (r.mode === 'live') badges.push('<span class="badge live">live</span>');
    const age = r.age_sec != null ? Math.round(r.age_sec) + 's' : '—';
    return `<div class="inst-row ${r.active ? 'active' : ''}">
      <span><strong>${r.host || r.instance_id}</strong> <span class="muted">${r.source || ''} · pid ${r.pid || '?'} · ${age}</span></span>
      <span>${badges.join(' ')}</span>
    </div>`;
  }).join('') || '<span class="muted small">No instances registered.</span>';
}

// --------------------------------------------------------------------------
// Controls
// --------------------------------------------------------------------------
async function loadControls() {
  const res = await api.api.controlOverview();
  if (!res.ok) { $('control-msg').textContent = 'Control board unavailable.'; return; }
  const d = res.data;
  $('kill-toggle').checked = !!d.kill_switch;
  const t = d.totals || {};
  $('control-msg').textContent = `${t.active_bots || 0}/${t.bot_count || 0} bots active · profit ${money(t.total_profit_usd)}`;
}

$('kill-toggle').addEventListener('change', async (e) => {
  const on = e.target.checked;
  const res = await api.api.killSwitch(on);
  $('control-msg').textContent = res.ok
    ? ('Kill-switch ' + (on ? 'ON — trading paused' : 'OFF — trading resumed'))
    : ('Failed: ' + ((res.data && res.data.error) || res.status));
  if (!res.ok) e.target.checked = !on;
});

$('run-all-btn').addEventListener('click', async () => {
  $('control-msg').textContent = 'Running tick…';
  const res = await api.api.runAll(false);
  if (!res.ok || (res.data && res.data.success === false)) {
    $('control-msg').textContent = 'Run failed: ' + ((res.data && res.data.error) || res.status);
  } else {
    $('control-msg').textContent = 'Tick complete.';
    loadControls();
  }
});

// --------------------------------------------------------------------------
// Payout
// --------------------------------------------------------------------------
async function loadPayout() {
  const res = await api.api.payoutStatus();
  if (!res.ok) { $('payout-kpis').innerHTML = '<span class="muted small">Payout unavailable.</span>'; return; }
  const d = res.data;
  const pp = d.paypal || {};
  const kpis = [];
  kpis.push(kpi('Mode', d.mode || (pp.live_enabled ? 'live' : 'paper'), pp.live_enabled ? 'good' : 'warn'));
  kpis.push(kpi('Sweepable', money(d.paypal_sweepable_usd != null ? d.paypal_sweepable_usd : d.sweepable_usd), 'good'));
  kpis.push(kpi('PayPal', pp.connected ? 'connected' : 'off', pp.connected ? 'good' : 'warn'));
  kpis.push(kpi('Ready', d.ready_to_sweep ? 'yes' : 'no', d.ready_to_sweep ? 'good' : 'warn'));
  $('payout-kpis').innerHTML = kpis.join('');
}

$('sweep-btn').addEventListener('click', () => {
  openModal({
    title: 'Confirm PayPal sweep',
    body: 'This moves real funds if live payout is enabled on the server. Proceed?',
    input: true,
    onConfirm: async (val) => {
      $('payout-msg').textContent = 'Sweeping…';
      const res = await api.api.payoutSweep(val);
      if (!res.ok || (res.data && res.data.success === false)) {
        $('payout-msg').textContent = 'Sweep failed: ' + ((res.data && res.data.error) || res.status);
      } else {
        $('payout-msg').textContent = 'Sweep submitted.';
        loadPayout();
      }
    },
  });
});

// --------------------------------------------------------------------------
// Local daemon runner
// --------------------------------------------------------------------------
async function syncRunner() {
  const st = await api.daemon.status();
  const running = !!st.running;
  $('runner-state').textContent = running
    ? `Running · pid ${st.pid} · ${st.mode} · ${st.profile}`
    : 'Stopped';
  $('daemon-start-btn').disabled = running;
  $('daemon-stop-btn').disabled = !running;
}

$('daemon-start-btn').addEventListener('click', async () => {
  const repoRoot = $('repo-root').value.trim();
  await api.config.setDaemon({ repoRoot, daemonScript: '' });
  const mode = $('daemon-mode').value;
  const profile = $('daemon-profile').value;
  if (mode === 'live') {
    openModal({
      title: 'Start LIVE daemon',
      body: 'This runs the profit daemon in live mode on this machine. It will refuse to start if another live instance is active on the server. Proceed?',
      onConfirm: () => doStart({ mode, profile }),
    });
  } else {
    doStart({ mode, profile });
  }
});

async function doStart(opts) {
  $('daemon-logs').textContent = '';
  const res = await api.daemon.start(opts);
  if (!res.ok) {
    appendLog('[start failed] ' + (res.error || 'unknown') + '\n');
  } else {
    appendLog(`[started pid ${res.pid} · ${res.mode} · ${res.profile}]\n`);
  }
  syncRunner();
}

$('daemon-stop-btn').addEventListener('click', async () => {
  await api.daemon.stop();
  appendLog('[stop requested]\n');
  syncRunner();
});

function appendLog(line) {
  const el = $('daemon-logs');
  el.textContent += line;
  el.scrollTop = el.scrollHeight;
}

api.daemon.onLog((line) => appendLog(line));
api.daemon.onExit(() => syncRunner());

$('refresh-btn').addEventListener('click', refreshAll);

// --------------------------------------------------------------------------
// Modal
// --------------------------------------------------------------------------
let modalConfirm = null;
function openModal({ title, body, input, onConfirm }) {
  $('modal-title').textContent = title;
  $('modal-body').textContent = body;
  $('modal-input-wrap').hidden = !input;
  $('modal-input').value = '';
  modalConfirm = onConfirm;
  $('modal').hidden = false;
}
function closeModal() { $('modal').hidden = true; modalConfirm = null; }
$('modal-cancel').addEventListener('click', closeModal);
$('modal-confirm').addEventListener('click', () => {
  const val = $('modal-input-wrap').hidden ? undefined : $('modal-input').value;
  const fn = modalConfirm;
  closeModal();
  if (fn) fn(val);
});

initGate();
