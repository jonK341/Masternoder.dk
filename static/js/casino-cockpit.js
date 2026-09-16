(function () {
  'use strict';

  function uid() {
    try {
      return localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
    } catch (e) {
      return 'default_user';
    }
  }

  function q(id) {
    return document.getElementById(id);
  }

  function getJson(path) {
    var sep = path.indexOf('?') >= 0 ? '&' : '?';
    return fetch(path + sep + 'user_id=' + encodeURIComponent(uid()), { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : {}; })
      .catch(function () { return {}; });
  }

  function fmt(n, d) {
    var x = Number(n || 0);
    if (!isFinite(x)) return '0';
    return x.toLocaleString(undefined, { minimumFractionDigits: d || 0, maximumFractionDigits: d || 2 });
  }

  function loadCamgirls() {
    var el = q('casino-cockpit-camgirls');
    if (!el) return;
    getJson('/api/camgirls/performers').then(function (data) {
      var performers = data.performers || data.items || [];
      var online = performers.filter(function (p) { return p.status === 'online' || p.live; }).length;
      el.textContent = performers.length
        ? performers.length + ' performers · ' + online + ' live now'
        : 'Performer lounge ready';
    });
  }

  function loadIncomeMonitor() {
    var el = q('casino-cockpit-income');
    var fill = q('casino-cockpit-income-fill');
    if (!el) return;
    Promise.all([
      getJson('/api/casino/house-stats?currency=coins'),
      getJson('/api/exchange/health'),
      getJson('/api/exchange/trades?limit=20')
    ]).then(function (res) {
      var house = res[0] || {};
      var health = res[1] || {};
      var trades = (res[2] && res[2].trades) || [];
      var wagered = Number(house.total_wagered || 0);
      var profit = Number(house.house_profit || house.net || 0);
      var fees = Number(health.treasury_fees_mn2 || 0);
      var score = Math.min(100, Math.max(8, trades.length * 4 + fees * 10 + Math.abs(profit) / 25));
      el.textContent = 'Casino wagered: ' + fmt(wagered, 0) +
        ' · House net: ' + fmt(profit, 2) +
        ' · Exchange trades: ' + trades.length +
        ' · Fees: ' + fmt(fees, 4) + ' MN2';
      if (fill) fill.style.width = score + '%';
    });
  }

  function initTocShortcuts() {
    document.querySelectorAll('.casino-toc a[href^="#"]').forEach(function (link) {
      link.addEventListener('click', function () {
        var target = q((link.getAttribute('href') || '').slice(1));
        if (target) {
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });
  }

  function loadBridgeLeaderboard() {
    var el = q('casino-bridge-leaderboard');
    if (!el) return;
    getJson('/api/exchange/casino-bridge/leaderboard').then(function (d) {
      if (!d || !d.success) { el.textContent = 'Leaderboard unavailable'; return; }
      el.innerHTML = (d.leaderboard || []).slice(0, 5).map(function (r) {
        return '#' + r.rank + ' ' + r.user_id + ' — ' + r.score + ' pts';
      }).join(' · ') || 'No scores yet this week';
    });
  }

  function loadExchangeBridge() {
    var mn2El = q('casino-bridge-mn2');
    var profitEl = q('casino-bridge-profit');
    var rentEl = q('casino-bridge-rentals');
    var cta = q('casino-bridge-cta');
    if (!mn2El) return;
    getJson('/api/casino/exchange-bridge').then(function (d) {
      if (!d || !d.success) return;
      mn2El.textContent = 'MN2 ' + fmt(d.mn2_balance, 4);
      profitEl.textContent = 'Exchange profit ' + fmt(d.exchange_profit_usd, 2) + ' USD';
      rentEl.textContent = (d.rental_count || 0) + ' active rentals';
      if (cta && d.controller_url) cta.href = d.controller_url;
      if (cta && d.cross_promo) cta.title = d.cross_promo;
    });
  }

  function init() {
    initTocShortcuts();
    loadCamgirls();
    loadIncomeMonitor();
    loadExchangeBridge();
    loadBridgeLeaderboard();
    setInterval(loadIncomeMonitor, 60000);
    setInterval(loadExchangeBridge, 45000);
    setInterval(loadBridgeLeaderboard, 90000);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
