/**
 * Camgirls — performer catalog, age gate, unlock, tip.
 */
(function () {
  'use strict';

  var performers = [];
  var studio = null;
  var filter = 'all';

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
      .replace(/>/g, '&gt;');
  }

  function msg(text, isErr) {
    var el = document.getElementById('cg-msg');
    if (el) {
      el.textContent = text || '';
      el.style.color = isErr ? '#ff8866' : '#ffaa44';
    }
  }

  function favoritesKey() {
    return 'cg_favorites_' + uid();
  }

  function loadFavorites() {
    try {
      return JSON.parse(localStorage.getItem(favoritesKey()) || '[]');
    } catch (e) {
      return [];
    }
  }

  function saveFavorites(list) {
    try {
      localStorage.setItem(favoritesKey(), JSON.stringify(list));
    } catch (e) {}
  }

  function toggleFav(id) {
    var favs = loadFavorites();
    var i = favs.indexOf(id);
    if (i >= 0) favs.splice(i, 1);
    else favs.push(id);
    saveFavorites(favs);
    fetch('/api/camgirls/performers/' + encodeURIComponent(id) + '/favorite', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: uid() }),
    }).catch(function () {});
    renderGrid();
  }

  function showAgeGate(show) {
    var gate = document.getElementById('cg-age-gate');
    if (gate) gate.style.display = show ? 'block' : 'none';
  }

  function verifyAge() {
    var year = parseInt((document.getElementById('cg-birth-year') || {}).value, 10);
    if (!year) {
      msg('Enter birth year', true);
      return;
    }
    fetch('/api/camgirls/age-verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: uid(), birth_year: year }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (d.success) {
          showAgeGate(false);
          msg('Age verified — unlock and tip enabled.');
          loadPerformers();
        } else msg(d.error || 'Verification failed', true);
      });
  }

  function loadAgents() {
    fetch('/api/camgirls/agents')
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        var strip = document.getElementById('cg-agents');
        var chips = document.getElementById('cg-agent-chips');
        if (!strip || !chips || !d.agents) return;
        strip.style.display = 'block';
        chips.innerHTML = d.agents
          .map(function (a) {
            return '<span class="cg-agent-chip">' + esc(a.display_name || a.agent_id) + '</span>';
          })
          .join('');
      })
      .catch(function () {});
  }

  function loadStatus() {
    fetch('/api/camgirls/status')
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        var strip = document.getElementById('cg-status-strip');
        var text = document.getElementById('cg-status-text');
        if (!strip || !text || !d.success) return;
        strip.style.display = 'block';
        var voice = d.voice_live ? 'voice live' : 'voice preview';
        text.textContent =
          (d.performers_online || 0) +
          ' performers online · ' +
          voice +
          ' · ' +
          (d.note || 'AI studio ready');
      })
      .catch(function () {});
  }

  function paypalUnlock(id) {
    fetch('/api/camgirls/paypal/create-order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: uid(), action: 'unlock', performer_id: id }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (d.approve_url) {
          try {
            sessionStorage.setItem('cg_paypal_order', d.order_id || '');
          } catch (e) {}
          window.location.href = d.approve_url;
        } else msg(d.error || 'PayPal unavailable', true);
      });
  }

  function joinFanClub(id) {
    fetch('/api/camgirls/performers/' + encodeURIComponent(id) + '/fan-club', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: uid() }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (d.code === 'age_verification_required') {
          showAgeGate(true);
          msg('18+ verification required', true);
          return;
        }
        if (d.code === 'unlock_required') {
          msg('Unlock the room first', true);
          return;
        }
        msg(d.success ? 'Welcome to fan club!' : d.error || 'Could not join', !d.success);
        if (d.success) loadPerformers();
      });
  }

  function handlePayPalReturn() {
    var params = new URLSearchParams(window.location.search);
    if (params.get('paypal') !== 'success') return;
    var orderId = '';
    try {
      orderId = sessionStorage.getItem('cg_paypal_order') || '';
      sessionStorage.removeItem('cg_paypal_order');
    } catch (e) {}
    if (!orderId) {
      msg('PayPal approved — refresh if unlock did not apply.');
      return;
    }
    fetch('/api/camgirls/paypal/capture', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: uid(), order_id: orderId }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        msg(d.success ? 'PayPal payment complete!' : d.error || 'Capture failed', !d.success);
        if (d.success) loadPerformers();
        if (window.history && window.history.replaceState) {
          window.history.replaceState({}, '', '/camgirls/');
        }
      });
  }

  function loadPerformers() {
    var grid = document.getElementById('cg-grid');
    if (grid) grid.textContent = 'Loading performers…';
    fetch('/api/camgirls/performers?user_id=' + encodeURIComponent(uid()))
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (!d.success) {
          msg(d.error || 'Could not load performers', true);
          if (grid) grid.innerHTML = '<p>Failed to load catalog.</p>';
          return;
        }
        performers = d.performers || [];
        if (!performers.length) {
          if (grid) grid.innerHTML = '<p>No performers available.</p>';
          return;
        }
        var needsAge = performers.some(function (p) {
          return !p.age_verified;
        });
        showAgeGate(needsAge);
        renderGrid();
      })
      .catch(function () {
        msg('Network error loading performers', true);
        if (grid) grid.innerHTML = '<p>Could not reach API.</p>';
      });
  }

  function renderGrid() {
    var grid = document.getElementById('cg-grid');
    if (!grid) return;
    var favs = loadFavorites();
    var rows = performers.filter(function (p) {
      if (filter === 'favorites') return favs.indexOf(p.id) >= 0;
      return true;
    });
    if (!rows.length) {
      grid.innerHTML = '<p>No performers match this filter.</p>';
      return;
    }
    grid.innerHTML = rows
      .map(function (p) {
        var avatar = p.avatar_url || '/static/camgirls/avatar-demo.svg';
        var unlocked = p.unlocked ? '<span class="cg-badge">Unlocked</span>' : '';
        var fanBadge = p.fan_club ? ' <span class="cg-fc-badge">Fan club</span>' : '';
        return (
          '<article class="cg-card" data-id="' + esc(p.id) + '">' +
          '<div style="display:flex;gap:12px;align-items:center;">' +
          '<img class="cg-card-thumb" src="' + esc(avatar) + '" alt="">' +
          '<div><strong>' + esc(p.display_name) + '</strong> <span class="cg-ai-badge">AI</span>' +
          unlocked +
          fanBadge +
          '<p style="font-size:0.85rem;opacity:0.8;margin:6px 0 0;">' + esc(p.bio || p.tagline || '') + '</p></div>' +
          '<button type="button" class="cg-studio-btn cg-fav-btn" data-fav="' + esc(p.id) + '">' +
          (favs.indexOf(p.id) >= 0 ? '★' : '☆') +
          '</button></div>' +
          '<div class="cg-actions">' +
          (p.unlocked
            ? '<button type="button" class="cg-tip" data-tip="' + esc(p.id) + '">Tip ' + esc(p.tip_min_mn2) + '+ MN2</button>'
            : '<button type="button" class="cg-unlock" data-unlock="' + esc(p.id) + '">Unlock ' + esc(p.unlock_price_mn2) + ' MN2</button>' +
              '<button type="button" class="cg-studio-btn" data-paypal-unlock="' + esc(p.id) + '">PayPal unlock</button>') +
          (p.unlocked && !p.fan_club
            ? '<button type="button" class="cg-studio-btn" data-fanclub="' + esc(p.id) + '">Join fan club</button>'
            : '') +
          '<button type="button" class="cg-chat-toggle" data-chat="' + esc(p.id) + '">Chat</button>' +
          '</div>' +
          '<div class="cg-wheel-result"></div>' +
          '<div class="cg-chat-panel" id="cg-chat-' + esc(p.id) + '" style="display:none;"></div>' +
          '</article>'
        );
      })
      .join('');

    grid.querySelectorAll('[data-unlock]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-unlock');
        fetch('/api/camgirls/performers/' + encodeURIComponent(id) + '/unlock', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: uid() }),
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (d) {
            if (d.code === 'age_verification_required') {
              showAgeGate(true);
              msg('18+ verification required', true);
              return;
            }
            msg(d.success ? 'Room unlocked!' : d.error || 'Unlock failed', !d.success);
            if (d.success) loadPerformers();
          });
      });
    });

    grid.querySelectorAll('[data-paypal-unlock]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        paypalUnlock(btn.getAttribute('data-paypal-unlock'));
      });
    });

    grid.querySelectorAll('[data-fanclub]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        joinFanClub(btn.getAttribute('data-fanclub'));
      });
    });

    grid.querySelectorAll('[data-tip]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-tip');
        var p = performers.find(function (x) {
          return x.id === id;
        });
        var amt = (p && p.tip_min_mn2) || 5;
        fetch('/api/camgirls/performers/' + encodeURIComponent(id) + '/tip', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: uid(), amount: amt }),
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (d) {
            msg(d.success ? 'Tip sent — thank you!' : d.error || 'Tip failed', !d.success);
          });
      });
    });

    grid.querySelectorAll('[data-fav]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        toggleFav(btn.getAttribute('data-fav'));
      });
    });

    grid.querySelectorAll('[data-chat]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-chat');
        var panel = document.getElementById('cg-chat-' + id);
        if (!panel) return;
        var open = panel.style.display !== 'none';
        panel.style.display = open ? 'none' : 'block';
        if (!open && window.CamgirlsStudio) window.CamgirlsStudio.openChat(panel, id);
      });
    });

    if (window.CamgirlsStudio) window.CamgirlsStudio.enhanceCards(grid, performers);
  }

  document.addEventListener('DOMContentLoaded', function () {
    var ageBtn = document.getElementById('cg-age-btn');
    if (ageBtn) ageBtn.addEventListener('click', verifyAge);
    document.querySelectorAll('#cg-filter-bar button').forEach(function (btn) {
      btn.addEventListener('click', function () {
        document.querySelectorAll('#cg-filter-bar button').forEach(function (b) {
          b.classList.remove('cg-filter-active');
        });
        btn.classList.add('cg-filter-active');
        filter = btn.getAttribute('data-filter') || 'all';
        renderGrid();
      });
    });
    loadAgents();
    loadStatus();
    handlePayPalReturn();
    loadPerformers();
  });
})();
