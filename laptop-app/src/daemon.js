'use strict';

// Local profit-daemon process runner.
//
// Spawns `python scripts/all_profit_daemons.py` from the repo checkout with
// PROFIT_DAEMON_REPORT_URL + EXCHANGE_ADMIN_KEY set so the laptop instance
// reports heartbeats to the server (double-tick detection). Streams stdout/err
// back to the renderer and tracks a single child process.

const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

let child = null;
let startedAt = null;
let lastMode = null;
let lastProfile = null;

function pythonBin(repoRoot) {
  // Prefer the repo venv, fall back to system python3/python.
  const candidates = process.platform === 'win32'
    ? [path.join(repoRoot, '.venv', 'Scripts', 'python.exe'), 'python']
    : [path.join(repoRoot, '.venv', 'bin', 'python'), 'python3', 'python'];
  for (const c of candidates) {
    if (c.includes(path.sep) && fs.existsSync(c)) return c;
  }
  return process.platform === 'win32' ? 'python' : 'python3';
}

function status() {
  return {
    running: !!child,
    pid: child ? child.pid : null,
    started_at: startedAt,
    mode: lastMode,
    profile: lastProfile,
  };
}

function start(opts) {
  if (child) return { ok: false, error: 'daemon already running' };
  const repoRoot = String(opts.repoRoot || '').trim();
  if (!repoRoot || !fs.existsSync(repoRoot)) {
    return { ok: false, error: 'repo root not set or does not exist' };
  }
  const script = String(opts.daemonScript || 'scripts/all_profit_daemons.py').trim();
  const scriptPath = path.isAbsolute(script) ? script : path.join(repoRoot, script);
  if (!fs.existsSync(scriptPath)) {
    return { ok: false, error: 'daemon script not found: ' + scriptPath };
  }

  const mode = opts.mode === 'live' ? 'live' : 'paper';
  const profile = String(opts.profile || 'max');

  const env = { ...process.env, EXCHANGE_PROFIT_PROFILE: profile, PYTHONUNBUFFERED: '1' };
  if (opts.serverUrl) env.PROFIT_DAEMON_REPORT_URL = opts.serverUrl;
  if (opts.adminKey) env.EXCHANGE_ADMIN_KEY = opts.adminKey;
  // Paper vs live: the daemon reads live gates from env; in paper mode we make
  // sure the live arbitrage / payout flags are off so nothing trades for real.
  if (mode === 'paper') {
    env.EXCHANGE_ARBITRAGE_LIVE = '0';
    env.EXCHANGE_AUTO_PAYPAL_SWEEP = '0';
    env.CASINO_AGENT_DRY_RUN = '1';
  }

  const args = [scriptPath, '--profile', profile];
  try {
    child = spawn(pythonBin(repoRoot), args, { cwd: repoRoot, env });
  } catch (err) {
    child = null;
    return { ok: false, error: String(err && err.message || err) };
  }
  startedAt = new Date().toISOString();
  lastMode = mode;
  lastProfile = profile;

  const emit = (line) => { if (typeof opts.onLog === 'function') opts.onLog(line); };
  child.stdout.on('data', (b) => emit(b.toString()));
  child.stderr.on('data', (b) => emit(b.toString()));
  child.on('exit', (code) => {
    const pid = child ? child.pid : null;
    child = null;
    startedAt = null;
    if (typeof opts.onExit === 'function') opts.onExit(code);
    emit(`\n[process ${pid} exited with code ${code}]\n`);
  });

  return { ok: true, pid: child.pid, mode, profile };
}

function stop() {
  if (!child) return { ok: true, alreadyStopped: true };
  try {
    child.kill('SIGTERM');
  } catch (_) { /* ignore */ }
  return { ok: true };
}

module.exports = { status, start, stop };
