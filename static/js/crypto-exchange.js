/**
 * MasterNoder Crypto Exchange UI — /api/exchange/*
 */
(function () {
  'use strict';

  var selected = 'BTC';
  var catalog = null;
  var lastQuote = null;
  var termsVersion = '2026-06-v1';

  function uid() {
    try { return localStorage.getItem('game_user_id') || 'default_user'; }
    catch (e) { return 'default_user'; }
  }

  function q(id) { return document.getElementById(id); }

  function msg(t) { var el = q('cex-msg'); if (el) el.textContent = t || ''; }

  function fmt(n, d) {
    var x = Number(n || 0);
    if (!isFinite(x)) return '—';
    if (x > 0 && x < 0.0001) return x.toExponential(4);
    return x.toLocaleString(undefined, { minimumFractionDigits: d || 0, maximumFractionDigits: d || 8 });
  }

  function getJson(path) {
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

  function renderAssets(assets) {
    var list = q('cex-asset-list');
    var search = (q('cex-asset-search') || {}).value || '';
    search = search.toLowerCase();
    if (!list) return;
    var rows = (assets || []).filter(function (a) {
      if (!search) return true;
      return (a.symbol + ' ' + a.name).toLowerCase().indexOf(search) >= 0;
    });
    list.innerHTML = rows.map(function (a) {
      var cls = a.symbol === selected ? 'cex-asset-row active' : 'cex-asset-row';
      return '<div class="' + cls + '" data-sym="' + a.symbol + '">' +
        '<span><span class="sym">' + a.symbol + '</span> ' + a.name + '</span>' +
        '<span class="price">$' + fmt(a.price_usd, a.price_usd < 1 ? 6 : 2) + '</span></div>';
    }).join('');
    list.querySelectorAll('[data-sym]').forEach(function (row) {
      row.addEventListener('click', function () {
        selected = row.getAttribute('data-sym');
        renderAssets(assets);
        updateSelected();
        renderStaking(assets);
      });
    });
  }

  function updateSelected() {
    var el = q('cex-selected-asset');
    var lim = q('cex-limit-symbol');
    var asset = (catalog && catalog.assets || []).find(function (a) { return a.symbol === selected; });
    var label = asset ? asset.symbol + ' — ' + asset.name + ' ($' + fmt(asset.price_usd, 2) + ')' : selected;
    if (el) el.textContent = label;
    if (lim) lim.value = selected;
    if (q('cex-paypal-symbol')) q('cex-paypal-symbol').value = selected;
  }

  function renderWallet(w) {
    var el = q('cex-wallet-balances');
    if (!el || !w || !w.success) return;
    var assets = w.assets || {};
    var keys = Object.keys(assets).filter(function (k) { return Number(assets[k]) > 0; });
    if (!keys.length) {
      el.innerHTML = '<p class="cex-muted">No exchange balances yet. Buy assets via swap.</p>';
      return;
    }
    el.innerHTML = keys.map(function (k) {
      return '<div class="cex-wallet-row"><span>' + k + '</span><strong>' + fmt(assets[k], 8) + '</strong></div>';
    }).join('');
  }

  function renderRewards(r) {
    var tier = q('cex-fee-tier');
    if (tier && r && r.success) {
      tier.textContent = (r.tier && r.tier.label) || 'Bronze';
    }
    var bonusCard = q('cex-bonus-card');
    if (bonusCard && r && r.welcome_bonus_claimed) {
      bonusCard.innerHTML = '<p class="cex-muted">Welcome bonus already claimed.</p>';
    }
  }

  function renderTrades(trades) {
    var el = q('cex-recent-trades');
    if (!el) return;
    var rows = (trades && trades.trades) || [];
    if (!rows.length) { el.textContent = 'No trades yet.'; return; }
    el.innerHTML = rows.slice(0, 8).map(function (t) {
      var ts = (t.ts || '').slice(0, 19).replace('T', ' ');
      return '<div>' + ts + ' · ' + (t.symbol || '?') + ' ' + (t.side || t.type || '') + ' ' + fmt(t.amount, 6) + '</div>';
    }).join('');
  }

  function renderOrders(orders) {
    var el = q('cex-open-orders');
    if (!el) return;
    var rows = (orders && orders.orders) || [];
    if (!rows.length) { el.innerHTML = '<p class="cex-muted">No open limit orders.</p>'; return; }
    el.innerHTML = rows.map(function (o) {
      return '<div class="cex-wallet-row">' + o.symbol + ' ' + o.side + ' ' + fmt(o.remaining, 6) + ' @ ' + fmt(o.limit_price, 4) +
        ' <button type="button" class="cex-btn cex-btn--ghost" data-cancel="' + o.order_id + '">Cancel</button></div>';
    }).join('');
    el.querySelectorAll('[data-cancel]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        postJson('/api/exchange/orders/cancel', { order_id: btn.getAttribute('data-cancel') }).then(function (res) {
          msg(res.success ? 'Order cancelled' : (res.error || 'Failed'));
          refresh();
        });
      });
    });
  }

  function renderStaking(assets) {
    var el = q('cex-staking-list');
    if (!el) return;
    var stakeable = (assets || []).filter(function (a) { return Number(a.staking_apy_bps || 0) > 0; });
    el.innerHTML = stakeable.map(function (a) {
      var apy = (Number(a.staking_apy_bps) / 100).toFixed(2);
      return '<div class="cex-wallet-row"><span>' + a.symbol + ' (' + apy + '% APY)</span>' +
        '<button type="button" class="cex-btn cex-btn--ghost" data-stake="' + a.symbol + '">Claim daily</button></div>';
    }).join('');
    el.querySelectorAll('[data-stake]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        postJson('/api/exchange/staking/claim', { symbol: btn.getAttribute('data-stake') }).then(function (res) {
          msg(res.success ? ('Staking +' + fmt(res.reward, 8) + ' ' + res.symbol) : (res.error || 'Claim failed'));
          refresh();
        });
      });
    });
  }

  function renderPayPalMn2Packs(data) {
    var el = q('cex-paypal-mn2-packs');
    if (!el) return;
    var packs = (data && data.packs) || [];
    if (!packs.length) {
      el.innerHTML = '<p class="cex-muted">PayPal MN2 packs are not configured yet.</p>';
      return;
    }
    el.innerHTML = packs.map(function (p) {
      return '<article class="cex-pack"><strong>' + (p.name || p.id) + '</strong>' +
        '<span>$' + fmt(p.price_usd, 2) + ' -> ' + fmt(p.mn2_granted, 4) + ' MN2</span>' +
        '<button type="button" class="cex-btn cex-btn--primary" data-paypal-mn2="' + p.id + '">Buy with PayPal</button></article>';
    }).join('');
    el.querySelectorAll('[data-paypal-mn2]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        startPayPalMn2(btn.getAttribute('data-paypal-mn2'));
      });
    });
  }

  function renderAgents(data) {
    var summary = q('cex-agent-summary');
    var list = q('cex-agent-list');
    if (!summary || !list) return;
    var agents = (data && data.agents) || [];
    summary.textContent = (data && data.enabled ? 'Enabled' : 'Disabled') +
      ' · ' + agents.length + ' agents · tick #' + ((data && data.tick_count) || 0);
    if (!agents.length) {
      list.innerHTML = '<p class="cex-muted">No exchange agents configured.</p>';
      return;
    }
    list.innerHTML = agents.map(function (a) {
      var last = (a.state && a.state.last_action) || {};
      return '<div class="cex-agent-row"><strong>' + (a.name || a.id) + '</strong><br>' +
        (a.strategy || 'rotation') + ' · ' + ((a.assets || []).join(', ') || 'all') +
        (last.symbol ? '<br>Last: ' + last.side + ' ' + last.symbol + ' ' + fmt(last.amount, 6) : '') +
        '</div>';
    }).join('');
  }

  function renderProgress(data) {
    var summary = q('cex-progress-summary');
    var fill = q('cex-progress-fill');
    var scores = q('cex-high-scores');
    var status = q('cex-status-report');
    if (!summary || !data || !data.success) return;
    var tier = (data.tier && data.tier.label) || 'Bronze';
    summary.innerHTML =
      '<strong>$' + fmt(data.portfolio_value_usd, 2) + '</strong> portfolio · ' +
      fmt(data.asset_count, 0) + ' assets<br>' +
      '$' + fmt(data.volume_usd_30d, 2) + ' 30d volume · ' +
      fmt(data.trade_count, 0) + ' trades · ' + tier + ' tier';
    if (fill) fill.style.width = Math.max(0, Math.min(100, Number(data.tier_progress_pct || 0))) + '%';
    if (scores) {
      var hs = data.high_scores || {};
      scores.innerHTML =
        '<div>Portfolio rank: #' + (hs.portfolio_rank || '—') + '</div>' +
        '<div>Volume rank: #' + (hs.volume_rank || '—') + '</div>' +
        '<div>Open orders: ' + fmt(data.open_order_count, 0) + '</div>';
    }
    if (status) {
      var items = data.status_items || [];
      status.innerHTML = items.length
        ? items.map(function (it) { return '<span class="cex-status-pill">' + (it.text || '') + '</span>'; }).join('')
        : '<span class="cex-status-pill">Status clear.</span>';
    }
  }

  function renderProfitAgent(data) {
    var summary = q('cex-profit-summary');
    var insights = q('cex-profit-insights');
    var agents = q('cex-agent-performance');
    if (!summary || !data || !data.success) return;
    var roi = data.roi_pct == null ? '—' : (fmt(data.roi_pct, 2) + '%');
    summary.innerHTML =
      '<strong>$' + fmt(data.estimated_total_pnl_usd, 2) + '</strong> est. total P/L<br>' +
      'Realized: $' + fmt(data.realized_pnl_usd, 2) +
      ' · Unrealized: $' + fmt(data.unrealized_pnl_usd, 2) + '<br>' +
      'ROI: ' + roi +
      ' · Fees: $' + fmt(data.fees_paid_usd, 2) +
      ' · 30d projection: $' + fmt(data.monthly_projection_usd, 2);
    if (insights) {
      var rows = data.insights || [];
      insights.innerHTML = rows.length
        ? rows.map(function (it) { return '<span class="cex-status-pill">' + (it.text || '') + '</span>'; }).join('')
        : '<span class="cex-status-pill">No profit signals yet.</span>';
    }
    if (agents) {
      var perf = data.agent_performance || [];
      agents.innerHTML = perf.length
        ? perf.slice(0, 4).map(function (a) {
          var pnl = Number(a.realized_pnl_usd || 0) + Number(a.unrealized_pnl_usd || 0);
          return '<div class="cex-agent-row"><strong>' + a.agent_id + '</strong><br>' +
            'P/L: $' + fmt(pnl, 2) + ' · portfolio: $' + fmt(a.portfolio_value_usd, 2) +
            ' · trades: ' + fmt(a.trade_count, 0) + '</div>';
        }).join('')
        : '<p class="cex-muted">Agent performance will appear after daemon trades.</p>';
    }
  }

  function renderGatewayStatus(data) {
    var el = q('cex-gateway-status');
    if (!el || !data || !data.success) return;
    var totals = data.totals || {};
    var checks = data.ready_checks || [];
    var ready = data.ready ? 'Ready' : 'Needs ops check';
    el.innerHTML =
      '<strong>' + ready + '</strong> · pending: ' + fmt(totals.pending_count, 0) +
      ' · captured: ' + fmt(totals.captured_count, 0) +
      ' · expired: ' + fmt(totals.expired_pending_count, 0) +
      '<div class="cex-status-report">' +
      checks.map(function (c) {
        return '<span class="cex-status-pill">' + (c.ok ? 'OK: ' : 'Check: ') +
          (c.label || c.id) + ' · ' + (c.detail || '') + '</span>';
      }).join('') +
      '</div>';
  }

  function refresh() {
    var u = encodeURIComponent(uid());
    return Promise.all([
      getJson('/api/exchange/catalog'),
      getJson('/api/exchange/wallet?user_id=' + u),
      getJson('/api/exchange/rewards?user_id=' + u),
      getJson('/api/exchange/trades?limit=10'),
      getJson('/api/exchange/orders?limit=20'),
      getJson('/api/exchange/paypal/mn2-packs'),
      getJson('/api/exchange/agents'),
      getJson('/api/exchange/user-progress?user_id=' + u),
      getJson('/api/exchange/profit-agent?user_id=' + u),
      getJson('/api/exchange/gateway/status'),
    ]).then(function (res) {
      catalog = res[0];
      if (catalog && catalog.success) {
        q('cex-asset-count').textContent = String(catalog.asset_count || 25);
        q('cex-legal-notice').textContent = catalog.legal_notice || '';
        if (catalog.lawful_bonus && catalog.lawful_bonus.terms_version) {
          termsVersion = catalog.lawful_bonus.terms_version;
        }
        if (catalog.lawful_bonus && q('cex-bonus-desc')) {
          q('cex-bonus-desc').textContent = catalog.lawful_bonus.terms_summary || q('cex-bonus-desc').textContent;
        }
        renderAssets(catalog.assets);
        renderStaking(catalog.assets);
        updateSelected();
      }
      renderWallet(res[1]);
      renderRewards(res[2]);
      renderTrades(res[3]);
      renderOrders(res[4]);
      renderPayPalMn2Packs(res[5]);
      renderAgents(res[6]);
      renderProgress(res[7]);
      renderProfitAgent(res[8]);
      renderGatewayStatus(res[9]);
    }).catch(function () { msg('Could not load exchange data.'); });
  }

  function doQuote() {
    var amount = parseFloat((q('cex-swap-amount') || {}).value || '0');
    if (!amount) { msg('Enter amount'); return; }
    postJson('/api/exchange/quote', {
      symbol: selected,
      side: (q('cex-swap-side') || {}).value || 'buy',
      amount: amount,
      quote: (q('cex-swap-quote') || {}).value || 'MN2',
    }).then(function (res) {
      if (!res.success) { msg(res.error || 'Quote failed'); return; }
      lastQuote = res;
      var prev = q('cex-quote-preview');
      var line = res.side === 'buy'
        ? 'Cost: ' + fmt(res.quote_cost, 6) + ' ' + res.quote_currency + ' · Fee: ' + fmt(res.fee_quote, 6)
        : 'Receive: ' + fmt(res.quote_received, 6) + ' ' + res.quote_currency + ' · Fee: ' + fmt(res.fee_quote, 6);
      if (prev) prev.textContent = line + ' · ' + res.fee_bps + ' bps · ~$' + fmt(res.usd_value, 2);
      msg('Quote ready — confirm swap');
    });
  }

  function doSwap() {
    if (!lastQuote) { doQuote(); return; }
    postJson('/api/exchange/swap', {
      quote_id: lastQuote.quote_id,
      symbol: lastQuote.symbol,
      side: lastQuote.side,
      amount: lastQuote.amount,
      quote: lastQuote.quote_currency,
    }).then(function (res) {
      if (res.success) {
        msg('Swap complete');
        lastQuote = null;
        q('cex-quote-preview').textContent = '';
        refresh();
      } else {
        msg(res.error || 'Swap failed');
      }
    });
  }

  function doLimit() {
    postJson('/api/exchange/orders', {
      symbol: selected,
      side: (q('cex-limit-side') || {}).value || 'buy',
      amount: parseFloat((q('cex-limit-amount') || {}).value || '0'),
      limit_price: parseFloat((q('cex-limit-price') || {}).value || '0'),
      quote: 'MN2',
    }).then(function (res) {
      msg(res.success ? 'Limit order placed' : (res.error || 'Order failed'));
      refresh();
    });
  }

  function doBonus() {
    if (!(q('cex-bonus-accept') || {}).checked) {
      msg('Accept terms to claim bonus');
      return;
    }
    postJson('/api/exchange/bonus/claim', { terms_version: termsVersion, accepted: true }).then(function (res) {
      msg(res.success ? ('Bonus +' + fmt(res.bonus_mn2, 4) + ' MN2 (hold until ' + (res.hold_until || '').slice(0, 10) + ')') : (res.error || 'Bonus failed'));
      refresh();
    });
  }

  function doTax() {
    getJson('/api/exchange/tax-report?user_id=' + encodeURIComponent(uid())).then(function (res) {
      var pre = q('cex-tax-report');
      if (pre) pre.textContent = JSON.stringify(res, null, 2);
    });
  }

  function startPayPalMn2(packId) {
    msg('Opening PayPal checkout…');
    postJson('/api/exchange/paypal/create-mn2-order', { pack_id: packId }).then(function (res) {
      if (res && res.success && res.approve_url) {
        try {
          sessionStorage.setItem('cex_paypal_pack', packId);
          sessionStorage.setItem('cex_paypal_order', res.order_id || '');
        } catch (e) {}
        window.location.href = res.approve_url;
      } else {
        msg((res && res.error) || 'Could not start PayPal checkout');
      }
    }).catch(function () {
      msg('PayPal checkout failed to start.');
    });
  }

  function doPayPalCrypto() {
    var usd = parseFloat((q('cex-paypal-usd') || {}).value || '0');
    if (!usd) { msg('Enter USD amount'); return; }
    msg('Preparing PayPal crypto checkout…');
    postJson('/api/exchange/paypal/crypto-quote', {
      symbol: selected,
      usd_amount: usd,
    }).then(function (quote) {
      var prev = q('cex-paypal-crypto-preview');
      if (!quote || !quote.success) {
        if (prev) prev.textContent = (quote && quote.error) || 'Quote failed';
        msg((quote && quote.error) || 'Quote failed');
        return null;
      }
      if (prev) {
        prev.textContent = '$' + fmt(quote.usd_amount, 2) + ' buys ~' +
          fmt(quote.asset_amount, 8) + ' ' + quote.symbol +
          ' after $' + fmt(quote.fee_usd, 2) + ' fee.';
      }
      return postJson('/api/exchange/paypal/create-crypto-order', {
        symbol: selected,
        usd_amount: usd,
      });
    }).then(function (res) {
      if (!res) return;
      if (res.success && res.approve_url) {
        try {
          sessionStorage.setItem('cex_crypto_paypal_order', res.order_id || '');
          sessionStorage.setItem('cex_crypto_paypal_symbol', selected);
        } catch (e) {}
        window.location.href = res.approve_url;
      } else {
        msg((res && res.error) || 'Could not start crypto checkout');
      }
    }).catch(function () {
      msg('PayPal crypto checkout failed to start.');
    });
  }

  function runAgentTick() {
    msg('Running exchange bot tick…');
    postJson('/api/exchange/agents/tick', { force: true }).then(function (res) {
      if (res && res.success) {
        msg('Bot tick #' + res.tick_count + ' completed (' + ((res.actions || []).length) + ' actions).');
        refresh();
      } else {
        msg((res && res.error) || 'Bot tick failed');
      }
    });
  }

  function handlePayPalReturn() {
    var params = new URLSearchParams(window.location.search);
    if (params.get('exchange_paypal') !== 'success') return;
    var orderId = params.get('token') || params.get('order_id');
    var packId = params.get('pack_id');
    try {
      orderId = orderId || sessionStorage.getItem('cex_paypal_order');
      packId = packId || sessionStorage.getItem('cex_paypal_pack');
    } catch (e) {}
    if (!orderId || !packId) {
      msg('PayPal returned without an order id or pack id.');
      return;
    }
    msg('Confirming PayPal payment…');
    postJson('/api/exchange/paypal/capture-mn2-order', {
      order_id: orderId,
      pack_id: packId,
    }).then(function (res) {
      if (res && res.success) {
        msg('PayPal captured. +' + fmt(res.mn2_granted, 4) + ' MN2 credited.');
        try {
          sessionStorage.removeItem('cex_paypal_pack');
          sessionStorage.removeItem('cex_paypal_order');
        } catch (e) {}
        refresh();
      } else {
        msg((res && res.error) || 'PayPal capture failed');
      }
      window.history.replaceState({}, document.title, window.location.pathname);
    });
  }

  function handleCryptoPayPalReturn() {
    var params = new URLSearchParams(window.location.search);
    if (params.get('crypto_paypal') !== 'success') return;
    var orderId = params.get('token') || params.get('order_id');
    try {
      orderId = orderId || sessionStorage.getItem('cex_crypto_paypal_order');
    } catch (e) {}
    if (!orderId) {
      msg('PayPal returned without an order id.');
      return;
    }
    msg('Confirming PayPal crypto purchase…');
    postJson('/api/exchange/paypal/capture-crypto-order', { order_id: orderId }).then(function (res) {
      if (res && res.success) {
        msg('PayPal captured. +' + fmt(res.asset_amount, 8) + ' ' + res.symbol + ' credited.');
        try {
          sessionStorage.removeItem('cex_crypto_paypal_order');
          sessionStorage.removeItem('cex_crypto_paypal_symbol');
        } catch (e) {}
        refresh();
      } else {
        msg((res && res.error) || 'PayPal crypto capture failed');
      }
      window.history.replaceState({}, document.title, window.location.pathname);
    });
  }

  function initTabs() {
    document.querySelectorAll('.cex-tab').forEach(function (tab) {
      tab.addEventListener('click', function () {
        document.querySelectorAll('.cex-tab').forEach(function (t) { t.classList.remove('active'); });
        document.querySelectorAll('.cex-tab-panel').forEach(function (p) { p.classList.remove('active'); });
        tab.classList.add('active');
        var panel = q('cex-tab-' + tab.getAttribute('data-tab'));
        if (panel) panel.classList.add('active');
      });
    });
    var initial = new URLSearchParams(window.location.search).get('tab');
    if (initial) {
      var btn = document.querySelector('.cex-tab[data-tab="' + initial + '"]');
      if (btn) btn.click();
    }
  }

  function init() {
    initTabs();
    q('cex-swap-btn').addEventListener('click', doSwap);
    q('cex-swap-amount').addEventListener('change', function () { lastQuote = null; });
    q('cex-limit-btn').addEventListener('click', doLimit);
    q('cex-bonus-btn').addEventListener('click', doBonus);
    q('cex-tax-btn').addEventListener('click', doTax);
    q('cex-paypal-crypto-btn').addEventListener('click', doPayPalCrypto);
    if (q('cex-agent-tick-btn') && !q('cex-agent-tick-btn').disabled) {
      q('cex-agent-tick-btn').addEventListener('click', runAgentTick);
    }
    q('cex-asset-search').addEventListener('input', function () {
      if (catalog && catalog.assets) renderAssets(catalog.assets);
    });
    refresh();
    handlePayPalReturn();
    handleCryptoPayPalReturn();
    setInterval(refresh, 60000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
