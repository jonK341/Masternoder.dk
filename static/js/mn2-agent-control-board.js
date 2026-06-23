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

  function setBanner(text, ok) {
    if (!banner) return;
    banner.textContent = text;
    banner.style.borderLeft = '4px solid ' + (ok ? '#00ff88' : '#ffaa44');
  }

  function render(snap) {
    var v = document.getElementById('ecb-verdict');
    var p = document.getElementById('ecb-pressure');
    var q = document.getElementById('ecb-queue');
    var h = document.getElementById('ecb-halt');
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
    if (logEl) {
      logEl.textContent = JSON.stringify(snap, null, 2).slice(0, 4000);
    }
    var ok = (snap.conservation && snap.conservation.verdict === 'green');
    setBanner('Last update ' + new Date().toLocaleTimeString(), ok);
  }

  function poll() {
    fetch('/api/ops/snapshot', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j.success) render(j);
        else setBanner(j.error || 'Snapshot failed', false);
      })
      .catch(function (e) { setBanner(String(e), false); });
  }

  function connectSse() {
    if (typeof EventSource === 'undefined') {
      poll();
      setInterval(poll, 15000);
      return;
    }
    try {
      es = new EventSource('/api/ops/stream?interval=15');
      es.onmessage = function (ev) {
        try {
          var data = JSON.parse(ev.data);
          if (data.type === 'ops') render(data);
        } catch (e) { /* ignore */ }
      };
      es.onerror = function () {
        if (es) { es.close(); es = null; }
        setBanner('SSE disconnected — polling fallback', false);
        poll();
        setInterval(poll, 15000);
      };
    } catch (e) {
      poll();
      setInterval(poll, 15000);
    }
  }

  document.addEventListener('DOMContentLoaded', connectSse);
})();
