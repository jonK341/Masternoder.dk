/**
 * Camgirls Giga UI — Top 10 intelligence (10 upgrades).
 */
(function () {
  'use strict';

  var top10Map = {};
  var top10List = [];
  var vibeFilter = 'all';

  function apiUrl(path) {
    return typeof window.cgApi === 'function' ? window.cgApi(path) : path;
  }

  function staticUrl(path) {
    return typeof window.cgStatic === 'function' ? window.cgStatic(path) : path;
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function performerHref(id) {
    if (typeof window.cgPerformerPath === 'function') {
      return window.cgPerformerPath(id);
    }
    return '/camgirls/p/' + encodeURIComponent(id) + '/';
  }

  function mountHero(platform) {
    var host = document.querySelector('.cg-header');
    if (!host || document.getElementById('cg-giga-hero')) return;
    var scale = (platform && platform.scale) || {};
    var hero = document.createElement('section');
    hero.id = 'cg-giga-hero';
    hero.className = 'cg-giga-hero';
    hero.innerHTML =
      '<div class="cg-giga-hero-inner">' +
      '<h1>Studio Intelligence · Top 10</h1>' +
      '<p class="cg-giga-hero-sub">Neural-ranked performers · agent mesh · MN2 on-chain rails · LiveKit voice · real-time roster telemetry.</p>' +
      '<div class="cg-giga-telemetry" id="cg-giga-telemetry"></div>' +
      '</div>';
    host.parentNode.insertBefore(hero, host);
    host.classList.add('cg-giga-header-legacy');
    var tel = document.getElementById('cg-giga-telemetry');
    if (!tel) return;
    tel.innerHTML =
      '<span class="cg-giga-stat"><strong>' +
      esc(platform.performers_count || '—') +
      '</strong> live AI hosts</span>' +
      '<span class="cg-giga-stat"><strong>' +
      esc(platform.agents_linked || '—') +
      '</strong> agents linked</span>' +
      '<span class="cg-giga-stat">scale <strong>' +
      esc(scale.progress_pct != null ? scale.progress_pct + '%' : '—') +
      '</strong></span>' +
      '<span class="cg-giga-stat">roster <strong>' +
      esc(scale.current || '—') +
      '/' +
      esc(scale.target || 250) +
      '</strong></span>';
  }

  function mountTicker(stack) {
    if (document.getElementById('cg-intel-ticker')) return;
    var labels = stack && stack.length ? stack : ['Agent mesh', 'MN2 wallet', 'SSE chat', 'LiveKit', 'Skill sets'];
    var doubled = labels.concat(labels);
    var row = document.createElement('div');
    row.id = 'cg-intel-ticker';
    row.className = 'cg-intel-ticker';
    row.innerHTML =
      '<div class="cg-intel-ticker-inner">' +
      doubled.map(function (t) {
        return '<span>◎ ' + esc(t) + '</span>';
      }).join('') +
      '</div>';
    var anchor = document.getElementById('cg-giga-hero') || document.querySelector('.cg-header');
    if (anchor && anchor.parentNode) {
      anchor.parentNode.insertBefore(row, anchor.nextSibling);
    }
  }

  function mountRing(scale) {
    var tel = document.getElementById('cg-giga-telemetry');
    if (!tel || document.getElementById('cg-roster-ring')) return;
    var pct = parseFloat(scale.progress_pct || 0);
    var circ = 2 * Math.PI * 30;
    var off = circ * (1 - Math.min(100, pct) / 100);
    var ring = document.createElement('div');
    ring.id = 'cg-roster-ring';
    ring.className = 'cg-roster-ring-wrap';
    ring.innerHTML =
      '<svg width="72" height="72" viewBox="0 0 72 72">' +
      '<circle cx="36" cy="36" r="30" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="6"/>' +
      '<circle cx="36" cy="36" r="30" fill="none" stroke="#9dff66" stroke-width="6" stroke-dasharray="' +
      circ +
      '" stroke-dashoffset="' +
      off +
      '"/></svg>' +
      '<span class="cg-roster-ring-label">' +
      Math.round(pct) +
      '%</span>';
    tel.appendChild(ring);
  }

  function renderTop10(data) {
    if (document.getElementById('cg-top10-panel') || !data.top10) return;
    var panel = document.createElement('section');
    panel.id = 'cg-top10-panel';
    panel.className = 'cg-top10-panel';
    panel.innerHTML =
      '<h2>🏆 Top 10 Intelligence <span>neural rank · tech stack</span></h2>' +
      '<p class="cg-constellation">Agent constellation — each host maps to <code>camgirl_agent_*</code> with skill sets + MN2 mesh.</p>' +
      '<ol class="cg-top10-list" id="cg-top10-list"></ol>';
    var ticker = document.getElementById('cg-intel-ticker');
    var parent = ticker && ticker.parentNode ? ticker.parentNode : document.querySelector('.cg-page');
    if (parent) {
      parent.insertBefore(panel, ticker ? ticker.nextSibling : null);
    }
    var list = document.getElementById('cg-top10-list');
    if (!list) return;
    top10List = data.top10;
    top10Map = {};
    data.top10.forEach(function (row) {
      top10Map[row.performer_id] = row;
    });
    list.innerHTML = data.top10
      .map(function (row) {
        var pic = row.picture_url || '/static/camgirls/avatar-demo.svg';
        var tech = (row.technologies || []).slice(0, 4);
        return (
          '<li class="cg-top10-row"><span class="cg-top10-rank">#' +
          esc(row.rank) +
          '</span><img class="cg-top10-avatar" src="' +
          esc(staticUrl(pic)) +
          '" alt=""><div class="cg-top10-meta"><strong><a href="' +
          esc(performerHref(row.performer_id)) +
          '" style="color:inherit">' +
          esc(row.display_name) +
          '</a></strong><small>' +
          esc(row.intel_summary || '') +
          ' · score ' +
          esc(row.score) +
          '</small></div><div class="cg-top10-tech">' +
          tech
            .map(function (t) {
              return '<span class="cg-top10-chip">' + esc(t) + '</span>';
            })
            .join('') +
          '</div></li>'
        );
      })
      .join('');
    renderSpotlight(data.top10.slice(0, 3));
  }

  function renderSpotlight(rows) {
    if (!rows.length || document.getElementById('cg-spotlight')) return;
    var wrap = document.createElement('section');
    wrap.id = 'cg-spotlight';
    wrap.className = 'cg-spotlight';
    wrap.innerHTML =
      '<div class="cg-spotlight-track">' +
      rows
        .map(function (row) {
          var pic = row.picture_url || '/static/camgirls/avatar-demo.svg';
          return (
            '<article class="cg-spotlight-card">' +
            '<span class="cg-spotlight-label">Spotlight #' +
            esc(row.rank) +
            '</span>' +
            '<img class="cg-spotlight-bg" src="' +
            esc(staticUrl(pic)) +
            '" alt="">' +
            '<div class="cg-spotlight-body"><strong>' +
            esc(row.display_name) +
            '</strong><p style="font-size:0.8rem;opacity:0.75;margin:6px 0 0">' +
            esc(row.vibe) +
            ' · ' +
            esc(row.task_kind || 'agent') +
            '</p><a href="' +
            esc(performerHref(row.performer_id)) +
            '">Enter studio →</a></div></article>'
          );
        })
        .join('') +
      '</div>';
    var top = document.getElementById('cg-top10-panel');
    if (top && top.parentNode) top.parentNode.insertBefore(wrap, top.nextSibling);
  }

  function mountVibeFilters() {
    var bar = document.getElementById('cg-filter-bar');
    if (!bar || document.getElementById('cg-giga-vibe-filters')) return;
    var extra = document.createElement('div');
    extra.id = 'cg-giga-vibe-filters';
    extra.className = 'cg-filter-bar cg-giga-filters';
    extra.innerHTML = [
      ['all', 'All vibes'],
      ['cosmic', 'Cosmic'],
      ['studio', 'Studio'],
      ['signal', 'Signal'],
      ['legacy', 'Legacy OG'],
    ]
      .map(function (pair, i) {
        return (
          '<button type="button" class="' +
          (i === 0 ? 'cg-filter-active' : '') +
          '" data-vibe="' +
          esc(pair[0]) +
          '">' +
          esc(pair[1]) +
          '</button>'
        );
      })
      .join('');
    bar.parentNode.insertBefore(extra, bar.nextSibling);
    extra.querySelectorAll('button').forEach(function (btn) {
      btn.addEventListener('click', function () {
        extra.querySelectorAll('button').forEach(function (b) {
          b.classList.remove('cg-filter-active');
        });
        btn.classList.add('cg-filter-active');
        vibeFilter = btn.getAttribute('data-vibe') || 'all';
        applyVibeToGrid();
      });
    });
  }

  function applyVibeToGrid() {
    document.querySelectorAll('#cg-grid .cg-card').forEach(function (card) {
      var vibe = card.getAttribute('data-cg-vibe') || 'legacy';
      var hide = vibeFilter !== 'all' && vibe !== vibeFilter;
      card.classList.toggle('cg-giga-hidden', hide);
    });
  }

  function enhanceCards() {
    document.querySelectorAll('#cg-grid .cg-card').forEach(function (card) {
      var id = card.getAttribute('data-id');
      if (!id) return;
      var intel = top10Map[id];
      if (intel) {
        card.setAttribute('data-cg-vibe', intel.vibe || 'legacy');
        if (!card.querySelector('.cg-giga-rank-badge') && intel.rank <= 10) {
          var badge = document.createElement('span');
          badge.className = 'cg-giga-rank-badge';
          badge.textContent = 'TOP ' + intel.rank;
          card.style.position = 'relative';
          card.appendChild(badge);
        }
        if (!card.querySelector('.cg-giga-vibe')) {
          var title = card.querySelector('strong');
          if (title) {
            var vibe = document.createElement('span');
            vibe.className = 'cg-giga-vibe';
            vibe.textContent = intel.vibe || '';
            title.appendChild(vibe);
          }
        }
      }
      if (!card.querySelector('.cg-mn2-rail')) {
        var rail = document.createElement('div');
        rail.className = 'cg-mn2-rail';
        rail.innerHTML =
          '<span><span class="cg-mn2-dot live"></span>Agent mesh</span>' +
          '<span><span class="cg-mn2-dot live"></span>MN2 rail</span>' +
          '<span><span class="cg-mn2-dot"></span>Wallet audit</span>';
        var actions = card.querySelector('.cg-actions');
        if (actions) card.insertBefore(rail, actions);
      }
    });
    applyVibeToGrid();
  }

  function mountCommandPalette(catalog) {
    if (document.getElementById('cg-cmd-palette')) return;
    var pal = document.createElement('div');
    pal.id = 'cg-cmd-palette';
    pal.className = 'cg-cmd-palette';
    pal.innerHTML =
      '<div class="cg-cmd-box">' +
      '<input class="cg-cmd-input" id="cg-cmd-input" type="text" placeholder="Jump to performer…" autocomplete="off">' +
      '<div class="cg-cmd-results" id="cg-cmd-results"></div>' +
      '<p class="cg-cmd-hint">⌘K / Ctrl+K — neural jump</p></div>';
    document.body.appendChild(pal);
    var input = document.getElementById('cg-cmd-input');
    var results = document.getElementById('cg-cmd-results');
    var items = catalog || [];

    function renderResults(q) {
      q = (q || '').toLowerCase();
      var rows = items.filter(function (p) {
        var name = (p.display_name || p.performer_id || '').toLowerCase();
        var id = (p.id || p.performer_id || '').toLowerCase();
        return !q || name.indexOf(q) >= 0 || id.indexOf(q) >= 0;
      }).slice(0, 12);
      results.innerHTML = rows
        .map(function (p, i) {
          var pid = p.id || p.performer_id;
          return (
            '<div class="cg-cmd-item' +
            (i === 0 ? ' active' : '') +
            '" data-href="' +
            esc(performerHref(pid)) +
            '">' +
            esc(p.display_name || pid) +
            '</div>'
          );
        })
        .join('');
    }

    function open() {
      pal.classList.add('open');
      input.value = '';
      renderResults('');
      input.focus();
    }
    function close() {
      pal.classList.remove('open');
    }

    pal.addEventListener('click', function (e) {
      if (e.target === pal) close();
    });
    input.addEventListener('input', function () {
      renderResults(input.value);
    });
    results.addEventListener('click', function (e) {
      var item = e.target.closest('.cg-cmd-item');
      if (item) window.location.href = item.getAttribute('data-href');
    });
    document.addEventListener('keydown', function (e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        open();
      }
      if (e.key === 'Escape') close();
    });
  }

  function loadIntel() {
    fetch(apiUrl('/api/camgirls/intel/top10'))
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (!d.success) return;
        mountHero(d);
        mountTicker(d.intel_stack);
        mountRing(d.scale || {});
        renderTop10(d);
        mountVibeFilters();
        mountCommandPalette(
          (d.top10 || []).map(function (row) {
            return { id: row.performer_id, display_name: row.display_name };
          })
        );
        enhanceCards();
      })
      .catch(function () {});
  }

  var commandCatalog = [];

  function setCommandCatalog(rows) {
    if (!rows || !rows.length) return;
    commandCatalog = rows.map(function (p) {
      return { id: p.id, display_name: p.display_name };
    });
    mountCommandPalette(commandCatalog);
  }

  window.CamgirlsGiga = {
    onGridRendered: function (performers) {
      if (performers && performers.length) setCommandCatalog(performers);
      enhanceCards();
    },
    refresh: loadIntel,
  };

  document.documentElement.classList.add('cg-giga');

  document.addEventListener('DOMContentLoaded', function () {
    if (window.CG_SINGLE_PERFORMER) {
      document.documentElement.classList.add('cg-giga');
      return;
    }
    loadIntel();
  });
})();
