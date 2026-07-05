/**
 * Ecosystem control board on agents/index.html — SSE with poll fallback.
 */
(function () {
  'use strict';

  var board = document.getElementById('ecosystem-control-board');
  if (!board) return;

  var banner = document.getElementById('ecb-status-banner');
  var logEl = document.getElementById('ecb-log');
  var es = null;
  var pollTimer = null;

  function setBanner(text, ok) {
    if (!banner) return;
    banner.textContent = text;
    banner.style.borderLeft = '4px solid ' + (ok ? '#00ff88' : '#ffaa44');
  }

  function fmtHouse(h) {
    if (!h || !h.combined_house) return '—';
    var parts = [];
    Object.keys(h.combined_house).forEach(function (c) {
      parts.push(c + ':' + h.combined_house[c]);
    });
    return parts.join(' ') || '—';
  }

  function render(snap) {
    var v = document.getElementById('ecb-verdict');
    var p = document.getElementById('ecb-pressure');
    var q = document.getElementById('ecb-queue');
    var h = document.getElementById('ecb-halt');
    var wh = document.getElementById('ecb-webhooks');
    var fg = document.getElementById('ecb-float');
    var house = document.getElementById('ecb-house');
    if (v) v.textContent = (snap.conservation && snap.conservation.verdict) || '—';
    if (p) {
      var wp = snap.worker_pressure || {};
      p.textContent = wp.score != null ? wp.score + ' (' + (wp.recommendation || '') + ')' : '—';
    }
    if (q) {
      var vq = snap.video_queue || {};
      q.textContent = (vq.queued != null ? vq.queued : '—') + ' / ' + (vq.active != null ? vq.active : '—');
    }
    if (h) {
      var ks = snap.agent_kill_switch || {};
      h.textContent = ks.global_halt ? 'HALTED' : 'OK';
      h.style.color = ks.global_halt ? '#ff6666' : '#00ff88';
    }
    if (wh) {
      var wo = snap.webhook_outbox || {};
      var pending = wo.pending != null ? wo.pending : ((wo.by_status && wo.by_status.pending) || 0);
      wh.textContent = String(pending);
      wh.style.color = pending > 0 ? '#ffaa44' : '#00ff88';
    }
    if (fg) {
      var f = snap.float_gate || {};
      fg.textContent = f.verdict || (f.allowed === false ? 'red' : '—');
      fg.style.color = f.verdict === 'green' ? '#00ff88' : '#ffaa44';
    }
    if (house) house.textContent = fmtHouse(snap.house_income_24h);
    if (logEl) {
      logEl.textContent = JSON.stringify(snap, null, 2).slice(0, 4000);
    }
    var ok = (snap.conservation && snap.conservation.verdict === 'green');
    setBanner('Last update ' + new Date().toLocaleTimeString(), ok);
  }

  function poll() {
    fetch('/api/ops/public-snapshot', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j.success) render(j);
        else setBanner(j.error || 'Snapshot failed', false);
      })
      .catch(function (e) { setBanner(String(e), false); });
  }

  function startPollFallback() {
    poll();
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(poll, 15000);
  }

  function connectSse() {
    if (typeof EventSource === 'undefined') {
      startPollFallback();
      return;
    }
    try {
      es = new EventSource('/api/ops/public-stream?interval=15');
      es.onmessage = function (ev) {
        try {
          var data = JSON.parse(ev.data);
          if (data.type === 'ops') render(data);
        } catch (e) { /* ignore */ }
      };
      es.onerror = function () {
        if (es) { es.close(); es = null; }
        setBanner('SSE disconnected — polling fallback', false);
        startPollFallback();
      };
    } catch (e) {
      startPollFallback();
    }
  }

  document.addEventListener('DOMContentLoaded', connectSse);
})();
