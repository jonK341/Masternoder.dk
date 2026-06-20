/**
 * Aggregator hub v2 — catalog (75), top-25, control panel, fulfillment, progress monitor.
 */
(function (global) {
  'use strict';

  function uid() {
    try {
      return localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
    } catch (e) {
      return 'default_user';
    }
  }

  function get(path) {
    return fetch(path, { credentials: 'same-origin' }).then(function (r) {
      return r.json();
    });
  }

  function post(path, body) {
    return fetch(path, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    }).then(function (r) {
      return r.json();
    });
  }

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function award(action) {
    if (global.AggregatorEngagement && global.AggregatorEngagement.award) {
      global.AggregatorEngagement.award(action);
    }
  }

  function renderProgressBar(pct, label) {
    pct = Math.max(0, Math.min(100, Number(pct) || 0));
    return (
      '<div class="agg-v2-progress-row">' +
      '<span class="agg-v2-progress-label">' + esc(label) + '</span>' +
      '<div class="agg-v2-progress-track"><div class="agg-v2-progress-fill" style="width:' + pct + '%"></div></div>' +
      '<span class="agg-v2-progress-pct">' + pct + '%</span></div>'
    );
  }

  function loadProgressMonitor() {
    var host = document.getElementById('agg-progress-monitor');
    if (!host) return;
    get('/api/aggregators/progress?user_id=' + encodeURIComponent(uid())).then(function (d) {
      if (!d || !d.success) {
        host.innerHTML = '<p class="agg-v2-muted">Progress unavailable.</p>';
        return;
      }
      var html =
        '<div class="agg-v2-progress-summary">' +
        '<strong>' + d.assigned_count + '</strong> / ' + d.catalog_total + ' aggregators assigned · ' +
        d.active_aggregators + ' active</div>';
      (d.milestones || []).forEach(function (m) {
        html += renderProgressBar(m.pct, m.label + (m.done ? ' ✓' : ''));
      });
      host.innerHTML = html;
      var fill = document.getElementById('agg-global-progress-fill');
      var lbl = document.getElementById('agg-global-progress-label');
      if (fill) fill.style.width = (d.assignment_pct || 0) + '%';
      if (lbl) lbl.textContent = 'Hub progress ' + (d.assignment_pct || 0) + '%';
    }).catch(function () {
      host.innerHTML = '<p class="agg-v2-muted">Could not load progress.</p>';
    });
  }

  function cardHtml(a, rank) {
    var rankBadge = rank != null ? '<span class="agg-v2-rank">#' + rank + '</span>' : '';
    var status = a.status === 'beta' ? '<span class="agg-v2-badge beta">beta</span>' : '';
    var ai = a.ai_enabled !== false ? '<span class="agg-v2-badge ai">AI</span>' : '';
    var href = a.href || '#';
    var tech = Array.isArray(a.technologies) ? a.technologies.join(' · ') : (a.tech || '');
    return (
      '<article class="agg-v2-card" data-agg-id="' + esc(a.id) + '">' +
      rankBadge +
      '<h4>' + esc(a.name) + '</h4>' +
      '<div class="agg-v2-badges">' + ai + status + '<span class="agg-v2-badge cat">' + esc(a.category) + '</span></div>' +
      '<p class="agg-v2-use">' + esc(a.use || a.function || '') + '</p>' +
      '<p class="agg-v2-tech">' + esc(tech) + '</p>' +
      '<p class="agg-v2-agent">Agent: <code>' + esc(a.agent_id || '—') + '</code></p>' +
      '<div class="agg-v2-card-actions">' +
      '<a href="' + esc(href) + '" class="agg-v2-btn">Open</a>' +
      '<button type="button" class="agg-v2-btn assign" data-assign-agg="' + esc(a.id) + '" data-assign-agent="' + esc(a.agent_id || '') + '">Assign agent</button>' +
      '</div></article>'
    );
  }

  function wireAssignButtons(root) {
    if (!root) return;
    root.querySelectorAll('[data-assign-agg]').forEach(function (btn) {
      if (btn._wired) return;
      btn._wired = true;
      btn.addEventListener('click', function () {
        var aggId = btn.getAttribute('data-assign-agg');
        var agentId = btn.getAttribute('data-assign-agent') || prompt('Agent id:', 'content_generator_agent');
        if (!agentId) return;
        btn.disabled = true;
        post('/api/aggregators/control/assign', {
          user_id: uid(),
          aggregator_id: aggId,
          agent_id: agentId,
        }).then(function (d) {
          btn.disabled = false;
          if (d.success) {
            award('catalog_assign');
            loadProgressMonitor();
            loadControlPanel();
            btn.textContent = 'Assigned ✓';
          } else {
            alert(d.error || 'Assign failed');
          }
        });
      });
    });
  }

  function loadCatalog() {
    var grid = document.getElementById('agg-catalog-grid');
    var catSel = document.getElementById('agg-catalog-category');
    var search = document.getElementById('agg-catalog-search');
    if (!grid) return;
    var cat = catSel ? catSel.value : 'all';
    var q = search ? search.value.trim() : '';
    grid.innerHTML = '<p class="agg-v2-muted">Loading catalog…</p>';
    var url = '/api/aggregators/catalog?limit=100&user_id=' + encodeURIComponent(uid());
    if (cat && cat !== 'all') url += '&category=' + encodeURIComponent(cat);
    if (q) url += '&search=' + encodeURIComponent(q);
    get(url).then(function (d) {
      if (!d || !d.success || !(d.aggregators || []).length) {
        grid.innerHTML = '<p class="agg-v2-muted">No aggregators match.</p>';
        return;
      }
      if (catSel && catSel.options.length <= 1 && (d.categories || []).length) {
        d.categories.forEach(function (c) {
          var o = document.createElement('option');
          o.value = c;
          o.textContent = c.replace(/_/g, ' ');
          catSel.appendChild(o);
        });
      }
      grid.innerHTML = d.aggregators.map(function (a) {
        return cardHtml(a);
      }).join('');
      wireAssignButtons(grid);
      award('catalog_loaded');
    }).catch(function () {
      grid.innerHTML = '<p class="agg-v2-muted">Catalog load failed.</p>';
    });
  }

  function loadTop25() {
    var grid = document.getElementById('agg-top25-grid');
    if (!grid) return;
    grid.innerHTML = '<p class="agg-v2-muted">Loading top 25…</p>';
    get('/api/aggregators/top25').then(function (d) {
      if (!d || !d.success) {
        grid.innerHTML = '<p class="agg-v2-muted">Top 25 unavailable.</p>';
        return;
      }
      grid.innerHTML = (d.aggregators || []).map(function (a) {
        return cardHtml(a, a.rank);
      }).join('');
      wireAssignButtons(grid);
    });
  }

  function loadFulfillment() {
    var host = document.getElementById('agg-fulfillment-body');
    if (!host) return;
    get('/api/aggregators/fulfillment').then(function (d) {
      if (!d || !d.success) {
        host.innerHTML = '<p class="agg-v2-muted">Fulfillment data unavailable.</p>';
        return;
      }
      var html = '<p>' + esc(d.description || '') + '</p><ol class="agg-v2-playbook">';
      (d.playbook || []).forEach(function (step) {
        html +=
          '<li><strong>Step ' + step.step + ':</strong> ' + esc(step.action) +
          ' via <em>' + esc(step.aggregator) + '</em> → ' + esc(step.reward) + '</li>';
      });
      html += '</ol><div class="agg-v2-grid agg-v2-grid--compact">';
      (d.aggregators || []).forEach(function (a) {
        html += cardHtml(a);
      });
      html += '</div>';
      host.innerHTML = html;
      wireAssignButtons(host);
    });
  }

  function loadControlPanel() {
    var host = document.getElementById('agg-control-body');
    if (!host) return;
    get('/api/aggregators/control?user_id=' + encodeURIComponent(uid())).then(function (d) {
      if (!d || !d.success) {
        host.innerHTML = '<p class="agg-v2-muted">Control panel unavailable.</p>';
        return;
      }
      var assigns = d.assignments || {};
      var keys = Object.keys(assigns);
      var html =
        '<p>Auto-run agents: <strong>' + (d.auto_run ? 'ON' : 'OFF') + '</strong> ' +
        '<button type="button" id="agg-toggle-autorun" class="agg-v2-btn">' + (d.auto_run ? 'Disable' : 'Enable') + '</button></p>';
      html += '<h4>Your assignments (' + keys.length + ')</h4>';
      if (!keys.length) {
        html += '<p class="agg-v2-muted">No agents assigned yet — use Catalog or Top 25.</p>';
      } else {
        html += '<ul class="agg-v2-assign-list">';
        keys.forEach(function (k) {
          var a = assigns[k];
          html += '<li><code>' + esc(k) + '</code> → <code>' + esc(a.agent_id) + '</code></li>';
        });
        html += '</ul>';
      }
      html += '<h4>Available agent types</h4><div class="agg-v2-agent-chips">';
      (d.agents_available || []).slice(0, 20).forEach(function (ag) {
        html += '<span class="agg-v2-chip">' + esc(ag.agent_id) + ' (' + (ag.aggregators || []).length + ')</span>';
      });
      html += '</div>';
      host.innerHTML = html;
      var toggle = document.getElementById('agg-toggle-autorun');
      if (toggle) {
        toggle.addEventListener('click', function () {
          post('/api/aggregators/control/assign', {
            user_id: uid(),
            aggregator_id: '_global',
            agent_id: 'orchestrator_agent',
            auto_run: !d.auto_run,
          }).then(function () {
            loadControlPanel();
          });
        });
      }
    });
  }

  function initFilters() {
    var catSel = document.getElementById('agg-catalog-category');
    var search = document.getElementById('agg-catalog-search');
    var btn = document.getElementById('agg-catalog-search-btn');
    if (catSel) catSel.addEventListener('change', loadCatalog);
    if (btn) btn.addEventListener('click', loadCatalog);
    if (search) {
      search.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') loadCatalog();
      });
    }
  }

  function initTabHooks() {
    global.__aggHubV2OnTab = function (tabId) {
      if (tabId === 'catalog') loadCatalog();
      if (tabId === 'top25') loadTop25();
      if (tabId === 'fulfillment') loadFulfillment();
      if (tabId === 'control') loadControlPanel();
      if (tabId === 'progress') loadProgressMonitor();
    };
  }

  function init() {
    initFilters();
    initTabHooks();
    loadProgressMonitor();
    if (document.querySelector('.agg-tab-panel[data-agg-tab="catalog"]:not([hidden])')) loadCatalog();
  }

  global.AggregatorHubV2 = {
    loadCatalog: loadCatalog,
    loadTop25: loadTop25,
    loadFulfillment: loadFulfillment,
    loadControlPanel: loadControlPanel,
    loadProgressMonitor: loadProgressMonitor,
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})(window);
