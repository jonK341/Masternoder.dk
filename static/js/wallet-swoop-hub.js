/**
 * Shared MN2 / USDT / USDC wallet + swoop pool hub for /wallets, profile wallet, and site chrome.
 */
(function (global) {
  'use strict';

  function uid() {
    if (global.Mn2SiteBridge && global.Mn2SiteBridge.uid) return global.Mn2SiteBridge.uid();
    try {
      return localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
    } catch (e) {
      return 'default_user';
    }
  }

  function fmt(n, d) {
    var x = Number(n || 0);
    if (!isFinite(x)) return '—';
    d = d === undefined ? 4 : d;
    if (x > 0 && x < 0.0001) return x.toExponential(3);
    return x.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: d });
  }

  function loadHub() {
    if (global.Mn2SiteBridge && global.Mn2SiteBridge.loadWalletHub) {
      return global.Mn2SiteBridge.loadWalletHub();
    }
    var u = encodeURIComponent(uid());
    return Promise.all([
      fetch('/api/exchange/wallet?user_id=' + u, { credentials: 'same-origin' }).then(function (r) { return r.json(); }),
      fetch('/api/exchange/mn2-pool/status', { credentials: 'same-origin' }).then(function (r) { return r.json(); }),
      fetch('/api/exchange/swoop/assets', { credentials: 'same-origin' }).then(function (r) { return r.json(); }),
    ]).then(function (res) {
      return { wallet: res[0], pool: res[1], swoop: res[2], success: !!(res[0] && res[0].success) };
    });
  }

  function swoopUrl(from, to) {
    return '/exchange?swoop=' + encodeURIComponent(from + ',' + to);
  }

  var CHIP_STYLE = 'display:inline-block;padding:6px 12px;border-radius:999px;border:1px solid rgba(125,249,255,0.35);color:#7df9ff;background:rgba(0,212,255,0.08);text-decoration:none;font-size:0.78rem;font-weight:700;margin:0 6px 6px 0;';

  function chipHtml(from, to, activeFrom, activeTo, label) {
    var style = CHIP_STYLE;
    if (from === activeFrom && to === activeTo) {
      style += 'border-color:#00d4ff;background:rgba(0,212,255,0.2);';
    }
    var text = label || (from + ' → ' + to);
    return '<a style="' + style + '" href="' + swoopUrl(from, to) + '" title="' + text + '">' + text + '</a>';
  }

  function renderBalances(el, wallet) {
    if (!el) return;
    if (!wallet || !wallet.success) {
      el.innerHTML = '<p class="wallet-muted">Exchange wallet unavailable.</p>';
      return;
    }
    var assets = wallet.assets || {};
    var rows = [
      { sym: 'MN2', val: wallet.mn2_balance },
      { sym: 'USDT', val: assets.USDT },
      { sym: 'USDC', val: assets.USDC },
    ];
    el.innerHTML = rows.map(function (row) {
      return '<div class="wallet-balance-row"><span>' + row.sym + '</span><strong>' + fmt(row.val, 6) + '</strong></div>';
    }).join('');
  }

  function renderPool(el, pool) {
    if (!el) return;
    if (!pool || !pool.success) {
      el.innerHTML = '<p class="wallet-muted">MN2 liquidity pool unavailable.</p>';
      return;
    }
    var assets = pool.pool_assets || {};
    var gaps = pool.pool_gaps || {};
    var reserve = pool.reserve_assets || {};
    var bps = pool.pool_swap_reserve_bps || 200;
    var health = pool.health || {};
    var healthLine = health.score != null
      ? '<p class="wallet-muted" style="font-weight:700;color:' +
        (health.band === 'red' ? '#ff6b6b' : health.band === 'yellow' ? '#f5c842' : '#3dd68c') +
        '">Pool health ' + Number(health.score).toFixed(0) + '/100</p>'
      : '';
    var lines = healthLine + ['MN2', 'USDT', 'USDC'].map(function (sym) {
      var gap = gaps[sym];
      var note = gap ? ' · need ' + fmt(gap, 4) : '';
      return '<div class="wallet-balance-row"><span>Pool ' + sym + '</span><strong>' + fmt(assets[sym], 4) + note + '</strong></div>';
    }).join('');
    lines += '<p class="wallet-muted" style="margin:8px 0 0">Reserve (' + (bps / 100).toFixed(1) + '% per swoop): MN2 ' +
      fmt(reserve.MN2, 4) + ' · USDT ' + fmt(reserve.USDT, 4) + ' · USDC ' + fmt(reserve.USDC, 4) + '</p>';
    if (pool.swap_back_hint) {
      lines += '<p class="wallet-muted">' + pool.swap_back_hint + '</p>';
    }
    el.innerHTML = lines;
  }

  function renderSwoopChips(el, activeFrom, activeTo, presets) {
    if (!el) return;
    var html = '';
    if (presets && presets.length) {
      html += presets.map(function (p) {
        return chipHtml(p.from, p.to, activeFrom, activeTo, p.label);
      }).join('');
    }
    var pairs = [
      ['USDT', 'MN2'], ['USDC', 'MN2'], ['MN2', 'USDT'], ['MN2', 'USDC'],
      ['USDT', 'USDC'], ['USDC', 'USDT'],
    ];
    html += pairs.map(function (p) {
      return chipHtml(p[0], p[1], activeFrom, activeTo);
    }).join('');
    el.innerHTML = html;
  }

  function mount(root, opts) {
    opts = opts || {};
    if (!root) return;
    var balancesEl = root.querySelector('[data-wallet-hub-balances]');
    var poolEl = root.querySelector('[data-wallet-hub-pool]');
    var chipsEl = root.querySelector('[data-wallet-hub-chips]');
    loadHub().then(function (hub) {
      renderBalances(balancesEl, hub.wallet);
      renderPool(poolEl, hub.pool);
      renderSwoopChips(chipsEl, opts.activeFrom, opts.activeTo, hub.swoop_presets);
      if (opts.onLoad) opts.onLoad(hub);
    }).catch(function () {
      if (balancesEl) balancesEl.innerHTML = '<p class="wallet-muted">Could not load wallet hub.</p>';
    });
  }

  global.WalletSwoopHub = {
    uid: uid,
    fmt: fmt,
    loadHub: loadHub,
    mount: mount,
    swoopUrl: swoopUrl,
    renderBalances: renderBalances,
    renderPool: renderPool,
    renderSwoopChips: renderSwoopChips,
  };
})(window);
