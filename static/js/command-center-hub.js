(function (global) {
  'use strict';

  var uid = function () {
    return localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || (window.MnUserId ? window.MnUserId.read() : '');
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
      { title: 'Casino Fund & Play', href: '/casino/#casino-fund-play', desc: 'PayPal / MN2 buy-in + Hot tables', reward: 'Conversion' },
      { title: 'Casino cashflow (ops)', href: '/command-center#casino', desc: 'House edge, deposits, exchange bridge', reward: 'Ops income' },
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
      { title: 'Camgirls studio', href: '/camgirls/', desc: 'AI hosts · MN2 or PayPal unlock, tips, gifts', reward: 'Studio MN2 + PayPal' },
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
      { title: 'Fund & Play', href: '/casino/#casino-fund-play', desc: 'PayPal packs + MN2 buy-in', reward: 'Deposits' },
      { title: 'Hot tables', href: '/casino/#casino-tab-home', desc: 'Dice, Keno, Slots, Flip, Crash, Roulette', reward: 'House edge' },
      { title: 'Lounge / cockpit', href: '/casino/?tab=lounge', desc: 'Quests, bridge, income monitor', reward: 'Retention' },
      { title: 'Contest table', href: '/casino/?tab=compete', desc: 'Leaderboards, tournaments, streak quests', reward: 'Competition' },
      { title: 'Camgirls lounge', href: '/camgirls/', desc: 'PayPal or MN2 unlocks, tips, fan club, private', reward: 'Premium spend' },
      { title: 'Social casino', href: '/casino/?tab=social', desc: 'Share wins, referrals, Discord', reward: 'Viral loop' },
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
      .catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'command-center-hub.js', context: 'catch' }); }
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
      .catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'command-center-hub.js', context: 'catch' }); }
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
    }).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'command-center-hub.js', context: 'catch' }); }
      el.textContent = 'Exchange monitor unavailable.';
    });
  }

  function opsToken() {
    try {
      return sessionStorage.getItem('cc_ops_token') || '';
    } catch (e) {
      return '';
    }
  }

  function setOpsToken(value) {
    try {
      if (value) sessionStorage.setItem('cc_ops_token', value);
      else sessionStorage.removeItem('cc_ops_token');
    } catch (e) { /* session only */ }
  }

  function fmtRail(n, rail) {
    var x = Number(n || 0);
    if (rail === 'mn2') return x.toFixed(4);
    if (rail === 'usd') return x.toFixed(2);
    return String(Math.round(x));
  }

  function renderCashflow(d) {
    var el = document.getElementById('cc-casino-monitor');
    var metrics = document.getElementById('cc-cashflow-metrics');
    var rails = document.getElementById('cc-cashflow-rails');
    var games = document.getElementById('cc-cashflow-games');
    if (!el) return;
    if (!d || !d.success) {
      el.textContent = (d && d.error) || 'Cashflow unavailable.';
      if (metrics) metrics.hidden = true;
      if (rails) rails.hidden = true;
      if (games) games.hidden = true;
      return;
    }
    var fin = d.financial_usd || {};
    var cf = d.cashflow || {};
    var paypal = cf.paypal_deposits || {};
    var buyins = cf.mn2_buyins || {};
    var bridge = cf.exchange_to_casino || {};
    el.innerHTML =
      '<strong>Ops cashflow</strong> · last ' + (d.since_hours || 24) + 'h' +
      ' · net ops USD $' + Number(fin.net_ops_usd || 0).toFixed(2) +
      ' · generated ' + (d.generated_at || '—');
    if (metrics) {
      metrics.hidden = false;
      metrics.innerHTML =
        '<div class="cc-cashflow-metric"><span>House edge USD</span><strong>$' + Number(fin.house_edge_usd || 0).toFixed(2) + '</strong></div>' +
        '<div class="cc-cashflow-metric"><span>Rake USD</span><strong>$' + Number(fin.rake_usd || 0).toFixed(2) + '</strong></div>' +
        '<div class="cc-cashflow-metric"><span>PayPal deposits</span><strong>$' + Number(paypal.amount_usd || 0).toFixed(2) + '</strong><span>' + (paypal.count || 0) + ' captures</span></div>' +
        '<div class="cc-cashflow-metric"><span>MN2 buy-ins</span><strong>$' + Number(buyins.casino_usd_credit || 0).toFixed(2) + '</strong><span>' + Number(buyins.price_mn2 || 0).toFixed(2) + ' MN2 · ' + (buyins.count || 0) + '</span></div>' +
        '<div class="cc-cashflow-metric"><span>Exchange → casino</span><strong>$' + Number(bridge.amount_usd || 0).toFixed(2) + '</strong><span>' + (bridge.casino_coins || 0) + ' coins · ' + (bridge.count || 0) + '</span></div>' +
        '<div class="cc-cashflow-metric"><span>Rebates USD</span><strong>$' + Number(fin.rebates_usd || 0).toFixed(2) + '</strong></div>';
    }
    if (rails) {
      var casino = d.casino || {};
      var keys = Object.keys(casino);
      if (!keys.length) {
        rails.hidden = true;
      } else {
        rails.hidden = false;
        rails.innerHTML = '<h3 style="margin:12px 0 6px;font-size:0.95rem;color:#7ee8ff;">House by rail</h3><table class="cc-cashflow-table"><thead><tr><th>Rail</th><th>Bets</th><th>Wagered</th><th>House</th><th>Rake</th></tr></thead><tbody>' +
          keys.map(function (rail) {
            var row = casino[rail] || {};
            return '<tr><td>' + rail.toUpperCase() + '</td><td>' + (row.bets || 0) + '</td><td>' +
              fmtRail(row.total_bet, rail) + '</td><td>' + fmtRail(row.house_edge, rail) + '</td><td>' +
              fmtRail(row.rake, rail) + '</td></tr>';
          }).join('') + '</tbody></table>';
      }
    }
    if (games) {
      var byGame = d.by_game || {};
      var gids = Object.keys(byGame).slice(0, 12);
      if (!gids.length) {
        games.hidden = true;
      } else {
        games.hidden = false;
        games.innerHTML = '<h3 style="margin:12px 0 6px;font-size:0.95rem;color:#7ee8ff;">Top games (all rails)</h3><table class="cc-cashflow-table"><thead><tr><th>Game</th><th>Rails</th><th>House (sum units)</th></tr></thead><tbody>' +
          gids.map(function (gid) {
            var railsMap = byGame[gid] || {};
            var parts = Object.keys(railsMap).map(function (r) {
              return r.toUpperCase() + ' ' + fmtRail((railsMap[r] || {}).house_edge, r);
            });
            return '<tr><td>' + gid + '</td><td>' + Object.keys(railsMap).join(', ') + '</td><td>' + parts.join(' · ') + '</td></tr>';
          }).join('') + '</tbody></table>' +
          '<p class="cc-cashflow-note">Per-rail house figures are not summed across coins/MN2/USD.</p>';
      }
    }
  }

  function loadCasinoCashflow() {
    var el = document.getElementById('cc-casino-monitor');
    var token = opsToken();
    var input = document.getElementById('cc-ops-token');
    if (input && token && !input.value) input.value = token;
    if (!token) {
      if (el) el.textContent = 'Enter ops token to load cashflow.';
      return;
    }
    if (el) el.textContent = 'Loading cashflow…';
    fetch('/api/casino/ops/income-summary?since_hours=24&venue=all', {
      credentials: 'same-origin',
      headers: { 'X-Ops-Token': token },
    })
      .then(function (r) {
        return r.json().then(function (d) {
          d = d || {};
          d._http = r.status;
          return d;
        });
      })
      .then(function (d) {
        if (d._http === 403) {
          renderCashflow({ success: false, error: 'Unauthorized — check ops token (MN2_OPS_SECRET).' });
          return;
        }
        renderCashflow(d);
      })
      .catch(function () {
        if (window.ErrorManager && window.ErrorManager.logJSError) {
          window.ErrorManager.logJSError(new Error('caught'), { source: 'command-center-hub.js', context: 'catch' });
        }
        renderCashflow({ success: false, error: 'Cashflow request failed.' });
      });
  }

  function loadCasinoMonitor() {
    // Public today snapshot as a lightweight fallback line under cashflow auth.
    var el = document.getElementById('cc-casino-monitor');
    if (!el || opsToken()) return;
    fetch('/api/casino/house-stats?user_id=' + encodeURIComponent(uid()) + '&currency=coins')
      .then(function (r) { return r.ok ? r.json() : {}; })
      .then(function (d) {
        if (!d || !d.success) return;
        el.innerHTML = '<strong>Public today (coins)</strong> · games: ' + (d.games_played || 0) +
          ' · wagered: ' + Number(d.total_wagered || 0).toFixed(0) +
          ' · house net: ' + Number(d.house_net || 0).toFixed(0) +
          ' · <em>enter ops token for full cashflow</em>';
      }).catch(function () { /* optional */ });
  }

  function bindCashflowAuth() {
    var loadBtn = document.getElementById('cc-ops-load');
    var clearBtn = document.getElementById('cc-ops-clear');
    var input = document.getElementById('cc-ops-token');
    if (input && opsToken()) input.value = opsToken();
    if (loadBtn) {
      loadBtn.addEventListener('click', function () {
        var value = (input && input.value) || '';
        setOpsToken(value.trim());
        loadCasinoCashflow();
      });
    }
    if (clearBtn) {
      clearBtn.addEventListener('click', function () {
        setOpsToken('');
        if (input) input.value = '';
        renderCashflow({ success: false, error: 'Token cleared. Enter ops token to load cashflow.' });
        loadCasinoMonitor();
      });
    }
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
    bindCashflowAuth();
    if (opsToken()) loadCasinoCashflow();
    else loadCasinoMonitor();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})(window);

;(function () {
  if (typeof window === 'undefined' || !window.ErrorManager || typeof window.ErrorManager.logJSError !== 'function') return;
  var source = 'command-center-hub.js';
  window.addEventListener('error', function (event) {
    var file = (event && event.filename) || '';
    if (file.indexOf(source) === -1) return;
    window.ErrorManager.logJSError(event.error || new Error(event.message || 'script error'), { source: source, context: 'window_error' });
  });
})();
