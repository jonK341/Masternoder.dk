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
      return localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || (window.MnUserId ? window.MnUserId.read() : '');
    } catch (e) {
      return (window.MnUserId ? window.MnUserId.read() : '');
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

  function infobarPill(label, on) {
    return (
      '<span class="cg-infobar-pill' +
      (on ? ' cg-infobar-on' : '') +
      '">' +
      esc(label) +
      '</span>'
    );
  }

  function performerInfobar(p) {
    var t = p.tech || {};
    var voice = t.voice_mode === 'live' ? 'Voice live' : 'Voice preview';
    var pay = (t.payments && t.payments.length ? t.payments.join(' + ') : 'MN2').toUpperCase();
    var agent = t.task_kind ? 'Agent · ' + t.task_kind : 'Agent';
    return (
      '<div class="cg-infobar">' +
      infobarPill('Live AI', !!t.online) +
      infobarPill(voice, true) +
      infobarPill(agent, !!t.agent_id) +
      infobarPill(pay, true) +
      infobarPill('Chat·Gifts·Dance', !!(t.features && t.features.length)) +
      '</div>'
    );
  }

  function loadStatus() {
    fetch('/api/camgirls/status')
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        var strip = document.getElementById('cg-status-strip');
        var chips = document.getElementById('cg-info-chips');
        var text = document.getElementById('cg-status-text');
        var todos = document.getElementById('cg-next-todos');
        if (!strip || !chips || !text || !d.success) return;
        strip.style.display = 'block';
        var pays = (d.platform_tech && d.platform_tech.payments) || [];
        chips.innerHTML =
          infobarPill((d.performers_online || 0) + ' performers', true) +
          infobarPill((d.agents_linked || 0) + ' agents linked', true) +
          infobarPill(d.voice_live ? 'LiveKit live' : 'LiveKit preview', true) +
          infobarPill(d.paypal_configured ? 'PayPal on' : 'PayPal off', !!d.paypal_configured) +
          infobarPill('MN2 wallet', true) +
          infobarPill((pays.join(' + ') || 'mn2').toUpperCase(), true) +
          infobarPill('Catalog: ' + (d.catalog_source || 'json'), true);
        text.textContent = d.note || 'AI studio ready';
        if (todos) {
          var items = d.next_todos || [];
          if (!items.length) {
            todos.innerHTML = '<li>All Phase 0 items shipped — see MN2_TODO for ops.</li>';
          } else {
            todos.innerHTML = items
              .map(function (item) {
                return (
                  '<li><span class="cg-todo-pri">' +
                  esc(item.priority || '—') +
                  '</span><strong>' +
                  esc(item.title || '') +
                  '</strong> — ' +
                  esc(item.detail || '') +
                  '</li>'
                );
              })
              .join('');
          }
        }
      })
      .catch(function () {});
  }

  function paypalCheckout(action, performerId, extra) {
    var body = { user_id: uid(), action: action || 'unlock', performer_id: performerId };
    extra = extra || {};
    if (extra.amount_mn2 != null) body.amount_mn2 = extra.amount_mn2;
    if (extra.gift_id) body.gift_id = extra.gift_id;
    if (extra.minutes != null) body.minutes = extra.minutes;
    fetch('/api/camgirls/paypal/create-order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
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
        if (d.approve_url) {
          try {
            sessionStorage.setItem('cg_paypal_order', d.order_id || '');
            sessionStorage.setItem(
              'cg_paypal_ctx',
              JSON.stringify({
                action: action,
                performer_id: performerId,
                gift_id: extra.gift_id || '',
                minutes: extra.minutes || 0,
              })
            );
          } catch (e) {}
          window.location.href = d.approve_url;
        } else msg(d.error || 'PayPal unavailable', true);
      });
  }

  function paypalUnlock(id) {
    paypalCheckout('unlock', id);
  }

  window.CamgirlsPaypal = { checkout: paypalCheckout };

  function startPrivateShow(id, minutes) {
    var mins = parseInt(minutes, 10) || 5;
    fetch('/api/camgirls/performers/' + encodeURIComponent(id) + '/private-show', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: uid(), minutes: mins }),
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
        msg(
          d.success ? 'Private show active for ' + mins + ' min!' : d.error || 'Private show failed',
          !d.success
        );
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
    if (params.get('paypal') === 'cancel') {
      try {
        sessionStorage.removeItem('cg_paypal_order');
        sessionStorage.removeItem('cg_paypal_ctx');
      } catch (e) {}
      if (window.history && window.history.replaceState) {
        window.history.replaceState({}, '', '/camgirls/');
      }
      return;
    }
    var orderId = params.get('token') || '';
    try {
      orderId = orderId || sessionStorage.getItem('cg_paypal_order') || '';
      sessionStorage.removeItem('cg_paypal_order');
    } catch (e) {}
    var paypalCtx = {};
    try {
      paypalCtx = JSON.parse(sessionStorage.getItem('cg_paypal_ctx') || '{}');
      sessionStorage.removeItem('cg_paypal_ctx');
    } catch (e2) {
      paypalCtx = {};
    }
    var approved = params.get('paypal') === 'success' || !!(params.get('PayerID') || params.get('PayerId'));
    if (!orderId || !approved) {
      if (params.get('paypal') === 'success' && !orderId) {
        msg('PayPal approved — capture will finish from the order webhook if unlock did not apply.');
      }
      return;
    }
    fetch('/api/camgirls/paypal/capture', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: uid() || params.get('user_id') || '', order_id: orderId }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        var doneMsg = 'PayPal payment complete!';
        if (d.success) {
          if (paypalCtx.action === 'unlock') doneMsg = 'Room unlocked via PayPal!';
          else if (paypalCtx.action === 'tip') doneMsg = 'Tip sent via PayPal — thank you!';
          else if (paypalCtx.action === 'gift') doneMsg = 'Gift sent via PayPal!';
          else if (paypalCtx.action === 'fan_club') doneMsg = 'Fan club joined via PayPal!';
          else if (paypalCtx.action === 'private_show') doneMsg = 'Private show started via PayPal!';
        }
        msg(d.success ? doneMsg : d.error || 'Capture failed', !d.success);
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
        if (window.CG_SINGLE_PERFORMER) {
          performers = performers.filter(function (p) {
            return p.id === window.CG_SINGLE_PERFORMER;
          });
        } else {
          var deep = new URLSearchParams(window.location.search).get('performer');
          if (deep) {
            performers = performers.filter(function (p) {
              return p.id === deep;
            });
          }
        }
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
          performerInfobar(p) +
          '<div style="display:flex;gap:12px;align-items:center;">' +
          '<img class="cg-card-thumb" src="' + esc(avatar) + '" alt="">' +
          '<div><strong><a href="/camgirls/p/' + esc(p.id) + '/" style="color:inherit;text-decoration:none;">' +
          esc(p.display_name) +
          '</a></strong> <span class="cg-ai-badge">AI</span>' +
          unlocked +
          fanBadge +
          '<p style="font-size:0.85rem;opacity:0.8;margin:6px 0 0;">' + esc(p.bio || p.tagline || '') + '</p></div>' +
          '<button type="button" class="cg-studio-btn cg-fav-btn" data-fav="' + esc(p.id) + '">' +
          (favs.indexOf(p.id) >= 0 ? '★' : '☆') +
          '</button></div>' +
          '<div class="cg-actions">' +
          (p.unlocked
            ? '<button type="button" class="cg-tip" data-tip="' + esc(p.id) + '">Tip ' + esc(p.tip_min_mn2) + '+ MN2</button>' +
              '<button type="button" class="cg-studio-btn" data-paypal-tip="' + esc(p.id) + '">PayPal tip</button>'
            : '<button type="button" class="cg-unlock" data-unlock="' + esc(p.id) + '">Unlock ' + esc(p.unlock_price_mn2) + ' MN2</button>' +
              '<button type="button" class="cg-studio-btn" data-paypal-unlock="' + esc(p.id) + '">PayPal unlock</button>') +
          (p.unlocked && !p.fan_club
            ? '<button type="button" class="cg-studio-btn" data-fanclub="' +
              esc(p.id) +
              '">Fan club MN2</button>' +
              '<button type="button" class="cg-studio-btn" data-paypal-fanclub="' +
              esc(p.id) +
              '">Fan club PayPal</button>'
            : '') +
          (p.unlocked
            ? '<button type="button" class="cg-studio-btn" data-private="' +
              esc(p.id) +
              '">Private 5m</button>' +
              '<button type="button" class="cg-studio-btn" data-paypal-private="' +
              esc(p.id) +
              '">Private PayPal</button>'
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

    grid.querySelectorAll('[data-paypal-tip]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-paypal-tip');
        var p = performers.find(function (x) {
          return x.id === id;
        });
        var amt = (p && p.tip_min_mn2) || 5;
        paypalCheckout('tip', id, { amount_mn2: amt });
      });
    });

    grid.querySelectorAll('[data-fanclub]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        joinFanClub(btn.getAttribute('data-fanclub'));
      });
    });

    grid.querySelectorAll('[data-paypal-fanclub]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        paypalCheckout('fan_club', btn.getAttribute('data-paypal-fanclub'));
      });
    });

    grid.querySelectorAll('[data-private]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        startPrivateShow(btn.getAttribute('data-private'), 5);
      });
    });

    grid.querySelectorAll('[data-paypal-private]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        paypalCheckout('private_show', btn.getAttribute('data-paypal-private'), { minutes: 5 });
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
