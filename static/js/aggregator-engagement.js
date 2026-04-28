/**
 * Aggregator engagement: award small unified points per action + session HUD.
 * Requires POST /api/aggregators/engagement/award (see intelligence_aggregator_routes).
 */
(function () {
  'use strict';

  function getUserId() {
    try {
      return (
        localStorage.getItem('user_id') ||
        localStorage.getItem('vidgenerator_user_id') ||
        localStorage.getItem('game_user_id') ||
        'default_user'
      );
    } catch (e) {
      return 'default_user';
    }
  }

  var sessionAwarded = 0;

  function bumpHud(delta, action) {
    sessionAwarded += delta;
    var el = document.getElementById('agg-session-points');
    var last = document.getElementById('agg-last-action');
    if (el) el.textContent = sessionAwarded.toFixed(1);
    if (last) last.textContent = action || '—';
  }

  function award(action, extra) {
    var uid = getUserId();
    return fetch('/api/aggregators/engagement/award', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(
        Object.assign({ user_id: uid, action: action || 'interaction' }, extra || {})
      ),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (data.success && data.awarded != null) {
          bumpHud(Number(data.awarded), action);
        }
        return data;
      })
      .catch(function () {
        return { success: false };
      });
  }

  function refreshTotalsHud() {
    var uid = getUserId();
    return fetch('/api/points/all?user_id=' + encodeURIComponent(uid))
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        var p = (d && d.points) || {};
        var act = document.getElementById('agg-total-activity');
        var gp = document.getElementById('agg-total-game');
        var kn = document.getElementById('agg-total-knowledge');
        if (act) act.textContent = (p.activity_points != null ? p.activity_points : 0).toLocaleString();
        if (gp) gp.textContent = (p.game_points != null ? p.game_points : 0).toLocaleString();
        if (kn) kn.textContent = (p.knowledge_points != null ? p.knowledge_points : 0).toLocaleString();
      })
      .catch(function () {});
  }

  window.AggregatorEngagement = {
    award: award,
    refreshTotalsHud: refreshTotalsHud,
    bumpHud: bumpHud,
    getUserId: getUserId,
  };

  document.addEventListener('DOMContentLoaded', function () {
    refreshTotalsHud();
    setInterval(refreshTotalsHud, 60000);
  });
})();
