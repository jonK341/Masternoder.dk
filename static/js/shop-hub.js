/**
 * Shop storefront — glance stats (count-up, pulse, MN2 glow), aligned with profile hub.
 */
(function (global) {
  'use strict';

  var shopGlanceInitialized = false;

  function fmtNum(n) {
    var x = Number(n);
    if (!isFinite(x)) return '—';
    if (x >= 1000000) return (x / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
    if (Math.abs(x) >= 10000) return Math.round(x).toLocaleString();
    if (Number.isInteger(x)) return String(x);
    return x.toFixed(x < 10 ? 2 : 1);
  }

  function setElText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function pulseShopGlance() {
    var strip = document.getElementById('shop-glance-stats');
    if (!strip) return;
    strip.classList.remove('shop-stats-pulse');
    void strip.offsetWidth;
    strip.classList.add('shop-stats-pulse');
  }

  function updateMn2Glow(balance) {
    var stat = document.getElementById('shop-glance-mn2-stat');
    if (!stat) return;
    stat.classList.toggle('shop-glance-mn2-glow', isFinite(balance) && balance > 0);
  }

  function animateStat(id, target, opts) {
    opts = opts || {};
    var el = document.getElementById(id);
    if (!el) return;
    var targetNum = Number(target);
    if (!isFinite(targetNum)) {
      el.textContent = '—';
      delete el.dataset.rawValue;
      return;
    }
    var start = Number(el.dataset.rawValue);
    if (!isFinite(start)) start = 0;
    if (opts.instant || Math.abs(targetNum - start) < 0.0001) {
      el.dataset.rawValue = String(targetNum);
      el.textContent = fmtNum(targetNum);
      return;
    }
    var duration = opts.duration != null ? opts.duration : 720;
    var t0 = global.performance ? performance.now() : Date.now();
    el.dataset.rawValue = String(targetNum);
    function frame(now) {
      var t = global.performance ? now : Date.now();
      var p = Math.min(1, (t - t0) / duration);
      var eased = 1 - Math.pow(1 - p, 3);
      var cur = start + (targetNum - start) * eased;
      el.textContent = fmtNum(cur);
      if (p < 1) requestAnimationFrame(frame);
      else el.textContent = fmtNum(targetNum);
    }
    requestAnimationFrame(frame);
  }

  /**
   * @param {{ coins?: number, mn2?: number, catalog?: number, inventory?: number, xp?: number, level?: number, animate?: boolean }} patch
   */
  global.refreshShopGlance = function (patch) {
    patch = patch || {};
    var animate =
      patch.animate === true || (patch.animate !== false && shopGlanceInitialized);
    shopGlanceInitialized = true;
    if (animate) pulseShopGlance();
    var statOpts = animate ? {} : { instant: true };

    if (patch.coins != null) animateStat('shop-glance-coins', patch.coins, statOpts);
    if (patch.mn2 != null) {
      animateStat('shop-glance-mn2', patch.mn2, statOpts);
      updateMn2Glow(Number(patch.mn2));
    }
    if (patch.catalog != null) animateStat('shop-glance-catalog', patch.catalog, statOpts);
    if (patch.inventory != null) animateStat('shop-glance-inventory', patch.inventory, statOpts);
    if (patch.xp != null) animateStat('shop-glance-xp', patch.xp, statOpts);
    if (patch.level != null) animateStat('shop-glance-level', patch.level, statOpts);

    var pill = document.getElementById('shop-hero-user-pill');
    if (pill && patch.userLabel) pill.textContent = patch.userLabel;
  };

  function wireHeroRefresh() {
    var btn = document.getElementById('shop-hero-refresh');
    if (!btn || btn._bound) return;
    btn._bound = true;
    btn.addEventListener('click', function () {
      btn.disabled = true;
      btn.textContent = 'Refreshing…';
      var jobs = [];
      if (typeof global.loadCurrency === 'function') jobs.push(global.loadCurrency());
      if (typeof global.loadShopItems === 'function') jobs.push(global.loadShopItems());
      Promise.all(jobs).finally(function () {
        btn.disabled = false;
        btn.textContent = 'Refresh shop';
        global.refreshShopGlance({ animate: true });
      });
    });
  }

  function initShopHub() {
    wireHeroRefresh();
    var uid =
      localStorage.getItem('game_user_id') ||
      localStorage.getItem('user_id') ||
      'default_user';
    var shortId = uid.length > 18 ? uid.slice(0, 8) + '…' + uid.slice(-4) : uid;
    global.refreshShopGlance({
      userLabel: shortId,
      coins: 0,
      mn2: 0,
      catalog: 0,
      inventory: 0,
      xp: 0,
      level: 1,
      animate: false,
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initShopHub);
  } else {
    initShopHub();
  }
})(typeof window !== 'undefined' ? window : globalThis);
