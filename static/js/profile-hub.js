/**
 * Profile hub — focused tabs, overview summary, deep links (#mn2-wallet).
 */
(function (global) {
  'use strict';

  function escapeHtml(value) {
    if (global.profileEscapeHtml) return global.profileEscapeHtml(value);
    return String(value ?? '').replace(/[&<>"']/g, function (ch) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
    });
  }

  function hubUserId() {
    return (
      (global.profileManager && global.profileManager.userId) ||
      localStorage.getItem('game_user_id') ||
      localStorage.getItem('user_id') ||
      'default_user'
    );
  }

  var SCROLL_MAP = {
    overview: 'profile-hub-overview',
    avatar: 'profile-section-avatar',
    account: 'profile-section-account',
    skills: 'profile-section-skills',
    trophies: 'profile-trophies-card',
    points: 'profile-section-points',
    leaderboard: 'profile-section-leaderboard',
    shop: 'profile-section-shop',
    wallet: 'mn2-wallet',
    settings: 'account-privacy-card',
    security: 'profile-section-security-layer',
    agents: 'my-agents-card',
    activity: 'profile-section-activity',
    lab: 'profile-section-lab-logbook',
    battle: 'quick-battle-profile-card',
    progress: 'profile-section-achievements',
  };

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

  function pulseGlanceStrip() {
    var strip = document.getElementById('profile-glance-stats');
    if (!strip) return;
    strip.classList.remove('profile-stats-pulse');
    void strip.offsetWidth;
    strip.classList.add('profile-stats-pulse');
  }

  function updateMn2Glow(balance) {
    var stat = document.getElementById('profile-glance-mn2-stat');
    if (!stat) return;
    var glow = isFinite(balance) && balance > 0;
    stat.classList.toggle('profile-glance-mn2-glow', glow);
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

  var ROUTE_LABELS = {
    overview: 'Overview',
    avatar: 'Avatar',
    account: 'Account',
    skills: 'Skills',
    trophies: 'Trophies',
    points: 'Points',
    leaderboard: 'Leaderboard',
    shop: 'Shop',
    wallet: 'Wallet',
    security: 'Security',
    settings: 'Settings',
    agents: 'Agents',
    activity: 'Activity',
    lab: 'Lab',
    battle: 'Battle',
    progress: 'Progress',
  };

  var SUMMARY_STATS = [
    { key: 'level', label: 'Level' },
    { key: 'xp_total', label: 'XP' },
    { key: 'coins', label: 'Coins' },
    { key: 'game_points', label: 'Game' },
    { key: 'battle_points', label: 'Battle' },
    { key: 'trophy_points', label: 'Trophies' },
  ];

  var profileGlanceInitialized = false;

  function renderProfileGlance(data, uid, opts) {
    opts = opts || {};
    var pts =
      data && data.unified_points && data.unified_points.points ? data.unified_points.points : {};
    var profile = (data && data.profile) || {};
    var prefs = profile.preferences || {};
    var display = prefs.display_name || profile.display_name || profile.username || uid;
    var level = pts.level != null ? pts.level : 1;
    var animate = opts.animate === true || (opts.animate !== false && profileGlanceInitialized);
    profileGlanceInitialized = true;
    if (animate) pulseGlanceStrip();
    var statOpts = animate ? {} : { instant: true };
    animateStat('profile-glance-level', level, statOpts);
    animateStat('profile-glance-xp', pts.xp_total != null ? pts.xp_total : 0, statOpts);
    animateStat('profile-glance-coins', pts.coins != null ? pts.coins : 0, statOpts);
    animateStat('profile-glance-battle', pts.battle_points != null ? pts.battle_points : 0, statOpts);
    animateStat('profile-glance-game', pts.game_points != null ? pts.game_points : 0, statOpts);
    animateStat('profile-core-level', level, statOpts);
    var pill = document.getElementById('profile-hero-user-pill');
    if (pill) {
      var shortId = uid.length > 18 ? uid.slice(0, 8) + '…' + uid.slice(-4) : uid;
      pill.textContent = String(display).slice(0, 24) + (String(display).length > 24 ? '…' : '') + ' · ' + shortId;
    }
    fetch('/api/mn2/balance?user_id=' + encodeURIComponent(uid))
      .then(function (r) {
        return r.json();
      })
      .then(function (b) {
        var bal = b && b.success ? Number(b.mn2_balance) : NaN;
        updateMn2Glow(bal);
        if (isFinite(bal)) animateStat('profile-glance-mn2', bal, statOpts);
        else setElText('profile-glance-mn2', '—');
      })
      .catch(function () {
        updateMn2Glow(NaN);
        setElText('profile-glance-mn2', '—');
      });
  }

  function renderHubSummary(data) {
    var pts =
      data && data.unified_points && data.unified_points.points ? data.unified_points.points : {};
    var sum = document.getElementById('profile-hub-summary');
    if (sum) {
      sum.innerHTML =
        '<div class="fp-stats profile-hub-fp-stats">' +
        SUMMARY_STATS.map(function (item) {
          var v = pts[item.key] != null ? pts[item.key] : 0;
          return (
            '<div class="fp-stat"><div class="v">' +
            escapeHtml(fmtNum(v)) +
            '</div><div class="l">' +
            escapeHtml(item.label) +
            '</div></div>'
          );
        }).join('') +
        '</div>';
      var shop = (data && data.shop_summary) || {};
      var inv = shop.inventory && shop.inventory.length ? shop.inventory.length : 0;
      var pur = shop.purchases && shop.purchases.length ? shop.purchases.length : 0;
      sum.innerHTML +=
        '<p class="profile-hub-shop-line">Shop inventory <strong>' +
        inv +
        '</strong> · recent purchases <strong>' +
        pur +
        '</strong></p>';
    }
    var lb = document.getElementById('profile-hub-leaderboard-snippet');
    if (lb && data && data.leaderboard_snippet && data.leaderboard_snippet.length) {
      lb.innerHTML =
        '<ol class="profile-leaderboard-list">' +
        data.leaderboard_snippet
          .map(function (row, i) {
            return (
              '<li><span class="profile-lb-rank">' +
              (i + 1) +
              '</span><code>' +
              escapeHtml(row.user_id || 'user') +
              '</code><span class="profile-lb-xp">' +
              escapeHtml(fmtNum(row.xp_total || 0)) +
              ' XP</span></li>'
            );
          })
          .join('') +
        '</ol>';
    } else if (lb) {
      lb.innerHTML = '<p class="fp-muted">No leaderboard data yet.</p>';
    }
  }

  global.refreshProfileHubSummary = function (userId, opts) {
    var uid = userId || hubUserId();
    return fetch('/api/user/profile/' + encodeURIComponent(uid) + '/aggregated')
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (data && data.success) {
          renderHubSummary(data);
          renderProfileGlance(data, uid, { animate: opts && opts.animate });
        }
        return data;
      })
      .catch(function () {
        var sum = document.getElementById('profile-hub-summary');
        if (sum) sum.textContent = 'Could not load unified overview.';
        return null;
      });
  };

  global.applyFocusedProfileRoute = function (route) {
    var activeRoute = route || 'overview';
    document.body.classList.add('profile-route-focused');
    document.querySelectorAll('[data-profile-route]').forEach(function (el) {
      var routes = (el.getAttribute('data-profile-route') || '').split(/\s+/).filter(Boolean);
      el.hidden = routes.indexOf(activeRoute) === -1;
    });
    var note = document.getElementById('profile-route-note');
    if (note) {
      note.textContent =
        'Viewing: ' +
        (ROUTE_LABELS[activeRoute] || activeRoute) +
        '. Switch tabs above to browse other sections.';
    }
    document.querySelectorAll('#profile-hub-nav [data-hub-scroll]').forEach(function (x) {
      var on = x.getAttribute('data-hub-scroll') === activeRoute;
      x.classList.toggle('is-active', on);
      x.classList.toggle('active', on);
      x.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    var hubStatus = document.getElementById('profile-hub-status');
    if (hubStatus) {
      hubStatus.textContent = ROUTE_LABELS[activeRoute] || activeRoute;
    }
    if (activeRoute === 'wallet' && global.ProfileMn2Wallet && typeof global.ProfileMn2Wallet.load === 'function') {
      global.ProfileMn2Wallet.load();
    }
    if (activeRoute === 'shop' && global.profileManager && typeof global.profileManager.loadShopInventoryV9 === 'function') {
      global.profileManager.loadShopInventoryV9();
    }
    if (activeRoute === 'security') {
      if (global.profileManager) {
        if (typeof global.profileManager.loadPasswordProtection === 'function') {
          global.profileManager.loadPasswordProtection();
        }
        if (typeof global.profileManager.loadAccountSecurity === 'function') {
          global.profileManager.loadAccountSecurity();
        }
      }
      if (global.Mn2WithdrawalSecurity && typeof global.Mn2WithdrawalSecurity.refresh === 'function') {
        global.Mn2WithdrawalSecurity.refresh();
      }
    }
  };

  function navigateHubTab(key, scroll) {
    global.applyFocusedProfileRoute(key);
    try {
      var url = new URL(global.location.href);
      if (key === 'overview') url.searchParams.delete('tab');
      else url.searchParams.set('tab', key);
      global.history.replaceState({}, document.title, url.pathname + url.search + url.hash);
    } catch (e) {
      /* ignore */
    }
    if (scroll !== false) {
      var id = SCROLL_MAP[key] || 'profile-hub-overview';
      var el = document.getElementById(id);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  function resolveInitialTab() {
    var tab = new URLSearchParams(global.location.search).get('tab');
    var hashRoute = (global.location.hash || '').replace(/^#/, '').toLowerCase();
    if (!tab && (hashRoute === 'mn2-wallet' || hashRoute === 'profile-mn2-wallet-card')) {
      tab = 'wallet';
    }
    if (!tab) return 'overview';
    var btnKey = {
      account: 'account',
      user: 'account',
      avatar: 'avatar',
      skills: 'skills',
      trophies: 'trophies',
      progress: 'progress',
      points: 'points',
      leaderboard: 'leaderboard',
      activity: 'activity',
      shop: 'shop',
      inventory: 'shop',
      wallet: 'wallet',
      security: 'security',
      settings: 'settings',
      agents: 'agents',
      lab: 'lab',
      battle: 'battle',
    };
    return btnKey[tab] || (SCROLL_MAP[tab] ? tab : 'overview');
  }

  function wireHeroRefresh() {
    var heroRefresh = document.getElementById('profile-hero-refresh');
    if (!heroRefresh || heroRefresh._bound) return;
    heroRefresh._bound = true;
    heroRefresh.addEventListener('click', function () {
      heroRefresh.disabled = true;
      heroRefresh.textContent = 'Refreshing…';
      var jobs = [global.refreshProfileHubSummary(undefined, { animate: true })];
      if (global.profileManager && typeof global.profileManager.loadProfile === 'function') {
        jobs.push(global.profileManager.loadProfile());
      }
      Promise.all(jobs).finally(function () {
        heroRefresh.disabled = false;
        heroRefresh.textContent = 'Refresh data';
        heroRefresh.removeAttribute('disabled');
      });
    });
  }

  function wireOverviewShortcuts() {
    document.querySelectorAll('[data-profile-go-tab]').forEach(function (btn) {
      if (btn._hubGoBound) return;
      btn._hubGoBound = true;
      btn.addEventListener('click', function () {
        var key = btn.getAttribute('data-profile-go-tab');
        if (!key) return;
        var navBtn = document.querySelector('#profile-hub-nav [data-hub-scroll="' + key + '"]');
        if (navBtn) navBtn.click();
        else navigateHubTab(key);
      });
    });
  }

  function initProfileHub() {
    var uid = localStorage.getItem('game_user_id') || 'default_user';
    var nav = document.getElementById('profile-hub-nav');
    if (nav && !nav._hubNavBound) {
      nav._hubNavBound = true;
      nav.addEventListener('click', function (ev) {
        var b = ev.target.closest('[data-hub-scroll]');
        if (!b) return;
        navigateHubTab(b.getAttribute('data-hub-scroll'));
      });
    }
    global.refreshProfileHubSummary(uid);
    var initial = resolveInitialTab();
    setTimeout(function () {
      if (initial === 'overview') {
        global.applyFocusedProfileRoute('overview');
      } else {
        var btn = document.querySelector('#profile-hub-nav [data-hub-scroll="' + initial + '"]');
        if (btn) btn.click();
        else global.applyFocusedProfileRoute(initial);
      }
    }, 300);
    wireHeroRefresh();
    wireOverviewShortcuts();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initProfileHub);
  } else {
    initProfileHub();
  }
})(typeof window !== 'undefined' ? window : globalThis);
