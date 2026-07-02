/* Exchange hub — page-level tab nav + lazy loaders (pattern: mn2-crypto-hub.js) */
(function () {
  'use strict';

  var TAB_LABELS = {
    trade: 'Trade',
    overview: 'Overview',
    bots: 'Bots & daemons',
    liquidity: 'Sales pool',
    treasury: 'Treasury',
    marketplace: 'Marketplace',
    venues: 'Venues',
  };

  var loaded = {};
  var handlers = {};
  var pollTimers = {};

  function q(id) { return document.getElementById(id); }

  function fetchJson(path, opts) {
    opts = opts || {};
    var timeoutMs = opts.timeout || 8000;
    var retries = opts.retries != null ? opts.retries : 1;
    var attempt = 0;

    function run() {
      var ctrl = new AbortController();
      var timer = setTimeout(function () { ctrl.abort(); }, timeoutMs);
      return fetch(path, {
        credentials: 'same-origin',
        signal: ctrl.signal,
        headers: opts.headers || {},
        method: opts.method || 'GET',
        body: opts.body || undefined,
      }).then(function (r) {
        clearTimeout(timer);
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      }).catch(function (err) {
        clearTimeout(timer);
        if (attempt < retries) {
          attempt += 1;
          return run();
        }
        throw err;
      });
    }
    return run();
  }

  function shell(tabId) {
    return document.querySelector('.cex-tab-shell[data-cex-tab="' + tabId + '"]');
  }

  function setLoading(tabId, on) {
    var el = shell(tabId);
    if (!el) return;
    el.classList.toggle('cex-tab-shell--loading', !!on);
    var slot = el.querySelector('.cex-tab-load-slot');
    if (!slot) return;
    if (on) {
      slot.innerHTML = '<div class="cex-tab-spinner" role="status"><span class="cex-tab-spinner-ic"></span> Loading…</div>';
      slot.hidden = false;
    } else if (!slot.querySelector('.cex-tab-error')) {
      slot.hidden = true;
      slot.innerHTML = '';
    }
  }

  function setError(tabId, message, retryFn) {
    var el = shell(tabId);
    if (!el) return;
    el.classList.remove('cex-tab-shell--loading');
    var slot = el.querySelector('.cex-tab-load-slot');
    if (!slot) return;
    slot.hidden = false;
    slot.innerHTML =
      '<div class="cex-tab-error">' +
      '<p>' + (message || 'Could not load this section.') + '</p>' +
      '<button type="button" class="cex-btn cex-btn--ghost cex-tab-retry">Retry</button></div>';
    var btn = slot.querySelector('.cex-tab-retry');
    if (btn && retryFn) btn.addEventListener('click', function () {
      loaded[tabId] = false;
      retryFn();
    });
  }

  function clearSlot(tabId) {
    var el = shell(tabId);
    if (!el) return;
    el.classList.remove('cex-tab-shell--loading');
    var slot = el.querySelector('.cex-tab-load-slot');
    if (slot) { slot.hidden = true; slot.innerHTML = ''; }
  }

  function runHandlers(tabId) {
    var list = handlers[tabId] || [];
    if (!list.length) { clearSlot(tabId); return Promise.resolve(); }
    setLoading(tabId, true);
    return Promise.all(list.map(function (fn) {
      try { return Promise.resolve(fn()); }
      catch (e) { return Promise.reject(e); }
    })).then(function () {
      clearSlot(tabId);
    }).catch(function () {
      setError(tabId, 'Request timed out or failed.', function () { loadTab(tabId, true); });
    });
  }

  function loadTab(tabId, force) {
    if (!force && loaded[tabId]) return;
    loaded[tabId] = true;
    return runHandlers(tabId);
  }

  function stopPoll(tabId) {
    if (pollTimers[tabId]) {
      clearInterval(pollTimers[tabId]);
      pollTimers[tabId] = null;
    }
  }

  function startPoll(tabId, fn, ms) {
    stopPoll(tabId);
    pollTimers[tabId] = setInterval(fn, ms || 15000);
  }

  function applyTab(tabId) {
    if (!TAB_LABELS[tabId]) tabId = 'trade';
    document.querySelectorAll('.cex-tab-shell[data-cex-tab]').forEach(function (el) {
      var on = el.getAttribute('data-cex-tab') === tabId;
      el.hidden = !on;
      el.classList.toggle('active', on);
    });
    var nav = q('cex-hub-nav');
    if (nav) {
      nav.querySelectorAll('.cex-hub-tab').forEach(function (btn) {
        var on = btn.getAttribute('data-cex-tab') === tabId;
        btn.classList.toggle('active', on);
        btn.setAttribute('aria-selected', on ? 'true' : 'false');
      });
    }
    var note = q('cex-route-note');
    if (note) note.textContent = 'Viewing: ' + (TAB_LABELS[tabId] || tabId) + '. Data loads when you open each tab.';
    try {
      var url = new URL(window.location.href);
      if (tabId === 'trade') url.searchParams.delete('hub');
      else url.searchParams.set('hub', tabId);
      var swapTab = url.searchParams.get('tab');
      var hash = window.location.hash || '';
      window.history.replaceState({}, document.title, url.pathname + url.search + hash);
    } catch (e) { /* ignore */ }
    loadTab(tabId);
    Object.keys(pollTimers).forEach(function (k) {
      if (k !== tabId) stopPoll(k);
    });
    if (tabId === 'bots') {
      startPoll('bots', function () {
        if (window.CexMarketplace && window.CexMarketplace.pollBots) window.CexMarketplace.pollBots();
      }, 15000);
    }
  }

  function onTab(tabId, fn) {
    if (!handlers[tabId]) handlers[tabId] = [];
    handlers[tabId].push(fn);
  }

  function initNav() {
    var nav = q('cex-hub-nav');
    if (!nav) return;
    nav.addEventListener('click', function (ev) {
      var btn = ev.target.closest('[data-cex-tab]');
      if (!btn || !nav.contains(btn)) return;
      applyTab(btn.getAttribute('data-cex-tab'));
    });
    document.querySelectorAll('[data-cex-goto]').forEach(function (a) {
      a.addEventListener('click', function (ev) {
        var tab = a.getAttribute('data-cex-goto');
        if (!tab) return;
        ev.preventDefault();
        applyTab(tab);
        var hash = a.getAttribute('href');
        if (hash && hash.charAt(0) === '#') {
          var target = document.querySelector(hash);
          if (target) setTimeout(function () { target.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 120);
        }
      });
    });
    var hub = new URLSearchParams(window.location.search).get('hub');
    var valid = Object.prototype.hasOwnProperty.call(TAB_LABELS, hub);
    applyTab(valid ? hub : 'trade');
  }

  function renderHealth(data) {
    var el = q('cex-health-summary');
    if (!el) return;
    if (!data) { el.textContent = 'Health unavailable.'; return; }
    var kill = data.kill_switch ? 'ON — trading paused' : 'off';
    el.innerHTML =
      '<span class="cex-mon-kpi"><b>' + (data.service || 'exchange') + '</b> service</span>' +
      '<span class="cex-mon-kpi">Kill switch <b>' + kill + '</b></span>' +
      '<span class="cex-mon-kpi">Agents <b>' + (data.agent_count || 0) + '</b></span>' +
      '<span class="cex-mon-kpi">Fees <b>' + Number(data.treasury_fees_mn2 || 0).toFixed(4) + '</b> MN2</span>';
  }

  function renderSalesPool(data) {
    var el = q('cex-liquidity-summary');
    if (!el) return;
    if (!data || !data.success) { el.textContent = 'Sales pool status unavailable.'; return; }
    var pool = data.pool_assets || {};
    var keys = Object.keys(pool).filter(function (k) { return Number(pool[k]) > 0; });
    var lines = keys.length
      ? keys.map(function (k) { return k + ': ' + Number(pool[k]).toFixed(4); }).join(' · ')
      : 'No pooled balances yet.';
    el.innerHTML =
      '<div class="cex-mon-kpi"><b>' + (data.enabled ? 'Enabled' : 'Disabled') + '</b> sweep</div>' +
      '<div class="cex-muted">' + lines + '</div>' +
      '<div class="cex-muted">Ledger rows: ' + (data.ledger_rows || 0) + ' · last transfer: ' + (data.last_transfer_at || '—') + '</div>';
  }

  function renderTreasury(data) {
    var el = q('cex-treasury-summary');
    if (!el) return;
    if (!data || !data.success) { el.textContent = 'Treasury status unavailable.'; return; }
    el.innerHTML =
      '<div class="cex-mon-kpi"><b>$' + Number(data.ledger_stashed_usd || 0).toFixed(2) + '</b> stashed</div>' +
      '<div class="cex-muted">Paper $' + Number(data.ledger_stashed_usd_paper || 0).toFixed(2) +
      ' · Live $' + Number(data.ledger_stashed_usd_live || 0).toFixed(2) + '</div>' +
      '<div class="cex-muted">MN2 ' + Number(data.mn2_balance || 0).toFixed(4) +
      ' · wallet assets: ' + Object.keys(data.exchange_assets || {}).length + '</div>';
  }

  function renderVenues(data) {
    var el = q('cex-venues-summary');
    if (!el) return;
    if (!data || !data.success) { el.textContent = 'Venue readiness unavailable.'; return; }
    var rows = data.venues || [];
    el.innerHTML = rows.map(function (v) {
      var pill = v.live_ready ? 'cex-status-pill' : 'cex-status-pill muted';
      return '<div class="cex-watch-row"><b>' + (v.name || v.venue_id) + '</b>' +
        '<span class="' + pill + '">' + (v.live_ready ? 'live ready' : 'not ready') + '</span>' +
        '<span class="cex-muted">creds ' + (v.credentials_configured ? '✓' : '✗') +
        ' · live API ' + (v.live_supported ? '✓' : '✗') + '</span></div>';
    }).join('') || '<p class="cex-muted">No venues configured.</p>';
  }

  function loadLiquidityTab() {
    return fetchJson('/api/exchange/sales-pool/status', { timeout: 8000 }).then(renderSalesPool);
  }

  function loadTreasuryTab() {
    return fetchJson('/api/exchange/treasury/status', { timeout: 8000 }).then(renderTreasury);
  }

  function loadVenuesTab() {
    return fetchJson('/api/exchange/live/readiness', { timeout: 8000 }).then(renderVenues);
  }

  function loadOverviewHealth() {
    return fetchJson('/api/exchange/health', { timeout: 6000 }).then(renderHealth);
  }

  function renderProfitPathBaselines(data) {
    var el = q('cex-ppp-baselines');
    if (!el) return;
    if (!data || !data.success) { el.textContent = ''; return; }
    var total = data.total || 0;
    var rate = Number(data.success_rate_pct || 0).toFixed(0);
    el.innerHTML = 'Trade baselines: <b>' + total + '</b> (' + rate + '% success) · ' +
      '<a href="#" class="cex-mini-link" id="cex-ppp-baselines-link">view recent</a>';
    var link = q('cex-ppp-baselines-link');
    if (link) {
      link.onclick = function (e) {
        e.preventDefault();
        fetchJson('/api/exchange/profit-path/baselines?hours=168&limit=10', { timeout: 10000 })
          .then(function (d) {
            var rows = (d && d.baselines) || [];
            if (!rows.length) { alert('No baselines yet.'); return; }
            var lines = rows.map(function (b) {
              var p = b.predicted || {};
              var x = b.executed || {};
              return (b.ts || '').slice(0, 16) + ' ' + (b.source || '') + ' ' +
                (p.action_label || '') + ' → ' + (x.success ? 'OK' : 'fail') + ' (' + (x.mode || '') + ')';
            });
            alert('Recent baselines:\n' + lines.join('\n'));
          });
      };
    }
  }

  function renderProfitPathSummary(data) {
    var el = q('cex-ppp-summary');
    if (!el) return;
    if (!data || !data.success) { el.textContent = 'Profit path summary unavailable.'; return; }
    var topSkip = (data.top_skip_reasons && data.top_skip_reasons[0]) ? data.top_skip_reasons[0].reason : '—';
    el.innerHTML =
      '<span class="cex-mon-kpi">Scans <b>' + (data.scan_count || 0) + '</b></span>' +
      '<span class="cex-mon-kpi">Attempts <b>' + (data.attempt_count || 0) + '</b></span>' +
      '<span class="cex-mon-kpi">Fills <b>' + (data.fill_count || 0) + '</b></span>' +
      '<span class="cex-mon-kpi">Avg net <b>' + Number(data.avg_net_bps || 0).toFixed(1) + '</b> bps</span>' +
      '<span class="cex-mon-kpi">Hit rate <b>' + Number(data.hit_rate_pct || 0).toFixed(0) + '%</b></span>' +
      '<span class="cex-mon-kpi">Top skip <b>' + topSkip + '</b></span>';
  }

  function renderProfitPathTable(data) {
    var body = q('cex-ppp-table-body');
    if (!body) return;
    var rows = (data && data.paths) || [];
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="6" class="cex-muted">No matching paths.</td></tr>';
      return;
    }
    body.innerHTML = rows.map(function (r) {
      var v = r.venues || {};
      var route = (r.symbol || '') + ' ' + (v.buy || '?') + '→' + (v.sell || '?');
      var ts = (r.ts || '').replace('T', ' ').replace('Z', '');
      var note = r.skip_reason || ((r.execution && r.execution.realized_pnl_usd) ? ('$' + Number(r.execution.realized_pnl_usd).toFixed(2)) : '');
      return '<tr>' +
        '<td>' + ts.slice(0, 19) + '</td>' +
        '<td>' + (r.phase || '') + '</td>' +
        '<td>' + route + '</td>' +
        '<td>' + Number(r.net_bps || 0).toFixed(1) + '</td>' +
        '<td>' + (r.decision || '') + '</td>' +
        '<td class="cex-muted">' + (note || '—') + '</td></tr>';
    }).join('');
  }

  function renderSwapRotation(data) {
    var el = q('cex-swap-rotation');
    if (!el) return;
    var list = (data && data.actions) || [];
    if (!list.length) {
      el.innerHTML = '<p class="cex-muted">No rotation actions — funding looks OK or run more arb ticks.</p>';
      return;
    }
    var live = data.rotation_live_enabled ? 'live on' : 'dry-run only';
    el.innerHTML = '<p class="cex-muted" style="margin:0 0 6px">' + list.length + ' action(s) · ' + live + '</p>' +
      list.map(function (a) {
        var pri = a.priority || 'medium';
        return '<div class="cex-ppp-suggestion cex-ppp-suggestion--' + pri + '">' +
          '<span class="cex-badge">' + (a.type || 'action') + '</span> ' + (a.label || a.reason || '') + '</div>';
      }).join('');
  }

  function renderProfitPathSuggestions(data) {
    var el = q('cex-ppp-suggestions');
    if (!el) return;
    var list = (data && data.suggestions) || [];
    if (!list.length) { el.innerHTML = '<p class="cex-muted">No suggestions yet — run more arb ticks.</p>'; return; }
    el.innerHTML = list.map(function (s) {
      var pri = s.priority || 'medium';
      return '<div class="cex-ppp-suggestion cex-ppp-suggestion--' + pri + '">' +
        '<span class="cex-badge">' + pri + '</span> ' + (s.message || '') + '</div>';
    }).join('');
  }

  function profitPathQuery() {
    var agent = (q('cex-ppp-filter-agent') && q('cex-ppp-filter-agent').value || '').trim();
    var symbol = (q('cex-ppp-filter-symbol') && q('cex-ppp-filter-symbol').value || '').trim();
    var hours = (q('cex-ppp-filter-hours') && q('cex-ppp-filter-hours').value) || '24';
    var decision = (q('cex-ppp-filter-decision') && q('cex-ppp-filter-decision').value || '').trim();
    var qs = '?hours=' + encodeURIComponent(hours) + '&limit=50';
    if (agent) qs += '&agent=' + encodeURIComponent(agent);
    if (symbol) qs += '&symbol=' + encodeURIComponent(symbol);
    if (decision) qs += '&decision=' + encodeURIComponent(decision);
    return qs;
  }

  function loadProfitPathResearch() {
    var qs = profitPathQuery();
    return Promise.all([
      fetchJson('/api/exchange/profit-path/summary' + qs.replace(/&limit=\d+/, ''), { timeout: 10000 }).then(renderProfitPathSummary),
      fetchJson('/api/exchange/profit-path/search' + qs, { timeout: 10000 }).then(renderProfitPathTable),
      fetchJson('/api/exchange/profit-path/suggestions', { timeout: 10000 }).then(renderProfitPathSuggestions),
      fetchJson('/api/exchange/profit-path/baselines/summary?hours=168', { timeout: 10000 }).then(renderProfitPathBaselines),
      fetchJson('/api/exchange/swap-rotation/suggestions?hours=24&limit=8', { timeout: 10000 }).then(renderSwapRotation),
    ]);
  }

  function initProfitPathFilters() {
    var btn = q('cex-ppp-search-btn');
    if (!btn || btn._pppBound) return;
    btn._pppBound = true;
    btn.addEventListener('click', function () {
      loaded.bots = false;
      loadTab('bots', true);
    });
  }

  onTab('overview', loadOverviewHealth);
  onTab('liquidity', loadLiquidityTab);
  onTab('treasury', loadTreasuryTab);
  onTab('venues', loadVenuesTab);
  onTab('bots', function () {
    initProfitPathFilters();
    return loadProfitPathResearch();
  });

  window.ExchangeHub = {
    onTab: onTab,
    applyTab: applyTab,
    loadTab: loadTab,
    fetchJson: fetchJson,
    setLoading: setLoading,
    setError: setError,
    clearSlot: clearSlot,
    TAB_LABELS: TAB_LABELS,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNav);
  } else {
    initNav();
  }
})();
