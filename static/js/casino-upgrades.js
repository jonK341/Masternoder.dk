(function () {
  'use strict';

  var activeCategory = 'all';
  var catalogCache = null;
  var progressCache = null;

  function uid() {
    try {
      return localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
    } catch (e) {
      return 'default_user';
    }
  }

  function q(id) {
    return document.getElementById(id);
  }

  function fmt(n, d) {
    var x = Number(n || 0);
    if (!isFinite(x)) return '0';
    return x.toLocaleString(undefined, { minimumFractionDigits: d || 0, maximumFractionDigits: d || 2 });
  }

  function priceLabel(row) {
    var parts = [];
    if (row.cost_coins != null) parts.push(fmt(row.cost_coins, 0) + ' coins');
    if (row.cost_mn2 != null) parts.push(fmt(row.cost_mn2, 4) + ' MN2');
    if (row.cost_xp != null) parts.push(fmt(row.cost_xp, 0) + ' XP');
    return parts.join(' · ') || 'Free';
  }

  function statusClass(status) {
    if (status === 'owned') return 'owned';
    if (status === 'available') return 'available';
    return 'locked';
  }

  function renderSummary(progress) {
    var el = q('casino-levelup-summary');
    if (!el || !progress || !progress.success) {
      if (el) el.textContent = 'Progress unavailable.';
      return;
    }
    var pct = progress.progress_pct || 0;
    el.innerHTML =
      '<div class="casino-levelup-level">Level ' + (progress.casino_level || 1) +
      ' · XP ' + fmt(progress.casino_xp, 0) + '</div>' +
      '<div class="casino-levelup-bar-wrap"><div class="casino-levelup-bar" style="width:' + pct + '%"></div></div>' +
      '<div class="casino-levelup-stats">' + (progress.unlocked || 0) + ' / ' + (progress.total || 250) +
      ' unlocked (' + pct + '%)</div>' +
      (progress.active_bonuses ? (
        '<div class="casino-levelup-bonuses">Active bonuses: +' + (progress.active_bonuses.xp_boost_pct || 0) +
        '% XP flair · ' + (progress.active_bonuses.visual_effects_count || 0) + ' visual effects</div>'
      ) : '');
  }

  function renderFilters(categories) {
    var wrap = q('casino-levelup-filters');
    if (!wrap) return;
    wrap.innerHTML = '';
    function addBtn(id, label, icon) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'casino-levelup-filter' + (activeCategory === id ? ' active' : '');
      btn.setAttribute('data-category', id);
      btn.textContent = (icon ? icon + ' ' : '') + label;
      btn.addEventListener('click', function () {
        activeCategory = id;
        renderFilters(categories);
        renderGrid(catalogCache);
      });
      wrap.appendChild(btn);
    }
    addBtn('all', 'All', '🎯');
    (categories || []).forEach(function (c) {
      addBtn(c.id, c.name, c.icon);
    });
  }

  function renderGrid(catalog) {
    var grid = q('casino-levelup-grid');
    if (!grid) return;
    if (!catalog || !catalog.success) {
      grid.textContent = 'Could not load upgrades.';
      return;
    }
    var rows = catalog.upgrades || [];
    if (activeCategory !== 'all') {
      rows = rows.filter(function (r) { return r.category === activeCategory; });
    }
    if (!rows.length) {
      grid.textContent = 'No upgrades in this category.';
      return;
    }
    grid.innerHTML = rows.map(function (row) {
      var st = row.status || 'catalog';
      var btn = '';
      if (st === 'available') {
        var cur = row.cost_coins != null ? 'coins' : (row.cost_xp != null ? 'xp' : 'mn2');
        btn = '<button type="button" class="casino-levelup-buy" data-id="' + row.id + '" data-currency="' + cur + '">Unlock</button>';
      } else if (st === 'owned') {
        btn = '<span class="casino-levelup-owned-badge">✓ Owned</span>';
      } else {
        btn = '<span class="casino-levelup-locked-badge">' +
          (st === 'locked_level' ? 'Lv ' + (row.level_required || 1) : 'Locked') + '</span>';
      }
      return '<article class="casino-levelup-card ' + statusClass(st) + '">' +
        '<div class="casino-levelup-icon">' + (row.icon || '⬆️') + '</div>' +
        '<div class="casino-levelup-body">' +
        '<div class="casino-levelup-name">' + (row.name || row.id) + '</div>' +
        '<div class="casino-levelup-desc">' + (row.description || '') + '</div>' +
        '<div class="casino-levelup-meta">Tier ' + (row.tier || 1) + ' · ' + priceLabel(row) + '</div>' +
        '</div>' + btn + '</article>';
    }).join('');

    grid.querySelectorAll('.casino-levelup-buy').forEach(function (btn) {
      btn.addEventListener('click', function () {
        purchaseUpgrade(btn.getAttribute('data-id'), btn.getAttribute('data-currency'));
      });
    });
  }

  function toast(msg) {
    if (window.__casinoShowToast) {
      window.__casinoShowToast(msg);
      return;
    }
    var el = q('casino-toast');
    if (!el) return;
    el.textContent = msg;
    el.classList.remove('hidden');
    setTimeout(function () { el.classList.add('hidden'); }, 3200);
  }

  function purchaseUpgrade(upgradeId, currency) {
    if (!upgradeId) return;
    fetch('/api/casino/upgrades/purchase', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: uid(), upgrade_id: upgradeId, currency: currency || 'coins' }),
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.success) {
          toast('Unlocked: ' + ((d.upgrade && d.upgrade.name) || upgradeId));
          progressCache = d.progress || progressCache;
          return refresh();
        }
        toast(d.error || 'Could not unlock upgrade');
      })
      .catch(function () { toast('Network error'); });
  }

  function fetchCatalog(category) {
    var path = '/api/casino/upgrades/catalog?user_id=' + encodeURIComponent(uid());
    if (category && category !== 'all') path += '&category=' + encodeURIComponent(category);
    return fetch(path, { credentials: 'same-origin' }).then(function (r) { return r.json(); });
  }

  function fetchProgress() {
    return fetch('/api/casino/upgrades/progress?user_id=' + encodeURIComponent(uid()), { credentials: 'same-origin' })
      .then(function (r) { return r.json(); });
  }

  function refresh() {
    return Promise.all([fetchCatalog(), fetchProgress()]).then(function (res) {
      catalogCache = res[0];
      progressCache = res[1];
      renderSummary(progressCache);
      renderFilters((catalogCache && catalogCache.categories) || []);
      renderGrid(catalogCache);
    });
  }

  window.__casinoUpgrades = { refresh: refresh };

  function init() {
    if (!q('casino-levelup-grid')) return;
    refresh();
    document.addEventListener('casino:tab-change', function (ev) {
      if (ev.detail && ev.detail.tab === 'levelup') refresh();
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
