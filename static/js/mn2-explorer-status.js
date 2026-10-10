(function () {
  'use strict';

  function q(id) { return document.getElementById(id); }

  function fmtCheck(name, val) {
    if (val == null) return '—';
    if (typeof val === 'boolean') return val ? 'yes' : 'no';
    if (typeof val === 'object') return JSON.stringify(val);
    return String(val);
  }

  function renderChecks(data) {
    var grid = q('ex-status-checks');
    if (!grid || !data) return;
    var checks = data.checks || {};
    var cards = [
      { title: 'RPC', body: checks.rpc },
      { title: 'Rich list', body: checks.rich_list },
      { title: 'Mempool', body: checks.mempool },
      { title: 'Chain sync', body: checks.chain_sync },
      { title: 'Fork', body: checks.fork },
      { title: 'Eiquidus', body: data.iquidus },
    ];
    grid.innerHTML = cards.map(function (c) {
      var body = c.body || {};
      var rows = Object.keys(body).map(function (k) {
        return '<div class="ex-status-row"><span>' + k + '</span><code>' + fmtCheck(k, body[k]) + '</code></div>';
      }).join('');
      return '<div class="ex-status-card"><h2>' + c.title + '</h2>' + rows + '</div>';
    }).join('');
  }

  function refresh() {
    fetch('/api/mn2/explorer/status', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var pill = q('ex-status-pill');
        var updated = q('ex-status-updated');
        if (!d) return;
        var status = d.status || 'unknown';
        if (pill) {
          pill.textContent = status.toUpperCase();
          pill.className = 'ex-status-pill ex-status-pill--' + status;
        }
        renderChecks(d);
        if (updated) updated.textContent = 'Kind: ' + (d.explorer_kind || '—') + ' · Updated ' + new Date().toLocaleString();
      })
      .catch(function () {
        var pill = q('ex-status-pill');
        if (pill) {
          pill.textContent = 'UNREACHABLE';
          pill.className = 'ex-status-pill ex-status-pill--degraded';
        }
      });
  }

  refresh();
  setInterval(refresh, 30000);
})();
