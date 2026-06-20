(function (global) {
  'use strict';

  var musicCtx = null;
  var musicNodes = {};
  var voiceOn = true;
  var goalProgress = {};

  function api(path, opts) {
    opts = opts || {};
    return fetch(path, {
      method: opts.method || 'GET',
      credentials: 'same-origin',
      headers: Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {}),
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    }).then(function (r) {
      return r.json().then(function (j) {
        return { status: r.status, data: j };
      });
    });
  }

  function speak(text, voiceProfile) {
    if (!voiceOn || !text || !global.speechSynthesis) return;
    try {
      var u = new SpeechSynthesisUtterance(text);
      var vp = voiceProfile || {};
      u.lang = vp.lang || 'en-US';
      u.pitch = vp.pitch != null ? vp.pitch : 1;
      u.rate = vp.rate != null ? vp.rate : 1;
      global.speechSynthesis.cancel();
      global.speechSynthesis.speak(u);
    } catch (e) { /* ignore */ }
  }

  function startMic(inputEl) {
    var SR = global.SpeechRecognition || global.webkitSpeechRecognition;
    if (!SR || !inputEl) return;
    try {
      var rec = new SR();
      rec.lang = 'en-US';
      rec.onresult = function (ev) {
        var t = ev.results[0][0].transcript;
        inputEl.value = (inputEl.value + ' ' + t).trim();
      };
      rec.start();
    } catch (e) { /* ignore */ }
  }

  function ensureAudio() {
    if (!musicCtx) {
      var AC = global.AudioContext || global.webkitAudioContext;
      if (AC) musicCtx = new AC();
    }
    return musicCtx;
  }

  function stopMusic(pid) {
    var n = musicNodes[pid];
    if (!n) return;
    try {
      if (n.interval) clearInterval(n.interval);
      (n.oscillators || []).forEach(function (o) {
        try { o.stop(); } catch (e) { /* */ }
      });
    } catch (e) { /* */ }
    delete musicNodes[pid];
  }

  function startMusic(pid, theme) {
    stopMusic(pid);
    var ctx = ensureAudio();
    if (!ctx) return;
    var bpm = (theme && theme.bpm) || 100;
    var oscs = [];
    var gain = ctx.createGain();
    gain.gain.value = 0.04;
    gain.connect(ctx.destination);
    var bass = ctx.createOscillator();
    bass.type = 'sine';
    bass.frequency.value = 55;
    bass.connect(gain);
    bass.start();
    oscs.push(bass);
    var tick = 0;
    var interval = setInterval(function () {
      tick++;
      var pulse = ctx.createOscillator();
      var pg = ctx.createGain();
      pulse.type = 'triangle';
      pulse.frequency.value = 220 + (tick % 4) * 40;
      pg.gain.value = 0.02;
      pulse.connect(pg);
      pg.connect(gain);
      pulse.start();
      pulse.stop(ctx.currentTime + 0.08);
    }, (60 / bpm) * 1000 * 2);
    musicNodes[pid] = { oscillators: oscs, interval: interval, gain: gain };
    if (ctx.state === 'suspended') ctx.resume();
  }

  function triggerDance(card, animation) {
    var stage = card.querySelector('.cg-stage-avatar');
    if (!stage) return;
    stage.classList.remove('cg-dance-shimmy', 'cg-dance-spin', 'cg-dance-bounce', 'cg-dance-wave', 'cg-dance-vip');
    var cls = 'cg-dance-' + (animation || 'shimmy');
    stage.classList.add(cls);
    setTimeout(function () {
      stage.classList.remove(cls);
    }, 2800);
  }

  function triggerBuzz(card, level) {
    var bar = card.querySelector('.cg-buzz-fill');
    if (!bar) return;
    var pct = Math.min(100, (level || 1) * 18);
    bar.style.width = pct + '%';
    card.classList.add('cg-buzz-pulse');
    setTimeout(function () {
      card.classList.remove('cg-buzz-pulse');
    }, 600);
  }

  function updateGoal(card, pid, studio, addedMn2) {
    var goal = (studio && studio.goal_progress) || {};
    var goalMn2 = goal.goal_mn2 || (studio && studio.goal_mn2);
    if (!goalMn2) return;
    var g = goalProgress[pid];
    if (g == null) g = goal.raised_mn2 || 0;
    g += addedMn2 || 0;
    goalProgress[pid] = g;
    var pct = Math.min(100, Math.round((g / goalMn2) * 100));
    var fill = card.querySelector('.cg-goal-fill');
    var label = card.querySelector('.cg-goal-label');
    if (fill) fill.style.width = pct + '%';
    if (label) label.textContent = (goal.label || studio.goal_label || 'Goal') + ' — ' + pct + '%';
  }

  function applyScene(card, sceneId) {
    var av = card.querySelector('.cg-stage-avatar');
    var filters = {
      neon_club: 'none',
      moonlit: 'hue-rotate(220deg) brightness(0.9)',
      zen_garden: 'hue-rotate(90deg) saturate(0.8)',
      fire_pit: 'hue-rotate(30deg) saturate(1.3)',
      gold_lounge: 'sepia(0.3) brightness(1.1)',
    };
    if (av) av.style.filter = filters[sceneId] || 'none';
  }

  function buildLeaderboardHtml(leaders) {
    if (!leaders || !leaders.length) return '';
    var html = '<div class="cg-leaderboard"><span class="cg-lb-title">🏆 Top tippers</span>';
    leaders.forEach(function (L) {
      html += '<span class="cg-lb-row">#' + L.rank + ' ' + (L.user_label || 'fan') + ' · ' + L.amount_mn2 + ' MN2</span>';
    });
    return html + '</div>';
  }

  function fakeViewers() {
    return 12 + Math.floor(Math.random() * 88);
  }

  function spinWheel(card) {
    var outcomes = ['Double dance', 'Free emoji', 'Tip luck +5', 'VIP wave', 'Try again', 'Shimmy bonus'];
    var pick = outcomes[Math.floor(Math.random() * outcomes.length)];
    var el = card.querySelector('.cg-wheel-result');
    if (el) el.textContent = '🎡 ' + pick;
  }

  function rollDice(card) {
    var a = 1 + Math.floor(Math.random() * 6);
    var b = 1 + Math.floor(Math.random() * 6);
    var el = card.querySelector('.cg-wheel-result');
    if (el) el.textContent = '🎲 ' + a + '+' + b + '=' + (a + b);
  }

  function emojiRain(card, emoji) {
    var stage = card.querySelector('.cg-stage');
    if (!stage) return;
    var span = document.createElement('span');
    span.className = 'cg-emoji-float';
    span.textContent = emoji || '✨';
    span.style.left = Math.round(Math.random() * 80) + '%';
    stage.appendChild(span);
    setTimeout(function () {
      if (span.parentNode) span.parentNode.removeChild(span);
    }, 2000);
  }

  function buildStudioHtml(p, studio) {
    if (!studio) return '';
    var unlocked = p.unlocked;
    var feats = studio.features || [];
    var social = p.social || {};
    var viewers = fakeViewers();
    var goal = p.goal || studio.goal_progress || {};
    var goalPct = goal.percent || 0;
    var favIcon = p.favorite ? '⭐' : '☆';
    var fcBadge = p.fan_club_member ? '<span class="cg-fc-badge">Fan club</span>' : '';
    var sched = p.next_show ? '<span class="cg-schedule">📅 ' + p.next_show + '</span>' : '';
    var html =
      '<div class="cg-stage" data-pid="' + p.id + '">' +
      '<div class="cg-stage-top">' +
      '<button type="button" class="cg-studio-btn cg-fav-btn" data-action="favorite" data-id="' + p.id + '" title="Favorite">' + favIcon + '</button>' +
      '<span class="cg-viewers">👁 ' + viewers + '</span>' + fcBadge + sched +
      (studio.music_enabled || feats.indexOf('room_music') >= 0
        ? '<button type="button" class="cg-studio-btn" data-action="music-toggle" data-id="' + p.id + '">🎵 Music</button>'
        : '') +
      (studio.voice_enabled || feats.indexOf('voice_reply') >= 0
        ? '<button type="button" class="cg-studio-btn" data-action="voice-toggle" data-id="' + p.id + '">🔊 Voice</button>'
        : '') +
      '</div>' +
      '<div class="cg-stage-avatar-wrap">' +
      '<img class="cg-stage-avatar" src="' + (p.avatar_url || '/static/camgirls/avatar-demo.svg') + '" alt="">' +
      '<div class="cg-buzz-bar"><div class="cg-buzz-fill"></div></div>' +
      '</div>';
    if (feats.indexOf('token_goals') >= 0 && (studio.goal_mn2 || goal.goal_mn2)) {
      html +=
        '<div class="cg-goal-wrap">' +
        '<div class="cg-goal-label">' + (goal.label || studio.goal_label || 'Goal') + ' — ' + goalPct + '%</div>' +
        '<div class="cg-goal-bar"><div class="cg-goal-fill" style="width:' + goalPct + '%"></div></div></div>';
    }
    html += buildLeaderboardHtml(p.leaderboard);
    if (!unlocked) {
      html += '<p class="cg-studio-lock">Unlock for gifts, dances, voice, fan club & PM</p></div>';
      return html;
    }
    html += '<div class="cg-wheel-result"></div><div class="cg-studio-actions cg-studio-actions-main">';
    if (feats.indexOf('tip_menu') >= 0) {
      html +=
        '<button type="button" class="cg-tip cg-studio-btn" data-action="tip" data-id="' + p.id + '" data-amount="5">5</button>' +
        '<button type="button" class="cg-tip cg-studio-btn" data-action="tip" data-id="' + p.id + '" data-amount="10">10</button>' +
        '<button type="button" class="cg-tip cg-studio-btn" data-action="tip" data-id="' + p.id + '" data-amount="25">25</button>';
    }
    if (feats.indexOf('gift_menu') >= 0 && studio.gifts) {
      Object.keys(studio.gifts).forEach(function (gid) {
        var g = studio.gifts[gid];
        if (!g) return;
        html +=
          '<button type="button" class="cg-gift cg-studio-btn" data-action="gift" data-id="' + p.id + '" data-gift="' + gid + '" title="' + (g.label || gid) + '">' +
          (g.emoji || '🎁') + '</button>';
      });
    }
    if (feats.indexOf('dance_requests') >= 0 && studio.dances) {
      Object.keys(studio.dances).forEach(function (did) {
        var d = studio.dances[did];
        if (!d) return;
        html +=
          '<button type="button" class="cg-dance cg-studio-btn" data-action="dance" data-id="' + p.id + '" data-dance="' + did + '">💃 ' + (d.label || did) + '</button>';
      });
    }
    if (feats.indexOf('spin_wheel') >= 0) {
      html += '<button type="button" class="cg-studio-btn" data-action="wheel" data-id="' + p.id + '">🎡 Wheel</button>';
    }
    if (feats.indexOf('dice_game') >= 0) {
      html += '<button type="button" class="cg-studio-btn" data-action="dice" data-id="' + p.id + '">🎲 Dice</button>';
    }
    if (feats.indexOf('emoji_reactions') >= 0) {
      ['❤️', '🔥', '✨', '😘', '👑'].forEach(function (em) {
        html += '<button type="button" class="cg-studio-btn" data-action="emoji" data-id="' + p.id + '" data-emoji="' + em + '">' + em + '</button>';
      });
    }
    if (feats.indexOf('voice_input') >= 0) {
      html += '<button type="button" class="cg-studio-btn" data-action="mic" data-id="' + p.id + '">🎤 Mic</button>';
    }
    if (feats.indexOf('fan_club') >= 0 || social.fan_club_price_mn2) {
      html += '<button type="button" class="cg-studio-btn" data-action="fan-club" data-id="' + p.id + '">🎟 Fan club (' + (social.fan_club_price_mn2 || 15) + ')</button>';
    }
    if (feats.indexOf('vip_private_show') >= 0 || social.private_show_mn2_per_min) {
      html += '<button type="button" class="cg-studio-btn" data-action="private-show" data-id="' + p.id + '" data-minutes="5">🔒 Private 5m</button>';
    }
    if (feats.indexOf('offline_messages') >= 0) {
      html += '<button type="button" class="cg-studio-btn" data-action="offline" data-id="' + p.id + '">📬 Offline</button>';
    }
    if ((social.moods || []).length) {
      (social.moods || []).slice(0, 4).forEach(function (m) {
        html += '<button type="button" class="cg-studio-btn" data-action="mood" data-id="' + p.id + '" data-mood="' + m + '">🎭 ' + m + '</button>';
      });
    }
    if ((social.scenes || []).length) {
      html += '<button type="button" class="cg-studio-btn" data-action="scene" data-id="' + p.id + '" data-scene="' + (social.scenes[0] || 'neon_club') + '">🖼 Scene</button>';
    }
    html += '</div>';
    html += '<div class="cg-offline-compose" id="cg-offline-' + p.id + '" style="display:none;">' +
      '<input type="text" class="cg-offline-input" maxlength="500" placeholder="Offline note…">' +
      '<button type="button" class="cg-studio-btn" data-action="offline-send" data-id="' + p.id + '">Send</button></div>';
    html += '<div class="cg-private-timer" id="cg-private-' + p.id + '"></div></div>';
    return html;
  }

  function handleStudioAction(e, helpers) {
    var btn = e.target.closest('button[data-action]');
    if (!btn) return false;
    var action = btn.getAttribute('data-action');
    var id = btn.getAttribute('data-id');
    var card = btn.closest('.cg-card');
    if (!card) return false;

    if (action === 'music-toggle') {
      var playing = card.getAttribute('data-music') === '1';
      if (playing) {
        stopMusic(id);
        card.setAttribute('data-music', '0');
        btn.textContent = '🎵 Music';
        helpers.msg('Music off', true);
      } else {
        var st = JSON.parse(card.getAttribute('data-studio') || '{}');
        startMusic(id, st.music || { bpm: 100 });
        card.setAttribute('data-music', '1');
        btn.textContent = '⏹ Music';
        helpers.msg('Room music on', true);
      }
      return true;
    }
    if (action === 'voice-toggle') {
      voiceOn = !voiceOn;
      helpers.msg(voiceOn ? 'Voice replies on' : 'Voice replies off', true);
      return true;
    }
    if (action === 'tip') {
      var amt = parseFloat(btn.getAttribute('data-amount') || '10');
      api('/api/camgirls/performers/' + encodeURIComponent(id) + '/tip', {
        method: 'POST',
        body: { amount_mn2: amt },
      }).then(function (res) {
        if (res.data && res.data.success) {
          helpers.msg('Tip ' + amt + ' MN2 sent', true);
          var st = JSON.parse(card.getAttribute('data-studio') || '{}');
          updateGoal(card, id, st, amt);
          triggerBuzz(card, 2);
          emojiRain(card, '💰');
        } else helpers.msg((res.data && res.data.error) || 'Tip failed');
      });
      return true;
    }
    if (action === 'gift') {
      var gid = btn.getAttribute('data-gift');
      api('/api/camgirls/performers/' + encodeURIComponent(id) + '/gift', {
        method: 'POST',
        body: { gift_id: gid },
      }).then(function (res) {
        if (res.data && res.data.success) {
          var reply = res.data.performer_reply || 'Thank you!';
          helpers.msg('Gift sent: ' + (res.data.gift_label || gid), true);
          var log = card.querySelector('.cg-chat-log');
          if (log) {
            var line = document.createElement('div');
            line.className = 'cg-chat-line cg-chat-bot';
            line.textContent = reply;
            log.appendChild(line);
          }
          speak(reply, (JSON.parse(card.getAttribute('data-studio') || '{}')).voice);
          triggerBuzz(card, res.data.buzz || 2);
          emojiRain(card, res.data.gift_emoji || '🎁');
          var st = JSON.parse(card.getAttribute('data-studio') || '{}');
          updateGoal(card, id, st, res.data.amount_mn2 || 0);
        } else helpers.msg((res.data && res.data.error) || 'Gift failed');
      });
      return true;
    }
    if (action === 'dance') {
      var did = btn.getAttribute('data-dance');
      api('/api/camgirls/performers/' + encodeURIComponent(id) + '/dance', {
        method: 'POST',
        body: { dance_id: did },
      }).then(function (res) {
        if (res.data && res.data.success) {
          triggerDance(card, res.data.animation);
          var lingo = res.data.lingo || 'Dance!';
          helpers.msg(lingo, true);
          speak(lingo, (JSON.parse(card.getAttribute('data-studio') || '{}')).voice);
          var log = card.querySelector('.cg-chat-log');
          if (log) {
            var line = document.createElement('div');
            line.className = 'cg-chat-line cg-chat-bot';
            line.textContent = '💃 ' + lingo;
            log.appendChild(line);
          }
        } else helpers.msg((res.data && res.data.error) || 'Dance failed');
      });
      return true;
    }
    if (action === 'wheel') {
      spinWheel(card);
      return true;
    }
    if (action === 'dice') {
      rollDice(card);
      return true;
    }
    if (action === 'emoji') {
      emojiRain(card, btn.getAttribute('data-emoji'));
      return true;
    }
    if (action === 'mic') {
      var input = card.querySelector('.cg-chat-input');
      startMic(input);
      helpers.msg('Listening…', true);
      return true;
    }
    if (action === 'favorite') {
      api('/api/camgirls/performers/' + encodeURIComponent(id) + '/favorite', { method: 'POST', body: {} })
        .then(function (res) {
          if (res.data && res.data.success) {
            btn.textContent = res.data.favorite ? '⭐' : '☆';
            helpers.msg(res.data.favorite ? 'Added to favorites' : 'Removed from favorites', true);
            if (helpers.reloadCatalog) helpers.reloadCatalog();
          }
        });
      return true;
    }
    if (action === 'fan-club') {
      api('/api/camgirls/performers/' + encodeURIComponent(id) + '/fan-club', { method: 'POST', body: {} })
        .then(function (res) {
          if (res.data && res.data.success) {
            helpers.msg(res.data.performer_reply || 'Fan club joined!', true);
            speak(res.data.performer_reply, (JSON.parse(card.getAttribute('data-studio') || '{}')).voice);
            if (helpers.reloadCatalog) helpers.reloadCatalog();
          } else helpers.msg((res.data && res.data.error) || 'Fan club failed');
        });
      return true;
    }
    if (action === 'private-show') {
      var mins = parseInt(btn.getAttribute('data-minutes') || '5', 10);
      api('/api/camgirls/performers/' + encodeURIComponent(id) + '/private-show', {
        method: 'POST',
        body: { minutes: mins },
      }).then(function (res) {
        if (res.data && res.data.success) {
          helpers.msg(res.data.performer_reply || 'Private show started', true);
          var el = document.getElementById('cg-private-' + id);
          if (el) el.textContent = '🔒 Private ' + mins + 'm — ends in ' + (res.data.seconds_left || mins * 60) + 's';
          card.classList.add('cg-private-active');
          triggerDance(card, 'vip');
        } else helpers.msg((res.data && res.data.error) || 'Private show failed');
      });
      return true;
    }
    if (action === 'offline') {
      var panel = document.getElementById('cg-offline-' + id);
      if (panel) panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
      return true;
    }
    if (action === 'offline-send') {
      var offInput = card.querySelector('.cg-offline-input');
      var text = (offInput && offInput.value || '').trim();
      if (!text) { helpers.msg('Type an offline message'); return true; }
      api('/api/camgirls/performers/' + encodeURIComponent(id) + '/offline', {
        method: 'POST',
        body: { message: text },
      }).then(function (res) {
        if (res.data && res.data.success) {
          offInput.value = '';
          helpers.msg(res.data.performer_reply || 'Offline message queued', true);
        } else helpers.msg((res.data && res.data.error) || 'Offline failed');
      });
      return true;
    }
    if (action === 'mood') {
      var mood = btn.getAttribute('data-mood');
      api('/api/camgirls/performers/' + encodeURIComponent(id) + '/mood', {
        method: 'POST',
        body: { mood_id: mood },
      }).then(function (res) {
        if (res.data && res.data.success) {
          helpers.msg(res.data.lingo || 'Mood set', true);
          speak(res.data.lingo, (JSON.parse(card.getAttribute('data-studio') || '{}')).voice);
        }
      });
      return true;
    }
    if (action === 'scene') {
      var scene = btn.getAttribute('data-scene') || 'neon_club';
      applyScene(card, scene);
      helpers.msg('Scene: ' + scene, true);
      return true;
    }
    return false;
  }

  function enrichCard(card, p) {
    if (p.studio) {
      card.setAttribute('data-studio', JSON.stringify(p.studio));
    }
  }

  function onChatReply(card, reply, studio) {
    speak(reply, studio && studio.voice);
    triggerDance(card, 'wave');
  }

  global.CamgirlsStudio = {
    buildStudioHtml: buildStudioHtml,
    handleStudioAction: handleStudioAction,
    enrichCard: enrichCard,
    onChatReply: onChatReply,
    loadChatHistory: function (performerId, logEl) {
      if (!logEl) return;
      api('/api/camgirls/performers/' + encodeURIComponent(performerId) + '/chat/history?limit=20')
        .then(function (res) {
          if (!(res.data && res.data.success)) return;
          logEl.innerHTML = '';
          (res.data.messages || []).forEach(function (m) {
            var line = document.createElement('div');
            line.className = 'cg-chat-line cg-chat-' + (m.role === 'user' ? 'user' : 'bot');
            line.textContent = m.text;
            logEl.appendChild(line);
          });
          logEl.scrollTop = logEl.scrollHeight;
        });
    },
  };
})(typeof window !== 'undefined' ? window : this);
