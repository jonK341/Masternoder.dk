(function () {
  'use strict';

  var msgEl = document.getElementById('cg-msg');
  var grid = document.getElementById('cg-grid');
  var ageGate = document.getElementById('cg-age-gate');
  var agentsStrip = document.getElementById('cg-agents');
  var agentChips = document.getElementById('cg-agent-chips');

  function msg(t, ok) {
    if (!msgEl) return;
    msgEl.textContent = t || '';
    msgEl.style.color = ok ? '#00ff88' : '#ffaa44';
  }

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

  function showAgeGate(show) {
    if (ageGate) ageGate.style.display = show ? 'block' : 'none';
  }

  function appendChatLine(panel, text, role) {
    var line = document.createElement('div');
    line.className = 'cg-chat-line cg-chat-' + role;
    line.textContent = text;
    panel.appendChild(line);
    panel.scrollTop = panel.scrollHeight;
  }

  function renderCard(p) {
    var card = document.createElement('div');
    card.className = 'cg-card';
    card.setAttribute('data-performer-id', p.id);
    var unlocked = p.unlocked ? '<span class="cg-badge">Unlocked</span>' : '';
    var aiBadge = p.ai_enabled !== false
      ? '<span class="cg-ai-badge">AI · ' + (p.ai_persona || p.agent_id || 'companion') + '</span>'
      : '';
    var chatPrice = p.chat_price_mn2 != null ? p.chat_price_mn2 : 2;
    var chatBtn = p.unlocked
      ? '<button type="button" class="cg-chat-toggle" data-id="' + p.id + '" data-action="chat-toggle">Chat (' + chatPrice + ' MN2/msg)</button>'
      : '';
    card.innerHTML =
      '<div style="display:flex;gap:12px;align-items:center;">' +
      '<img src="' + (p.avatar_url || '/static/camgirls/avatar-demo.svg') + '" alt="">' +
      '<div><strong>' + (p.display_name || p.id) + '</strong><br><span style="opacity:0.7;font-size:0.85rem;">' +
      (p.tagline || '') + '</span> ' + unlocked + aiBadge + '</div></div>' +
      '<div style="margin-top:8px;font-size:0.85rem;">Unlock: <strong>' + p.unlock_price_mn2 + ' MN2</strong> · Tip from ' + p.tip_min_mn2 + ' MN2</div>' +
      '<div class="cg-actions">' +
      '<button type="button" class="cg-unlock" data-id="' + p.id + '" data-action="unlock">Unlock</button>' +
      '<button type="button" class="cg-tip" data-id="' + p.id + '" data-action="tip">Tip 10 MN2</button>' +
      chatBtn +
      '</div>' +
      '<div class="cg-chat-panel" id="cg-chat-' + p.id + '" style="display:none;">' +
      '<div class="cg-chat-log"></div>' +
      '<div class="cg-chat-compose">' +
      '<input type="text" class="cg-chat-input" maxlength="2000" placeholder="Say something…">' +
      '<button type="button" class="cg-chat-send cg-unlock" data-id="' + p.id + '" data-action="chat-send">Send</button>' +
      '</div></div>';
    return card;
  }

  function loadAgents() {
    if (!agentsStrip || !agentChips) return Promise.resolve();
    return api('/api/camgirls/agents')
      .then(function (res) {
        var d = res.data || {};
        if (!d.success || !(d.agents || []).length) return;
        agentsStrip.style.display = 'block';
        agentChips.innerHTML = '';
        d.agents.forEach(function (a) {
          var chip = document.createElement('span');
          chip.className = 'cg-agent-chip';
          chip.textContent = (a.name || a.agent_id) + ' → ' + (a.performer_id || '?');
          agentChips.appendChild(chip);
        });
      })
      .catch(function () {});
  }

  function loadCatalog() {
    if (grid) grid.textContent = 'Loading performers…';
    return api('/api/camgirls/performers')
      .then(function (res) {
        var d = res.data || {};
        if (!grid) return;
        if (!d.success) {
          var err = d.error || d.message || ('HTTP ' + res.status);
          msg('Could not load catalog: ' + err, false);
          grid.textContent = 'Catalog unavailable. Try again in a moment.';
          return;
        }
        grid.innerHTML = '';
        (d.performers || []).forEach(function (p) {
          grid.appendChild(renderCard(p));
        });
        if (!(d.performers || []).length) grid.textContent = 'No performers yet.';
      })
      .catch(function () {
        msg('Could not load catalog (network error).', false);
        if (grid) grid.textContent = 'Catalog unavailable.';
      });
  }

  function sendChat(performerId, inputEl, logEl) {
    var text = (inputEl && inputEl.value || '').trim();
    if (!text) {
      msg('Enter a message first.');
      return;
    }
    appendChatLine(logEl, text, 'user');
    inputEl.value = '';
    inputEl.disabled = true;
    api('/api/camgirls/chat', { method: 'POST', body: { performer_id: performerId, message: text } })
      .then(function (res) {
        inputEl.disabled = false;
        if (res.data && res.data.code === 'age_verification_required') {
          showAgeGate(true);
          msg('Confirm age before chat.');
          return;
        }
        if (res.data && res.data.code === 'unlock_required') {
          msg('Unlock this performer before chat.');
          return;
        }
        if (res.data && res.data.success) {
          appendChatLine(logEl, res.data.reply || '…', 'bot');
          var aiNote = res.data.agent_id ? ' via ' + res.data.agent_id : '';
          msg('Chat sent (' + (res.data.amount_mn2 || '') + ' MN2' + aiNote + ')', true);
        } else {
          msg((res.data && res.data.error) || 'Chat failed');
        }
      })
      .catch(function () {
        inputEl.disabled = false;
        msg('Chat request failed');
      });
  }

  function handleAction(e) {
    var btn = e.target.closest('button[data-action]');
    if (!btn) return;
    var id = btn.getAttribute('data-id');
    var action = btn.getAttribute('data-action');
    if (action === 'unlock') {
      api('/api/camgirls/performers/' + encodeURIComponent(id) + '/unlock', { method: 'POST', body: {} })
        .then(function (res) {
          if (res.data && res.data.code === 'age_verification_required') {
            showAgeGate(true);
            msg('Confirm age before spending MN2.');
            return;
          }
          if (res.data && res.data.success) {
            msg('Unlocked ' + id + ' for ' + (res.data.amount_mn2 || '') + ' MN2', true);
            loadCatalog();
          } else {
            msg((res.data && res.data.error) || 'Unlock failed');
          }
        });
    } else if (action === 'tip') {
      api('/api/camgirls/performers/' + encodeURIComponent(id) + '/tip', { method: 'POST', body: { amount_mn2: 10 } })
        .then(function (res) {
          if (res.data && res.data.code === 'age_verification_required') {
            showAgeGate(true);
            msg('Confirm age before tipping.');
            return;
          }
          if (res.data && res.data.success) msg('Tip sent: 10 MN2 to ' + id, true);
          else msg((res.data && res.data.error) || 'Tip failed');
        });
    } else if (action === 'chat-toggle') {
      var panel = document.getElementById('cg-chat-' + id);
      if (panel) panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    } else if (action === 'chat-send') {
      var chatPanel = document.getElementById('cg-chat-' + id);
      if (!chatPanel) return;
      sendChat(
        id,
        chatPanel.querySelector('.cg-chat-input'),
        chatPanel.querySelector('.cg-chat-log')
      );
    }
  }

  function handleChatKey(e) {
    if (e.key !== 'Enter' || e.shiftKey) return;
    var input = e.target;
    if (!input.classList.contains('cg-chat-input')) return;
    var panel = input.closest('.cg-chat-panel');
    if (!panel) return;
    var card = panel.closest('.cg-card');
    var id = card && card.getAttribute('data-performer-id');
    if (!id) return;
    e.preventDefault();
    sendChat(id, input, panel.querySelector('.cg-chat-log'));
  }

  document.getElementById('cg-age-btn').addEventListener('click', function () {
    var y = parseInt((document.getElementById('cg-birth-year') || {}).value, 10);
    api('/api/camgirls/age-verify', { method: 'POST', body: { confirm: true, birth_year: y || undefined } })
      .then(function (res) {
        if (res.data && res.data.success) {
          showAgeGate(false);
          msg('Age verified — you can unlock, tip, and chat.', true);
        } else msg((res.data && res.data.error) || 'Verification failed');
      });
  });

  if (grid) {
    grid.addEventListener('click', handleAction);
    grid.addEventListener('keydown', handleChatKey);
  }
  loadAgents().catch(function () {});
  loadCatalog().catch(function () { msg('Failed to load catalog'); });
})();
