/**
 * MasterNoder Crypto Exchange UI — /api/exchange/*
 */
(function () {
  'use strict';

  var selected = 'BTC';
  var catalog = null;
  var lastQuote = null;
  var lastSwoopQuote = null;
  var swoopMeta = null;
  var walletSnapshot = null;
  var swoopQuoteTimer = null;
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
    if (window.ExchangeHub && window.ExchangeHub.fetchJson) {
      return window.ExchangeHub.fetchJson(path, { timeout: 8000 });
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

  function swoopBalance(asset) {
    if (!walletSnapshot || !walletSnapshot.success) return 0;
    var sym = (asset || '').toUpperCase();
    if (sym === 'MN2') return Number(walletSnapshot.mn2_balance || 0);
    var assets = walletSnapshot.assets || {};
    return Number(assets[sym] || 0);
  }

  function updateSwoopBalances() {
    var from = (q('cex-swoop-from') || {}).value || 'MN2';
    var balEl = q('cex-swoop-from-bal');
    if (balEl) balEl.textContent = 'Balance: ' + fmt(swoopBalance(from), 6) + ' ' + from;
  }

  function renderSwoopPreview(res) {
    var el = q('cex-swoop-preview');
    if (!el) return;
    if (!res || !res.success) {
      el.innerHTML = '<span class="cex-muted">' + ((res && res.error) || 'Enter an amount to swoop.') + '</span>';
      return;
    }
    var lines = [
      '<strong>Swoop ' + fmt(res.from_amount, 6) + ' ' + res.from_asset +
        ' → ' + fmt(res.to_amount, 6) + ' ' + res.to_asset + '</strong>',
      'Fee: ' + fmt(res.fee_quote, 6) + ' ' + res.quote_currency + ' (' + res.fee_bps + ' bps)',
    ];
    if (res.pool_backed) {
      lines.push('<div class="cex-swoop-pool">Pool-backed · liquidity pool pays out</div>');
      if (Number(res.pool_reserve_quote || 0) > 0) {
        var pct = (Number(res.pool_reserve_bps || 200) / 100).toFixed(1);
        lines.push('<div class="cex-swoop-reserve">Reserve set aside: ' +
          fmt(res.pool_reserve_quote, 6) + ' ' + (res.pool_reserve_currency || res.to_asset) +
          ' (' + pct + '% for later ops)</div>');
      }
    }
    if (res.runway_warning && res.runway_warning.low_liquidity) {
      lines.push('<div class="cex-swoop-warn">⚠ Low pool liquidity — ~' +
        (res.runway_warning.estimated_swaps_remaining || 0) + ' swoops left at $' +
        (res.runway_warning.sample_usd || 10) + ' each</div>');
    }
    if (res.circuit_breaker) {
      lines.push('<div class="cex-swoop-warn">Pool circuit breaker active — swoops paused</div>');
    }
    lines.push('<span class="cex-muted">~$' + fmt(res.usd_value, 2) + ' notional</span>');
    el.innerHTML = lines.join('<br>');
    var est = q('cex-swoop-to-est');
    if (est) est.textContent = 'Estimate: ' + fmt(res.to_amount, 6) + ' ' + res.to_asset;
  }

  function scheduleSwoopQuote() {
    if (swoopQuoteTimer) clearTimeout(swoopQuoteTimer);
    swoopQuoteTimer = setTimeout(fetchSwoopQuote, 400);
  }

  function fetchSwoopQuote() {
    var from = (q('cex-swoop-from') || {}).value || 'MN2';
    var to = (q('cex-swoop-to') || {}).value || 'USDT';
    var amount = parseFloat((q('cex-swoop-amount') || {}).value || '0');
    lastSwoopQuote = null;
    if (!amount || from === to) {
      renderSwoopPreview(null);
      return;
    }
    postJson('/api/exchange/swoop/quote', { from_asset: from, to_asset: to, amount: amount })
      .then(function (res) {
        if (res && res.success) lastSwoopQuote = res;
        renderSwoopPreview(res);
        if (!res || !res.success) msg(res && res.error ? res.error : 'Swoop quote failed');
      });
  }

  function setSwoopPair(from, to, amount) {
    if (q('cex-swoop-from')) q('cex-swoop-from').value = from;
    if (q('cex-swoop-to')) q('cex-swoop-to').value = to;
    if (amount != null && q('cex-swoop-amount')) q('cex-swoop-amount').value = amount;
    document.querySelectorAll('.cex-swoop-chip').forEach(function (chip) {
      var active = chip.getAttribute('data-from') === from && chip.getAttribute('data-to') === to;
      chip.classList.toggle('active', active);
    });
    updateSwoopBalances();
    scheduleSwoopQuote();
  }

  function flipSwoop() {
    var from = (q('cex-swoop-from') || {}).value;
    var to = (q('cex-swoop-to') || {}).value;
    setSwoopPair(to, from);
  }

  function doSwoopMax() {
    var from = (q('cex-swoop-from') || {}).value || 'MN2';
    var bal = swoopBalance(from);
    if (q('cex-swoop-amount')) q('cex-swoop-amount').value = bal > 0 ? String(bal) : '';
    scheduleSwoopQuote();
  }

  function doSwoop() {
    if (!lastSwoopQuote) {
      fetchSwoopQuote();
      return;
    }
    postJson('/api/exchange/swoop', {
      quote_id: lastSwoopQuote.quote_id,
      from_asset: lastSwoopQuote.from_asset,
      to_asset: lastSwoopQuote.to_asset,
      amount: lastSwoopQuote.from_amount,
    }).then(function (res) {
      if (res && res.success) {
        msg('Swoop complete — received ' + fmt(res.to_amount, 6) + ' ' + res.to_asset);
        lastSwoopQuote = null;
        if (q('cex-swoop-amount')) q('cex-swoop-amount').value = '';
        renderSwoopPreview(null);
        refresh();
      } else {
        msg((res && res.error) || 'Swoop failed');
      }
    });
  }

  function renderSwoopMeta(data) {
    swoopMeta = data;
    var hint = q('cex-swoop-hint');
    if (hint && data && data.swap_back_hint) hint.textContent = data.swap_back_hint;
  }

  function applySwoopParams() {
    try {
      var params = new URLSearchParams(window.location.search);
      var swoop = params.get('swoop');
      if (!swoop) return;
      var parts = swoop.split(',');
      if (parts.length !== 2) return;
      setSwoopPair(parts[0].toUpperCase(), parts[1].toUpperCase());
      var tab = document.querySelector('.cex-tab[data-tab="swoop"]');
      if (tab) tab.click();
    } catch (e) {}
  }

  function renderWallet(w) {
    walletSnapshot = w;
    updateSwoopBalances();
    var el = q('cex-wallet-balances');
    if (!el || !w || !w.success) return;
    var assets = w.assets || {};
    var rows = [];
    if (w.mn2_balance != null) {
      rows.push('<div class="cex-wallet-row"><span>MN2 coins</span><strong>' + fmt(w.mn2_balance, 6) + '</strong></div>');
    }
    var pinned = ['USDT', 'USDC'];
    pinned.concat(Object.keys(assets).filter(function (k) {
      return pinned.indexOf(k) < 0 && Number(assets[k]) > 0;
    })).forEach(function (k) {
      rows.push('<div class="cex-wallet-row"><span>' + k + '</span><strong>' + fmt(assets[k], 8) + '</strong></div>');
    });
    el.innerHTML = rows.join('') || '<p class="cex-muted">No balances yet.</p>';
  }

  function renderMn2Pool(data) {
    var el = q('cex-mn2-pool');
    if (!el) return;
    if (!data || !data.success) {
      el.innerHTML = '<p class="cex-muted">MN2 pool unavailable.</p>';
      return;
    }
    var assets = data.pool_assets || {};
    var gaps = data.pool_gaps || {};
    var reserve = data.reserve_assets || {};
    var reserveBps = data.pool_swap_reserve_bps || 200;
    var health = data.health || {};
    var cb = data.circuit_breaker || {};
    var healthHtml = '';
    if (health.score != null) {
      healthHtml = '<div class="cex-pool-health cex-pool-health--' + (health.band || 'green') + '">Pool health: ' +
        Number(health.score).toFixed(0) + '/100' +
        (cb.level && cb.level !== 'green' ? ' · ' + (cb.reason || cb.level) : '') + '</div>';
    }
    el.innerHTML = healthHtml + ['MN2', 'USDT', 'USDC'].map(function (sym) {
      var gap = gaps[sym];
      var note = gap ? ' · need ' + fmt(gap, 4) : '';
      return '<div class="cex-wallet-row"><span>' + sym + '</span><strong>' + fmt(assets[sym], 4) + note + '</strong></div>';
    }).join('') +
      '<div class="cex-muted">Reserve (' + (reserveBps / 100).toFixed(1) + '% per swap): MN2 ' +
      fmt(reserve.MN2, 4) + ' · USDT ' + fmt(reserve.USDT, 4) + ' · USDC ' + fmt(reserve.USDC, 4) + '</div>' +
      '<canvas id="cex-pool-depth-chart" height="80" style="width:100%;margin-top:8px;max-height:80px"></canvas>';
    loadPoolDepthChart();
  }

  function loadPoolDepthChart() {
    var canvas = q('cex-pool-depth-chart');
    if (!canvas || !canvas.getContext) return;
    fetch('/api/exchange/ops/depth-chart?hours=168').then(function (r) { return r.json(); }).then(function (d) {
      if (!d || !d.success || !d.points || !d.points.length) return;
      var ctx = canvas.getContext('2d');
      var w = canvas.width = canvas.offsetWidth || 300;
      var h = canvas.height = 80;
      ctx.clearRect(0, 0, w, h);
      var pts = d.points;
      var maxY = 1;
      pts.forEach(function (p) {
        maxY = Math.max(maxY, Number(p.MN2 || 0), Number(p.USDT || 0), Number(p.USDC || 0));
      });
      var colors = { MN2: '#00d4ff', USDT: '#3dd68c', USDC: '#7df9ff' };
      ['MN2', 'USDT', 'USDC'].forEach(function (sym) {
        ctx.beginPath();
        ctx.strokeStyle = colors[sym];
        ctx.lineWidth = 1.5;
        pts.forEach(function (p, i) {
          var x = (i / Math.max(pts.length - 1, 1)) * w;
          var y = h - (Number(p[sym] || 0) / maxY) * (h - 8) - 4;
          if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        });
        ctx.stroke();
      });
    }).catch(function () {});
  }

  function renderSwoopPresets(presets) {
    var wrap = q('cex-swoop-presets');
    if (!wrap || !presets || !presets.length) return;
    wrap.innerHTML = presets.map(function (p) {
      return '<button type="button" class="cex-swoop-chip cex-swoop-preset" data-from="' + p.from +
        '" data-to="' + p.to + '" title="' + (p.label || '') + '">' + (p.label || (p.from + ' → ' + p.to)) + '</button>';
    }).join('');
  }

  function renderQuoteSelects(quotes) {
    var wanted = (quotes && quotes.length) ? quotes : ['MN2', 'COINS', 'USDT', 'USDC'];
    ['cex-swap-quote', 'cex-limit-quote'].forEach(function (id) {
      var el = q(id);
      if (!el) return;
      var cur = el.value;
      el.innerHTML = wanted.map(function (item) {
        return '<option value="' + item + '">' + (item === 'COINS' ? 'Coins' : item) + '</option>';
      }).join('');
      if (wanted.indexOf(cur) >= 0) el.value = cur;
    });
  }

  function renderBinanceStables(data) {
    var el = q('cex-binance-stables');
    if (!el) return;
    if (!data || !data.success) {
      el.innerHTML = '<p class="cex-muted">Binance stable wallets unavailable.</p>';
      return;
    }
    var rows = data.wallets || [];
    el.innerHTML = rows.map(function (w) {
      var conn = w.connected ? 'connected' : 'not connected';
      var addr = w.address_masked || 'awaiting Binance address';
      return '<div class="cex-wallet-row">' +
        '<span>' + w.asset + ' · ' + (w.network || 'TRC20') + '</span>' +
        '<strong>' + conn + '</strong></div>' +
        '<div class="cex-muted">' + addr + (w.tradeable ? ' · tradable vs MN2' : '') + '</div>';
    }).join('') || '<p class="cex-muted">USDT and USDC wallets will appear after Binance sync.</p>';
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

  function refreshCore() {
    var u = encodeURIComponent(uid());
    return Promise.all([
      getJson('/api/exchange/catalog'),
      getJson('/api/exchange/wallet?user_id=' + u),
      getJson('/api/exchange/rewards?user_id=' + u),
      getJson('/api/exchange/trades?limit=10'),
      getJson('/api/exchange/binance/stable-wallets'),
      getJson('/api/exchange/mn2-pool/status'),
      getJson('/api/exchange/swoop/assets'),
      getJson('/api/exchange/wallet-hub'),
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
        renderQuoteSelects(catalog.quote_currencies);
        applyTradeParams();
        renderAssets(catalog.assets);
        renderStaking(catalog.assets);
        updateSelected();
      }
      renderWallet(res[1]);
      renderRewards(res[2]);
      renderTrades(res[3]);
      renderBinanceStables(res[4]);
      renderMn2Pool(res[5]);
      renderSwoopMeta(res[6]);
      if (res[7] && res[7].swoop_presets) renderSwoopPresets(res[7].swoop_presets);
    }).catch(function () { msg('Could not load exchange data.'); });
  }

  function refreshTradeExtras() {
    var u = encodeURIComponent(uid());
    return Promise.all([
      getJson('/api/exchange/orders?limit=20'),
      getJson('/api/exchange/paypal/mn2-packs'),
    ]).then(function (res) {
      renderOrders(res[0]);
      renderPayPalMn2Packs(res[1]);
    });
  }

  function refreshOverview() {
    var u = encodeURIComponent(uid());
    return Promise.all([
      getJson('/api/exchange/user-progress?user_id=' + u),
      getJson('/api/exchange/profit-agent?user_id=' + u),
      getJson('/api/exchange/gateway/status'),
    ]).then(function (res) {
      renderProgress(res[0]);
      renderProfitAgent(res[1]);
      renderGatewayStatus(res[2]);
    });
  }

  function refreshBots() {
    return getJson('/api/exchange/agents').then(renderAgents);
  }

  function refresh() {
    return refreshCore().then(function () {
      return refreshTradeExtras();
    });
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
      quote: (q('cex-limit-quote') || {}).value || 'MN2',
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

  function applyTradeParams() {
    try {
      var params = new URLSearchParams(window.location.search);
      if (params.get('swoop')) {
        applySwoopParams();
        return;
      }
      var asset = (params.get('asset') || '').toUpperCase();
      var quote = (params.get('quote') || '').toUpperCase();
      var side = (params.get('side') || '').toLowerCase();
      if (asset) selected = asset;
      if (quote && q('cex-swap-quote')) q('cex-swap-quote').value = quote;
      if (quote && q('cex-limit-quote')) q('cex-limit-quote').value = quote;
      if (side && q('cex-swap-side')) q('cex-swap-side').value = side === 'sell' ? 'sell' : 'buy';
      if (asset || quote) {
        var swapTab = document.querySelector('.cex-tab[data-tab="swap"]');
        if (swapTab) swapTab.click();
      }
    } catch (e) {}
  }

  function initSwoop() {
    if (!q('cex-swoop-from')) return;
    q('cex-swoop-from').addEventListener('change', function () {
      updateSwoopBalances();
      scheduleSwoopQuote();
    });
    q('cex-swoop-to').addEventListener('change', function () {
      scheduleSwoopQuote();
    });
    q('cex-swoop-amount').addEventListener('input', function () {
      lastSwoopQuote = null;
      scheduleSwoopQuote();
    });
    q('cex-swoop-flip').addEventListener('click', flipSwoop);
    q('cex-swoop-max').addEventListener('click', doSwoopMax);
    q('cex-swoop-btn').addEventListener('click', doSwoop);
    var chipsWrap = q('cex-swoop-chips');
    var presetsWrap = q('cex-swoop-presets');
    function onChipClick(e) {
      var chip = e.target.closest('.cex-swoop-chip');
      if (!chip) return;
      setSwoopPair(chip.getAttribute('data-from'), chip.getAttribute('data-to'));
    }
    if (chipsWrap) chipsWrap.addEventListener('click', onChipClick);
    if (presetsWrap) presetsWrap.addEventListener('click', onChipClick);
    setSwoopPair('USDT', 'MN2');
    applySwoopParams();
  }

  function init() {
    initTabs();
    initSwoop();
    applyTradeParams();
    if (q('cex-swap-btn')) q('cex-swap-btn').addEventListener('click', doSwap);
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
    if (window.ExchangeHub) {
      window.ExchangeHub.onTab('trade', function () {
        return refreshCore().then(refreshTradeExtras);
      });
      window.ExchangeHub.onTab('overview', refreshOverview);
      window.ExchangeHub.onTab('bots', refreshBots);
    } else {
      refresh();
    }
    handlePayPalReturn();
    handleCryptoPayPalReturn();
    setInterval(function () {
      var tradeShell = document.querySelector('.cex-tab-shell[data-cex-tab="trade"]');
      if (tradeShell && !tradeShell.hidden) refreshCore();
    }, 60000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
