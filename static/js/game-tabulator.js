/**
 * Game hub tabulator — grouped nav replacing sidebar clutter.
 */
(function (global) {
  'use strict';

  var SECTIONS = [
    {
      id: 'play',
      label: '▶ Play',
      tabs: [
        { id: 'overview', label: '🏆 Trophy Hunt' },
        { id: 'campaign', label: '📡 Nexus' },
        { id: 'quests', label: '📜 Quests' },
        { id: 'challenges', label: '🎯 Challenges' },
        { id: 'starmap25', label: '🗺️ Star Map' },
      ],
    },
    {
      id: 'progress',
      label: '📈 Progress',
      tabs: [
        { id: 'achievements', label: '🏅 Trophies' },
        { id: 'milestones', label: '🎯 Milestones' },
        { id: 'stats', label: '📊 Stats' },
        { id: 'history', label: '📜 XP History' },
        { id: 'timeline', label: '📅 Timeline' },
      ],
    },
    {
      id: 'compete',
      label: '🏅 Compete',
      tabs: [
        { id: 'leaderboard', label: '🏆 Leaderboard' },
        { id: 'social', label: '👥 Social' },
      ],
    },
    {
      id: 'earn',
      label: '💰 Earn',
      tabs: [{ id: 'rewards', label: '💎 Level MN2' }],
    },
    {
      id: 'guide',
      label: '📚 Guide',
      tabs: [
        { id: 'epic', label: '🌙 Calm Journey' },
        { id: 'walkthrough', label: '📖 Walkthrough' },
        { id: 'guides', label: '📚 Guides' },
      ],
    },
  ];

  var state = { section: 'play', tab: 'overview', claimable: 0 };

  function tabToSection(tabId) {
    for (var i = 0; i < SECTIONS.length; i++) {
      var sec = SECTIONS[i];
      for (var j = 0; j < sec.tabs.length; j++) {
        if (sec.tabs[j].id === tabId) return sec.id;
      }
    }
    return 'play';
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function activateTab(tabId, pushHash) {
    if (!tabId) return;
    state.tab = tabId;
    state.section = tabToSection(tabId);
    var legacy = document.querySelector('.game-tab[data-tab="' + tabId + '"]');
    if (legacy) legacy.click();
    render();
    if (pushHash !== false) {
      try {
        history.replaceState(null, '', '#' + tabId);
      } catch (e) {}
    }
  }

  function renderSubnav() {
    var sub = document.getElementById('game-hub-subnav');
    if (!sub) return;
    var sec = SECTIONS.filter(function (s) {
      return s.id === state.section;
    })[0];
    if (!sec) return;
    sub.innerHTML = sec.tabs
      .map(function (t) {
        return (
          '<button type="button" class="game-hub-tab' +
          (state.tab === t.id ? ' active' : '') +
          '" data-game-tab="' +
          esc(t.id) +
          '" role="tab">' +
          esc(t.label) +
          '</button>'
        );
      })
      .join('');
    sub.querySelectorAll('[data-game-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        activateTab(btn.getAttribute('data-game-tab'));
      });
    });
  }

  function renderSections() {
    var nav = document.getElementById('game-hub-nav');
    if (!nav) return;
    nav.innerHTML = SECTIONS.map(function (sec) {
      var dot =
        sec.id === 'earn' && state.claimable > 0
          ? '<span class="gh-dot">' + (state.claimable > 9 ? '9+' : state.claimable) + '</span>'
          : '';
      return (
        '<button type="button" class="game-hub-section' +
        (state.section === sec.id ? ' active' : '') +
        '" data-game-section="' +
        esc(sec.id) +
        '" role="tab">' +
        esc(sec.label) +
        dot +
        '</button>'
      );
    }).join('');
    nav.querySelectorAll('[data-game-section]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var sid = btn.getAttribute('data-game-section');
        var sec = SECTIONS.filter(function (s) {
          return s.id === sid;
        })[0];
        if (!sec || !sec.tabs.length) return;
        var stillHere = sec.tabs.some(function (t) {
          return t.id === state.tab;
        });
        activateTab(stillHere ? state.tab : sec.tabs[0].id);
      });
    });
  }

  function render() {
    renderSections();
    renderSubnav();
  }

  function refreshClaimable() {
    var uid =
      localStorage.getItem('game_user_id') ||
      localStorage.getItem('user_id') ||
      'default_user';
    fetch('/api/game/crypto/level-rewards?user_id=' + encodeURIComponent(uid))
      .then(function (r) {
        return r.ok ? r.json() : {};
      })
      .then(function (d) {
        if (d && d.success !== false) {
          state.claimable = Number(d.claimable_count || 0);
          renderSections();
        }
      })
      .catch(function () {});
  }

  function init() {
    var layout = document.querySelector('.hunter-game-layout');
    if (!layout || document.getElementById('game-hub-nav')) return;
    document.body.classList.add('game-tabulator-v2');
    var shell = document.createElement('div');
    shell.className = 'game-hub-shell';
    shell.innerHTML =
      '<nav class="game-hub-nav" id="game-hub-nav" aria-label="Game hub sections"></nav>' +
      '<div class="game-hub-subnav" id="game-hub-subnav" role="tablist" aria-label="Section tabs"></div>';
    layout.parentNode.insertBefore(shell, layout);

    var hash = (window.location.hash || '').replace('#', '');
    if (hash) {
      state.section = tabToSection(hash);
      state.tab = hash;
    }
    render();

    document.addEventListener('click', function (e) {
      var t = e.target.closest('[data-tab-target]');
      if (!t) return;
      var tab = t.getAttribute('data-tab-target');
      if (tab && tab !== 'battle') activateTab(tab);
    });

    refreshClaimable();
    setInterval(refreshClaimable, 60000);

    global.GameTabulator = {
      activate: activateTab,
      refreshClaimable: refreshClaimable,
      getState: function () {
        return { section: state.section, tab: state.tab };
      },
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window);
