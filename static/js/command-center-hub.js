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
      { title: 'Exchange', href: '/exchange/', desc: 'Buy MN2, trade 25 assets, tax logs', reward: 'Fees + rebates' },
      { title: 'Exchange Profit Oracle', href: '/exchange/#cex-profit-oracle', desc: 'Profit bot, P/L, fees, and projections', reward: 'Profit intelligence' },
      { title: 'Casino cockpit', href: '/casino/#casino-cockpit', desc: 'Games, income monitor, contests', reward: 'House + engagement' },
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
    exchange: [
      { title: 'Buy MN2 with PayPal', href: '/exchange?tab=onramp', desc: 'Fiat redirect through PayPal, MN2 wallet credit', reward: 'MN2 liquidity' },
      { title: 'Gateway layer', href: '/exchange/#cex-gateway-layer', desc: 'Pending orders, capture readiness, payment rails', reward: 'Safer payments' },
      { title: 'Profit Oracle Agent', href: '/exchange/#cex-profit-oracle', desc: 'Estimated P/L, fee drag, ROI, projections', reward: 'Better decisions' },
      { title: '25-asset exchange', href: '/exchange/', desc: 'Swap, limits, staking, tax records', reward: 'Trading fees' },
      { title: 'Bot daemon', href: '/exchange/#cex-agent-cross-trading', desc: 'Cross-trading agents and performance monitor', reward: 'Liquidity automation' },
      { title: 'Internal MN2 market', href: '/explorer?tab=market', desc: 'MN2 / coins order book', reward: 'Market activity' },
      { title: 'Profile wallet', href: '/profile#mn2-wallet', desc: 'Deposits, withdrawals, statements', reward: 'Retention' },
    ],
    casino: [
      { title: 'Casino cockpit', href: '/casino/#casino-cockpit', desc: 'Table of contents + live monitors', reward: 'House income' },
      { title: 'Contest table', href: '/casino/#casino-tab-leaderboard', desc: 'Leaderboards, tournaments, streak quests', reward: 'Competition' },
      { title: 'Camgirls lounge', href: '/camgirls/', desc: 'MN2 unlocks, tips, fan clubs', reward: 'Premium spend' },
      { title: 'Social casino', href: '/casino/#casino-tab-social', desc: 'Share wins, referrals, Discord', reward: 'Viral loop' },
    ],
    agents: [
      { title: 'Agents control', href: '/agents/', desc: 'Assign agents', reward: 'Automation' },
      { title: 'Lab agents', href: '/lab/#agents', desc: 'Science cron', reward: 'Daily progress' },
      { title: 'Casino evolution skills', href: '/casino/#casino-cockpit', desc: 'Risk, VIP, tournament, camgirl concierge', reward: 'Retention ops' },
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
      if (history && history.replaceState) {
        history.replaceState({}, document.title, '?tab=' + encodeURIComponent(tab));
      }
    });
    var initial = new URLSearchParams(window.location.search).get('tab') || (window.location.hash || '').replace('#', '');
    if (initial) {
      var btn = nav.querySelector('[data-cc-tab="' + initial + '"]');
      if (btn) btn.click();
    }
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

  function loadExchangeMonitor() {
    var el = document.getElementById('cc-exchange-monitor');
    if (!el) return;
    Promise.all([
      fetch('/api/exchange/health').then(function (r) { return r.ok ? r.json() : {}; }),
      fetch('/api/exchange/trades?limit=25').then(function (r) { return r.ok ? r.json() : {}; }),
      fetch('/api/exchange/catalog').then(function (r) { return r.ok ? r.json() : {}; }),
      fetch('/api/exchange/profit-agent?user_id=' + encodeURIComponent(uid())).then(function (r) { return r.ok ? r.json() : {}; }),
      fetch('/api/exchange/gateway/status').then(function (r) { return r.ok ? r.json() : {}; })
    ]).then(function (res) {
      var h = res[0] || {};
      var trades = (res[1] && res[1].trades) || [];
      var cat = res[2] || {};
      var profit = res[3] || {};
      var gateway = (res[4] && res[4].totals) || {};
      el.innerHTML = '<strong>Exchange monitor</strong> · ' +
        (h.status || 'unknown') + ' · assets: ' + (cat.asset_count || h.asset_count || '—') +
        ' · recent trades: ' + trades.length +
        ' · treasury fees: ' + Number(h.treasury_fees_mn2 || 0).toFixed(4) + ' MN2' +
        ' · P/L: $' + Number(profit.estimated_total_pnl_usd || 0).toFixed(2) +
        ' · gateway pending: ' + Number(gateway.pending_count || 0);
    }).catch(function () {
      el.textContent = 'Exchange monitor unavailable.';
    });
  }

  function loadCasinoMonitor() {
    var el = document.getElementById('cc-casino-monitor');
    if (!el) return;
    fetch('/api/casino/house-stats?user_id=' + encodeURIComponent(uid()) + '&currency=coins')
      .then(function (r) { return r.ok ? r.json() : {}; })
      .then(function (d) {
        el.innerHTML = '<strong>Casino monitor</strong> · bets: ' + (d.total_bets || d.bets || '—') +
          ' · wagered: ' + Number(d.total_wagered || 0).toFixed(2) +
          ' · house net: ' + Number(d.house_profit || d.net || 0).toFixed(2);
      }).catch(function () {
        el.textContent = 'Casino monitor unavailable.';
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
    loadExchangeMonitor();
    loadCasinoMonitor();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})(window);
