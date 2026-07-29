/**
 * Game Monitor tab — unified dashboard + earn check-in (Phase 11).
 */
(function () {
  'use strict';

  function uid() {
    return localStorage.getItem('game_user_id')
      || localStorage.getItem('user_id')
      || 'default_user';
  }

  function q(id) { return document.getElementById(id); }

  function setText(id, v) {
    var el = q(id);
    if (el) el.textContent = v == null ? '—' : String(v);
  }

  function loadEarnList() {
    return fetch('/api/game-hub/earn/top10', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var el = q('monitor-earn-list');
        if (!el) return;
        var rows = (d && d.earn_functions) || [];
        if (!rows.length) {
          el.textContent = 'No earn functions configured.';
          return;
        }
        el.innerHTML = '<ul style="margin:0;padding-left:18px;">' + rows.map(function (e) {
          return '<li><code>' + e.id + '</code> — ' + e.default_mn2 + ' MN2</li>';
        }).join('') + '</ul>';
        setText('mon-earn', rows.length);
      })
      .catch(function () {
        var el = q('monitor-earn-list');
        if (el) el.textContent = 'Could not load earn list.';
      });
  }

  function loadMonitor() {
    var user = uid();
    setText('mon-level', '…');
    var pings = q('monitor-pings');
    if (pings) pings.textContent = 'Loading…';

    var urls = [
      '/api/aggregator/unified-dashboard/data?user_id=' + encodeURIComponent(user),
      '/api/battle/progress?user_id=' + encodeURIComponent(user),
      '/api/star-map/25/status?user_id=' + encodeURIComponent(user),
      '/api/lab/overview?user_id=' + encodeURIComponent(user),
      '/api/game/hunters/profile?user_id=' + encodeURIComponent(user),
      '/api/trophies/list?user_id=' + encodeURIComponent(user),
    ];

    return Promise.all(urls.map(function (u) {
      return fetch(u, { credentials: 'same-origin' })
        .then(function (r) { return r.json().catch(function () { return { success: false, status: r.status }; }); })
        .catch(function () { return { success: false, error: 'network' }; });
    })).then(function (parts) {
      var dash = parts[0] || {};
      var pts = (dash.points || {});
      setText('mon-level', pts.level != null ? pts.level : (dash.stats && dash.stats.level) || '—');
      setText('mon-xp', pts.total_xp != null ? pts.total_xp : (dash.stats && dash.stats.xp_total) || '—');
      var systems = pts.systems || {};
      setText('mon-mn2', systems.mn2_balance != null ? systems.mn2_balance : '—');
      if (pings) {
        pings.textContent = JSON.stringify({
          dashboard_ok: !!dash.points || dash.success !== false,
          battle: parts[1],
          starmap: parts[2],
          lab: parts[3],
          hunters: parts[4],
          trophies: parts[5],
        }, null, 2);
      }
    });
  }

  function checkIn() {
    return fetch('/api/game-hub/earn/check-in', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ user_id: uid() }),
    }).then(function (r) { return r.json(); }).then(function (d) {
      var btn = q('monitor-checkin-btn');
      if (btn) btn.textContent = d.duplicate ? 'Already checked in' : (d.success ? 'Checked in!' : (d.error || 'Failed'));
      loadMonitor();
    }).catch(function () {});
  }

  function bind() {
    var refresh = q('monitor-refresh-btn');
    var checkin = q('monitor-checkin-btn');
    if (refresh) refresh.addEventListener('click', function () { loadMonitor(); loadEarnList(); });
    if (checkin) checkin.addEventListener('click', checkIn);

    document.querySelectorAll('.game-tab[data-tab="monitor"]').forEach(function (tab) {
      tab.addEventListener('click', function () {
        loadMonitor();
        loadEarnList();
        if (window.Mn2ActivityMonitor && typeof window.Mn2ActivityMonitor.mount === 'function') {
          var root = document.getElementById('mn2-activity-monitor');
          if (root) window.Mn2ActivityMonitor.mount(root);
        }
      });
    });
  }

  document.addEventListener('DOMContentLoaded', bind);
})();
