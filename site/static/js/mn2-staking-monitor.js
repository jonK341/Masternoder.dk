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
    fetch('/api/mn2/network-overview', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (o) {
        var b = q('sm-failover-banner');
        if (!b || !o || !o.rpc_failover) return;
        var fo = o.rpc_failover;
        if (fo.enabled && fo.active === 'standby') {
          b.style.display = 'block';
          b.textContent = 'RPC failover active: using standby node (' + (fo.promote_reason || 'promoted') + '). Primary may be down.';
        } else if (fo.enabled && fo.configured) {
          b.style.display = 'none';
        }
      }).catch(function () {});
    loadHealthHub();
  }

  function hubClass(status) {
    if (status === 'healthy' || status === 'active' || status === 'enabled') return 'ok';
    if (status === 'disabled' || status === 'unconfigured' || status === 'unknown') return 'warn';
    return 'bad';
  }

  function hubCard(label, value, sub, status) {
    return '<div class="hub-card ' + hubClass(status) + '">' +
      '<div class="label">' + label + '</div>' +
      '<div class="value">' + value + '</div>' +
      (sub ? '<div class="sub">' + sub + '</div>' : '') +
      '</div>';
  }

  function fmtHubTime(v) {
    if (v == null || v === '') return '';
    if (typeof v === 'number') {
      var ms = v > 1e12 ? v : v * 1000;
      return new Date(ms).toISOString().slice(0, 19).replace('T', ' ');
    }
    return String(v).slice(0, 19);
  }

  function mintSub(mint) {
    if (!mint) return '';
    if (mint.mnsync === true && mint.staking_active) return 'minting · mnsync ok';
    if (mint.mnsync === false) return 'mnsync pending';
    if (mint.staking_active) return 'minting';
    return 'not minting';
  }

  function loadHealthHub() {
    fetch('/api/mn2/health', { credentials: 'same-origin' })
      .then(function (r) {
        return r.json().then(function (d) { return { http: r.status, data: d }; });
      })
      .then(function (res) {
        var d = res.data;
        var grid = q('hub-grid');
        if (!grid || !d) return;
        var c = d.components || {};
        var rpc = c.mn2_rpc || {};
        var scan = c.deposit_scanner || {};
        var mint = c.daemon_staking || {};
        var disc = c.discord_outbox || {};
        var alerts = c.network_alerts || {};
        var scanSub = scan.last_run && scan.last_run.end != null
          ? ('last ' + fmtHubTime(scan.last_run.end))
          : 'no runs logged';
        var cards = [
          hubCard('MN2 RPC', rpc.status || '—', rpc.block_height != null ? ('height ' + rpc.block_height) : (rpc.error || ''), rpc.status),
          hubCard('Block sync', (c.block_monotonicity || {}).status || '—', (c.block_monotonicity || {}).last_height != null ? ('last ' + c.block_monotonicity.last_height) : '', (c.block_monotonicity || {}).status),
          hubCard('Deposit scanner', scan.status || '—', scanSub, scan.status),
          hubCard('Daemon minting', mint.status || '—', mintSub(mint), mint.status),
          hubCard('Discord outbox', disc.status || '—', disc.configured ? (disc.failures_recent + ' fail / ' + disc.total_recent + ' recent') : 'webhook not set', disc.status),
          hubCard('Network alerts', alerts.status || '—', alerts.recent_count ? (alerts.recent_count + ' recent') : 'none', alerts.status),
        ];
        grid.innerHTML = cards.join('');
        var up = q('hub-updated');
        if (up) up.textContent = 'Health updated ' + new Date().toLocaleTimeString() + ' · overall ' + (d.status || '—') + (res.http >= 400 ? ' (HTTP ' + res.http + ')' : '');
        loadServicesGrid();
      })
      .catch(function () {
        var grid = q('hub-grid');
        if (grid) grid.innerHTML = '<div class="hub-card bad"><div class="label">Health</div><div class="value">Unavailable</div></div>';
      });
  }

  function loadServicesGrid() {
    fetch('/api/mn2/services', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var grid = q('services-grid');
        if (!grid || !d || !d.services) return;
        grid.innerHTML = d.services.map(function (s) {
          return hubCard(s.name || s.id, s.status || '—', s.category || s.id, s.status);
        }).join('');
        var up = q('services-updated');
        if (up && d.summary) {
          up.textContent = 'Services: ' + (d.summary.overall || '—') + ' · ' +
            (d.summary.healthy || 0) + ' healthy / ' + (d.summary.total || 0) + ' total';
        }
      })
      .catch(function () {
        var grid = q('services-grid');
        if (grid) grid.innerHTML = '<div class="hub-card bad"><div class="label">Services</div><div class="value">Unavailable</div></div>';
      });
  }

  refresh();
  setInterval(refresh, 15000);
})();
