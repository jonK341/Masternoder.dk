/**
 * Shop panel sub-navigation — PayPal, MN2, Deals, Account.
 */
(function (global) {
  'use strict';

  var CONFIG = {
    coins: [
      { id: 'packs', label: 'Coin packs', card: 'buy-coins-section' },
      { id: 'subscription', label: 'Pro sub', card: 'subscription-section' },
      { id: 'studio', label: 'Studio rail', card: 'scr-deposit-section' },
    ],
    mn2: [
      { id: 'overview', label: 'Overview', card: 'mn2-overview-card' },
      { id: 'hosting', label: 'Hosting', card: 'mn2-hosting-services-card' },
      { id: 'bundle', label: 'On-ramp bundle', card: 'tier-b-onramp-card' },
      { id: 'wallet', label: 'Wallet', card: 'mn2-wallet-section' },
    ],
    deals: [
      { id: 'pass', label: 'Battle pass', card: 'battle-pass-card' },
      { id: 'copy', label: 'Copy-trade', card: 'copy-trading-premium-card' },
      { id: 'vip', label: 'VIP', card: 'vip-card' },
      { id: 'spin', label: 'Wheel', card: 'spin-wheel-card' },
      { id: 'boxes', label: 'Mystery boxes', card: 'mystery-boxes-card' },
      { id: 'flash', label: 'Flash sales', card: 'flash-sales-card' },
      { id: 'gifts', label: 'Gifts', card: 'gift-coins-card' },
      { id: 'legends', label: 'Top 25', card: 'top25-card' },
    ],
    account: [
      { id: 'stall', label: 'My stall', card: 'my-stall-card' },
      { id: 'inventory', label: 'Inventory', card: 'my-inventory-card' },
      { id: 'downloads', label: 'Downloads', card: 'digital-downloads-card' },
      { id: 'history', label: 'History', card: 'purchase-history-card' },
    ],
  };

  var active = {};

  function apply(panel, subId) {
    var tabs = CONFIG[panel];
    var nav = document.querySelector('[data-shop-subnav="' + panel + '"]');
    if (!tabs || !nav) return;
    var sid = subId || active[panel] || tabs[0].id;
    active[panel] = sid;
    nav.innerHTML = tabs
      .map(function (t) {
        var on = t.id === sid;
        return (
          '<button type="button" class="shop-subnav-btn' +
          (on ? ' active' : '') +
          '" data-shop-subtab="' +
          t.id +
          '" role="tab" aria-selected="' +
          (on ? 'true' : 'false') +
          '">' +
          t.label +
          '</button>'
        );
      })
      .join('');
    tabs.forEach(function (t) {
      var el = document.getElementById(t.card);
      if (!el) return;
      el.hidden = t.id !== sid;
    });
  }

  function onPanel(panel) {
    if (CONFIG[panel]) apply(panel, active[panel]);
  }

  function init() {
    document.querySelectorAll('[data-shop-subnav]').forEach(function (nav) {
      nav.addEventListener('click', function (ev) {
        var btn = ev.target.closest('[data-shop-subtab]');
        if (!btn) return;
        var panel = nav.getAttribute('data-shop-subnav');
        apply(panel, btn.getAttribute('data-shop-subtab'));
        var tabs = CONFIG[panel] || [];
        var entry = tabs.find(function (t) {
          return t.id === btn.getAttribute('data-shop-subtab');
        });
        var el = entry && document.getElementById(entry.card);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
    Object.keys(CONFIG).forEach(function (panel) {
      var host = document.querySelector('[data-panel="' + panel + '"].active');
      if (host) apply(panel);
    });
  }

  global.ShopSubnav = { init: init, onPanel: onPanel, apply: apply };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window);
