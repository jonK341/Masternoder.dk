/**
 * Profile Hub — 2 pages: Dashboard | Account & Settings
 * Preserves ?tab= deep links by mapping old tab names to page + scroll target.
 */
(function (global) {
  'use strict';

  var PAGES = {
    dashboard: {
      label: 'Dashboard',
      defaultTab: 'overview',
      tabs: ['overview', 'leaderboard', 'wallet', 'points', 'trophies', 'activity']
    },
    account: {
      label: 'Account & Settings',
      defaultTab: 'account',
      tabs: [
        'account', 'settings', 'security', 'shop', 'agents', 'avatar',
        'skills', 'progress', 'battle', 'lab'
      ]
    }
  };

  var SCROLL_MAP = {
    overview: 'profile-hub-overview',
    avatar: 'profile-section-avatar',
    account: 'profile-section-account',
    skills: 'profile-section-skills',
    trophies: 'profile-trophies-card',
    points: 'profile-section-points',
    leaderboard: 'profile-section-leaderboard',
    shop: 'profile-section-shop',
    wallet: 'profile-mn2-wallet-card',
    settings: 'account-privacy-card',
    security: 'profile-security-frame',
    agents: 'my-agents-card',
    activity: 'profile-section-activity',
    lab: 'profile-section-lab-logbook',
    battle: 'quick-battle-profile-card',
    progress: 'profile-section-achievements'
  };

  var TAB_ALIASES = {
    account: 'account', user: 'account', avatar: 'avatar', skills: 'skills',
    trophies: 'trophies', progress: 'progress', points: 'points',
    leaderboard: 'leaderboard', activity: 'activity', shop: 'shop',
    inventory: 'shop', wallet: 'wallet', security: 'security', settings: 'settings',
    agents: 'agents', lab: 'lab', battle: 'battle', dashboard: 'overview',
    overview: 'overview'
  };

  var HASH_ALIASES = {
    'mn2-wallet': 'wallet',
    'profile-mn2-wallet-card': 'wallet',
    wallet: 'wallet'
  };

  var routeToPage = {};
  Object.keys(PAGES).forEach(function (pageKey) {
    PAGES[pageKey].tabs.forEach(function (tab) {
      routeToPage[tab] = pageKey;
    });
  });

  var state = { route: 'overview', page: 'dashboard', securityBound: false, walletLoaded: false };

  function resolvePage(route) {
    return routeToPage[route] || 'dashboard';
  }

  function scrollToRoute(route) {
    var id = SCROLL_MAP[route];
    if (!id) return;
    var el = document.getElementById(id);
    if (el && !el.hidden) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  function updateUrl(route) {
    try {
      var url = new URL(global.location.href);
      if (route === 'overview') url.searchParams.delete('tab');
      else url.searchParams.set('tab', route);
      global.history.replaceState({}, document.title, url.pathname + url.search + url.hash);
    } catch (e) { /* ignore */ }
  }

  function bindSecuritySubnavOnce() {
    if (state.securityBound) return;
    state.securityBound = true;
    document.querySelectorAll('.profile-security-subnav [data-security-scroll]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var key = btn.getAttribute('data-security-scroll');
        document.querySelectorAll('.profile-security-subnav .tab-btn').forEach(function (b) {
          b.classList.toggle('active', b === btn);
        });
        document.querySelectorAll('[data-security-panel]').forEach(function (panel) {
          panel.style.display = panel.getAttribute('data-security-panel') === key ? '' : 'none';
        });
      });
    });
  }

  function expandAccordionForRoute(route) {
    var id = SCROLL_MAP[route];
    if (!id) return;
    var el = document.getElementById(id);
    if (!el) return;
    var acc = el.closest('.profile-hub-accordion');
    if (acc && acc.classList.contains('is-collapsed')) {
      acc.classList.remove('is-collapsed');
      var btn = acc.querySelector('.profile-hub-accordion-toggle');
      if (btn) btn.setAttribute('aria-expanded', 'true');
    }
  }

  function onRouteSideEffects(route) {
    if (global.ProfileMn2Wallet && typeof global.ProfileMn2Wallet.load === 'function') {
      if ((state.page === 'dashboard' || route === 'wallet') && !state.walletLoaded) {
        global.ProfileMn2Wallet.load();
        state.walletLoaded = true;
      }
    }
    if (route === 'security' || (state.page === 'account' && route === 'account')) {
      if (global.profileManager) {
        if (typeof global.profileManager.loadPasswordProtection === 'function') {
          global.profileManager.loadPasswordProtection();
        }
        if (route === 'security' && typeof global.profileManager.loadAccountSecurity === 'function') {
          global.profileManager.loadAccountSecurity();
        }
        if (global.ProfileSecurity && typeof global.ProfileSecurity.init === 'function') {
          global.ProfileSecurity.init(global.profileManager.userId);
        }
      }
      bindSecuritySubnavOnce();
      if (global.Mn2WithdrawalSecurity && typeof global.Mn2WithdrawalSecurity.refresh === 'function') {
        global.Mn2WithdrawalSecurity.refresh();
      }
    }
  }

  function syncPrimaryNav(page) {
    document.querySelectorAll('#profile-hub-primary [data-hub-page]').forEach(function (btn) {
      var on = btn.getAttribute('data-hub-page') === page;
      btn.classList.toggle('active', on);
      btn.setAttribute('aria-selected', on ? 'true' : 'false');
    });
  }

  function applyRoute(route, opts) {
    opts = opts || {};
    route = route || 'overview';
    if (!routeToPage[route] && !SCROLL_MAP[route]) route = 'overview';

    state.route = route;
    state.page = resolvePage(route);

    document.body.classList.add('profile-route-focused', 'profile-route-ready');
    document.body.setAttribute('data-profile-route', route);
    document.body.setAttribute('data-profile-page', state.page);

    document.querySelectorAll('[data-profile-page]').forEach(function (el) {
      var pages = (el.getAttribute('data-profile-page') || '').split(/\s+/).filter(Boolean);
      el.hidden = pages.indexOf(state.page) === -1;
    });

    var note = document.getElementById('profile-route-note');
    if (note) {
      note.textContent = state.page === 'dashboard'
        ? 'Dashboard — wallet, progress, and activity'
        : 'Account & settings — login, security, shop, agents';
    }

    syncPrimaryNav(state.page);
    expandAccordionForRoute(route);
    onRouteSideEffects(route);

    if (!opts.skipUrl) updateUrl(route);
    if (!opts.skipScroll) scrollToRoute(route);

    global.dispatchEvent(new CustomEvent('profile-hub-route', {
      detail: { route: route, page: state.page, group: state.page }
    }));
  }

  function routeFromUrl() {
    var hash = (global.location.hash || '').replace(/^#/, '').toLowerCase();
    if (hash && HASH_ALIASES[hash]) return HASH_ALIASES[hash];

    var tab = new URLSearchParams(global.location.search).get('tab');
    if (!tab) return null;
    tab = tab.toLowerCase();
    return TAB_ALIASES[tab] || (SCROLL_MAP[tab] ? tab : null);
  }

  function bindNav() {
    var primary = document.getElementById('profile-hub-primary');
    if (primary) {
      primary.addEventListener('click', function (ev) {
        var btn = ev.target.closest('[data-hub-page]');
        if (!btn) return;
        var page = btn.getAttribute('data-hub-page');
        var meta = PAGES[page];
        if (!meta) return;
        applyRoute(meta.defaultTab);
      });
    }

    document.querySelectorAll('.profile-hub-accordion-toggle').forEach(function (btn) {
      if (btn._hubBound) return;
      btn._hubBound = true;
      btn.addEventListener('click', function () {
        var acc = btn.closest('.profile-hub-accordion');
        if (!acc) return;
        var collapsed = acc.classList.toggle('is-collapsed');
        btn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
      });
    });

    var walletJump = document.getElementById('profile-wallet-summary-jump');
    if (walletJump) {
      walletJump.addEventListener('click', function (ev) {
        ev.preventDefault();
        applyRoute('wallet');
      });
    }
  }

  function init() {
    bindNav();
    var initial = routeFromUrl() || 'overview';
    applyRoute(initial, { skipScroll: true });
    setTimeout(function () { scrollToRoute(state.route); }, 350);

    global.addEventListener('hashchange', function () {
      var route = routeFromUrl();
      if (route) applyRoute(route);
    });
  }

  global.ProfileHubBar = {
    init: init,
    applyRoute: applyRoute,
    routeFromUrl: routeFromUrl,
    scrollMap: SCROLL_MAP,
    pages: PAGES
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window);
