/* Platform 100-upgrade cross-area widgets — mounts on [data-platform-area] */
(function () {
  'use strict';

  function uid() {
    return localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
  }

  function q(sel, root) {
    return (root || document).querySelector(sel);
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function fmtUsd(n) {
    if (n == null || isNaN(Number(n))) return '—';
    return '$' + Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function fetchJson(path) {
    return fetch(path, { credentials: 'same-origin' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function mount() {
    var el = document.querySelector('[data-platform-area]');
    if (!el) return;
    var area = el.getAttribute('data-platform-area');
    if (!area) return;
    initStrip(el, area);
    initArea(area);
  }

  function initStrip(el, area) {
    fetchJson('/api/platform/upgrades?area=' + encodeURIComponent(area))
      .then(function (d) {
        if (!d || !d.success) return;
        var pct = d.total ? Math.round((d.done / d.total) * 100) : 0;
        el.innerHTML =
          '<div class="platform-upgrade-strip">' +
          '<div class="platform-upgrade-progress">' +
          '<strong>Platform upgrades</strong> — ' + d.done + '/' + d.total + ' done (' + pct + '%)' +
          '<div class="platform-upgrade-bar"><span style="width:' + pct + '%"></span></div>' +
          '</div>' +
          '<div class="platform-upgrade-actions">' +
          '<a href="/docs/PLATFORM_100_UPGRADES.md" target="_blank" rel="noopener">Roadmap</a>' +
          '<a href="/docs/PLATFORM_UPGRADES_BATCH2.md" target="_blank" rel="noopener">Batch 2</a>' +
          '<button type="button" class="pu-refresh" data-area="' + esc(area) + '">Refresh</button>' +
          '</div></div>';
        var btn = el.querySelector('.pu-refresh');
        if (btn) btn.addEventListener('click', function () { initArea(area, true); });
      })
      .catch(function () {});
  }

  function widgetHtml(title, metrics, extra) {
    var rows = (metrics || []).map(function (m) {
      return '<div><span>' + esc(m.label) + '</span><strong>' + esc(m.value) + '</strong></div>';
    }).join('');
    return (
      '<div class="platform-upgrade-widget">' +
      '<h3>' + esc(title) + '</h3>' +
      '<div class="platform-upgrade-metrics">' + rows + '</div>' +
      (extra || '') +
      '</div>'
    );
  }

  function initArea(area, force) {
    var slot = document.getElementById('platform-area-widget');
    if (!slot) return;
    fetchJson('/api/platform/area/' + encodeURIComponent(area) + '/summary?user_id=' + encodeURIComponent(uid()))
      .then(function (d) {
        if (!d || !d.success) return;
        if (area === 'explorer') renderExplorer(slot, d);
        else if (area === 'exchange') renderExchange(slot, d);
        else if (area === 'profile') renderProfile(slot, d);
        else if (area === 'shop') renderShop(slot, d);
        else if (area === 'casino') renderCasino(slot, d);
        else if (area === 'generator') renderGenerator(slot, d);
        else if (area === 'command-center') renderCommandCenter(slot, d);
        else if (area === 'game') renderGame(slot, d);
        else if (area === 'quest') renderQuest(slot, d);
        else if (area === 'battle') renderBattle(slot, d);
      })
      .catch(function () {
        if (force) slot.textContent = 'Summary unavailable — try again.';
      });
  }

  function renderExplorer(slot, d) {
    enhanceExplorerTables();
    addCacheBadge('ex-updated', d.cache_source);
    var refreshBtn = document.getElementById('ex-refresh-btn');
    if (!refreshBtn) {
      var upd = document.getElementById('ex-updated');
      if (upd && upd.parentNode) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.id = 'ex-refresh-btn';
        btn.className = 'platform-upgrade-actions';
        btn.style.cssText = 'margin-left:8px;padding:4px 10px;font-size:0.8rem;';
        btn.textContent = '↻ Refresh';
        btn.addEventListener('click', function () {
          if (typeof window.__exRefresh === 'function') window.__exRefresh();
          else document.dispatchEvent(new CustomEvent('mn2-explorer-refresh'));
        });
        upd.parentNode.insertBefore(btn, upd.nextSibling);
      }
    }
    slot.innerHTML = widgetHtml('Explorer live', [
      { label: 'Block height', value: d.block_height != null ? d.block_height : '—' },
      { label: 'MN2 price', value: d.mn2_usd_price != null ? '$' + d.mn2_usd_price : '—' },
      { label: 'Daemon', value: d.daemon_reachable ? 'Online' : 'Unreachable' },
      { label: 'Masternodes', value: d.masternode_count != null ? d.masternode_count : '—' },
    ]);
  }

  function enhanceExplorerTables() {
    document.querySelectorAll('.mn2-tab-panel[data-mn2-tab="explorer"] table').forEach(function (tbl) {
      var wrap = tbl.parentElement;
      if (wrap && !wrap.classList.contains('ex-table-mobile')) {
        wrap.classList.add('ex-table-mobile');
        var headers = [];
        tbl.querySelectorAll('thead th').forEach(function (th, i) {
          headers[i] = th.textContent.trim();
        });
        tbl.querySelectorAll('tbody tr').forEach(function (tr) {
          tr.querySelectorAll('td').forEach(function (td, i) {
            if (headers[i]) td.setAttribute('data-label', headers[i]);
          });
        });
      }
    });
  }

  function addCacheBadge(targetId, source) {
    var el = document.getElementById(targetId);
    if (!el) return;
    var old = el.querySelector('.platform-cache-badge');
    if (old) old.remove();
    var badge = document.createElement('span');
    badge.className = 'platform-cache-badge';
    badge.textContent = 'cache: ' + (source || 'live');
    el.appendChild(badge);
  }

  function renderExchange(slot, d) {
    slot.innerHTML = widgetHtml('Exchange treasury', [
      { label: 'Live stash', value: fmtUsd(d.live_stash_usd) },
      { label: 'Paper stash', value: fmtUsd(d.paper_stash_usd) },
      { label: 'Total', value: fmtUsd(d.total_stash_usd) },
    ],
      '<div class="platform-upgrade-actions" style="margin-top:10px;">' +
      '<a href="' + esc(d.profit_link || '/profit/') + '">Profit daemon</a>' +
      '<a href="' + esc(d.oracle_link || '/exchange/#cex-profit-oracle') + '">Profit Oracle</a>' +
      '<button type="button" id="cex-pu-refresh">↻ Refresh stash</button></div>');
    var btn = document.getElementById('cex-pu-refresh');
    if (btn) btn.addEventListener('click', function () { initArea('exchange', true); });
  }

  function renderProfile(slot, d) {
    slot.innerHTML = widgetHtml('Profile & PPP', [
      { label: 'Level', value: d.level != null ? d.level : '—' },
      { label: 'XP', value: d.xp != null ? d.xp : '—' },
      { label: 'Coins', value: d.coins != null ? d.coins : '—' },
      { label: 'MN2 wallet', value: d.mn2_balance != null ? d.mn2_balance + ' MN2' : '—' },
      { label: 'Agent level (PPP)', value: d.agent_level != null ? d.agent_level : '—' },
    ],
      (d.ppp_synced ? '<p style="margin:8px 0 0;font-size:0.8rem;color:#00ff88;">PPP quest sync active</p>' : ''));
    var qs = document.getElementById('quick-stats');
    if (qs && !qs.querySelector('.pu-agent-level')) {
      var chip = document.createElement('div');
      chip.className = 'stat-card pu-agent-level';
      chip.innerHTML = '<div class="stat-value">' + esc(d.agent_level != null ? d.agent_level : '—') + '</div><div class="stat-label">Agent level (PPP)</div>';
      qs.appendChild(chip);
    }
  }

  function renderShop(slot, d) {
    slot.innerHTML = widgetHtml('Shop MN2 pricing', [
      { label: 'USD / MN2', value: d.mn2_usd_price != null ? '$' + d.mn2_usd_price : '—' },
      { label: 'Cart key', value: d.cart_key || 'local' },
    ],
      '<div class="platform-upgrade-actions" style="margin-top:10px;">' +
      '<a href="' + esc(d.daily_deal_endpoint || '/api/shop/daily-deal') + '" target="_blank" rel="noopener">Daily deal API</a></div>');
    ensureShopCartPersistence(d.cart_key);
    annotateShopMn2Prices(d.mn2_usd_price);
  }

  function ensureShopCartPersistence(key) {
    if (!key || window.__shopCartPersist) return;
    window.__shopCartPersist = true;
    try {
      var saved = localStorage.getItem(key);
      if (saved && window.shopCart && typeof window.shopCart.restore === 'function') {
        window.shopCart.restore(JSON.parse(saved));
      }
      document.addEventListener('shop-cart-updated', function () {
        if (window.shopCart && window.shopCart.items) {
          localStorage.setItem(key, JSON.stringify(window.shopCart.items));
        }
      });
    } catch (e) { /* ignore */ }
  }

  function annotateShopMn2Prices(usdPerMn2) {
    if (!usdPerMn2 || isNaN(Number(usdPerMn2))) return;
    document.querySelectorAll('.shop-item [data-price-mn2], .shop-item .item-price').forEach(function (el) {
      var coins = parseFloat(el.getAttribute('data-coins') || el.textContent.replace(/[^\d.]/g, ''));
      if (!coins || isNaN(coins)) return;
      var mn2 = coins / 100;
      var usd = mn2 * Number(usdPerMn2);
      var tag = el.parentElement && el.parentElement.querySelector('.pu-mn2-price');
      if (!tag) {
        tag = document.createElement('div');
        tag.className = 'pu-mn2-price';
        tag.style.cssText = 'font-size:0.78rem;color:#00d4ff;margin-top:4px;';
        (el.parentElement || el).appendChild(tag);
      }
      tag.textContent = '≈ ' + mn2.toFixed(4) + ' MN2 (' + fmtUsd(usd) + ')';
    });
  }

  function renderCasino(slot, d) {
    var rg = d.responsible_gaming || {};
    var banner = document.getElementById('platform-rg-banner');
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'platform-rg-banner';
      banner.className = 'platform-rg-banner';
      var header = document.querySelector('.casino-header');
      if (header) header.after(banner);
    }
    banner.innerHTML = '🛡️ <strong>Responsible gaming</strong> — ' +
      esc(rg.message || 'Set limits in your profile. Virtual coins first; real-money stakes require verification.') +
      ' <a href="/profile">Profile limits</a> · <a href="' + esc(d.profit_link || '/profit/') + '">Profit monitor</a>';
    slot.innerHTML = widgetHtml('Casino agents', [
      { label: 'Session cap', value: rg.daily_cap != null ? rg.daily_cap : 'default' },
      { label: 'Bets today', value: rg.bets_today != null ? rg.bets_today : '—' },
    ],
      '<div class="platform-upgrade-actions" style="margin-top:10px;">' +
      '<a href="' + esc(d.agent_control_link || '/exchange/#cex-control-center') + '">Agent control</a>' +
      '<a href="/profit/">Profit daemon</a></div>');
  }

  function renderGenerator(slot, d) {
    slot.innerHTML = widgetHtml('Generator API', [
      { label: 'API status', value: d.api_ready ? 'Ready' : (d.api_message || 'Check config') },
      { label: 'Queue depth', value: d.queue_depth != null ? d.queue_depth : '—' },
    ],
      '<div id="pu-gen-history" style="margin-top:10px;font-size:0.82rem;opacity:0.85;">Loading history…</div>');
    fetchJson('/api/generator/history?user_id=' + encodeURIComponent(uid()) + '&limit=5')
      .then(function (h) {
        var box = document.getElementById('pu-gen-history');
        if (!box) return;
        var jobs = (h && h.jobs) || (h && h.history) || [];
        if (!jobs.length) { box.textContent = 'No recent jobs.'; return; }
        box.innerHTML = '<strong>Recent jobs</strong><ul style="margin:6px 0 0;padding-left:18px;">' +
          jobs.slice(0, 5).map(function (j) {
            return '<li>' + esc(j.status || j.state || 'job') + ' — ' + esc(j.id || j.job_id || '') + '</li>';
          }).join('') + '</ul>';
      })
      .catch(function () {
        var box = document.getElementById('pu-gen-history');
        if (box) box.textContent = 'History unavailable.';
      });
    var pill = document.getElementById('genHealthPill');
    if (pill) pill.textContent = d.api_ready ? 'API: ready' : 'API: ' + (d.api_message || 'warn');
  }

  function renderCommandCenter(slot, d) {
    slot.innerHTML = widgetHtml('Ops dashboard', [
      { label: 'MN2 daemon', value: d.daemon_reachable ? 'Online (' + (d.daemon_connections || 0) + ' peers)' : 'Unreachable' },
      { label: 'Top25 open', value: d.top25_open != null ? d.top25_open : '—' },
      { label: 'Top25 done', value: d.top25_done != null ? d.top25_done : '—' },
    ],
      '<div class="platform-upgrade-actions" style="margin-top:10px;">' +
      '<a href="/profit/">Profit daemon</a>' +
      '<a href="/exchange/#cex-profit-oracle">Profit Oracle</a>' +
      '<a href="/docs/PROFIT_CRITICAL_TOP25.md" target="_blank" rel="noopener">Top25 doc</a></div>');
    var mon = document.getElementById('cc-power-label');
    if (mon) {
      mon.textContent = 'Daemon ' + (d.daemon_reachable ? 'online' : 'offline') +
        ' · Top25 ' + (d.top25_done || 0) + '/' + (d.top25_total || 25) + ' resolved';
    }
  }

  function renderGame(slot, d) {
    var grid = (d.featured || []).map(function (g) {
      return '<a href="' + esc(g.href) + '">' + esc(g.title) + '</a>';
    }).join('');
    slot.innerHTML = widgetHtml('Game hub', [
      { label: 'Your level', value: d.level != null ? d.level : '—' },
      { label: 'XP', value: d.xp != null ? d.xp : '—' },
      { label: 'Online now', value: d.online_estimate != null ? d.online_estimate : '1+' },
    ],
      '<div class="platform-featured-grid" style="margin-top:10px;">' + grid + '</div>');
    var online = document.getElementById('game-online-count');
    if (!online) {
      var glance = document.getElementById('game-at-a-glance');
      if (glance) {
        online = document.createElement('div');
        online.id = 'game-online-count';
        glance.appendChild(online);
      }
    }
    if (online) online.innerHTML = 'Online <span style="color:#00ff88;font-weight:700;">' + esc(d.online_estimate || '1+') + '</span>';
  }

  function renderQuest(slot, d) {
    slot.innerHTML = widgetHtml('Quest board', [
      { label: 'Active', value: d.active_quests != null ? d.active_quests : '—' },
      { label: 'Claimable', value: d.claimable != null ? d.claimable : '—' },
      { label: 'Streak', value: (d.streak && d.streak.days) ? d.streak.days + ' days' : '—' },
    ],
      (d.ppp_sync ? '<p style="margin:8px 0 0;font-size:0.8rem;color:#00ff88;">PPP quest sync active</p>' : ''));
    var header = document.querySelector('.page-header');
    if (header && !document.getElementById('pu-quest-ppp-badge')) {
      var b = document.createElement('span');
      b.id = 'pu-quest-ppp-badge';
      b.className = 'platform-cache-badge';
      b.style.marginLeft = '10px';
      b.textContent = 'PPP synced';
      header.querySelector('h1').appendChild(b);
    }
  }

  function renderBattle(slot, d) {
    var lb = (d.leaderboard || []).slice(0, 3).map(function (r, i) {
      return '<li>#' + (i + 1) + ' ' + esc(r.user_id || r.name || 'player') + ' — ' + esc(r.score != null ? r.score : r.battle_points || '') + '</li>';
    }).join('') || '<li>No leaderboard data yet</li>';
    var hist = (d.recent_matches || []).slice(0, 3).map(function (m) {
      return '<li>' + esc(m.result || m.outcome || 'match') + ' vs ' + esc(m.opponent || m.opponent_id || '—') + '</li>';
    }).join('') || '<li>No recent matches</li>';
    var stats = d.stats || {};
    slot.innerHTML = widgetHtml('Battle arena', [
      { label: 'Total battles', value: stats.total_battles != null ? stats.total_battles : '—' },
      { label: 'Wins', value: stats.wins != null ? stats.wins : '—' },
      { label: 'Battle points', value: stats.battle_points != null ? stats.battle_points : '—' },
    ],
      '<a class="platform-battle-cta" href="' + esc(d.enter_battle_href || '/battle#quick-battle') + '">⚔️ Enter battle now</a>' +
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:10px;font-size:0.82rem;">' +
      '<div><strong>Leaderboard</strong><ul style="margin:6px 0 0;padding-left:18px;">' + lb + '</ul></div>' +
      '<div><strong>Recent matches</strong><ul style="margin:6px 0 0;padding-left:18px;">' + hist + '</ul></div></div>');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
})();
