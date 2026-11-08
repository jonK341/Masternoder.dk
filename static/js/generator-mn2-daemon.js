/**
 * Generator page — MN2 network overview / daemon strip (WW2 field terminal).
 */
(function () {
  'use strict';

  function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function fmtDaemonVer(v) {
    if (v == null || v === '') return '—';
    var n = Number(v);
    if (!isNaN(n) && n >= 1000000) {
      return [
        Math.floor(n / 1000000),
        Math.floor((n % 1000000) / 10000),
        Math.floor((n % 10000) / 100),
        n % 100,
      ].join('.');
    }
    return String(v);
  }

  function applyDaemonStats(ov) {
    if (!ov) return;
    var dm = ov.daemon || {};
    var h = ov.block_height != null ? ov.block_height : dm.block_height;
    if (h != null) setText('gen-d-block', String(h));
    if (dm.connections != null) setText('gen-d-peers', String(dm.connections));
    if (dm.mempool_tx != null) setText('gen-d-mempool', String(dm.mempool_tx));
    if (dm.version != null) setText('gen-d-ver', fmtDaemonVer(dm.version));
    if (dm.staking_status) setText('gen-d-stake', String(dm.staking_status));
    else if (ov.staking_health && ov.staking_health.status) {
      setText('gen-d-stake', String(ov.staking_health.status));
    }
    if (dm.masternode_sync_pct != null) {
      setText('gen-d-mnsync', Number(dm.masternode_sync_pct).toFixed(1) + '%');
    }
    if (dm.header_lag != null) setText('gen-d-lag', String(dm.header_lag));
    if (dm.relay_fee != null) setText('gen-d-relay', Number(dm.relay_fee).toFixed(6));
    if (ov.mn2_usd_price != null) {
      setText('gen-d-price', '$' + Number(ov.mn2_usd_price).toFixed(4));
    }
    setText('gen-daemon-updated', 'Updated ' + new Date().toLocaleTimeString());
  }

  function refresh() {
    var bridge = window.Mn2SiteBridge;
    if (bridge && typeof bridge.loadNetworkOverview === 'function') {
      bridge.loadNetworkOverview().then(applyDaemonStats).catch(function () {
        setText('gen-daemon-updated', 'Daemon stats unavailable');
      });
      return;
    }
    fetch('/api/mn2/network-overview', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(applyDaemonStats)
      .catch(function () {
        setText('gen-daemon-updated', 'Daemon stats unavailable');
      });
  }

  window.GeneratorMn2Daemon = { refresh: refresh };

  document.addEventListener('DOMContentLoaded', function () {
    refresh();
    setInterval(refresh, 120000);
  });
})();
