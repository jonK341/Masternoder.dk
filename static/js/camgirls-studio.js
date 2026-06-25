/**
 * Camgirls studio — chat compose, gifts, dances (uses studio catalog API).
 */
(function (global) {
  'use strict';

  var catalog = null;

  function uid() {
    try {
      return global.localStorage.getItem('game_user_id') || global.localStorage.getItem('user_id') || 'default_user';
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

  function loadCatalog() {
    if (catalog) return Promise.resolve(catalog);
    return fetch('/api/camgirls/studio/catalog')
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (d.success) catalog = d;
        return catalog;
      })
      .catch(function () {
        return null;
      });
  }

  function openChat(panel, performerId) {
    if (!panel || panel._wired) return;
    panel._wired = true;
    panel.innerHTML =
      '<div class="cg-chat-log" id="cg-log-' + esc(performerId) + '"></div>' +
      '<div class="cg-chat-compose">' +
      '<input class="cg-chat-input" id="cg-input-' + esc(performerId) + '" placeholder="Say something…">' +
      '<button type="button" class="cg-unlock cg-send-btn">Send</button></div>' +
      '<div class="cg-studio-actions" id="cg-studio-' + esc(performerId) + '"></div>';
    var sendBtn = panel.querySelector('.cg-send-btn');
    var input = panel.querySelector('.cg-chat-input');
    var log = panel.querySelector('.cg-chat-log');
    function append(line, cls) {
      var div = document.createElement('div');
      div.className = 'cg-chat-line ' + (cls || 'cg-chat-bot');
      div.textContent = line;
      log.appendChild(div);
      log.scrollTop = log.scrollHeight;
    }
    sendBtn.addEventListener('click', function () {
      var text = (input.value || '').trim();
      if (!text) return;
      append(text, 'cg-chat-user');
      input.value = '';
      fetch('/api/camgirls/performers/' + encodeURIComponent(performerId) + '/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: uid(), message: text }),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (d) {
          append(d.reply || d.error || '…', 'cg-chat-bot');
        });
    });
    loadCatalog().then(function (cat) {
      var host = panel.querySelector('#cg-studio-' + performerId);
      if (!host || !cat || !cat.gifts) return;
      Object.keys(cat.gifts).forEach(function (key) {
        var g = cat.gifts[key];
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'cg-studio-btn';
        btn.textContent = (g.label || key) + ' ' + (g.price_mn2 || 0) + ' MN2';
        btn.addEventListener('click', function () {
          fetch('/api/camgirls/performers/' + encodeURIComponent(performerId) + '/tip', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: uid(), amount: g.price_mn2 || 5 }),
          })
            .then(function (r) {
              return r.json();
            })
            .then(function (d) {
              if (d.success) append('Gift sent: ' + (g.label || key), 'cg-chat-bot');
            });
        });
        host.appendChild(btn);
      });
    });
  }

  function enhanceCards(grid, performers) {
    if (!grid || !performers) return;
    performers.forEach(function (p) {
      fetch('/api/camgirls/performers/' + encodeURIComponent(p.id) + '/goal')
        .then(function (r) {
          return r.json();
        })
        .then(function (g) {
          var card = grid.querySelector('[data-id="' + p.id + '"]');
          if (!card || !g.success) return;
          var wrap = document.createElement('div');
          wrap.className = 'cg-goal-wrap';
          wrap.innerHTML =
            'Goal: ' +
            (g.raised_mn2 || 0).toFixed(1) +
            ' / ' +
            (g.goal_mn2 || 0) +
            ' MN2' +
            '<div class="cg-goal-bar"><div class="cg-goal-fill" style="width:' +
            (g.percent || 0) +
            '%"></div></div>';
          card.appendChild(wrap);
        })
        .catch(function () {});
    });
  }

  global.CamgirlsStudio = { loadCatalog: loadCatalog, openChat: openChat, enhanceCards: enhanceCards };
})(window);
