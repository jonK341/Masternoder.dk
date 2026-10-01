/**
 * Exchange hub — glance metrics + framed site tour
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'cex_onboard_v20261001_done';

  var STEPS = [
    {
      tab: 'trade',
      frameTitle: 'Trade desk',
      frameBody: 'Instant swap · PayPal buy · Limit orders · Staking · Tax export',
      title: 'Start with Trade',
      body: 'Pick a market on the left, swap in the center, and watch your custodial wallet on the right. MN2 and Coins are both supported as quote currencies.',
    },
    {
      tab: 'overview',
      frameTitle: 'Overview & health',
      frameBody: 'Kill switch · Profit blockers · Progress · Profit Oracle · Gateway',
      title: 'Overview keeps you honest',
      body: 'Health KPIs, profit-path blockers, and your progress monitor live here. Use this tab before turning bots to live mode.',
    },
    {
      tab: 'bots',
      frameTitle: 'Bots & research',
      frameBody: 'Profit path table · Agent marketplace · Daemon rental · Cross-trading',
      title: 'Bots & daemons',
      body: 'Paper-trade by default. Rent daemons, attach skill packs, and inspect profit-path scans before you commit capital.',
    },
    {
      tab: 'marketplace',
      frameTitle: 'Marketplace',
      frameBody: 'Agent shop · NFT lane · Rentals · Exchange shop boosts',
      title: 'Marketplace & shop',
      body: 'Buy or rent agents, browse NFT listings, and spend MN2 on boosts, trust badges, and rental extensions.',
    },
    {
      tab: 'liquidity',
      frameTitle: 'Sales pool',
      frameBody: 'Sweep balances · Pooled assets · Ledger history',
      title: 'Sales pool',
      body: 'See how idle assets are swept into the shared sales pool and when the last transfer ran.',
    },
    {
      tab: 'treasury',
      frameTitle: 'Treasury',
      frameBody: 'Stashed USD · Paper vs live · MN2 treasury wallet',
      title: 'Treasury',
      body: 'Platform treasury and fee collection — separate from your personal exchange wallet.',
    },
    {
      tab: 'venues',
      frameTitle: 'Venues',
      frameBody: 'API credentials · Live readiness · Per-exchange status',
      title: 'Venue readiness',
      body: 'Check which external exchanges have keys configured and are cleared for live API trading.',
    },
  ];

  var stepIndex = 0;

  function q(id) { return document.getElementById(id); }

  function uid() {
    try { return localStorage.getItem('game_user_id') || 'default_user'; }
    catch (e) { return 'default_user'; }
  }

  function fetchJson(path) {
    if (window.ExchangeHub && window.ExchangeHub.fetchJson) {
      return window.ExchangeHub.fetchJson(path, { timeout: 8000 });
    }
    return fetch(path, { credentials: 'same-origin' }).then(function (r) { return r.json(); });
  }

  function setText(id, text) {
    var el = q(id);
    if (el) el.textContent = text;
  }

  function pulseStats() {
    var strip = q('cex-glance-stats');
    if (!strip) return;
    strip.classList.remove('cex-stats-pulse');
    void strip.offsetWidth;
    strip.classList.add('cex-stats-pulse');
  }

  function loadGlance() {
    var u = encodeURIComponent(uid());
    return Promise.all([
      fetchJson('/api/exchange/catalog').catch(function () { return null; }),
      fetchJson('/api/exchange/health').catch(function () { return null; }),
      fetchJson('/api/exchange/wallet?user_id=' + u).catch(function () { return null; }),
      fetchJson('/api/exchange/rewards?user_id=' + u).catch(function () { return null; }),
    ]).then(function (res) {
      var catalog = res[0];
      var health = res[1];
      var wallet = res[2];
      var rewards = res[3];

      if (catalog && catalog.success) {
        setText('cex-glance-markets', String(catalog.asset_count || (catalog.assets && catalog.assets.length) || 25));
      }
      if (health) {
        setText('cex-glance-agents', String(health.agent_count || 0));
        setText('cex-glance-kill', health.kill_switch ? 'ON' : 'Off');
      }
      if (wallet && wallet.success) {
        var keys = Object.keys(wallet.assets || {}).filter(function (k) {
          return Number(wallet.assets[k]) > 0;
        });
        setText('cex-glance-balances', String(keys.length));
      }
      if (rewards && rewards.success && rewards.tier) {
        setText('cex-glance-tier', rewards.tier.label || 'Bronze');
      }

      var mn2El = q('cex-mn2-balance');
      if (mn2El && mn2El.textContent && mn2El.textContent !== '—') {
        setText('cex-glance-mn2', mn2El.textContent);
        var mn2Stat = q('cex-glance-mn2-stat');
        if (mn2Stat) mn2Stat.classList.add('cex-glance-mn2-glow');
      }

      var status = q('cex-hero-status');
      if (status) {
        var mk = (catalog && catalog.success) ? (catalog.asset_count || 25) + ' markets live' : 'Markets loading…';
        var ks = health && health.kill_switch ? ' · Kill switch ON' : '';
        status.textContent = mk + ks + ' · Updated ' + new Date().toLocaleTimeString();
      }
      pulseStats();
    });
  }

  function displayName() {
    try {
      return localStorage.getItem('game_display_name') || localStorage.getItem('game_username') || '';
    } catch (e) {
      return '';
    }
  }

  function updateUserPill() {
    var pill = q('cex-hero-user-pill');
    if (!pill) return;
    var name = displayName();
    pill.textContent = name ? name : 'Guest trader';
  }

  function renderStep() {
    var step = STEPS[stepIndex];
    if (!step) return;
    setText('cex-onboard-step-num', 'Step ' + (stepIndex + 1) + ' of ' + STEPS.length);
    setText('cex-onboard-title', step.title);
    var body = q('cex-onboard-body-text');
    if (body) body.textContent = step.body;
    setText('cex-onboard-frame-title', step.frameTitle);
    setText('cex-onboard-frame-body', step.frameBody);
    var bar = q('cex-onboard-progress-bar');
    if (bar) {
      bar.style.width = String(((stepIndex + 1) / STEPS.length) * 100) + '%';
    }
    var back = q('cex-onboard-back');
    if (back) back.disabled = stepIndex === 0;
    var next = q('cex-onboard-next');
    if (next) next.textContent = stepIndex === STEPS.length - 1 ? 'Finish tour' : 'Next';
  }

  function openOnboard() {
    var root = q('cex-onboard');
    if (!root) return;
    stepIndex = 0;
    renderStep();
    root.hidden = false;
    root.setAttribute('aria-hidden', 'false');
  }

  function closeOnboard(markDone) {
    var root = q('cex-onboard');
    if (!root) return;
    root.hidden = true;
    root.setAttribute('aria-hidden', 'true');
    if (markDone) {
      try { localStorage.setItem(STORAGE_KEY, '1'); } catch (e) { /* ignore */ }
    }
  }

  function goStep(delta) {
    stepIndex += delta;
    if (stepIndex < 0) stepIndex = 0;
    if (stepIndex >= STEPS.length) {
      closeOnboard(true);
      return;
    }
    renderStep();
  }

  function jumpToStepTab() {
    var step = STEPS[stepIndex];
    if (!step) return;
    if (window.ExchangeHub && window.ExchangeHub.applyTab) {
      window.ExchangeHub.applyTab(step.tab);
    }
    closeOnboard(true);
    setTimeout(function () {
      var wrap = document.querySelector('.cex-hub-wrap');
      if (wrap) wrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 80);
  }

  function maybeAutoTour() {
    try {
      if (localStorage.getItem(STORAGE_KEY) === '1') return;
      var force = window.location.search.indexOf('tour=1') >= 0;
      setTimeout(openOnboard, force ? 400 : 1400);
    } catch (e) { /* ignore */ }
  }

  function bindGotoControl(btn) {
    btn.addEventListener('click', function (ev) {
      if (btn.tagName === 'A' && btn.getAttribute('href') && btn.getAttribute('href').charAt(0) === '#') {
        ev.preventDefault();
      }
      var tab = btn.getAttribute('data-cex-goto');
      if (window.ExchangeHub && window.ExchangeHub.applyTab && tab) {
        window.ExchangeHub.applyTab(tab);
      }
      var hash = btn.getAttribute('data-cex-hash') || (btn.getAttribute('href') || '').replace(/^[^#]*/, '');
      if (hash && hash.charAt(0) === '#') {
        var target = document.querySelector(hash);
        if (target) {
          setTimeout(function () {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }, 150);
        }
      }
    });
  }

  function bindMapCards() {
    document.querySelectorAll('.cex-map-card[data-cex-goto], .cex-hotshot-cta[data-cex-goto], a[data-cex-goto][href^="#"]').forEach(bindGotoControl);
  }

  function init() {
    updateUserPill();
    loadGlance();
    bindMapCards();

    var refresh = q('cex-hero-refresh');
    if (refresh && !refresh._cexOnboardRefreshBound) {
      refresh._cexOnboardRefreshBound = true;
      refresh.addEventListener('click', function () {
        loadGlance();
        if (window.CexAccountBridge && window.CexAccountBridge.refresh) {
          window.CexAccountBridge.refresh({ animate: true });
        }
        if (window.ExchangeHub && window.ExchangeHub.loadTab) {
          window.ExchangeHub.loadTab('trade', true);
        }
      });
    }

    var start = q('cex-onboard-start');
    if (start) start.addEventListener('click', openOnboard);

    var closeBtn = q('cex-onboard-close');
    if (closeBtn) closeBtn.addEventListener('click', function () { closeOnboard(false); });

    var backdrop = q('cex-onboard-backdrop');
    if (backdrop) backdrop.addEventListener('click', function () { closeOnboard(false); });

    var back = q('cex-onboard-back');
    if (back) back.addEventListener('click', function () { goStep(-1); });

    var next = q('cex-onboard-next');
    if (next) next.addEventListener('click', function () { goStep(1); });

    var jump = q('cex-onboard-jump');
    if (jump) jump.addEventListener('click', jumpToStepTab);

    var skip = q('cex-onboard-skip');
    if (skip) skip.addEventListener('click', function () { closeOnboard(true); });

    maybeAutoTour();
    setTimeout(loadGlance, 2800);
    setInterval(loadGlance, 120000);
  }

  window.CexOnboard = { open: openOnboard, refreshGlance: loadGlance };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
