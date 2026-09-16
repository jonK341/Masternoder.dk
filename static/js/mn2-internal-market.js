/**
 * Internal MN2 ↔ coins order book (trader agent liquidity + user orders).
 * API: /api/market/* — separate from PayPal Model B (/api/mn2/p2p/*).
 */
(function () {
  'use strict';

  var root = document.getElementById('mn2-internal-market');
  if (!root) return;

  var pollTimer = null;

  function uid() {
    try { return localStorage.getItem('game_user_id') || 'default_user'; }
    catch (e) { return 'default_user'; }
  }

  function q(id) { return document.getElementById(id); }

  function fmt(n, d) {
    var x = Number(n || 0);
    if (!isFinite(x)) return '—';
    return x.toLocaleString(undefined, { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 });
  }

  function msg(t) {
    var el = q('im-market-msg');
    if (el) el.textContent = t || '';
  }

  function fetchJson(path) {
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

  function renderTicker(t) {
    var el = q('im-ticker');
    if (!el || !t || !t.success) return;
    el.innerHTML =
      '<div class="im-metric"><span>Best ask</span><strong>' + (t.best_ask != null ? fmt(t.best_ask, 2) + ' coins/MN2' : '—') + '</strong></div>' +
      '<div class="im-metric"><span>Best bid</span><strong>' + (t.best_bid != null ? fmt(t.best_bid, 2) + ' coins/MN2' : '—') + '</strong></div>' +
      '<div class="im-metric"><span>Sell depth</span><strong>' + fmt(t.sell_depth, 0) + '</strong></div>' +
      '<div class="im-metric"><span>Last trade</span><strong>' + (t.last_price_coins_per_mn2 != null ? fmt(t.last_price_coins_per_mn2, 2) + ' coins/MN2' : '—') + '</strong></div>';
  }

  function renderTraderStrip(status) {
    var el = q('im-trader-strip');
    if (!el || !status || !status.success) return;
    var pool = status.pool_staked_by_traders_mn2;
    var agents = (status.trader_agents || []).length;
    el.innerHTML =
      '<span class="im-pill">🤖 ' + agents + ' trader agents</span>' +
      '<span class="im-pill">Pool staked: ' + fmt(pool, 2) + ' MN2</span>' +
      '<span class="im-pill im-pill--muted">Auto tick every ~15 min</span>';
  }

  function renderBalances(points) {
    var pts = (points && points.points) || points || {};
    var coinsEl = q('im-user-coins');
    var mn2El = q('im-user-mn2');
    if (coinsEl) coinsEl.textContent = fmt(pts.coins, 0);
    if (mn2El) mn2El.textContent = fmt(pts.mn2_balance, 4);
  }

  function renderOrders(orders) {
    var el = q('im-sell-orders');
    if (!el) return;
    var rows = orders || [];
    var me = uid();
    if (!rows.length) {
      el.innerHTML = '<p class="im-empty">No open sell orders. Trader agents will post liquidity on the next tick.</p>';
      return;
    }
    el.innerHTML =
      '<table class="im-table"><thead><tr><th>Seller</th><th>MN2</th><th>Price</th><th>Cost</th><th></th></tr></thead><tbody>' +
      rows.map(function (o) {
        var amt = Number(o.remaining_mn2 || o.mn2_amount || 0);
        var price = Number(o.price_coins_per_mn2 || 0);
        var cost = amt * price;
        var isMine = o.user_id === me;
        var isAgent = (o.user_id || '').indexOf('trader_agent_') === 0;
        var seller = isAgent ? o.user_id.replace(/_/g, ' ') : (isMine ? 'You' : (o.user_id || '—'));
        var buyBtn = isMine
          ? '<button type="button" class="im-btn im-btn--ghost" data-cancel="' + o.order_id + '">Cancel</button>'
          : '<button type="button" class="im-btn" data-fill="' + o.order_id + '" data-max="' + amt + '">Buy</button>';
        return '<tr><td>' + seller + '</td><td class="num">' + fmt(amt, 4) + '</td><td class="num">' + fmt(price, 2) + '</td><td class="num">' + fmt(cost, 0) + '</td><td>' + buyBtn + '</td></tr>';
      }).join('') +
      '</tbody></table>';

    el.querySelectorAll('[data-fill]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var oid = btn.getAttribute('data-fill');
        var max = parseFloat(btn.getAttribute('data-max') || '0');
        var qty = parseFloat(window.prompt('MN2 to buy (max ' + max + '):', String(Math.min(max, 25))) || '0');
        if (!qty || qty <= 0) return;
        postJson('/api/market/fill', { order_id: oid, mn2_amount: qty }).then(function (res) {
          if (res && res.success) {
            msg('Filled ' + fmt(qty, 4) + ' MN2');
            refresh();
          } else {
            msg((res && res.error) || 'Fill failed');
          }
        });
      });
    });

    el.querySelectorAll('[data-cancel]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var oid = btn.getAttribute('data-cancel');
        postJson('/api/market/cancel', { order_id: oid }).then(function (res) {
          if (res && res.success) { msg('Order cancelled'); refresh(); }
          else { msg((res && res.error) || 'Cancel failed'); }
        });
      });
    });
  }

  function renderTrades(trades) {
    var el = q('im-recent-trades');
    if (!el) return;
    var rows = trades || [];
    if (!rows.length) {
      el.innerHTML = '<p class="im-empty">No trades yet.</p>';
      return;
    }
    el.innerHTML =
      '<table class="im-table im-table--compact"><thead><tr><th>Time</th><th>MN2</th><th>Coins</th><th>Buyer</th></tr></thead><tbody>' +
      rows.map(function (t) {
        var ts = (t.ts || '').replace('T', ' ').slice(0, 19);
        var buyer = (t.buyer || '').indexOf('trader_agent_') === 0 ? t.buyer.replace(/_/g, ' ') : (t.buyer || '—');
        return '<tr><td>' + ts + 'Z</td><td class="num">' + fmt(t.mn2, 4) + '</td><td class="num">' + fmt(t.coins, 0) + '</td><td>' + buyer + '</td></tr>';
      }).join('') +
      '</tbody></table>';
  }

  function refresh() {
    var u = encodeURIComponent(uid());
    return Promise.all([
      fetchJson('/api/market/ticker'),
      fetchJson('/api/market/orders?side=sell&limit=20'),
      fetchJson('/api/market/trades?limit=8'),
      fetchJson('/api/agents/trader-staking/status?user_id=' + u),
      fetchJson('/api/points/all?user_id=' + u),
    ]).then(function (res) {
      renderTicker(res[0]);
      renderOrders((res[1] && res[1].orders) || []);
      renderTrades((res[2] && res[2].trades) || []);
      renderTraderStrip(res[3]);
      renderBalances(res[4]);
    }).catch(function () {
      msg('Could not refresh market data.');
    });
  }

  function postSell() {
    var amt = parseFloat((q('im-sell-amount') || {}).value || '0');
    var price = parseFloat((q('im-sell-price') || {}).value || '0');
    if (!amt || !price) { msg('Enter MN2 amount and price (coins per MN2)'); return; }
    postJson('/api/market/orders', { side: 'sell', mn2_amount: amt, price_coins_per_mn2: price }).then(function (res) {
      if (res && res.success) {
        msg('Listed ' + fmt(amt, 4) + ' MN2 @ ' + fmt(price, 2) + ' coins/MN2');
        refresh();
      } else {
        msg((res && res.error) || 'Could not list');
      }
    });
  }

  function init() {
    fetchJson('/api/market/config').then(function (cfg) {
      if (!cfg || !cfg.success || !cfg.enabled) {
        root.style.display = 'none';
        return;
      }
      root.style.display = '';
      var ref = cfg.reference_price_coins_per_mn2;
      var priceInput = q('im-sell-price');
      if (priceInput && ref && !priceInput.value) priceInput.placeholder = String(ref);

      var sellBtn = q('im-sell-btn');
      if (sellBtn) sellBtn.addEventListener('click', postSell);
      var refBtn = q('im-refresh-btn');
      if (refBtn) refBtn.addEventListener('click', refresh);

      refresh();
      if (pollTimer) clearInterval(pollTimer);
      pollTimer = setInterval(refresh, 45000);
    }).catch(function () {
      root.style.display = 'none';
    });
  }

  window.MN2InternalMarket = { refresh: refresh, init: init };
  init();
})();
