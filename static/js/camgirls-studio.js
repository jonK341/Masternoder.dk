/**

 * Camgirls studio — chat, gifts, dances, voice stub.

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



  function loadChatHistory(performerId, log) {

    fetch('/api/camgirls/performers/' + encodeURIComponent(performerId) + '/chat/history?user_id=' + encodeURIComponent(uid()))

      .then(function (r) {

        return r.json();

      })

      .then(function (d) {

        if (!d.success || !d.messages || !log) return;

        d.messages.forEach(function (m) {

          if (m.message) {

            var u = document.createElement('div');

            u.className = 'cg-chat-line cg-chat-user';

            u.textContent = m.message;

            log.appendChild(u);

          }

          if (m.reply) {

            var b = document.createElement('div');

            b.className = 'cg-chat-line cg-chat-bot';

            b.textContent = m.reply;

            log.appendChild(b);

          }

        });

        log.scrollTop = log.scrollHeight;

      })

      .catch(function () {});

  }



  function triggerDance(performerId, danceKey, label) {

    var card = document.querySelector('[data-id="' + performerId + '"]');

    var avatar = card && card.querySelector('.cg-card-thumb, .cg-stage-avatar');

    if (!avatar) return;

    avatar.classList.remove('cg-dance-shimmy', 'cg-dance-spin', 'cg-dance-bounce', 'cg-dance-wave', 'cg-dance-vip');

    void avatar.offsetWidth;

    var cls = danceKey === 'vip' ? 'cg-dance-vip' : 'cg-dance-' + danceKey;

    avatar.classList.add(cls);

    setTimeout(function () {

      avatar.classList.remove(cls);

    }, 4000);

    if (label && card) {

      var note = card.querySelector('.cg-wheel-result');

      if (note) note.textContent = 'Dance: ' + label;

    }

  }



  function openChat(panel, performerId) {

    if (!panel || panel._wired) return;

    panel._wired = true;

    panel.innerHTML =

      '<div class="cg-chat-log" id="cg-log-' + esc(performerId) + '"></div>' +

      '<div class="cg-chat-compose">' +

      '<input class="cg-chat-input" id="cg-input-' + esc(performerId) + '" placeholder="Say something…">' +

      '<button type="button" class="cg-unlock cg-send-btn">Send</button></div>' +

      '<div class="cg-wheel-result"></div>' +

      '<div class="cg-studio-actions" id="cg-studio-' + esc(performerId) + '"></div>';

    var sendBtn = panel.querySelector('.cg-send-btn');

    var input = panel.querySelector('.cg-chat-input');

    var log = panel.querySelector('.cg-chat-log');

    loadChatHistory(performerId, log);

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

      if (!host || !cat) return;

      if (cat.gifts) {

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

      }

      if (cat.dances) {

        Object.keys(cat.dances).forEach(function (key) {

          var d = cat.dances[key];

          var btn = document.createElement('button');

          btn.type = 'button';

          btn.className = 'cg-studio-btn';

          btn.textContent = '💃 ' + (d.label || key) + ' ' + (d.price_mn2 || 0) + ' MN2';

          btn.addEventListener('click', function () {

            fetch('/api/camgirls/performers/' + encodeURIComponent(performerId) + '/tip', {

              method: 'POST',

              headers: { 'Content-Type': 'application/json' },

              body: JSON.stringify({ user_id: uid(), amount: d.price_mn2 || 8 }),

            })

              .then(function (r) {

                return r.json();

              })

              .then(function (res) {

                if (res.success) {

                  triggerDance(performerId, key, d.label || key);

                  append('Dance unlocked: ' + (d.label || key), 'cg-chat-bot');

                } else append(res.error || 'Dance failed', 'cg-chat-bot');

              });

          });

          host.appendChild(btn);

        });

      }

      var voiceBtn = document.createElement('button');

      voiceBtn.type = 'button';

      voiceBtn.className = 'cg-studio-btn';

      voiceBtn.textContent = '🎙 Voice';

      voiceBtn.addEventListener('click', function () {

        fetch('/api/camgirls/livekit/token', {

          method: 'POST',

          headers: { 'Content-Type': 'application/json' },

          body: JSON.stringify({ user_id: uid(), performer_id: performerId }),

        })

          .then(function (r) {

            return r.json();

          })

          .then(function (d) {

            append(d.note || (d.mode === 'live' ? 'Voice room ready.' : 'Voice preview mode.'), 'cg-chat-bot');

          });

      });

      host.appendChild(voiceBtn);

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



  global.CamgirlsStudio = { loadCatalog: loadCatalog, openChat: openChat, enhanceCards: enhanceCards, triggerDance: triggerDance };

})(window);

