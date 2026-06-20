(function (global) {
  'use strict';

  var uid = function () {
    return localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
  };

  var LINKS = {
    overview: [
      { title: 'Battle', href: '/battle/', desc: 'Quick & ranked battles', reward: '0.01–0.05 MN2/win' },
      { title: 'Trophies', href: '/trophies/', desc: 'Collection & income', reward: 'Passive MN2' },
      { title: 'Game', href: '/game/', desc: 'Campaign & stats', reward: 'Level MN2' },
      { title: 'Quests', href: '/quests/', desc: 'Daily objectives', reward: 'Quest MN2' },
      { title: 'Battlegrounds', href: '/battlegrounds/', desc: 'Mass PvP zones', reward: 'BG MN2' },
      { title: 'Social', href: '/social/', desc: 'Crews & friends', reward: 'Social tips' },
      { title: 'Generator', href: '/generator/', desc: 'Video & clips', reward: 'Gen MN2' },
      { title: 'Debugger Q&A', href: '/debugger/#quiz', desc: 'Top 50 quiz', reward: 'Up to 0.05 MN2' },
    ],
    battle: [
      { title: 'Quick Battle', href: '/battle/', desc: 'Instant fights', reward: 'MN2 per win' },
      { title: 'Battlegrounds', href: '/battlegrounds/', desc: 'Zone control', reward: 'MN2 pool' },
      { title: 'Champions League', href: '/champions-league/', desc: 'Season ladder', reward: 'Trophy MN2' },
    ],
    trophies: [
      { title: 'Trophy table', href: '/trophies/', desc: 'All definitions', reward: 'Collector income' },
      { title: 'Star Map 25', href: '/starmap25/', desc: 'Constellation levels', reward: 'Map MN2' },
    ],
    game: [
      { title: 'Game hub', href: '/game/', desc: '17 tabs unified', reward: 'Level rewards' },
      { title: 'Campaign', href: '/game#campaign', desc: 'Hunter Nexus', reward: 'Campaign MN2' },
      { title: 'Leaderboard', href: '/game#leaderboard', desc: 'Rankings', reward: 'Top 25 MN2' },
    ],
    quests: [
      { title: 'Quest board', href: '/quests/', desc: 'Active quests', reward: 'Quest MN2' },
      { title: 'Lab tasks', href: '/lab/#workbench', desc: 'Science assignments', reward: 'Lab MN2' },
    ],
    battlegrounds: [{ title: 'Enter battlegrounds', href: '/battlegrounds/', desc: 'MN2 zone battles', reward: 'Zone MN2' }],
    social: [
      { title: 'Social hub', href: '/social/', desc: 'Posts & crews', reward: 'Tip MN2' },
      { title: 'Chat (Lab room)', href: '/lab/#discussion', desc: 'Lab discussion', reward: '—' },
    ],
    generator: [
      { title: 'Generator', href: '/generator/', desc: 'Video pipeline', reward: 'Gen MN2' },
      { title: 'Camgirls studio', href: '/camgirls/', desc: 'Actor integration', reward: 'Studio MN2' },
    ],
    agents: [
      { title: 'Agents control', href: '/agents/', desc: 'Assign agents', reward: 'Automation' },
      { title: 'Lab agents', href: '/lab/#agents', desc: 'Science cron', reward: 'Daily progress' },
    ],
  };

  function card(item) {
    return (
      '<a class="cc-card" href="' +
      item.href +
      '" style="text-decoration:none;color:inherit;display:block;">' +
      '<h3>' +
      item.title +
      '</h3><p style="margin:0;font-size:0.85rem;opacity:0.8;">' +
      item.desc +
      '</p><div class="cc-reward">' +
      item.reward +
      '</div></a>'
    );
  }

  function renderGrid(id, items) {
    var el = document.getElementById(id);
    if (!el || !items) return;
    el.innerHTML = items.map(card).join('');
  }

  function initTabs() {
    var nav = document.getElementById('cc-hub-nav');
    if (!nav) return;
    nav.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-cc-tab]');
      if (!btn) return;
      var tab = btn.getAttribute('data-cc-tab');
      nav.querySelectorAll('.cc-tab').forEach(function (b) {
        b.classList.toggle('active', b === btn);
      });
      document.querySelectorAll('.cc-panel').forEach(function (p) {
        p.classList.toggle('active', p.id === 'cc-panel-' + tab);
      });
    });
  }

  function loadPowerMonitor() {
    var fill = document.getElementById('cc-power-fill');
    var label = document.getElementById('cc-power-label');
    var u = encodeURIComponent(uid());
    Promise.all([
      fetch('/api/battle/stats?user_id=' + u).then(function (r) {
        return r.ok ? r.json() : {};
      }),
      fetch('/api/generator/crypto-rewards?user_id=' + u).then(function (r) {
        return r.ok ? r.json() : {};
      }),
      fetch('/api/mn2/balance?user_id=' + u).then(function (r) {
        return r.ok ? r.json() : {};
      }),
    ])
      .then(function (res) {
        var battle = res[0] || {};
        var gen = res[1] || {};
        var bal = res[2] || {};
        var wins = Number(battle.wins || battle.total_wins || 0);
        var genJobs = Number(gen.jobs_completed || gen.total_jobs || 0);
        var mn2 = Number(bal.mn2_balance || 0);
        var score = Math.min(100, wins * 2 + genJobs * 3 + mn2 * 10);
        if (fill) fill.style.width = score + '%';
        if (label) {
          label.textContent =
            'Battles: ' + wins + ' wins · Generator jobs: ' + genJobs + ' · MN2: ' + mn2.toFixed(4);
        }
      })
      .catch(function () {
        if (label) label.textContent = 'Power data unavailable — links still work.';
      });
  }

  function loadAgents() {
    var st = document.getElementById('cc-agent-status');
    fetch('/api/agents/list?user_id=' + encodeURIComponent(uid()))
      .then(function (r) {
        return r.ok ? r.json() : {};
      })
      .then(function (d) {
        var n = (d.agents || d.items || []).length;
        if (st) st.textContent = n ? n + ' agents available — assign from Agents tab.' : 'Agents API ready — open Agents control.';
      })
      .catch(function () {
        if (st) st.textContent = 'Agent plugin idle (no blocking spinner).';
      });
  }

  function init() {
    Object.keys(LINKS).forEach(function (k) {
      renderGrid('cc-' + k + '-grid', LINKS[k]);
    });
    renderGrid('cc-overview-grid', LINKS.overview);
    initTabs();
    loadPowerMonitor();
    loadAgents();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})(window);
