/**
 * Hub Pages UX — status bar, refresh, loading/empty helpers
 * Auto-inits on pages with data-hub-page or known paths.
 */
(function (global) {
  'use strict';

  var APP_BASE = (typeof global.APP_BASE !== 'undefined') ? global.APP_BASE : '';

  var PAGE_META = {
    explorer: {
      title: 'MN2 Explorer',
      mount: '.mn2-hub-wrap',
      position: 'prepend',
      skeleton: '.ex-tiles',
      onRefresh: refreshExplorer
    },
    profile: {
      title: 'Profile Hub',
      mount: '.profile-container',
      position: 'prepend',
      onRefresh: refreshProfile
    },
    'command-center': {
      title: 'Command Center',
      mount: '.cc-page',
      position: 'prepend',
      onRefresh: refreshCommandCenter
    },
    game: {
      title: 'Hunter Game',
      mount: '.hunter-game-app',
      position: 'prepend',
      skeleton: '#game-at-a-glance',
      onRefresh: refreshGame
    },
    quests: {
      title: 'Quest Board',
      mount: '.quests-page',
      position: 'prepend',
      onRefresh: refreshQuests
    },
    battle: {
      title: 'Battle Arena',
      mount: '.battle-arena',
      position: 'prepend',
      skeleton: '#battle-at-a-glance',
      onRefresh: refreshBattle
    },
    exchange: {
      title: 'Exchange',
      mount: '.cex-page',
      position: 'prepend',
      onRefresh: refreshExchangeHub
    },
    shop: {
      title: 'Shop',
      mount: '.shop-page',
      position: 'prepend',
      onRefresh: refreshShop
    },
    casino: {
      title: 'Casino',
      mount: '.casino-page',
      position: 'prepend',
      onRefresh: refreshCasino
    },
    generator: {
      title: 'Generator',
      mount: '.gen-page',
      position: 'prepend',
      onRefresh: refreshGenerator
    }
  };

  var state = {
    page: null,
    badge: null,
    syncEl: null,
    refreshBtn: null,
    skeletonOn: false
  };

  function detectPage() {
    var body = document.body;
    if (body && body.getAttribute('data-hub-page')) {
      return body.getAttribute('data-hub-page');
    }
    var path = (global.location && global.location.pathname) || '';
    if (/\/explorer\/?$/i.test(path) || path.indexOf('/explorer') === 0) return 'explorer';
    if (/\/profile\/?$/i.test(path) || path.indexOf('/profile') === 0) return 'profile';
    if (/\/command-center\/?$/i.test(path)) return 'command-center';
    if (/\/game\/?$/i.test(path) || path.indexOf('/game') === 0) return 'game';
    if (/\/quests\/?$/i.test(path)) return 'quests';
    if (/\/battle\/?$/i.test(path)) return 'battle';
    if (/\/exchange\/?$/i.test(path) || path.indexOf('/exchange') === 0) return 'exchange';
    if (/\/shop\/?$/i.test(path) || path.indexOf('/shop') === 0) return 'shop';
    if (/\/casino\/?$/i.test(path) || path.indexOf('/casino') === 0) return 'casino';
    if (/\/generator\/?$/i.test(path) || path.indexOf('/generator') === 0) return 'generator';
    return null;
  }

  function emptyStateHtml(opts) {
    opts = opts || {};
    var actions = (opts.actions || []).map(function (a) {
      var cls = a.secondary ? ' secondary' : '';
      return '<a href="' + a.href + '" class="' + cls.trim() + '">' + a.label + '</a>';
    }).join('');
    return (
      '<div class="hub-ux-empty" role="status">' +
      '<div class="hub-ux-empty-icon">' + (opts.icon || '📭') + '</div>' +
      '<p class="hub-ux-empty-title">' + (opts.title || 'Nothing here yet') + '</p>' +
      '<p class="hub-ux-empty-desc">' + (opts.desc || '') + '</p>' +
      (actions ? '<div class="hub-ux-empty-actions">' + actions + '</div>' : '') +
      '</div>'
    );
  }

  function loadingHtml(msg) {
    return (
      '<div class="hub-ux-loading-block" role="status" aria-live="polite">' +
      '<div class="loading-spinner" aria-hidden="true"></div>' +
      '<span>' + (msg || 'Loading…') + '</span></div>'
    );
  }

  function setStatus(kind, label) {
    if (!state.badge) return;
    state.badge.className = 'hub-ux-status-badge hub-ux-status-badge--' + (kind || 'loading');
    state.badge.textContent = label || kind || 'loading';
  }

  function setSyncTime() {
    if (state.syncEl) {
      state.syncEl.textContent = 'Updated ' + new Date().toLocaleTimeString();
    }
  }

  function skeleton(on) {
    var meta = PAGE_META[state.page];
    if (!meta || !meta.skeleton) return;
    var el = document.querySelector(meta.skeleton);
    if (!el) return;
    el.classList.toggle('hub-ux-skeleton', !!on);
    state.skeletonOn = !!on;
  }

  function markReady(kind) {
    skeleton(false);
    setStatus(kind || 'ok', kind === 'empty' ? 'Empty' : 'Live');
    setSyncTime();
  }

  function buildBar(meta) {
    var bar = document.createElement('div');
    bar.className = 'hub-ux-bar';
    bar.setAttribute('role', 'region');
    bar.setAttribute('aria-label', meta.title + ' toolbar');
    bar.innerHTML =
      '<div class="hub-ux-bar-left">' +
      '<span class="hub-ux-bar-title">' + meta.title + '</span>' +
      '<nav class="hub-ux-quick-links" aria-label="Profit and exchange">' +
      '<a class="hub-ux-quick-link hub-ux-quick-link--profit" href="' + APP_BASE + '/profit/" title="24/7 profit daemon monitor">⚡ Profit</a>' +
      '<a class="hub-ux-quick-link" href="' + APP_BASE + '/exchange/" title="25-crypto exchange">💱 Exchange</a>' +
      '<a class="hub-ux-quick-link secondary" href="' + APP_BASE + '/exchange/#cex-profit-oracle" title="Profit oracle agent">📊 Oracle</a>' +
      '</nav></div>' +
      '<div class="hub-ux-bar-right">' +
      '<span class="hub-ux-status-badge hub-ux-status-badge--loading">Loading</span>' +
      '<span class="hub-ux-sync-time" aria-live="polite"></span>' +
      '<button type="button" class="hub-ux-refresh-btn" aria-label="Refresh page data">' +
      '<span class="hub-ux-refresh-icon">↻</span> Refresh</button></div>';
    return bar;
  }

  function mountBar(meta) {
    var target = document.querySelector(meta.mount);
    if (!target) return null;
    var bar = buildBar(meta);
    if (meta.position === 'prepend') {
      target.insertBefore(bar, target.firstChild);
    } else {
      target.appendChild(bar);
    }
    state.badge = bar.querySelector('.hub-ux-status-badge');
    state.syncEl = bar.querySelector('.hub-ux-sync-time');
    state.refreshBtn = bar.querySelector('.hub-ux-refresh-btn');
    if (state.refreshBtn) {
      state.refreshBtn.addEventListener('click', onRefreshClick);
    }
    return bar;
  }

  function onRefreshClick() {
    var meta = PAGE_META[state.page];
    if (!meta || !meta.onRefresh) return;
    if (state.refreshBtn) {
      state.refreshBtn.disabled = true;
      state.refreshBtn.classList.add('is-spinning');
    }
    setStatus('loading', 'Refreshing');
    skeleton(true);
    Promise.resolve(meta.onRefresh())
      .catch(function () { setStatus('warn', 'Partial'); })
      .finally(function () {
        if (state.refreshBtn) {
          state.refreshBtn.disabled = false;
          state.refreshBtn.classList.remove('is-spinning');
        }
      });
  }

  function refreshExplorer() {
    if (global.Mn2ExplorerOverview && global.Mn2ExplorerOverview.refresh) {
      global.Mn2ExplorerOverview.refresh();
      markReady('ok');
      return Promise.resolve();
    }
    return fetch('/api/mn2/network-overview', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        markReady(d && d.success ? 'ok' : 'warn');
      });
  }

  function refreshProfile() {
    global.dispatchEvent(new CustomEvent('hub-ux-refresh', { detail: { page: 'profile' } }));
    if (typeof global.loadProfileData === 'function') {
      return Promise.resolve(global.loadProfileData()).then(function () { markReady('ok'); });
    }
    markReady('ok');
    return Promise.resolve();
  }

  function refreshCommandCenter() {
    global.dispatchEvent(new CustomEvent('hub-ux-refresh', { detail: { page: 'command-center' } }));
    if (global.CommandCenterHub && global.CommandCenterHub.refreshAll) {
      return global.CommandCenterHub.refreshAll().then(function () { markReady('ok'); });
    }
    markReady('ok');
    return Promise.resolve();
  }

  function refreshGame() {
    global.dispatchEvent(new CustomEvent('hub-ux-refresh', { detail: { page: 'game' } }));
    var u = localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
    return fetch('/api/points/all?user_id=' + encodeURIComponent(u))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var p = (d && d.points) ? d.points : {};
        function el(id, v) { var x = document.getElementById(id); if (x) x.textContent = v; }
        el('game-overview-level', (p.level != null ? p.level : 1).toString());
        el('game-overview-xp', (p.xp_total != null ? p.xp_total : 0).toLocaleString());
        el('game-overview-coins', (p.coins != null ? p.coins : 0).toLocaleString());
        markReady('ok');
      })
      .catch(function () { markReady('warn'); });
  }

  function refreshQuests() {
    if (typeof global.loadQuests === 'function') {
      return global.loadQuests().then(function () { markReady('ok'); }).catch(function () { markReady('warn'); });
    }
    global.dispatchEvent(new CustomEvent('hub-ux-refresh', { detail: { page: 'quests' } }));
    markReady('ok');
    return Promise.resolve();
  }

  function refreshBattle() {
    global.dispatchEvent(new CustomEvent('hub-ux-refresh', { detail: { page: 'battle' } }));
    var u = localStorage.getItem('game_user_id') || 'default_user';
    var tasks = [
      fetch('/api/points/all?user_id=' + encodeURIComponent(u)).then(function (r) { return r.json(); }),
      fetch('/api/battle/stats?user_id=' + encodeURIComponent(u)).then(function (r) { return r.ok ? r.json() : {}; })
    ];
    return Promise.all(tasks)
      .then(function (res) {
        var p = (res[0] && res[0].points) ? res[0].points : {};
        var b = res[1] || {};
        function el(id, v) { var x = document.getElementById(id); if (x) x.textContent = v; }
        el('battle-overview-level', (p.level != null ? p.level : 1).toString());
        el('battle-overview-bp', (p.battle_points != null ? p.battle_points : 0).toLocaleString());
        el('battle-overview-xp', (p.xp_total != null ? p.xp_total : 0).toLocaleString());
        el('stat-total-battles', (b.total_battles != null ? b.total_battles : 0).toLocaleString());
        el('stat-wins', (b.wins != null ? b.wins : 0).toLocaleString());
        markReady('ok');
      })
      .catch(function () { markReady('warn'); });
  }

  function refreshExchangeHub() {
    global.dispatchEvent(new CustomEvent('hub-ux-refresh', { detail: { page: 'exchange' } }));
    if (global.PlatformUpgradesBatch2 && global.PlatformUpgradesBatch2.initArea) {
      global.PlatformUpgradesBatch2.initArea('exchange');
    }
    if (typeof global.initArea === 'function') {
      return Promise.resolve(global.initArea('exchange', true)).then(function () { markReady('ok'); });
    }
    markReady('ok');
    return Promise.resolve();
  }

  function refreshShop() {
    global.dispatchEvent(new CustomEvent('hub-ux-refresh', { detail: { page: 'shop' } }));
    if (global.PlatformUpgradesBatch2 && global.PlatformUpgradesBatch2.initArea) {
      global.PlatformUpgradesBatch2.initArea('shop');
    }
    markReady('ok');
    return Promise.resolve();
  }

  function refreshCasino() {
    global.dispatchEvent(new CustomEvent('hub-ux-refresh', { detail: { page: 'casino' } }));
    if (global.PlatformUpgradesBatch2 && global.PlatformUpgradesBatch2.initArea) {
      global.PlatformUpgradesBatch2.initArea('casino');
    }
    markReady('ok');
    return Promise.resolve();
  }

  function refreshGenerator() {
    global.dispatchEvent(new CustomEvent('hub-ux-refresh', { detail: { page: 'generator' } }));
    if (global.PlatformUpgradesBatch2 && global.PlatformUpgradesBatch2.initArea) {
      global.PlatformUpgradesBatch2.initArea('generator');
    }
    markReady('ok');
    return Promise.resolve();
  }

  function patchQuestEmptyState() {
    var orig = global.renderQuests;
    if (typeof orig !== 'function' || orig.__hubUxPatched) return;
    global.renderQuests = function (quests) {
      if (!quests || !quests.length) {
        var container = document.getElementById('quests-container');
        if (container) {
          container.innerHTML = emptyStateHtml({
            icon: '📋',
            title: 'No quests right now',
            desc: 'Complete game actions or check back daily for new objectives.',
            actions: [
              { href: APP_BASE + '/game/', label: 'Play Game' },
              { href: APP_BASE + '/battle/', label: 'Battle', secondary: true },
              { href: APP_BASE + '/profit/', label: 'Profit Daemon', secondary: true }
            ]
          });
        }
        setStatus('empty', 'Empty');
        setSyncTime();
        return;
      }
      setStatus('ok', 'Live');
      setSyncTime();
      return orig(quests);
    };
    global.renderQuests.__hubUxPatched = true;
  }

  function patchQuestLoadError() {
    var orig = global.loadQuests;
    if (typeof orig !== 'function' || orig.__hubUxPatched) return;
    global.loadQuests = function () {
      var container = document.getElementById('quests-container');
      if (container && !container.querySelector('.quest-card')) {
        container.innerHTML = loadingHtml('Loading quests…');
      }
      setStatus('loading', 'Loading');
      return Promise.resolve(orig.apply(this, arguments))
        .catch(function (e) {
          if (container) {
            container.innerHTML = emptyStateHtml({
              icon: '⚠️',
              title: 'Could not load quests',
              desc: 'Check your connection and try refresh.',
              actions: [{ href: '#', label: 'Retry', secondary: true }]
            });
            var retry = container.querySelector('.hub-ux-empty-actions a');
            if (retry) {
              retry.addEventListener('click', function (ev) {
                ev.preventDefault();
                onRefreshClick();
              });
            }
          }
          setStatus('error', 'Error');
          throw e;
        });
    };
    global.loadQuests.__hubUxPatched = true;
  }

  function enhanceQuestActions() {
    var actions = document.querySelector('.mn2-page-actions');
    if (!actions || actions.querySelector('[href*="profit"]')) return;
    var profit = document.createElement('a');
    profit.href = APP_BASE + '/profit/';
    profit.textContent = 'Profit Daemon';
    profit.className = 'secondary';
    var exchange = document.createElement('a');
    exchange.href = APP_BASE + '/exchange/';
    exchange.textContent = 'Exchange';
    exchange.className = 'secondary';
    actions.appendChild(profit);
    actions.appendChild(exchange);
  }

  function enhanceGameAtAGlance() {
    var section = document.getElementById('game-at-a-glance');
    if (!section || section.querySelector('[data-hub-profit-link]')) return;
    var links = section.querySelector('div[style*="flex-wrap"]');
    if (!links) return;
    var profit = document.createElement('a');
    profit.href = APP_BASE + '/profit/';
    profit.setAttribute('data-hub-profit-link', '1');
    profit.style.cssText = 'color:#00ff88;font-size:0.9rem;';
    profit.textContent = 'Profit';
    var exchange = document.createElement('a');
    exchange.href = APP_BASE + '/exchange/';
    exchange.setAttribute('data-hub-exchange-link', '1');
    exchange.style.cssText = 'color:#00d4ff;font-size:0.9rem;';
    exchange.textContent = 'Exchange';
    links.appendChild(profit);
    links.appendChild(exchange);
  }

  function enhanceBattleAtAGlance() {
    var section = document.getElementById('battle-at-a-glance');
    if (!section || section.querySelector('[data-hub-profit-link]')) return;
    var links = section.querySelector('div[style*="flex-wrap"]');
    if (!links) return;
    var profit = document.createElement('a');
    profit.href = APP_BASE + '/profit/';
    profit.setAttribute('data-hub-profit-link', '1');
    profit.style.cssText = 'color:var(--battle-primary);font-size:0.9rem;';
    profit.textContent = 'Profit';
    var exchange = document.createElement('a');
    exchange.href = APP_BASE + '/exchange/';
    exchange.setAttribute('data-hub-exchange-link', '1');
    exchange.style.cssText = 'color:var(--battle-secondary);font-size:0.9rem;';
    exchange.textContent = 'Exchange';
    links.appendChild(profit);
    links.appendChild(exchange);
  }

  function init() {
    state.page = detectPage();
    if (!state.page || !PAGE_META[state.page]) return;

    document.body.classList.add('hub-ux-page');
    if (!document.body.getAttribute('data-hub-page')) {
      document.body.setAttribute('data-hub-page', state.page);
    }

    var meta = PAGE_META[state.page];
    mountBar(meta);
    skeleton(true);
    setStatus('loading', 'Loading');

    if (state.page === 'game') enhanceGameAtAGlance();
    if (state.page === 'battle') enhanceBattleAtAGlance();

    global.addEventListener('hub-ux-data-ready', function (ev) {
      var detail = (ev && ev.detail) || {};
      markReady(detail.empty ? 'empty' : (detail.status || 'ok'));
    });

    global.addEventListener('hub-ux-data-error', function () {
      setStatus('error', 'Error');
      skeleton(false);
    });

    setTimeout(function () {
      if (state.skeletonOn) markReady('ok');
    }, 12000);
  }

  global.HubPagesUX = {
    init: init,
    patchQuests: function () {
      enhanceQuestActions();
      patchQuestEmptyState();
      patchQuestLoadError();
    },
    setStatus: setStatus,
    markReady: markReady,
    emptyStateHtml: emptyStateHtml,
    loadingHtml: loadingHtml,
    refresh: onRefreshClick
  };

  if (detectPage() === 'quests') {
    global.HubPagesUX.patchQuests();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window);
