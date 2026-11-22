/**
 * MasterNoder Crypto Exchange UI — /api/exchange/*
 */
(function () {
  'use strict';

  var selected = 'BTC';
  var catalog = null;
  var lastQuote = null;
  var lastWallet = null;
  var termsVersion = '2026-06-v1';
  var quoteCurrencies = ['MN2', 'COINS', 'USDC', 'USDT'];

  function uid() {
    try { return localStorage.getItem('game_user_id') || (window.MnUserId ? window.MnUserId.read() : ''); }
    catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'crypto-exchange.js', context: 'catch' }); } return (window.MnUserId ? window.MnUserId.read() : ''); }
  }

  function q(id) { return document.getElementById(id); }

  function msg(t, kind) {
    var el = q('cex-msg');
    if (!el) return;
    el.textContent = t || '';
    el.classList.remove('is-ok', 'is-err', 'is-info');
    if (kind) el.classList.add(kind);
  }

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
    if (q('cex-swap-asset-label')) q('cex-swap-asset-label').value = selected;
    lastQuote = null;
    setConfirmEnabled(false);
    var prev = q('cex-quote-preview');
    if (prev) prev.innerHTML = '<span class="cex-quote-meta">Asset updated — get a fresh quote.</span>';
  }

  function setConfirmEnabled(on) {
    var btn = q('cex-swap-confirm');
    if (btn) btn.disabled = !on;
  }

  function fillQuoteSelect(list) {
    var sel = q('cex-swap-quote');
    if (!sel || !list || !list.length) return;
    quoteCurrencies = list.slice();
    var cur = sel.value || 'MN2';
    sel.innerHTML = list.map(function (c) {
      var label = c === 'COINS' ? 'Coins' : c;
      return '<option value="' + c + '">' + label + '</option>';
    }).join('');
    if (list.indexOf(cur) >= 0) sel.value = cur;
    else sel.value = list[0];
  }

  function renderSwapBalances(w) {
    if (!w || !w.success) return;
    var assets = w.assets || {};
    function setBal(id, n) {
      var el = q(id);
      if (el) el.textContent = fmt(n, n != null && Math.abs(n) < 1 ? 4 : 2);
    }
    setBal('cex-swap-bal-mn2', w.mn2_balance);
    setBal('cex-swap-bal-coins', w.coins_balance);
    setBal('cex-swap-bal-usdc', assets.USDC);
    setBal('cex-swap-bal-usdt', assets.USDT);
    updateWithdrawAvailable();
  }

  function fillAssetSelects() {
    var symbols = [];
    if (catalog && catalog.assets) {
      symbols = catalog.assets.map(function (a) { return a.symbol; }).filter(Boolean);
    } else {
      symbols = ['USDT', 'USDC', 'BTC', 'ETH'];
    }
    ['cex-wd-asset', 'cex-dep-asset'].forEach(function (id) {
      var el = q(id);
      if (!el) return;
      var cur = el.value;
      el.innerHTML = symbols.filter(function (s) { return s !== 'MN2'; }).map(function (s) {
        return '<option value="' + s + '">' + s + '</option>';
      }).join('') + '<option value="MN2">MN2 (profile/on-chain)</option>';
      if (cur && symbols.indexOf(cur) >= 0) el.value = cur;
      else if (symbols.indexOf('USDT') >= 0) el.value = 'USDT';
    });
    updateWithdrawAvailable();
  }

  function updateWithdrawAvailable() {
    var assetEl = q('cex-wd-asset');
    var availEl = q('cex-wd-available');
    if (!assetEl || !availEl) return;
    var sym = (assetEl.value || 'USDT').toUpperCase();
    var bal = 0;
    if (lastWallet && lastWallet.success) {
      if (sym === 'MN2') bal = Number(lastWallet.mn2_balance || 0);
      else bal = Number((lastWallet.assets || {})[sym] || 0);
    }
    availEl.value = fmt(bal, bal && bal < 1 ? 6 : 4);
  }

  function loadStableMarketsStatus() {
    var el = q('cex-stable-status');
    if (!el) return;
    Promise.all([
      getJson('/api/exchange/multi-wallet/daemon').catch(function () { return null; }),
      getJson('/api/exchange/stable-markets').catch(function () { return null; }),
    ]).then(function (res) {
      var d = res[0] || res[1];
      if (!d || !d.success) {
        el.textContent = 'Could not load multi-wallet status.';
        return;
      }
      if (d.one_daemon) {
        el.textContent = 'One multi-daemon · ' + (d.tradeable_coins || []).length +
          ' coins · withdraw ' + (d.withdraw_live ? 'live' : 'needs live gates') +
          (d.venue_credentials ? '' : ' · Binance keys required') +
          (d.last_tick_at ? ' · last tick ' + String(d.last_tick_at).slice(0, 19) : '');
        return;
      }
      if (d.paper_mode) {
        el.textContent = 'Paper mode is on — balances are not transferable.';
        return;
      }
      el.textContent = 'Multi-wallet ready.';
    }).catch(function () {
      el.textContent = 'Could not load multi-wallet status.';
    });
  }

  function doDepositAddress() {
    if (!uid()) { msg('Sign in first.', 'is-err'); return; }
    var asset = ((q('cex-dep-asset') || {}).value || 'USDT').toUpperCase();
    var amount = (q('cex-dep-amount') || {}).value;
    var path = '/api/exchange/deposit?asset=' + encodeURIComponent(asset) +
      '&user_id=' + encodeURIComponent(uid()) +
      (amount ? '&amount=' + encodeURIComponent(amount) : '');
    getJson(path).then(function (res) {
      var box = q('cex-dep-info');
      if (!box) return;
      if (!res || !res.success) {
        box.innerHTML = '<span class="cex-quote-meta">' + ((res && (res.message || res.error)) || 'Failed') + '</span>';
        return;
      }
      box.innerHTML =
        '<div><strong>' + res.asset + '</strong> on ' + (res.network || '—') +
        ' · rail ' + (res.rail || '') + '</div>' +
        '<div style="word-break:break-all;margin-top:6px"><code>' + (res.address || '—') + '</code></div>' +
        (res.tag ? '<div>Memo/tag: <code>' + res.tag + '</code></div>' : '') +
        '<div class="cex-quote-meta" style="margin-top:6px">' + (res.message || '') + '</div>';
      if (res.network && q('cex-wd-network') && asset === ((q('cex-wd-asset') || {}).value || '')) {
        q('cex-wd-network').value = res.network;
      }
    });
  }

  function doDepositIntent() {
    if (!uid()) { msg('Sign in first.', 'is-err'); return; }
    var asset = ((q('cex-dep-asset') || {}).value || 'USDT').toUpperCase();
    var amount = Number((q('cex-dep-amount') || {}).value || 0);
    if (amount <= 0) { msg('Enter the exact deposit amount for the intent.', 'is-err'); return; }
    postJson('/api/exchange/deposit/intent', { asset: asset, amount: amount }).then(function (res) {
      if (res && res.success) {
        msg('Deposit intent ' + (res.intent && res.intent.intent_id) + ' created for ' + amount + ' ' + asset, 'is-ok');
        doDepositAddress();
      } else {
        msg((res && (res.message || res.error)) || 'Intent failed', 'is-err');
      }
    });
  }

  function doDepositConfirm() {
    if (!uid()) { msg('Sign in first.', 'is-err'); return; }
    var asset = ((q('cex-dep-asset') || {}).value || 'USDT').toUpperCase();
    var txid = ((q('cex-dep-txid') || {}).value || '').trim();
    var amount = Number((q('cex-dep-amount') || {}).value || 0);
    if (!txid) { msg('Paste the deposit txid.', 'is-err'); return; }
    postJson('/api/exchange/deposit/confirm', {
      asset: asset, txid: txid, amount: amount || undefined
    }).then(function (res) {
      if (res && res.success) {
        msg('Credited ' + fmt(res.credited && res.credited.amount, 6) + ' ' + asset, 'is-ok');
        if (res.wallet) renderWallet(res.wallet);
        else refresh();
      } else {
        msg((res && (res.message || res.error)) || 'Confirm failed', 'is-err');
      }
    });
  }

  function doStableWithdraw() {
    if (!uid()) { msg('Sign in to withdraw.', 'is-err'); return; }
    var asset = ((q('cex-wd-asset') || {}).value || 'USDT').toUpperCase();
    if (asset === 'MN2') {
      msg('Use Profile → Wallet → Withdraw for on-chain MN2.', 'is-info');
      window.location.href = '/profile?tab=wallet';
      return;
    }
    var amount = Number((q('cex-wd-amount') || {}).value || 0);
    var address = ((q('cex-wd-address') || {}).value || '').trim();
    var network = ((q('cex-wd-network') || {}).value || '').toUpperCase();
    if (!address || amount <= 0) {
      msg('Enter a destination address and amount.', 'is-err');
      return;
    }
    msg('Submitting ' + asset + ' withdraw…', 'is-info');
    postJson('/api/exchange/withdraw', {
      asset: asset,
      amount: amount,
      address: address,
      network: network || undefined
    }).then(function (res) {
      if (res && res.success) {
        msg('Withdrawn ' + fmt(res.withdrawn && res.withdrawn.send_amount, 6) + ' ' + asset +
          ' (id ' + ((res.withdrawn && res.withdrawn.withdraw_id) || 'pending') + ').', 'is-ok');
        if (res.wallet) renderWallet(res.wallet);
        else refresh();
      } else {
        msg((res && (res.message || res.error)) || 'Withdraw failed', 'is-err');
      }
    }).catch(function () {
      msg('Withdraw request failed', 'is-err');
    });
  }

  function quoteBalanceAvailable() {
    var quote = ((q('cex-swap-quote') || {}).value || 'MN2').toUpperCase();
    if (!lastWallet || !lastWallet.success) return 0;
    if (quote === 'MN2') return Number(lastWallet.mn2_balance || 0);
    if (quote === 'COINS') return Number(lastWallet.coins_balance || 0);
    return Number((lastWallet.assets || {})[quote] || 0);
  }

  function assetBalanceAvailable() {
    if (!lastWallet || !lastWallet.success) return 0;
    return Number((lastWallet.assets || {})[selected] || 0);
  }

  function renderWallet(w) {
    lastWallet = w;
    if (window.CexAccountBridge && window.CexAccountBridge.onExchangeWallet) {
      window.CexAccountBridge.onExchangeWallet(w);
    }
    renderSwapBalances(w);
    var el = q('cex-wallet-balances');
    if (!el || !w || !w.success) return;
    var rows = w.wallets || [];
    if (!rows.length) {
      var assets = w.assets || {};
      rows = Object.keys(assets).sort().map(function (k) {
        return { symbol: k, balance: assets[k] };
      });
      if (w.mn2_balance != null) {
        rows.unshift({ symbol: 'MN2', balance: w.mn2_balance });
      }
    }
    var lines = rows.map(function (r) {
      var bal = Number(r.balance || 0);
      var cls = bal > 0 ? 'cex-wallet-row is-funded' : 'cex-wallet-row';
      return '<div class="' + cls + '"><span>' + (r.symbol || '?') +
        (r.name && r.name !== r.symbol ? ' <small class="cex-muted">' + r.name + '</small>' : '') +
        '</span><strong>' + fmt(bal, bal && bal < 1 ? 6 : 4) + '</strong></div>';
    });
    if (Number(w.coins_balance || 0) > 0) {
      lines.unshift('<div class="cex-wallet-row is-funded"><span>Coins (shop)</span><strong>' +
        fmt(w.coins_balance, 2) + '</strong></div>');
    }
    if (!lines.length) {
      el.innerHTML = '<p class="cex-muted">No coin wallets yet. Sign in to open all market wallets.</p>';
      return;
    }
    el.innerHTML = '<p class="cex-muted" style="margin:0 0 8px">' +
      (w.wallet_count || rows.length) + ' coin wallets · ~$' + fmt(w.total_usd, 2) +
      '</p>' + lines.join('');
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
      var w = a.wallet || {};
      var wallets = w.wallets || [];
      var funded = wallets.filter(function (r) { return Number(r.balance || 0) > 0; });
      var balLine = (funded.length ? funded : wallets.slice(0, 6)).map(function (r) {
        return r.symbol + ' ' + fmt(r.balance, 4);
      }).join(' · ');
      return '<div class="cex-agent-row"><strong>' + (a.name || a.id) + '</strong><br>' +
        (a.strategy || 'rotation') + ' · ' + ((a.assets || []).join(', ') || 'all') +
        '<br><span class="cex-muted">' + (w.wallet_count || wallets.length) + ' wallets · MN2 ' +
        fmt(w.mn2_balance, 4) + ' · ~$' + fmt(w.total_usd, 2) + '</span>' +
        (balLine ? '<br>' + balLine : '') +
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
        var quotes = catalog.quote_currencies || catalog.quotes || quoteCurrencies;
        fillQuoteSelect(quotes);
        renderAssets(catalog.assets);
        renderStaking(catalog.assets);
        fillAssetSelects();
        updateSelected();
      }
      renderWallet(res[1]);
      renderRewards(res[2]);
      renderTrades(res[3]);
    }).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'crypto-exchange.js', context: 'catch' }); } msg('Could not load exchange data.', 'is-err'); });
  }

  function loadMn2Packs() {
    function withPacks(data) {
      var packs = (data && (data.packs || data.mn2_packs)) || [];
      return Object.assign({}, data || {}, { packs: packs });
    }
    return getJson('/api/exchange/paypal/mn2-packs').then(function (data) {
      if (data && (data.packs || data.mn2_packs)) return withPacks(data);
      return getJson('/api/shop/mn2-packs').then(withPacks);
    }).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'crypto-exchange.js', context: 'catch' }); }
      return getJson('/api/shop/mn2-packs').then(withPacks).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'crypto-exchange.js', context: 'catch' }); }
        return { packs: [] };
      });
    });
  }

  function refreshTradeExtras() {
    return Promise.all([
      getJson('/api/exchange/orders?limit=20').catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'crypto-exchange.js', context: 'catch' }); } return { orders: [] }; }),
      loadMn2Packs(),
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

  function renderQuoteCard(res) {
    var prev = q('cex-quote-preview');
    if (!prev) return;
    var main = res.side === 'buy'
      ? 'Pay ' + fmt(res.quote_cost, 6) + ' ' + res.quote_currency + ' → get ' + fmt(res.amount, 8) + ' ' + res.symbol
      : 'Sell ' + fmt(res.amount, 8) + ' ' + res.symbol + ' → get ' + fmt(res.quote_received, 6) + ' ' + res.quote_currency;
    var meta = 'Fee ' + fmt(res.fee_quote, 6) + ' ' + res.quote_currency +
      ' · ' + res.fee_bps + ' bps · ~$' + fmt(res.usd_value, 2) +
      (res.expires_at ? ' · expires ' + String(res.expires_at).slice(11, 19) + ' UTC' : '');
    prev.innerHTML = '<div class="cex-quote-main">' + main + '</div><div class="cex-quote-meta">' + meta + '</div>';
  }

  function doQuote() {
    if (!uid()) {
      msg('Set your profile user ID first (Profile → Account).', 'is-err');
      return;
    }
    var amount = parseFloat((q('cex-swap-amount') || {}).value || '0');
    var quote = ((q('cex-swap-quote') || {}).value || 'MN2').toUpperCase();
    var side = (q('cex-swap-side') || {}).value || 'buy';
    if (!amount || amount <= 0) { msg('Enter an amount greater than zero.', 'is-err'); return; }
    if (selected === quote) { msg('Pick a different market asset than the quote currency.', 'is-err'); return; }
    setConfirmEnabled(false);
    msg('Fetching quote…', 'is-info');
    postJson('/api/exchange/quote', {
      symbol: selected,
      side: side,
      amount: amount,
      quote: quote,
    }).then(function (res) {
      if (!res.success) {
        lastQuote = null;
        msg(res.error || 'Quote failed', 'is-err');
        return;
      }
      lastQuote = res;
      renderQuoteCard(res);
      setConfirmEnabled(true);
      msg('Quote ready — confirm to execute.', 'is-ok');
    }).catch(function () {
      lastQuote = null;
      msg('Quote request failed.', 'is-err');
    });
  }

  function doSwap() {
    if (!lastQuote) { doQuote(); return; }
    if (!uid()) {
      msg('Set your profile user ID first (Profile → Account).', 'is-err');
      return;
    }
    setConfirmEnabled(false);
    msg('Executing swap…', 'is-info');
    postJson('/api/exchange/swap', {
      quote_id: lastQuote.quote_id,
      symbol: lastQuote.symbol,
      side: lastQuote.side,
      amount: lastQuote.amount,
      quote: lastQuote.quote_currency,
    }).then(function (res) {
      if (res.success) {
        msg('Swap complete — balances updated.', 'is-ok');
        lastQuote = null;
        var prev = q('cex-quote-preview');
        if (prev) prev.innerHTML = '<span class="cex-quote-meta">Swap filled. Get another quote when ready.</span>';
        if (q('cex-swap-amount')) q('cex-swap-amount').value = '';
        refresh();
      } else {
        setConfirmEnabled(true);
        msg(res.error || 'Swap failed', 'is-err');
      }
    }).catch(function () {
      setConfirmEnabled(true);
      msg('Swap request failed.', 'is-err');
    });
  }

  function applyQuickPct(pct) {
    var side = (q('cex-swap-side') || {}).value || 'buy';
    var amountInput = q('cex-swap-amount');
    if (!amountInput) return;
    lastQuote = null;
    setConfirmEnabled(false);
    if (side === 'sell') {
      var hold = assetBalanceAvailable();
      if (hold <= 0) { msg('No ' + selected + ' balance to sell.', 'is-err'); return; }
      amountInput.value = String(hold * (pct / 100));
      msg('Amount set to ' + pct + '% of your ' + selected + '.', 'is-info');
      return;
    }
    var quote = ((q('cex-swap-quote') || {}).value || 'MN2').toUpperCase();
    var spend = quoteBalanceAvailable();
    var asset = (catalog && catalog.assets || []).find(function (a) { return a.symbol === selected; });
    var price = asset ? Number(asset['price_' + quote.toLowerCase()] || asset.price_mn2 || 0) : 0;
    if (quote === 'COINS' && asset && asset.price_coins) price = Number(asset.price_coins);
    if (quote === 'USDC' && asset && asset.price_usdc) price = Number(asset.price_usdc);
    if (quote === 'USDT' && asset && asset.price_usdt) price = Number(asset.price_usdt);
    if (!(spend > 0) || !(price > 0)) {
      msg('Need a ' + quote + ' balance and a live price to size the buy.', 'is-err');
      return;
    }
    var budget = spend * (pct / 100);
    var approx = budget / price;
    amountInput.value = String(Number(approx.toPrecision(6)));
    msg('Buy size ~' + pct + '% of your ' + quote + ' balance.', 'is-info');
  }

  function flipSide() {
    var side = q('cex-swap-side');
    if (!side) return;
    side.value = side.value === 'buy' ? 'sell' : 'buy';
    lastQuote = null;
    setConfirmEnabled(false);
    msg(side.value === 'buy' ? 'Buy mode — spend quote for asset.' : 'Sell mode — sell asset for quote.', 'is-info');
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
        } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'crypto-exchange.js', context: 'catch' }); }}
        window.location.href = res.approve_url;
      } else {
        msg((res && res.error) || 'Could not start PayPal checkout');
      }
    }).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'crypto-exchange.js', context: 'catch' }); }
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
        } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'crypto-exchange.js', context: 'catch' }); }}
        window.location.href = res.approve_url;
      } else {
        msg((res && res.error) || 'Could not start crypto checkout');
      }
    }).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'crypto-exchange.js', context: 'catch' }); }
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
    if (params.get('exchange_paypal') === 'cancel' || params.get('paypal') === 'cancel') return;
    var orderId = params.get('token') || params.get('order_id');
    var packId = params.get('pack_id');
    var storedOrder = '';
    try {
      storedOrder = sessionStorage.getItem('cex_paypal_order') || '';
      orderId = orderId || storedOrder;
      packId = packId || sessionStorage.getItem('cex_paypal_pack');
    } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'crypto-exchange.js', context: 'catch' }); }}
    var payerId = params.get('PayerID') || params.get('PayerId');
    var flagged = params.get('exchange_paypal') === 'success';
    var approved = flagged || params.get('paypal') === 'success' || !!payerId;
    if (params.get('crypto_paypal') === 'success' && !flagged) return;
    if (!approved && !storedOrder) return;
    if (!orderId) {
      if (flagged) msg('PayPal returned without an order id.');
      return;
    }
    msg('Confirming PayPal payment…');
    var body = { order_id: orderId };
    if (packId) body.pack_id = packId;
    postJson('/api/exchange/paypal/capture-mn2-order', body).then(function (res) {
      if (res && res.success) {
        msg('PayPal captured. +' + fmt(res.mn2_granted, 4) + ' MN2 credited.');
        try {
          sessionStorage.removeItem('cex_paypal_pack');
          sessionStorage.removeItem('cex_paypal_order');
        } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'crypto-exchange.js', context: 'catch' }); }}
        refresh();
      } else if (!flagged && (res && (res.error === 'pending_order_not_found' || res.error === 'order_not_found'))) {
        handleCryptoPayPalReturn(true);
        return;
      } else {
        msg((res && res.error) || 'PayPal capture failed');
      }
      window.history.replaceState({}, document.title, window.location.pathname);
    });
  }

  function handleCryptoPayPalReturn(fromMn2Fallback) {
    var params = new URLSearchParams(window.location.search);
    if (params.get('crypto_paypal') === 'cancel' || params.get('paypal') === 'cancel') return;
    var orderId = params.get('token') || params.get('order_id');
    var storedOrder = '';
    try {
      storedOrder = sessionStorage.getItem('cex_crypto_paypal_order') || '';
      orderId = orderId || storedOrder;
    } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'crypto-exchange.js', context: 'catch' }); }}
    var payerId = params.get('PayerID') || params.get('PayerId');
    var flagged = params.get('crypto_paypal') === 'success';
    var approved = flagged || params.get('paypal') === 'success' || !!payerId || !!fromMn2Fallback;
    if (!fromMn2Fallback && !flagged && !storedOrder) return;
    if (!approved && !storedOrder) return;
    if (!orderId) {
      if (flagged) msg('PayPal returned without an order id.');
      return;
    }
    msg('Confirming PayPal crypto purchase…');
    postJson('/api/exchange/paypal/capture-crypto-order', { order_id: orderId }).then(function (res) {
      if (res && res.success) {
        msg('PayPal captured. +' + fmt(res.asset_amount, 8) + ' ' + res.symbol + ' credited.');
        try {
          sessionStorage.removeItem('cex_crypto_paypal_order');
          sessionStorage.removeItem('cex_crypto_paypal_symbol');
        } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'crypto-exchange.js', context: 'catch' }); }}
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
    if (q('cex-quote-btn')) q('cex-quote-btn').addEventListener('click', doQuote);
    if (q('cex-swap-confirm')) q('cex-swap-confirm').addEventListener('click', doSwap);
    if (q('cex-swap-btn')) q('cex-swap-btn').addEventListener('click', doSwap);
    if (q('cex-swap-flip')) q('cex-swap-flip').addEventListener('click', flipSide);
    ['cex-swap-amount', 'cex-swap-side', 'cex-swap-quote'].forEach(function (id) {
      var el = q(id);
      if (!el) return;
      el.addEventListener('change', function () {
        lastQuote = null;
        setConfirmEnabled(false);
      });
      if (id === 'cex-swap-amount') {
        el.addEventListener('input', function () {
          lastQuote = null;
          setConfirmEnabled(false);
        });
      }
    });
    var quick = q('cex-quick-amts');
    if (quick) {
      quick.addEventListener('click', function (ev) {
        var btn = ev.target.closest('[data-pct]');
        if (!btn) return;
        applyQuickPct(Number(btn.getAttribute('data-pct') || 0));
      });
    }
    if (q('cex-limit-btn')) q('cex-limit-btn').addEventListener('click', doLimit);
    if (q('cex-bonus-btn')) q('cex-bonus-btn').addEventListener('click', doBonus);
    if (q('cex-tax-btn')) q('cex-tax-btn').addEventListener('click', doTax);
    if (q('cex-paypal-crypto-btn')) q('cex-paypal-crypto-btn').addEventListener('click', doPayPalCrypto);
    if (q('cex-wd-btn')) q('cex-wd-btn').addEventListener('click', doStableWithdraw);
    if (q('cex-wd-asset')) q('cex-wd-asset').addEventListener('change', function () {
      updateWithdrawAvailable();
      var asset = (q('cex-wd-asset').value || '').toUpperCase();
      getJson('/api/exchange/deposit?asset=' + encodeURIComponent(asset) + '&user_id=' + encodeURIComponent(uid() || 'anon'))
        .then(function (res) {
          if (res && res.network && q('cex-wd-network')) q('cex-wd-network').value = res.network;
        }).catch(function () {});
    });
    if (q('cex-dep-addr-btn')) q('cex-dep-addr-btn').addEventListener('click', doDepositAddress);
    if (q('cex-dep-intent-btn')) q('cex-dep-intent-btn').addEventListener('click', doDepositIntent);
    if (q('cex-dep-confirm-btn')) q('cex-dep-confirm-btn').addEventListener('click', doDepositConfirm);
    fillAssetSelects();
    loadStableMarketsStatus();
    if (q('cex-agent-tick-btn') && !q('cex-agent-tick-btn').disabled) {
      q('cex-agent-tick-btn').addEventListener('click', runAgentTick);
    }
    if (q('cex-asset-search')) {
      q('cex-asset-search').addEventListener('input', function () {
        if (catalog && catalog.assets) renderAssets(catalog.assets);
      });
    }
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
