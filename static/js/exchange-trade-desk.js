/**
 * Exchange trade desk — external pairs, broadcast monitor, market flow, PayPal sell, quick swap
 */
(function () {
  'use strict';

  var externalPrices = null;
  var sellCapStatus = null;
  var flowPaused = false;
  var flowTimer = null;
  var broadcastTimer = null;
  var selectedVenue = 'internal';
  var quickSwapQuote = null;
  var broadcastEs = null;
  var sseState = 'connecting';
  var flowSort = 'spread';
  var flowMinBps = 0;
  var lastFlowPairs = [];

  function q(id) { return document.getElementById(id); }

  function cexToast(text, type) {
    var host = q('cex-toast-host');
    if (!host) return;
    var el = document.createElement('div');
    el.className = 'cex-toast ' + (type === 'err' ? 'err' : type === 'warn' ? 'warn' : 'ok');
    el.textContent = text;
    host.appendChild(el);
    setTimeout(function () {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 4200);
  }
  window.cexToast = cexToast;

  function setSseStatus(state, label) {
    sseState = state;
    var el = q('cex-sse-status');
    var foot = q('cex-footer-sse');
    var txt = label || state;
    if (el) {
      el.className = 'cex-sse-status ' + state;
      el.textContent = '● ' + txt;
    }
    if (foot) foot.textContent = 'stream ' + txt;
  }

  function uid() {
    try { return localStorage.getItem('game_user_id') || 'default_user'; }
    catch (e) { return 'default_user'; }
  }

  function isAuthed() {
    var u = uid();
    return u && u !== 'default_user' && !u.startsWith('anon_');
  }

  function fmt(n, d) {
    var x = Number(n || 0);
    if (!isFinite(x)) return '—';
    if (x > 0 && x < 0.0001) return x.toExponential(3);
    return x.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: d == null ? 6 : d });
  }

  function fetchJson(path, opts) {
    if (window.ExchangeHub && window.ExchangeHub.fetchJson) {
      return window.ExchangeHub.fetchJson(path, opts || { timeout: 8000 });
    }
    return fetch(path, { credentials: 'same-origin' }).then(function (r) { return r.json(); });
  }

  function postJson(path, body) {
    body = body || {};
    body.user_id = uid();
    return fetch(path, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(function (r) { return r.json(); });
  }

  function renderSecurityBar() {
    var el = q('cex-security-bar');
    if (!el) return;
    if (!isAuthed()) {
      el.innerHTML =
        '<span class="cex-status-pill-inline warn">🔒 Guest mode — <a href="/profile" class="cex-mini-link">sign in</a> to trade &amp; PayPal</span>';
      return;
    }
    fetchJson('/api/exchange/risk/me?user_id=' + encodeURIComponent(uid())).then(function (r) {
      if (!r || !r.success) {
        el.innerHTML = '<span class="cex-status-pill-inline ok">🔐 Account linked</span>';
        return;
      }
      var lim = r.limits || {};
      var sellRem = r.sell_daily_remaining_usd;
      var pills =
        '<span class="cex-status-pill-inline ok">🔐 Secured · ' + uid().slice(0, 12) + '</span>' +
        '<span class="cex-status-pill-inline">Buy today $' + fmt(r.spent_day_usd, 2) +
        (lim.daily_fiat_buy_usd_cap ? ' / $' + fmt(lim.daily_fiat_buy_usd_cap, 0) : '') + '</span>';
      if (sellRem != null) {
        pills += '<span class="cex-status-pill-inline">PayPal sell left $' + fmt(sellRem, 2) + '</span>';
        if (sellRem <= 0) {
          pills += '<span class="cex-status-pill-inline warn cex-cooldown-pill">Daily sell cap reached</span>';
        } else if (sellRem < 100) {
          pills += '<span class="cex-status-pill-inline warn">Low sell quota</span>';
        }
      }
      el.innerHTML = pills;
    }).catch(function () {
      el.innerHTML = '<span class="cex-status-pill-inline ok">🔐 Account active</span>';
    });
  }

  function renderBroadcast(data) {
    var dot = q('cex-broadcast-dot');
    var kpis = q('cex-broadcast-kpis');
    var feed = q('cex-broadcast-feed');
    if (!feed) return;
    var monitor = (data && data.monitor) ? data.monitor : data;
    if (!monitor || !monitor.success) {
      if (dot) dot.className = 'cex-live-pulse off';
      feed.innerHTML = '<div class="cex-empty-hint cex-empty-hint--icon">🤖 Daemon monitor unavailable — open Bots tab or run a tick.</div>';
      return;
    }
    if (dot) dot.className = 'cex-live-pulse' + ((monitor.totals && monitor.totals.active_bots) ? '' : ' off');
    var t = monitor.totals || {};
    var metrics = data.daemon_metrics || monitor.daemon_metrics;
    if (kpis) {
      kpis.innerHTML =
        '<span class="cex-broadcast-kpi"><b>$' + fmt(t.realized_profit_usd, 2) + '</b> realized</span>' +
        '<span class="cex-broadcast-kpi"><b>' + (t.active_bots || 0) + '/' + (t.bot_count || 0) + '</b> bots</span>' +
        '<span class="cex-broadcast-kpi">IQ <b>' + (t.avg_intelligence || 100) + '</b></span>';
      if (metrics && metrics.loops) {
        var loops = metrics.loops || [];
        var fresh = loops.filter(function (l) { return !l.stale; }).length;
        kpis.innerHTML += '<span class="cex-broadcast-kpi"><b>' + fresh + '/' + loops.length + '</b> loops fresh</span>';
      }
    }
    var rows = monitor.feed || [];
    feed.innerHTML = rows.length
      ? rows.slice(0, 12).map(function (f) {
        var when = f.ts ? new Date(f.ts).toLocaleTimeString() : '';
        var kind = f.scope === 'you' ? 'you' : (f.type || 'event');
        return '<div class="cex-broadcast-row ' + (f.scope === 'you' ? 'you' : 'market') + '">' +
          '<span>' + (f.icon || '•') + '</span>' +
          '<span><span class="cex-event-type">' + kind + '</span> ' + (f.text || '') + '</span>' +
          '<span class="cex-muted">' + when + '</span></div>';
      }).join('')
      : '<div class="cex-empty-hint cex-empty-hint--icon">📭 No daemon activity yet — rent a bot or run a tick.</div>';
  }

  function loadBroadcast() {
    return fetchJson('/api/exchange/monitor/live?limit=20&include_metrics=1').then(function (data) {
      renderBroadcast({ monitor: data, daemon_metrics: data.daemon_metrics });
    }).catch(function () {
      var feed = q('cex-broadcast-feed');
      if (feed) feed.innerHTML = '<div class="cex-empty-hint cex-empty-hint--icon">⚠️ Broadcast fetch failed — retrying…</div>';
      cexToast('Live broadcast unavailable', 'warn');
    });
  }

  function sortFlowPairs(pairs) {
    var list = pairs.slice();
    if (flowSort === 'symbol') {
      list.sort(function (a, b) { return String(a.symbol).localeCompare(String(b.symbol)); });
    } else {
      list.sort(function (a, b) {
        function spreadOf(p) {
          var internal = Number(p.internal_usd || 0);
          var bin = (p.venues && p.venues.binance) || {};
          var nk = (p.venues && p.venues.nonkyc) || {};
          var ref = Number(bin.mid || 0) || Number(nk.mid || 0) || internal;
          return ref > 0 ? Math.abs((internal - ref) / ref * 10000) : 0;
        }
        return spreadOf(b) - spreadOf(a);
      });
    }
    if (flowMinBps > 0) {
      list = list.filter(function (p) {
        var internal = Number(p.internal_usd || 0);
        var bin = (p.venues && p.venues.binance) || {};
        var nk = (p.venues && p.venues.nonkyc) || {};
        var ref = Number(bin.mid || 0) || Number(nk.mid || 0) || internal;
        var spreadBps = ref > 0 ? Math.abs((internal - ref) / ref * 10000) : 0;
        return spreadBps >= flowMinBps;
      });
    }
    return list;
  }

  function updateVenueBadges(data) {
    var ok = data && data.success && (data.pairs || []).length > 0;
    document.querySelectorAll('.cex-venue-chip--trade').forEach(function (chip) {
      var badge = chip.querySelector('.cex-venue-badge');
      if (!badge) return;
      var venue = chip.getAttribute('data-venue');
      if (venue === 'internal') {
        badge.className = 'cex-venue-badge cex-venue-badge--live';
        badge.textContent = 'live';
      } else if (!ok) {
        badge.className = 'cex-venue-badge cex-venue-badge--offline';
        badge.textContent = 'offline';
      } else {
        badge.className = 'cex-venue-badge cex-venue-badge--paper';
        badge.textContent = 'paper';
      }
    });
  }

  function handleBroadcastEvent(data) {
    if (!data) return;
    if (data.monitor) renderBroadcast(data);
    if (data.prices && data.prices.success) renderMarketFlow(data.prices);
  }

  function startBroadcastStream() {
    if (typeof EventSource === 'undefined') {
      setSseStatus('polling', 'polling fallback');
      startPolling();
      return;
    }
    try {
      if (broadcastEs) { broadcastEs.close(); broadcastEs = null; }
      setSseStatus('reconnecting', 'connecting');
      broadcastEs = new EventSource('/api/exchange/stream?interval=10&limit=20');
      broadcastEs.onopen = function () { setSseStatus('connected', 'SSE live'); };
      broadcastEs.onmessage = function (ev) {
        setSseStatus('connected', 'SSE live');
        try {
          var data = JSON.parse(ev.data);
          if (data.type === 'broadcast') handleBroadcastEvent(data);
        } catch (e) { /* ignore */ }
      };
      broadcastEs.onerror = function () {
        setSseStatus('reconnecting', 'reconnecting…');
        if (broadcastEs) { broadcastEs.close(); broadcastEs = null; }
        startPolling();
      };
    } catch (e) {
      setSseStatus('polling', 'polling fallback');
      startPolling();
    }
  }

  function renderMarketFlow(data) {
    var grid = q('cex-flow-grid');
    var stale = q('cex-flow-stale');
    if (!grid) return;
    if (flowPaused) return;
    if (!data || !data.success) {
      grid.innerHTML = '<div class="cex-empty-hint cex-empty-hint--icon">⚠️ Could not load external prices.</div>';
      updateVenueBadges(null);
      return;
    }
    externalPrices = data;
    lastFlowPairs = data.pairs || [];
    updateVenueBadges(data);
    if (stale) stale.textContent = data.scanned_at ? 'Updated ' + String(data.scanned_at).slice(11, 19) + ' UTC' : '';
    var pairs = sortFlowPairs(lastFlowPairs);
    if (!pairs.length) {
      grid.innerHTML = '<div class="cex-empty-hint cex-empty-hint--icon">🔍 No pairs match filter — lower min bps.</div>';
      return;
    }
    grid.innerHTML = pairs.slice(0, 16).map(function (p) {
      var internal = Number(p.internal_usd || 0);
      var bin = (p.venues && p.venues.binance) || {};
      var nk = (p.venues && p.venues.nonkyc) || {};
      var binMid = Number(bin.mid || 0);
      var nkMid = Number(nk.mid || 0);
      var ref = binMid || nkMid || internal;
      var spreadBps = ref > 0 ? ((internal - ref) / ref * 10000) : 0;
      var spreadCls = spreadBps >= 0 ? 'spread-up' : 'spread-down';
      return '<div class="cex-flow-card">' +
        '<div><span class="sym">' + p.symbol + '</span></div>' +
        '<div class="venue-tag">Int $' + fmt(internal, internal < 1 ? 4 : 2) + '</div>' +
        (binMid ? '<div class="venue-tag">Binance $' + fmt(binMid, binMid < 1 ? 4 : 2) + '</div>' : '') +
        (nkMid ? '<div class="venue-tag">NonKYC $' + fmt(nkMid, nkMid < 1 ? 4 : 2) + '</div>' : '') +
        '<div class="' + spreadCls + '">Δ ' + fmt(spreadBps, 1) + ' bps</div></div>';
    }).join('');
  }

  function loadMarketFlow() {
    if (flowPaused) return Promise.resolve();
    var grid = q('cex-flow-grid');
    if (grid && !grid.querySelector('.cex-flow-card')) {
      grid.innerHTML = '<div class="cex-empty-hint">Loading market flows…</div>';
    }
    return fetchJson('/api/exchange/external/prices?venues=binance,nonkyc').then(renderMarketFlow);
  }

  function loadSellCapStatus() {
    return fetchJson('/api/exchange/paypal/sell-price-cap/status').then(function (d) {
      sellCapStatus = d;
      var note = q('cex-sell-cap-note');
      if (note && d && d.success) {
        var lim = d.limits || {};
        note.textContent = 'Price cap: min(internal, Binance/NonKYC ref). Max $' +
          fmt(lim.max_usd, 0) + '/tx · $' + fmt(lim.max_usd_daily, 0) + '/day · fee ' +
          (lim.fee_bps || 0) + ' bps. Refreshed ' + (d.updated_at ? String(d.updated_at).slice(0, 16).replace('T', ' ') : 'on first quote') + '.';
      }
    });
  }

  function decorateAssetRows(symbol) {
    if (!externalPrices || !externalPrices.pairs) return;
    var row = document.querySelector('.cex-asset-row[data-sym="' + symbol + '"]');
    if (!row) return;
    var pair = externalPrices.pairs.find(function (p) { return p.symbol === symbol; });
    if (!pair) return;
    var old = row.querySelector('.ext-prices');
    if (old) old.remove();
    var bin = (pair.venues && pair.venues.binance) || {};
    var nk = (pair.venues && pair.venues.nonkyc) || {};
    var parts = [];
    if (bin.mid) parts.push('BN ' + fmt(bin.mid, bin.mid < 1 ? 4 : 2));
    if (nk.mid) parts.push('NK ' + fmt(nk.mid, nk.mid < 1 ? 4 : 2));
    if (parts.length) {
      var span = document.createElement('span');
      span.className = 'ext-prices';
      span.textContent = parts.join(' · ');
      row.querySelector('.sym').parentNode.appendChild(span);
    }
  }

  function updateVenueBadge() {
    var badge = q('cex-pair-source-badge');
    if (!badge) return;
    if (selectedVenue === 'internal') {
      badge.textContent = 'internal';
      badge.className = 'cex-pair-badge cex-pair-badge--internal';
    } else {
      badge.textContent = selectedVenue;
      badge.className = 'cex-pair-badge cex-pair-badge--external';
    }
  }

  function initVenueChips() {
    document.querySelectorAll('.cex-venue-chip--trade').forEach(function (chip) {
      chip.addEventListener('click', function () {
        document.querySelectorAll('.cex-venue-chip--trade').forEach(function (c) { c.classList.remove('active'); c.setAttribute('aria-pressed', 'false'); });
        chip.classList.add('active');
        chip.setAttribute('aria-pressed', 'true');
        selectedVenue = chip.getAttribute('data-venue') || 'internal';
        updateVenueBadge();
        quickSwapQuote = null;
        try {
          document.dispatchEvent(new CustomEvent('cex-venue-change', { detail: { venue: selectedVenue } }));
        } catch (e) { /* ignore */ }
        if (window.CexTradeDesk && window.CexTradeDesk.onVenueChange) {
          window.CexTradeDesk.onVenueChange(selectedVenue);
        }
      });
    });
  }

  function doQuickSwapQuote() {
    var fromEl = q('cex-quick-from');
    var toEl = q('cex-quick-to');
    var amtEl = q('cex-quick-amount');
    var preview = q('cex-quick-preview');
    var msg = q('cex-msg');
    if (!fromEl || !toEl || !amtEl) return;
    var from = fromEl.value;
    var to = toEl.value;
    var amt = parseFloat(amtEl.value || '0');
    quickSwapQuote = null;
    if (!amt || from === to) {
      if (msg) msg.textContent = 'Pick two different assets and an amount.';
      return;
    }
    if (preview) preview.textContent = 'Quoting ' + from + ' → ' + to + '…';
    postJson('/api/exchange/quick-swap/quote', {
      from_asset: from,
      to_asset: to,
      amount: amt,
      venue: selectedVenue,
    }).then(function (res) {
      if (!res.success) {
        if (preview) preview.textContent = res.error || 'Quote failed';
        return;
      }
      quickSwapQuote = res;
      var legTxt = (res.legs || []).map(function (l) {
        return 'Leg ' + l.leg + ': ' + (l.action || l.side + ' ' + l.symbol);
      }).join(' · ');
      if (preview) {
        preview.textContent = 'Est. ~' + fmt(res.estimated_output, 6) + ' ' + to +
          ' (' + (res.leg_count || 1) + ' leg' + ((res.leg_count || 1) > 1 ? 's' : '') + ' via ' + (res.venue || 'internal') + ')' +
          (legTxt ? ' — ' + legTxt : '');
      }
    });
  }

  function doQuickSwapExecute() {
    if (!isAuthed()) {
      if (q('cex-msg')) q('cex-msg').textContent = 'Sign in to execute quick swap.';
      return;
    }
    if (!quickSwapQuote) {
      doQuickSwapQuote();
      return;
    }
    var fromEl = q('cex-quick-from');
    var toEl = q('cex-quick-to');
    var amtEl = q('cex-quick-amount');
    var preview = q('cex-quick-preview');
    postJson('/api/exchange/quick-swap/execute', {
      quote_id: quickSwapQuote.quote_id,
      from_asset: fromEl.value,
      to_asset: toEl.value,
      amount: parseFloat(amtEl.value || '0'),
      venue: selectedVenue,
    }).then(function (res) {
      if (q('cex-msg')) {
        q('cex-msg').textContent = res.success
          ? ('Quick swap done — ~' + fmt(res.estimated_output, 6) + ' ' + toEl.value)
          : (res.error || 'Quick swap failed');
      }
      if (res.success) {
        quickSwapQuote = null;
        if (preview) preview.textContent = '';
        if (window.CexTradeDesk && window.CexTradeDesk.refreshWallet) {
          window.CexTradeDesk.refreshWallet();
        }
      } else if (preview && res.failed_leg) {
        preview.textContent = 'Failed on leg ' + res.failed_leg + ': ' + (res.error || '');
      }
    });
  }

  function setPayPalSellStep(step) {
    var steps = document.querySelectorAll('#cex-sell-steps li');
    steps.forEach(function (li) {
      var n = parseInt(li.getAttribute('data-step'), 10);
      li.classList.remove('active', 'done');
      if (n < step) li.classList.add('done');
      if (n === step) li.classList.add('active');
    });
  }

  function doPayPalSellQuote() {
    setPayPalSellStep(1);
    var amt = parseFloat((q('cex-paypal-sell-amount') || {}).value || '0');
    var sym = window.CexTradeDesk && window.CexTradeDesk.getSelected ? window.CexTradeDesk.getSelected() : 'BTC';
    var preview = q('cex-paypal-sell-preview');
    if (!amt) {
      if (preview) preview.textContent = 'Enter amount to sell.';
      return;
    }
    postJson('/api/exchange/paypal/crypto-sell-quote', { symbol: sym, amount: amt }).then(function (q) {
      if (!q || !q.success) {
        if (preview) preview.textContent = (q && q.error) || 'Sell quote failed';
        cexToast((q && q.error) || 'Sell quote failed', 'err');
        return;
      }
      setPayPalSellStep(2);
      var cap = q.price_capped ? ' (capped vs external ref)' : '';
      preview.textContent = 'Sell ' + fmt(q.asset_amount, 8) + ' ' + q.symbol +
        ' → $' + fmt(q.usd_amount, 2) + ' PayPal' + cap +
        ' · ref $' + fmt(q.reference_usd, 2) + ' · fee $' + fmt(q.fee_usd, 2);
      preview.dataset.quoteId = q.quote_id || '';
      cexToast('Sell quote ready — confirm to queue PayPal', 'ok');
    });
  }

  function doPayPalSell() {
    if (!isAuthed()) {
      if (q('cex-msg')) q('cex-msg').textContent = 'Sign in to sell crypto via PayPal.';
      return;
    }
    var amt = parseFloat((q('cex-paypal-sell-amount') || {}).value || '0');
    var sym = window.CexTradeDesk && window.CexTradeDesk.getSelected ? window.CexTradeDesk.getSelected() : 'BTC';
    var preview = q('cex-paypal-sell-preview');
    var quoteId = preview && preview.dataset.quoteId;
    if (!quoteId) {
      doPayPalSellQuote();
      return;
    }
    if (!window.confirm('Confirm PayPal sell of ' + amt + ' ' + sym + '? Funds queue to PayPal after capture.')) {
      return;
    }
    setPayPalSellStep(3);
    postJson('/api/exchange/paypal/crypto-sell', { symbol: sym, amount: amt, quote_id: quoteId }).then(function (res) {
      if (q('cex-msg')) q('cex-msg').textContent = res.success
        ? ('Sold — $' + fmt((res.payout && res.payout.usd_amount) || 0, 2) + ' queued for PayPal')
        : (res.error || 'Sell failed');
      if (res.success) {
        cexToast('PayPal sell queued', 'ok');
        setPayPalSellStep(1);
        if (preview) { preview.textContent = ''; preview.dataset.quoteId = ''; }
        if (window.CexTradeDesk && window.CexTradeDesk.refreshWallet) {
          window.CexTradeDesk.refreshWallet();
        }
      } else {
        cexToast(res.error || 'Sell failed', 'err');
        setPayPalSellStep(2);
      }
      loadSellCapStatus();
      renderSecurityBar();
    });
  }

  function initCollapsible() {
    document.querySelectorAll('.cex-collapse-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var targetId = btn.getAttribute('data-collapse');
        var body = q(targetId);
        var section = btn.closest('.cex-collapsible');
        if (!body || !section) return;
        var collapsed = section.classList.toggle('collapsed');
        btn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        btn.textContent = collapsed ? '▶' : '▼';
      });
    });
  }

  function initFlowFilters() {
    var sortEl = q('cex-flow-sort');
    var minEl = q('cex-flow-min-bps');
    if (sortEl) {
      sortEl.addEventListener('change', function () {
        flowSort = sortEl.value;
        if (lastFlowPairs.length) renderMarketFlow(externalPrices);
      });
    }
    if (minEl) {
      minEl.addEventListener('change', function () {
        flowMinBps = parseFloat(minEl.value || '0') || 0;
        if (lastFlowPairs.length) renderMarketFlow(externalPrices);
      });
    }
  }

  function initOnboarding() {
    var banner = q('cex-onboard-banner');
    var dismiss = q('cex-onboard-dismiss');
    if (!banner) return;
    try {
      if (!localStorage.getItem('cex_onboard_dismissed')) banner.hidden = false;
    } catch (e) { banner.hidden = false; }
    if (dismiss) {
      dismiss.addEventListener('click', function () {
        banner.hidden = true;
        try { localStorage.setItem('cex_onboard_dismissed', '1'); } catch (e) {}
      });
    }
  }

  function initPriceAlertStub() {
    var btn = q('cex-price-alert-btn');
    if (!btn) return;
    btn.addEventListener('click', function () {
      cexToast('Price alerts coming soon — stub saved locally', 'warn');
      try {
        var n = parseInt(localStorage.getItem('cex_alert_stub') || '0', 10) + 1;
        localStorage.setItem('cex_alert_stub', String(n));
        var badge = q('cex-alert-badge');
        if (badge) badge.textContent = String(n);
      } catch (e) {}
    });
    try {
      var count = localStorage.getItem('cex_alert_stub') || '0';
      var badge = q('cex-alert-badge');
      if (badge) badge.textContent = count;
    } catch (e) {}
  }

  function initFlowControls() {
    var pause = q('cex-flow-pause');
    var refresh = q('cex-flow-refresh');
    if (pause) {
      pause.addEventListener('click', function () {
        flowPaused = !flowPaused;
        pause.textContent = flowPaused ? '▶ Resume' : '⏸ Pause';
        if (!flowPaused) loadMarketFlow();
      });
    }
    if (refresh) refresh.addEventListener('click', function () { loadMarketFlow(); });
  }

  function startPolling() {
    stopPolling();
    setSseStatus('polling', 'polling fallback');
    broadcastTimer = setInterval(loadBroadcast, 20000);
    flowTimer = setInterval(function () { if (!flowPaused) loadMarketFlow(); }, 30000);
  }

  function stopPolling() {
    if (broadcastTimer) { clearInterval(broadcastTimer); broadcastTimer = null; }
    if (flowTimer) { clearInterval(flowTimer); flowTimer = null; }
  }

  function stopBroadcastStream() {
    if (broadcastEs) { broadcastEs.close(); broadcastEs = null; }
    stopPolling();
  }

  function init() {
    renderSecurityBar();
    loadBroadcast();
    loadMarketFlow();
    loadSellCapStatus();
    initVenueChips();
    initFlowControls();
    initFlowFilters();
    initCollapsible();
    initOnboarding();
    initPriceAlertStub();
    updateVenueBadge();

    var qsBtn = q('cex-quick-quote-btn');
    if (qsBtn) qsBtn.addEventListener('click', doQuickSwapQuote);
    var qsExec = q('cex-quick-execute-btn');
    if (qsExec) qsExec.addEventListener('click', doQuickSwapExecute);
    var sellQ = q('cex-paypal-sell-quote-btn');
    if (sellQ) sellQ.addEventListener('click', doPayPalSellQuote);
    var sellBtn = q('cex-paypal-sell-btn');
    if (sellBtn) sellBtn.addEventListener('click', doPayPalSell);

    if (window.ExchangeHub) {
      window.ExchangeHub.onTab('trade', function () {
        renderSecurityBar();
        return Promise.all([loadBroadcast(), loadMarketFlow(), loadSellCapStatus()]);
      });
    }
    startBroadcastStream();

    document.addEventListener('visibilitychange', function () {
      if (document.hidden) stopBroadcastStream();
      else {
        startBroadcastStream();
        loadMarketFlow();
      }
    });
  }

  window.CexTradeDesk = {
    getSelected: function () {
      return (window.CexTradeDesk._selected) || 'BTC';
    },
    getVenue: function () {
      return selectedVenue || 'internal';
    },
    setSelected: function (sym) {
      window.CexTradeDesk._selected = sym;
      decorateAssetRows(sym);
    },
    onVenueChange: function (venue) { selectedVenue = venue; },
    refreshWallet: function () {},
    reloadExternal: loadMarketFlow,
    decorateAssetRows: decorateAssetRows,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
