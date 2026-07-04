/* Platform batch-2 upgrades (101–300) — widgets and hub enhancements */
(function () {
  'use strict';

  var APP_BASE = (typeof window.APP_BASE !== 'undefined') ? window.APP_BASE : '';

  function uid() {
    return localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function fetchJson(path) {
    return fetch(path, { credentials: 'same-origin' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function ensureMount(id, afterSel) {
    var el = document.getElementById(id);
    if (el) return el;
    var after = document.querySelector(afterSel);
    if (!after) return null;
    el = document.createElement('div');
    el.id = id;
    el.className = 'pu-batch2-mount';
    after.parentNode.insertBefore(el, after.nextSibling);
    return el;
  }

  function renderStrip(area, done, total) {
    var mount = document.querySelector('[data-platform-area="' + area + '"]');
    if (!mount || mount.querySelector('.pu-batch2-strip')) return;
    var pct = total ? Math.round((done / total) * 100) : 0;
    var strip = document.createElement('div');
    strip.className = 'pu-batch2-strip platform-upgrade-strip';
    strip.innerHTML =
      '<div class="platform-upgrade-progress">' +
      '<strong>Batch 2</strong> — ' + done + '/' + total + ' (' + pct + '%)' +
      '<div class="platform-upgrade-bar"><span style="width:' + pct + '%"></span></div></div>' +
      '<a href="/docs/PLATFORM_UPGRADES_BATCH2.md" target="_blank" rel="noopener">Batch 2 roadmap</a>';
    mount.appendChild(strip);
  }

  function renderExplorer(d) {
    var banner = document.getElementById('pu-ex-daemon-banner');
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'pu-ex-daemon-banner';
      banner.className = 'pu-daemon-banner';
      var wrap = document.querySelector('.mn2-hub-wrap') || document.body;
      wrap.insertBefore(banner, wrap.firstChild);
    }
    var online = d.daemon_reachable;
    banner.className = 'pu-daemon-banner ' + (online ? 'pu-daemon-banner--ok' : 'pu-daemon-banner--warn');
    banner.innerHTML = (online ? '🟢' : '🔴') + ' Daemon ' + (online ? 'online' : 'unreachable') +
      (d.staking_enabled ? ' · staking active' : '') +
      (d.connections != null ? ' · ' + d.connections + ' peers' : '') +
      (d.mn2_usd_price != null ? ' · MN2 $' + d.mn2_usd_price : '');
    if (d.cache_age_sec > 60) {
      banner.innerHTML += ' · <span class="pu-stale-warn">cache stale</span>';
    }
  }

  function renderExchange(d) {
    var slot = ensureMount('pu-ex-hot-ticker', '#platform-area-widget');
    if (!slot) return;
    var hot = (d.hot_symbols || []).join(', ') || '—';
    slot.innerHTML =
      '<div class="pu-batch2-widget">' +
      '<span class="pu-ticker-label">🔥 Hot pairs</span> ' + esc(hot) +
      (d.paper_mode ? ' <span class="platform-cache-badge">paper</span>' : '') +
      (d.profit_kill ? ' <span class="pu-stale-warn">profit kill ON</span>' : '') +
      '</div>';
    document.querySelectorAll('.cex-hub-tab').forEach(function (tab) {
      if (tab.querySelector('.pu-tab-badge')) return;
      var b = document.createElement('span');
      b.className = 'pu-tab-badge platform-cache-badge';
      b.textContent = '↻';
      b.title = 'Tab refresh available';
      tab.appendChild(b);
    });
  }

  function renderShop(d) {
    var deal = d.daily_deal;
    if (!deal) return;
    var strip = document.getElementById('pu-shop-daily-deal');
    if (!strip) {
      strip = document.createElement('div');
      strip.id = 'pu-shop-daily-deal';
      strip.className = 'pu-daily-deal-strip';
      var header = document.querySelector('.shop-header') || document.querySelector('.shop-page');
      if (header) header.insertAdjacentElement('afterend', strip);
    }
    strip.innerHTML =
      '🔥 <strong>Daily deal</strong> — ' + esc(deal.name) +
      ' <s>' + esc(deal.original_price) + '</s> → <strong>' + esc(deal.deal_price) + ' coins</strong>' +
      ' (' + esc(deal.discount_pct) + '% off)';
    var cartBadge = document.getElementById('pu-cart-badge');
    if (!cartBadge) {
      var cur = document.querySelector('.currency-display');
      if (cur) {
        cartBadge = document.createElement('span');
        cartBadge.id = 'pu-cart-badge';
        cartBadge.className = 'platform-cache-badge';
        cartBadge.style.marginLeft = '8px';
        cur.appendChild(cartBadge);
      }
    }
    if (cartBadge && window.shopCart && window.shopCart.items) {
      cartBadge.textContent = '🛒 ' + window.shopCart.items.length;
    }
  }

  function renderCasino(d) {
    var ticker = document.getElementById('pu-casino-wins-ticker');
    if (!ticker) {
      ticker = document.createElement('div');
      ticker.id = 'pu-casino-wins-ticker';
      ticker.className = 'pu-wins-ticker';
      var bridge = document.getElementById('casino-exchange-bridge');
      if (bridge) bridge.after(ticker);
    }
    fetchJson('/api/casino/wins/ticker?limit=5').then(function (t) {
      var lines = (t.wins || []).map(function (w) {
        return esc(w.line || w.agent + ' +' + w.net);
      }).join(' · ') || 'No recent wins yet';
      ticker.innerHTML = '🏆 ' + lines;
    }).catch(function () {
      ticker.textContent = '🏆 Wins ticker loading…';
    });
    var jack = document.getElementById('pu-jackpot-bar');
    if (!jack) {
      jack = document.createElement('div');
      jack.id = 'pu-jackpot-bar';
      jack.className = 'pu-jackpot-bar';
      ticker.after(jack);
    }
    jack.innerHTML = '💰 Jackpot pool: <strong>' + esc(d.jackpot_pool || 10000) + '</strong> coins · House edge ' + esc(d.house_edge_pct || 2.5) + '%';
    var bridge = d.exchange_bridge || {};
    var bridgeEl = document.getElementById('casino-bridge-mn2');
    if (bridgeEl && bridge.mn2_balance != null) {
      bridgeEl.textContent = bridge.mn2_balance + ' MN2';
    }
  }

  function renderGenerator(d) {
    var credits = document.getElementById('pu-gen-credits');
    if (!credits) {
      credits = document.createElement('div');
      credits.id = 'pu-gen-credits';
      credits.className = 'pu-gen-credits-chip platform-cache-badge';
      var pill = document.getElementById('genHealthPill');
      if (pill && pill.parentNode) pill.parentNode.appendChild(credits);
    }
    credits.textContent = 'Credits: ' + (d.generation_credits != null ? d.generation_credits : '—') +
      ' · Queue: ' + (d.queue_depth != null ? d.queue_depth : '—');
    var bar = document.getElementById('progressBar');
    if (bar && !bar.getAttribute('data-pu-pct')) {
      bar.setAttribute('data-pu-pct', '1');
      var lbl = document.createElement('span');
      lbl.id = 'pu-gen-pct-label';
      lbl.className = 'pu-gen-pct';
      lbl.style.cssText = 'font-size:0.8rem;margin-left:6px;';
      bar.parentNode.appendChild(lbl);
      setInterval(function () {
        var w = parseFloat(bar.style.width) || 0;
        var el = document.getElementById('pu-gen-pct-label');
        if (el) el.textContent = Math.round(w) + '%';
      }, 500);
    }
  }

  function renderQuest(d) {
    var badge = document.getElementById('pu-quest-streak');
    if (!badge) {
      var h = document.querySelector('.page-header h1');
      if (h) {
        badge = document.createElement('span');
        badge.id = 'pu-quest-streak';
        badge.className = 'platform-cache-badge';
        badge.style.marginLeft = '10px';
        h.appendChild(badge);
      }
    }
    if (badge) {
      badge.textContent = '🔥 Streak ' + (d.streak_days || 0) + 'd · Claimable ' + (d.claimable || 0);
    }
    if (!document.getElementById('pu-quest-filter')) {
      var actions = document.querySelector('.mn2-page-actions');
      if (actions) {
        var sel = document.createElement('select');
        sel.id = 'pu-quest-filter';
        sel.className = 'pu-quest-filter';
        sel.innerHTML = '<option value="">All types</option>' +
          (d.quest_types || []).map(function (t) {
            return '<option value="' + esc(t) + '">' + esc(t) + '</option>';
          }).join('');
        sel.addEventListener('change', function () {
          var v = sel.value;
          document.querySelectorAll('.quest-card').forEach(function (card) {
            if (!v) { card.style.display = ''; return; }
            var type = (card.getAttribute('data-quest-type') || card.textContent || '').toLowerCase();
            card.style.display = type.indexOf(v) >= 0 ? '' : 'none';
          });
        });
        actions.appendChild(sel);
      }
    }
  }

  function renderBattle(d) {
    var chip = document.getElementById('pu-battle-mm');
    if (!chip) {
      chip = document.createElement('span');
      chip.id = 'pu-battle-mm';
      chip.className = 'platform-cache-badge';
      var glance = document.getElementById('battle-at-a-glance');
      if (glance) glance.appendChild(chip);
    }
    chip.textContent = '⚔️ ' + esc(d.recommended_difficulty || 'normal') +
      ' · streak ' + (d.win_streak || 0) +
      ' · ~' + (d.mn2_per_win || 0.01) + ' MN2/win';
    var oneClick = document.getElementById('pu-quick-battle-oneclick');
    if (!oneClick) {
      oneClick = document.createElement('button');
      oneClick.id = 'pu-quick-battle-oneclick';
      oneClick.type = 'button';
      oneClick.className = 'platform-battle-cta';
      oneClick.textContent = '⚡ One-click quick battle';
      oneClick.addEventListener('click', function () {
        if (typeof window.startQuickBattle === 'function') window.startQuickBattle();
        else window.location.hash = 'quick-battle';
      });
      var widget = document.getElementById('platform-area-widget');
      if (widget) widget.appendChild(oneClick);
    }
    try {
      var diff = localStorage.getItem('quick_battle_difficulty');
      if (diff) {
        var sel = document.getElementById('quick-battle-difficulty');
        if (sel) sel.value = diff;
      }
      var sel2 = document.getElementById('quick-battle-difficulty');
      if (sel2 && !sel2.__puPersist) {
        sel2.__puPersist = true;
        sel2.addEventListener('change', function () {
          localStorage.setItem('quick_battle_difficulty', sel2.value);
        });
      }
    } catch (e) { /* ignore */ }
  }

  function renderProfile(d) {
    var badge = document.getElementById('pu-profile-ppp');
    if (!badge) {
      var qs = document.getElementById('quick-stats');
      if (qs) {
        badge = document.createElement('div');
        badge.id = 'pu-profile-ppp';
        badge.className = 'stat-card';
        badge.innerHTML = '<div class="stat-value">' + esc(d.agent_level || '—') + '</div><div class="stat-label">PPP sync</div>';
        qs.appendChild(badge);
      }
    }
    var links = document.getElementById('pu-profile-stats-links');
    if (!links && d.stats_links) {
      links = document.createElement('div');
      links.id = 'pu-profile-stats-links';
      links.className = 'platform-upgrade-actions';
      links.style.marginTop = '10px';
      links.innerHTML = d.stats_links.map(function (l) {
        return '<a href="' + esc(l.href) + '">' + esc(l.label) + '</a>';
      }).join('');
      var slot = document.getElementById('platform-area-widget');
      if (slot) slot.appendChild(links);
    }
  }

  function renderCommandCenter(d) {
    var panel = document.getElementById('pu-cc-monitors');
    if (!panel) {
      panel = document.createElement('div');
      panel.id = 'pu-cc-monitors';
      panel.className = 'pu-cc-monitors';
      var page = document.querySelector('.cc-page');
      if (page) page.appendChild(panel);
    }
    panel.innerHTML =
      '<div class="pu-batch2-widget">Exchange treasury: $' + esc(d.treasury_usd || '—') +
      ' · Top25 open: ' + esc(d.top25_open) + ' (P0: ' + esc(d.top25_p0) + ')' +
      (d.profit_kill ? ' · <span class="pu-stale-warn">KILL SWITCH</span>' : '') + '</div>';
  }

  function renderGame(d) {
    var pulse = document.getElementById('pu-game-pulse');
    if (!pulse) {
      pulse = document.createElement('span');
      pulse.id = 'pu-game-pulse';
      pulse.className = 'platform-cache-badge';
      var glance = document.getElementById('game-at-a-glance');
      if (glance) glance.appendChild(pulse);
    }
    pulse.textContent = 'Champion pulse: ' + (d.champion_pulse ? new Date(d.champion_pulse).toLocaleTimeString() : 'live');
  }

  var RENDERERS = {
    explorer: renderExplorer,
    exchange: renderExchange,
    shop: renderShop,
    casino: renderCasino,
    generator: renderGenerator,
    quest: renderQuest,
    battle: renderBattle,
    profile: renderProfile,
    'command-center': renderCommandCenter,
    game: renderGame
  };

  function initArea(area) {
    fetchJson('/api/platform/batch2/' + encodeURIComponent(area) + '/widgets?user_id=' + encodeURIComponent(uid()))
      .then(function (d) {
        if (!d || !d.success) return;
        renderStrip(area, d.batch2_done, d.batch2_total);
        var fn = RENDERERS[area];
        if (fn) fn(d);
      })
      .catch(function () {});
    if (area === 'shop') {
      fetchJson('/api/shop/daily-deal/ui').then(function (d) {
        if (d && d.success) renderShop({ daily_deal: d });
      }).catch(function () {});
    }
  }

  function detectArea() {
    var el = document.querySelector('[data-platform-area]');
    if (el) return el.getAttribute('data-platform-area');
    var body = document.body && document.body.getAttribute('data-hub-page');
    return body || null;
  }

  function init() {
    var area = detectArea();
    if (area) initArea(area);
    fetchJson('/api/platform/upgrades/combined').then(function (c) {
      if (!c || !c.success) return;
      var el = document.querySelector('.platform-upgrade-strip strong');
      if (el && el.textContent.indexOf('Platform upgrades') >= 0) {
        el.textContent = 'Platform upgrades (300)';
      }
    }).catch(function () {});
  }

  window.PlatformUpgradesBatch2 = { init: init, initArea: initArea };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
