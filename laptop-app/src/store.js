'use strict';

// Config + encrypted admin-key persistence.
//
// - Non-secret config (server URL, daemon paths) is JSON in userData/config.json.
// - The admin key is encrypted with Electron safeStorage (OS keychain-backed on
//   macOS/Windows, libsecret on Linux) and written to userData/admin-key.enc.
//   It is never written in plaintext. If OS encryption is unavailable we refuse
//   to persist the key (kept in memory for the session only).

const { app, safeStorage } = require('electron');
const path = require('path');
const fs = require('fs');

function userDir() {
  return app.getPath('userData');
}
function configPath() {
  return path.join(userDir(), 'config.json');
}
function keyPath() {
  return path.join(userDir(), 'admin-key.enc');
}

let _memKey = null; // session fallback when encryption unavailable

function getConfig() {
  try {
    return JSON.parse(fs.readFileSync(configPath(), 'utf8')) || {};
  } catch (_) {
    return {};
  }
}

function setConfig(patch) {
  const cfg = { ...getConfig(), ...patch };
  fs.mkdirSync(userDir(), { recursive: true });
  fs.writeFileSync(configPath(), JSON.stringify(cfg, null, 2), 'utf8');
  return cfg;
}

function setAdminKey(key) {
  if (safeStorage.isEncryptionAvailable()) {
    fs.mkdirSync(userDir(), { recursive: true });
    const enc = safeStorage.encryptString(String(key));
    fs.writeFileSync(keyPath(), enc);
    _memKey = null;
  } else {
    // No OS keystore: keep in memory only, do not touch disk.
    _memKey = String(key);
  }
}

function getAdminKey() {
  if (_memKey) return _memKey;
  try {
    if (!fs.existsSync(keyPath())) return '';
    const buf = fs.readFileSync(keyPath());
    return safeStorage.decryptString(buf);
  } catch (_) {
    return '';
  }
}

function hasAdminKey() {
  return !!getAdminKey();
}

function clearAdminKey() {
  _memKey = null;
  try { fs.unlinkSync(keyPath()); } catch (_) { /* ignore */ }
}

module.exports = { getConfig, setConfig, setAdminKey, getAdminKey, hasAdminKey, clearAdminKey };
