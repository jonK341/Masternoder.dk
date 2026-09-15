/**
 * Profile hub sub-tabs — secondary navigation within main hub tabs.
 */
(function (global) {
  'use strict';

  var SUBTAB_CONFIG = {
    account: [
      { id: 'identity', label: 'Identity', card: 'user-identity-card' },
      { id: 'discord', label: 'Discord', card: 'discord-link-card' },
      { id: 'privacy', label: 'Privacy', card: 'account-privacy-card' },
      { id: 'geo', label: 'Geo ref', card: 'profile-geo-ref-card' },
    ],
    wallet: [
      { id: 'mn2', label: 'MN2 Wallet', card: 'profile-mn2-wallet-card' },
      { id: 'staking', label: 'Staking', card: 'profile-mn2-staking-card' },
      { id: 'trader', label: 'Trader stake', card: 'profile-trader-staking-card' },
      { id: 'paypal', label: 'PayPal', card: 'paypal-control-panel-card' },
    ],
    security: [
      { id: 'layer', label: 'Security layer', card: 'profile-section-security-layer' },
      { id: 'password', label: 'Password', card: 'password-protection-card' },
      { id: 'realmoney', label: 'Real money', card: 'account-security-card' },
    ],
    agents: [
      { id: 'myagents', label: 'My agents', card: 'my-agents-card' },
      { id: 'control', label: 'Control', card: 'agent-control-card' },
      { id: 'monetize', label: 'Monetization', card: 'monetization-25-card' },
    ],
    activity: [
      { id: 'feed', label: 'Activity feed', card: 'profile-section-activity' },
      { id: 'clips', label: 'Clips', card: 'recent-clip-download-card' },
    ],
    progress: [
      { id: 'achievements', label: 'Achievements', card: 'profile-section-achievements' },
      { id: 'stats', label: 'Statistics', card: 'profile-section-statistics' },
      { id: 'psych', label: 'Comm psych', card: 'comm-psych-profile-card' },
      { id: 'trophy', label: 'Trophy game', card: 'profile-section-trophy-game' },
    ],
    overview: [
      { id: 'summary', label: 'Summary', card: 'profile-hub-overview' },
      { id: 'stats', label: 'Quick stats', card: 'quick-stats' },
      { id: 'account', label: 'Account', card: 'profile-section-account' },
      { id: 'avatar', label: 'Avatar', card: 'profile-section-avatar' },
      { id: 'leaderboard', label: 'Leaderboard', card: 'profile-section-leaderboard' },
    ],
    points: [{ id: 'points', label: 'Points', card: 'profile-section-points' }],
    shop: [{ id: 'inventory', label: 'Inventory', card: 'profile-section-shop' }],
    skills: [{ id: 'skills', label: 'Skills', card: 'profile-section-skills' }],
    trophies: [{ id: 'trophies', label: 'Trophies', card: 'profile-trophies-card' }],
    leaderboard: [{ id: 'leaderboard', label: 'Leaderboard', card: 'profile-section-leaderboard' }],
    lab: [{ id: 'logbook', label: 'Lab logbook', card: 'profile-section-lab-logbook' }],
    battle: [{ id: 'battle', label: 'Quick battle', card: 'quick-battle-profile-card' }],
    settings: [
      { id: 'privacy', label: 'Privacy', card: 'account-privacy-card' },
      { id: 'geo', label: 'Geo ref', card: 'profile-geo-ref-card' },
    ],
    avatar: [{ id: 'avatar', label: 'Avatar', card: 'profile-section-avatar' }],
  };

  var activeSubtab = {};

  function ensureSubnavEl() {
    var nav = document.getElementById('profile-hub-subnav');
    if (nav) return nav;
    var hubNav = document.getElementById('profile-hub-nav');
    if (!hubNav || !hubNav.parentNode) return null;
    nav = document.createElement('nav');
    nav.id = 'profile-hub-subnav';
    nav.className = 'profile-hub-subnav page-tabs';
    nav.setAttribute('role', 'tablist');
    nav.setAttribute('aria-label', 'Profile section');
    nav.hidden = true;
    hubNav.parentNode.insertBefore(nav, hubNav.nextSibling);
    return nav;
  }

  function applySubtab(route, subtabId) {
    var tabs = SUBTAB_CONFIG[route];
    if (!tabs || !tabs.length) {
      var nav = document.getElementById('profile-hub-subnav');
      if (nav) nav.hidden = true;
      return;
    }
    var sid = subtabId || activeSubtab[route] || tabs[0].id;
    activeSubtab[route] = sid;
    var nav = ensureSubnavEl();
    if (!nav) return;
    nav.hidden = false;
    nav.innerHTML = tabs
      .map(function (t) {
        var on = t.id === sid;
        return (
          '<button type="button" class="tab-btn' +
          (on ? ' active' : '') +
          '" data-profile-subtab="' +
          t.id +
          '" role="tab" aria-selected="' +
          (on ? 'true' : 'false') +
          '">' +
          t.label +
          '</button>'
        );
      })
      .join('');

    var cardIds = {};
    tabs.forEach(function (t) {
      cardIds[t.card] = t.id;
    });

    document.querySelectorAll('[data-profile-route]').forEach(function (el) {
      var routes = (el.getAttribute('data-profile-route') || '').split(/\s+/).filter(Boolean);
      if (routes.indexOf(route) === -1) return;
      var cid = el.id;
      if (!cardIds[cid]) {
        el.hidden = false;
        return;
      }
      el.hidden = cardIds[cid] !== sid;
    });

    try {
      var url = new URL(global.location.href);
      if (sid && sid !== tabs[0].id) url.searchParams.set('subtab', sid);
      else url.searchParams.delete('subtab');
      global.history.replaceState({}, document.title, url.pathname + url.search + url.hash);
    } catch (e) {}

    if (route === 'wallet' && sid === 'mn2' && global.ProfileMn2Wallet && typeof global.ProfileMn2Wallet.load === 'function') {
      global.ProfileMn2Wallet.load();
    }
  }

  function onMainRoute(route) {
    var tabs = SUBTAB_CONFIG[route];
    if (!tabs) {
      var nav = document.getElementById('profile-hub-subnav');
      if (nav) nav.hidden = true;
      return;
    }
    var fromUrl = '';
    try {
      fromUrl = new URLSearchParams(global.location.search).get('subtab') || '';
    } catch (e) {}
    applySubtab(route, fromUrl || activeSubtab[route] || tabs[0].id);
  }

  function init() {
    var nav = ensureSubnavEl();
    if (!nav) return;
    nav.addEventListener('click', function (ev) {
      var btn = ev.target.closest('[data-profile-subtab]');
      if (!btn) return;
      var main = document.querySelector('#profile-hub-nav .tab-btn.active');
      var route = main ? main.getAttribute('data-hub-scroll') : 'overview';
      applySubtab(route, btn.getAttribute('data-profile-subtab'));
      var cfg = SUBTAB_CONFIG[route];
      var entry = cfg && cfg.find(function (t) { return t.id === btn.getAttribute('data-profile-subtab'); });
      if (entry && entry.card) {
        var el = document.getElementById(entry.card);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  }

  global.ProfileHubSubtabs = { init: init, onMainRoute: onMainRoute, applySubtab: applySubtab };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window);
