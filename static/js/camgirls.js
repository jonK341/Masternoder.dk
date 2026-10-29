/**
 * Camgirls — performer catalog, age gate, unlock, tip.
 */
(function () {
  'use strict';

  var performers = [];
  var studio = null;
  var filter = 'all';

  function apiUrl(path) {
    return typeof window.cgApi === 'function' ? window.cgApi(path) : path;
  }

  function staticUrl(path) {
    return typeof window.cgStatic === 'function' ? window.cgStatic(path) : path;
  }

  function pageBase() {
    if (typeof window.cgPageBase === 'function') {
      return window.cgPageBase();
    }
    if (typeof window.cgIsAppMount === 'function' && window.cgIsAppMount()) {
      return '/app/';
    }
    return '/camgirls/';
  }

  function cgPerformerHref(id) {
    if (typeof window.cgPerformerPath === 'function') {
      return window.cgPerformerPath(id);
    }
    return '/camgirls/p/' + encodeURIComponent(id) + '/';
  }

  var CG_SHOP_BRAND_QUERY = 'category=digital_goods&tag=camgirls';

  function cgShopHref(query) {
    var q = query || '';
    if (typeof window.cgShopUrl === 'function') {
      return window.cgShopUrl(q);
    }
    return '/shop/' + (q ? (q.charAt(0) === '?' ? q : '?' + q) : '');
  }

  function applyAppExpandLayout() {
    if (typeof window.cgIsAppMount !== 'function' || !window.cgIsAppMount()) {
      return;
    }
    document.documentElement.classList.add('cg-app-expanded');
    var hdr = document.querySelector('.cg-header p');
    if (hdr && hdr.textContent.indexOf('MN2 block explorer') < 0) {
      var sub = document.querySelector('.cg-app-subtitle');
      if (!sub) {
        sub = document.createElement('p');
        sub.className = 'cg-app-subtitle';
        sub.style.cssText = 'font-size:0.9rem;opacity:0.85;margin:8px 0 0;';
        sub.innerHTML =
          '<strong>camgirls.masternoder.dk studio</strong> — 15 AI hosts · ' +
          '<a href="/">MN2 block explorer</a> · ' +
          '<a href="' +
          cgShopHref(CG_SHOP_BRAND_QUERY) +
          '">Brand packs shop</a>';
        var header = document.querySelector('.cg-header');
        if (header) header.appendChild(sub);
      }
    }
    document.querySelectorAll('.cg-shop-strip a[href], .cg-resell-link').forEach(function (a) {
      var href = a.getAttribute('href') || '';
      if (href.indexOf('/shop') >= 0 && href.indexOf('/app/shop') < 0) {
        a.setAttribute('href', cgShopHref(href.split('?')[1] || CG_SHOP_BRAND_QUERY));
      }
    });
    document.querySelectorAll('a[href^="/camgirls"]').forEach(function (a) {
      var h = a.getAttribute('href') || '';
      if (h.indexOf('/camgirls/p/') === 0) {
        a.setAttribute('href', cgPerformerHref(h.split('/camgirls/p/')[1].replace(/\/?$/, '')));
      } else if (h === '/camgirls/' || h === '/camgirls') {
        a.setAttribute('href', pageBase());
      }
    });
  }

  function uid() {
    try {
      return localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || (window.MnUserId ? window.MnUserId.read() : '');
    } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'camgirls.js', context: 'catch' }); }
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
    } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'camgirls.js', context: 'catch' }); }
      return [];
    }
  }

  function saveFavorites(list) {
    try {
      localStorage.setItem(favoritesKey(), JSON.stringify(list));
    } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'camgirls.js', context: 'catch' }); }}
  }

  function toggleFav(id) {
    var favs = loadFavorites();
    var i = favs.indexOf(id);
    if (i >= 0) favs.splice(i, 1);
    else favs.push(id);
    saveFavorites(favs);
    var perf = performers.find(function (x) {
      return x.id === id;
    });
    if (perf && favs.indexOf(id) >= 0) trackProfilerPicture('camgirl_favorite', perf);
    fetch(apiUrl('/api/camgirls/performers/' + encodeURIComponent(id) + '/favorite'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: uid() }),
    }).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'camgirls.js', context: 'catch' }); }});
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
    fetch(apiUrl('/api/camgirls/age-verify'), {
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
    fetch(apiUrl('/api/camgirls/agents'))
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
      .catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'camgirls.js', context: 'catch' }); }});
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

  function infobarPill(label, on) {
    return (
      '<span class="cg-infobar-pill' +
      (on ? ' cg-infobar-on' : '') +
      '">' +
      esc(label) +
      '</span>'
    );
  }

  var CG_UPGRADE_LABELS = {
    portrait_pictures: 'Portrait',
    close_up: 'Close-up',
    icon_webp: 'HD icon',
    gallery_hd: 'HD gallery',
  };

  function upgradeLabel(tag) {
    return CG_UPGRADE_LABELS[tag] || String(tag || '').replace(/_/g, ' ');
  }

  function performerUpgradeBar(p) {
    var tags = p.studio_upgrades || (p.media && p.media.studio_upgrades) || [];
    if (!tags.length) return '';
    return (
      '<div class="cg-infobar-upgrades">' +
      tags
        .map(function (tag) {
          return '<span class="cg-upgrade-pill">' + esc(upgradeLabel(tag)) + '</span>';
        })
        .join('') +
      '</div>'
    );
  }

  function portraitUrl(p) {
    return (
      p.picture_url ||
      (p.media && (p.media.picture_url || p.media.avatar_hd_url)) ||
      p.icon_url ||
      p.avatar_url ||
      ''
    );
  }

  function trackProfilerPicture(action, p) {
    var pic = portraitUrl(p);
    if (!pic || !uid()) return;
    fetch(apiUrl('/api/profiler/track'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: uid(),
        action_type: action,
        metadata: {
          performer_id: p.id,
          picture_url: pic,
        },
      }),
    })
      .then(function () {
        return fetch(apiUrl('/api/profiler/pictures'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: uid(),
            url: pic,
            source: 'camgirls_' + action,
          }),
        });
      })
      .catch(function () {});
  }

  function performerMediaBlock(p) {
    var m = p.media;
    if (!m) return '';
    var gal = (m.gallery || []).slice(0, 4);
    var portrait = portraitUrl(p);
    var hero = portrait
      ? '<img class="cg-card-portrait" src="' + esc(staticUrl(portrait)) + '" alt="" loading="lazy">'
      : '';
    var thumbs = gal
      .map(function (url, idx) {
        var cls = 'cg-gallery-thumb' + (idx === gal.length - 1 ? ' cg-closeup-thumb' : '');
        return (
          '<img class="' +
          cls +
          '" src="' +
          esc(staticUrl(url)) +
          '" alt="" loading="lazy">'
        );
      })
      .join('');
    var preview = '';
    if (m.preview_video_url || m.preview_video_mp4_url) {
      var vsrc = '';
      if (m.preview_video_url) {
        vsrc +=
          '<source src="' +
          esc(staticUrl(m.preview_video_url)) +
          '" type="video/webm">';
      }
      if (m.preview_video_mp4_url) {
        vsrc +=
          '<source src="' +
          esc(staticUrl(m.preview_video_mp4_url)) +
          '" type="video/mp4">';
      }
      preview =
        '<video class="cg-preview-video" muted loop playsinline poster="' +
        esc(staticUrl(m.preview_poster_url || '')) +
        '">' +
        vsrc +
        '</video>';
    } else if (m.preview_loop_svg_url) {
      preview =
        '<img class="cg-preview-video" src="' +
        esc(staticUrl(m.preview_loop_svg_url)) +
        '" alt="Preview loop">';
    }
    var resell = '';
    if (p.resell && p.resell.logo_url) {
      var shopQ =
        p.resell.shop_query ||
        (p.resell.shop_item_id
          ? 'highlight=' + encodeURIComponent(p.resell.shop_item_id)
          : CG_SHOP_BRAND_QUERY);
      var shopHref = cgShopHref(shopQ);
      resell =
        '<a class="cg-resell-link" href="' +
        esc(staticUrl(p.resell.logo_url)) +
        '" download title="Logo">Logo</a> · ' +
        '<a class="cg-resell-link" href="' +
        esc(shopHref) +
        '">Buy brand pack</a> · ' +
        '<a class="cg-resell-link" href="' +
        esc(apiUrl('/api/camgirls/performers/' + p.id + '/media')) +
        '" target="_blank" rel="noopener">Manifest</a>';
    }
    return (
      '<div class="cg-media-block">' +
      hero +
      preview +
      '<div class="cg-gallery-row">' +
      thumbs +
      '</div>' +
      performerUpgradeBar(p) +
      (resell ? '<p class="cg-resell-row">' + resell + '</p>' : '') +
      '</div>'
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
      (p.picture_url || portraitUrl(p) ? infobarPill('Portrait', true) : '') +
      '</div>' +
      performerUpgradeBar(p)
    );
  }

  function loadStatus() {
    fetch(apiUrl('/api/camgirls/status'))
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
          function todoLi(item) {
            return (
              '<li><span class="cg-todo-pri">' +
              esc(item.priority || '—') +
              '</span><strong>' +
              esc(item.title || '') +
              '</strong> — ' +
              esc(item.detail || '') +
              '</li>'
            );
          }
          var byCat = d.next_todos_by_category || [];
          if (byCat.length) {
            todos.innerHTML = byCat
              .map(function (cat) {
                var catItems = cat.items || [];
                if (!catItems.length) return '';
                var head =
                  '<div class="cg-todo-cat"><h4 class="cg-todo-cat-title">' +
                  esc(cat.title || cat.id || '') +
                  '</h4>';
                if (cat.description) {
                  head += '<p class="cg-todo-cat-desc">' + esc(cat.description) + '</p>';
                }
                return head + '<ol>' + catItems.map(todoLi).join('') + '</ol></div>';
              })
              .join('');
          } else {
            var items = d.next_todos || [];
            if (!items.length) {
              todos.innerHTML = '<ol><li>All Phase 0 items shipped — see MN2_TODO for ops.</li></ol>';
            } else {
              todos.innerHTML = '<ol>' + items.map(todoLi).join('') + '</ol>';
            }
          }
        }
      })
      .catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'camgirls.js', context: 'catch' }); }});
  }

  function paypalCheckout(action, performerId, extra) {
    var body = { user_id: uid(), action: action || 'unlock', performer_id: performerId };
    extra = extra || {};
    if (extra.amount_mn2 != null) body.amount_mn2 = extra.amount_mn2;
    if (extra.gift_id) body.gift_id = extra.gift_id;
    if (extra.minutes != null) body.minutes = extra.minutes;
    fetch(apiUrl('/api/camgirls/paypal/create-order'), {
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
          } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'camgirls.js', context: 'catch' }); }}
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
    fetch(apiUrl('/api/camgirls/performers/' + encodeURIComponent(id) + '/private-show'), {
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
    fetch(apiUrl('/api/camgirls/performers/' + encodeURIComponent(id) + '/fan-club'), {
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
      } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'camgirls.js', context: 'catch' }); }}
      if (window.history && window.history.replaceState) {
        window.history.replaceState({}, '', pageBase());
      }
      return;
    }
    var orderId = params.get('token') || '';
    try {
      orderId = orderId || sessionStorage.getItem('cg_paypal_order') || '';
      sessionStorage.removeItem('cg_paypal_order');
    } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'camgirls.js', context: 'catch' }); }}
    var paypalCtx = {};
    try {
      paypalCtx = JSON.parse(sessionStorage.getItem('cg_paypal_ctx') || '{}');
      sessionStorage.removeItem('cg_paypal_ctx');
    } catch (e2) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e2 instanceof Error ? e2 : new Error(String(e2)), { source: 'camgirls.js', context: 'catch' }); }
      paypalCtx = {};
    }
    var approved = params.get('paypal') === 'success' || !!(params.get('PayerID') || params.get('PayerId'));
    if (!orderId || !approved) {
      if (params.get('paypal') === 'success' && !orderId) {
        msg('PayPal approved — capture will finish from the order webhook if unlock did not apply.');
      }
      return;
    }
    fetch(apiUrl('/api/camgirls/paypal/capture'), {
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
          window.history.replaceState({}, '', pageBase());
        }
      });
  }

  function applyPerformerCatalog(d) {
    if (!d || !d.success) return false;
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
    return performers.length > 0;
  }

  function loadPerformers() {
    var grid = document.getElementById('cg-grid');
    var user = encodeURIComponent(uid());
    if (grid) {
      grid.innerHTML =
        '<p class="cg-loading">Loading performers… <span class="cg-loading-hint">(first load can take up to a minute)</span></p>';
    }
    fetch(apiUrl('/api/camgirls/performers?user_id=' + user + '&lite=1'))
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (applyPerformerCatalog(d)) {
          showAgeGate(
            performers.some(function (p) {
              return !p.age_verified;
            })
          );
          renderGrid();
          msg('Loading gallery & shop links…');
        }
      })
      .catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'camgirls.js', context: 'catch' }); }});
    fetch(apiUrl('/api/camgirls/performers?user_id=' + user))
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (!d.success) {
          if (!performers.length) {
            msg(d.error || 'Could not load performers', true);
            if (grid) grid.innerHTML = '<p>Failed to load catalog.</p>';
          }
          return;
        }
        if (!applyPerformerCatalog(d)) {
          if (grid) grid.innerHTML = '<p>No performers available.</p>';
          return;
        }
        var needsAge = performers.some(function (p) {
          return !p.age_verified;
        });
        showAgeGate(needsAge);
        renderGrid();
        if (window.CG_SINGLE_PERFORMER && performers[0]) {
          renderPerformerPageMedia(performers[0]);
        }
        msg('');
      })
      .catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'camgirls.js', context: 'catch' }); }
        if (!performers.length) {
          msg('Network error loading performers', true);
          if (grid) grid.innerHTML = '<p>Could not reach API. Retry in a moment.</p>';
        }
      });
  }

  function renderPerformerPageMedia(p) {
    var el = document.getElementById('cg-performer-media');
    if (!el || !p.media) return;
    var m = p.media;
    var brand =
      '<div class="cg-brand-row">' +
      '<img src="' +
      esc(staticUrl(m.icon_url || p.avatar_url)) +
      '" alt="Icon">' +
      '<img src="' +
      esc(staticUrl(m.logo_url || '')) +
      '" alt="Logo">' +
      '<a href="' +
      esc(apiUrl('/api/camgirls/performers/' + p.id + '/media')) +
      '" target="_blank" rel="noopener">Download resell manifest (JSON)</a>' +
      '</div>';
    el.innerHTML = performerMediaBlock(p) + brand;
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
        var avatar = p.icon_url || p.avatar_url || '/static/camgirls/avatar-demo.svg';
        var unlocked = p.unlocked ? '<span class="cg-badge">Unlocked</span>' : '';
        var fanBadge = p.fan_club ? ' <span class="cg-fc-badge">Fan club</span>' : '';
        return (
          '<article class="cg-card" data-id="' + esc(p.id) + '">' +
          performerInfobar(p) +
          performerMediaBlock(p) +
          '<div style="display:flex;gap:12px;align-items:center;">' +
          '<img class="cg-card-thumb" src="' + esc(staticUrl(avatar)) + '" alt="">' +
          '<div><strong><a href="' + esc(cgPerformerHref(p.id)) + '" style="color:inherit;text-decoration:none;">' +
          esc(p.display_name) +
          '</a></strong> <span class="cg-ai-badge">AI</span>' +
          unlocked +
          fanBadge +
          (p.floor
            ? '<p style="font-size:0.75rem;opacity:0.75;margin:4px 0 0;">' +
              esc(p.floor.nft_name || 'NFT') +
              ' · ' +
              esc(String(p.floor.hosting_spots || '')) +
              ' host spots · one MN2 wallet</p>'
            : '') +
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
        fetch(apiUrl('/api/camgirls/performers/' + encodeURIComponent(id) + '/unlock'), {
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
            if (d.success) {
              var unlocked = performers.find(function (x) {
                return x.id === id;
              });
              if (unlocked) trackProfilerPicture('camgirl_unlock', unlocked);
              loadPerformers();
            }
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
        fetch(apiUrl('/api/camgirls/performers/' + encodeURIComponent(id) + '/tip'), {
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
    applyAppExpandLayout();
    loadAgents();
    loadStatus();
    handlePayPalReturn();
    loadPerformers();
  });
})();
