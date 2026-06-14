/* MN2 staking monitor - polls /api/mn2/staking/monitor and renders aggregates + processes. */
(function () {
  'use strict';

  function fmt(n, d) { return Number(n || 0).toFixed(d == null ? 4 : d); }
  function q(id) { return document.getElementById(id); }

  function render(data) {
    if (!data || !data.success) return;
    var a = data.aggregates || {};
    q('t-total').textContent = fmt(a.total_staked, 2) + ' MN2';
    q('t-stakers').textContent = a.active_stakers || 0;
    q('t-rigs').textContent = a.active_rigs || 0;
    q('t-apr').textContent = fmt(a.pool_apr_percent, 2) + '%';
    q('t-paid').textContent = fmt(a.rewards_paid_lifetime_mn2, 4) + ' MN2';
    q('t-reserve').textContent = fmt(a.reserve_mn2, 2) + ' MN2';
    q('t-yield24').textContent = fmt(a.realized_yield_24h_mn2, 6) + ' MN2';
    q('t-paid24').textContent = fmt(a.rewards_paid_24h_mn2, 6) + ' MN2';

    var body = q('sm-body');
    var procs = data.processes || [];
    if (!procs.length) { body.innerHTML = '<tr><td colspan="8">No active stakers yet.</td></tr>'; return; }
    body.innerHTML = procs.map(function (p) {
      var rig = p.rig_active
        ? '<span class="pill on">on</span>'
        : '<span class="pill off">off</span>';
      return '<tr>' +
        '<td>' + (p.display_id || '') + '</td>' +
        '<td>' + fmt(p.staked, 4) + '</td>' +
        '<td class="tier">' + (p.longevity_tier || '--') + '</td>' +
        '<td>' + fmt(p.longevity_days, 1) + '</td>' +
        '<td>' + rig + '</td>' +
        '<td>' + Math.round((p.uptime_ratio || 0) * 100) + '%</td>' +
        '<td>' + fmt(p.effective_apr, 2) + '%</td>' +
        '<td>' + fmt(p.total_earned, 6) + '</td>' +
        '</tr>';
    }).join('');
  }

  function refresh() {
    fetch('/api/mn2/staking/monitor?limit=100', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(render)
      .catch(function () {});
  }

  refresh();
  setInterval(refresh, 15000);
})();
