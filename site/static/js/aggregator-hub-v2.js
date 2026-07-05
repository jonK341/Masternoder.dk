/**
 * Aggregator hub v2 — lazy tab loading for catalog, top25, control, fulfillment, progress.
 */
(function () {
  'use strict';

  var loaded = {};

  function uid() {
    try {
      return localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
    } catch (e) {
      return 'default_user';
    }
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function fetchJson(url) {
    return fetch(url, { credentials: 'same-origin' }).then(function (r) {
      return r.json();
    });
  }

  function renderCatalog(data) {
    var grid = document.getElementById('agg-catalog-grid');
    if (!grid) return;
    var rows = (data && data.aggregators) || [];
    if (!rows.length) {
      grid.innerHTML = '<p class="agg-v2-muted">No aggregators found.</p>';
      return;
    }
    grid.innerHTML = rows
      .map(function (a) {
        return (
          '<article class="agg-v2-card">' +
          '<h3>' + esc(a.name) + '</h3>' +
          '<p class="agg-v2-meta">' + esc(a.category) + ' · ' + esc(a.agent_id) + '</p>' +
          '<p class="agg-v2-desc">' + esc(a.description) + '</p>' +
          '<div class="agg-v2-tags">' +
          (a.technologies || []).map(function (t) {
            return '<span class="agg-v2-tag">' + esc(t) + '</span>';
          }).join('') +
          '</div>' +
          '<button type="button" class="agg-v2-btn agg-assign-btn" data-agg-id="' + esc(a.id) + '" data-agent-id="' + esc(a.agent_id) + '">Assign agent</button>' +
          '</article>'
        );
      })
      .join('');
    grid.querySelectorAll('.agg-assign-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var aggId = btn.getAttribute('data-agg-id');
        var agentId = btn.getAttribute('data-agent-id');
        fetch('/api/aggregators/assign', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: uid(), aggregator_id: aggId, agent_id: agentId }),
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (res) {
            btn.textContent = res.success ? 'Assigned ✓' : 'Failed';
            if (res.success) loadProgress();
          });
      });
    });
  }

  function loadCatalog() {
    if (loaded.catalog) return;
    var grid = document.getElementById('agg-catalog-grid');
    if (grid) grid.innerHTML = '<p class="agg-v2-muted">Loading catalog…</p>';
    var cat = document.getElementById('agg-catalog-category');
    var q = (document.getElementById('agg-catalog-search') || {}).value || '';
    var category = cat ? cat.value : 'all';
    var url = '/api/aggregators/catalog?limit=75';
    if (category && category !== 'all') url += '&category=' + encodeURIComponent(category);
    if (q) url += '&search=' + encodeURIComponent(q);
    fetchJson(url).then(function (data) {
      loaded.catalog = true;
      renderCatalog(data);
      if (cat && cat.options.length <= 1 && data.categories) {
        data.categories.forEach(function (c) {
          var opt = document.createElement('option');
          opt.value = c;
          opt.textContent = c;
          cat.appendChild(opt);
        });
      }
    }).catch(function () {
      if (grid) grid.innerHTML = '<p class="agg-v2-muted">Could not load catalog.</p>';
    });
  }

  function loadTop25() {
    if (loaded.top25) return;
    var grid = document.getElementById('agg-top25-grid');
    if (grid) grid.innerHTML = '<p class="agg-v2-muted">Loading top 25…</p>';
    fetchJson('/api/aggregators/top25').then(function (data) {
      loaded.top25 = true;
      if (!grid) return;
      var rows = (data && data.aggregators) || [];
      grid.innerHTML = rows
        .map(function (a) {
          return (
            '<article class="agg-v2-card agg-v2-card--rank">' +
            '<span class="agg-v2-rank">#' + esc(a.rank) + '</span>' +
            '<h3>' + esc(a.name) + '</h3>' +
            '<p class="agg-v2-desc">' + esc(a.description) + '</p>' +
            '</article>'
          );
        })
        .join('');
    });
  }

  function loadControl() {
    if (loaded.control) return;
    var body = document.getElementById('agg-control-body');
    if (body) body.innerHTML = '<p class="agg-v2-muted">Loading control panel…</p>';
    fetchJson('/api/aggregators/catalog?limit=12').then(function (data) {
      loaded.control = true;
      if (!body) return;
      var rows = (data && data.aggregators) || [];
      body.innerHTML =
        '<p class="agg-v2-lead">Quick-assign agents to priority aggregators.</p>' +
        '<div class="agg-v2-grid">' +
        rows
          .map(function (a) {
            return (
              '<div class="agg-v2-card"><strong>' + esc(a.name) + '</strong>' +
              '<button type="button" class="agg-v2-btn agg-assign-btn" data-agg-id="' + esc(a.id) + '" data-agent-id="' + esc(a.agent_id) + '">Assign</button></div>'
            );
          })
          .join('') +
        '</div>';
      body.querySelectorAll('.agg-assign-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
          fetch('/api/aggregators/assign', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: uid(),
              aggregator_id: btn.getAttribute('data-agg-id'),
              agent_id: btn.getAttribute('data-agent-id'),
            }),
          }).then(function (r) {
            return r.json();
          }).then(function (res) {
            btn.textContent = res.success ? 'OK' : 'Err';
            loadProgress();
          });
        });
      });
    });
  }

  function loadFulfillment() {
    if (loaded.fulfillment) return;
    var body = document.getElementById('agg-fulfillment-body');
    fetchJson('/api/aggregators/fulfillment').then(function (data) {
      loaded.fulfillment = true;
      if (!body) return;
      var steps = (data && data.playbook) || [];
      body.innerHTML =
        '<ol class="agg-v2-playbook">' +
        steps
          .map(function (s) {
            return '<li><strong>' + esc(s.title) + '</strong><span>' + esc(s.detail) + '</span></li>';
          })
          .join('') +
        '</ol>';
    });
  }

  function loadProgress() {
    var host = document.getElementById('agg-progress-monitor');
    var label = document.getElementById('agg-global-progress-label');
    var fill = document.getElementById('agg-global-progress-fill');
    fetchJson('/api/aggregators/progress?user_id=' + encodeURIComponent(uid())).then(function (data) {
      loaded.progress = true;
      var pct = data.percent || 0;
      if (label) {
        label.textContent = 'Hub progress — ' + (data.assigned_count || 0) + ' / ' + (data.total_aggregators || 75) + ' assigned (' + pct + '%)';
      }
      if (fill) fill.style.width = pct + '%';
      if (!host) return;
      var miles = (data.milestones || [])
        .map(function (m) {
          return '<li class="' + (m.done ? 'done' : '') + '">' + esc(m.label) + (m.done ? ' ✓' : '') + '</li>';
        })
        .join('');
      host.innerHTML = '<ul class="agg-v2-milestones">' + miles + '</ul>';
    });
  }

  function onTab(tabId) {
    if (tabId === 'catalog') loadCatalog();
    if (tabId === 'top25') loadTop25();
    if (tabId === 'control') loadControl();
    if (tabId === 'fulfillment') loadFulfillment();
    if (tabId === 'progress') loadProgress();
    if (tabId === 'monitor') loadProgress();
  }

  window.__aggHubV2OnTab = onTab;

  document.addEventListener('DOMContentLoaded', function () {
    var searchBtn = document.getElementById('agg-catalog-search-btn');
    if (searchBtn) {
      searchBtn.addEventListener('click', function () {
        loaded.catalog = false;
        loadCatalog();
      });
    }
    loadProgress();
  });
})();
