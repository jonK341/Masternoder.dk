/**
 * Aggregator monitor playfield: 2D grid with pseudo dimensions (x,y,z, t, layer)
 * Final battle runs inside the monitor overlay; progress from APIs.
 */
(function () {
  const GRID = 7;
  const CENTER = Math.floor(GRID / 2);

  function getUserId() {
    try {
      return localStorage.getItem('user_id') || localStorage.getItem('vidgenerator_user_id') || 'default_user';
    } catch (e) {
      return 'default_user';
    }
  }

  function el(id) {
    return document.getElementById(id);
  }

  function eg(action) {
    if (window.AggregatorEngagement && typeof window.AggregatorEngagement.award === 'function') {
      window.AggregatorEngagement.award(action);
    }
  }

  function logPrint(line) {
    const box = el('agg-user-print');
    if (!box) return;
    const ts = new Date().toISOString().slice(11, 19);
    box.textContent += `[${ts}] ${line}\n`;
    box.scrollTop = box.scrollHeight;
  }

  const state = {
    px: 0,
    py: 0,
    pz: 0,
    timeLayer: 0,
    stratum: 1,
    moves: 0,
    phase: 'explore',
    battleResult: null,
  };

  function dimsText() {
    return `x:${state.px} y:${state.py} z:${state.pz} · t:${state.timeLayer} · layer:${state.stratum}`;
  }

  function updateDimReadout() {
    const d = el('agg-dim-readout');
    if (d) d.textContent = dimsText();
  }

  function manhattanToGoal() {
    return Math.abs(state.px - CENTER) + Math.abs(state.py - CENTER);
  }

  function tryMove(dx, dy) {
    if (state.phase === 'battle') return;
    const nx = Math.max(0, Math.min(GRID - 1, state.px + dx));
    const ny = Math.max(0, Math.min(GRID - 1, state.py + dy));
    if (nx === state.px && ny === state.py) return;
    state.px = nx;
    state.py = ny;
    state.moves += 1;
    state.pz = (state.pz + (dx + dy + 7) % 3) % 5;
    state.timeLayer = (state.timeLayer + 1) % 24;
    state.stratum = 1 + (manhattanToGoal() % 4);
    updateDimReadout();
    renderGrid();
    logPrint(`move → cell (${state.px},${state.py}) · ${dimsText()}`);
    eg('monitor_move');
    if (state.px === CENTER && state.py === CENTER) {
      beginBattleOverlay();
    }
  }

  function renderGrid() {
    const host = el('agg-grid-host');
    if (!host) return;
    host.innerHTML = '';
    host.className = 'agg-grid-layer';
    for (let y = 0; y < GRID; y++) {
      for (let x = 0; x < GRID; x++) {
        const cell = document.createElement('button');
        cell.type = 'button';
        cell.className = 'agg-cell';
        cell.dataset.x = String(x);
        cell.dataset.y = String(y);
        if (x === CENTER && y === CENTER) cell.classList.add('goal');
        if (x === state.px && y === state.py) cell.classList.add('player');
        cell.title = `Cell ${x},${y}`;
        cell.addEventListener('click', () => {
          const dx = Math.sign(x - state.px);
          const dy = Math.sign(y - state.py);
          if (Math.abs(x - state.px) + Math.abs(y - state.py) === 1) tryMove(dx, dy);
        });
        host.appendChild(cell);
      }
    }
  }

  function beginBattleOverlay() {
    state.phase = 'battle';
    eg('battle_overlay_enter');
    const ov = el('agg-battle-overlay');
    if (ov) ov.hidden = false;
    logPrint('FINAL BATTLE — choose rock, paper, or scissors in the monitor');
  }

  function endBattleOverlay() {
    const ov = el('agg-battle-overlay');
    if (ov) ov.hidden = true;
    state.phase = 'explore';
    state.px = 0;
    state.py = 0;
    state.moves = 0;
    renderGrid();
    updateDimReadout();
  }

  async function runQuickBattle(move) {
    const uid = getUserId();
    try {
      const r = await fetch('/api/battle/quick', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: uid,
          opponent_type: 'ai',
          difficulty: 'balanced',
          player_move: move,
        }),
      });
      const data = await r.json();
      state.battleResult = data;
      const res = data.result || '?';
      const pts = data.points_delta;
      el('agg-battle-status').textContent = `Outcome: ${res} (${pts >= 0 ? '+' : ''}${pts} pts)`;
      logPrint(`battle ${move} → ${res} (${pts} pts)`);
      eg('monitor_battle_complete');
      if (window.AggregatorEngagement && window.AggregatorEngagement.refreshTotalsHud) {
        window.AggregatorEngagement.refreshTotalsHud();
      }
      await refreshProgressReader();
    } catch (e) {
      el('agg-battle-status').textContent = 'Battle request failed';
      logPrint('battle error: ' + (e && e.message));
    }
  }

  async function refreshProgressReader() {
    const uid = getUserId();
    const box = el('agg-progress-reader');
    if (!box) return;
    box.innerHTML = '<p>Loading…</p>';
    let html = '';
    try {
      const [bs, lv, comp, story] = await Promise.all([
        fetch(`/api/battle/stats?user_id=${encodeURIComponent(uid)}`).then((r) => r.json()),
        fetch(`/api/game/hunters/level?user_id=${encodeURIComponent(uid)}`).then((r) => r.json()),
        fetch(`/api/user/compendium/progress?user_id=${encodeURIComponent(uid)}`).then((r) => r.json()),
        fetch(`/api/game-hub/stories/progress?user_id=${encodeURIComponent(uid)}`).then((r) => r.json()),
      ]);
      const st = (bs && bs.stats) || {};
      const li = (lv && lv.level_info) || {};
      const compRead = comp.total_read ?? (comp.pages_read && comp.pages_read.length) ?? 0;
      const compTotal = comp.total_pages ?? 25;
      const storyPct = story.read_percent ?? story.percent ?? 0;
      const storyRead = story.read_count ?? 0;
      html += '<dl>';
      html += `<dt>Battle points</dt><dd>${st.battle_points ?? 0}</dd>`;
      html += `<dt>Wins / losses</dt><dd>${st.wins ?? 0} / ${st.losses ?? 0}</dd>`;
      html += `<dt>Streak</dt><dd>${st.win_streak ?? 0}</dd>`;
      html += `<dt>Hunter level</dt><dd>${li.current_level ?? '—'}</dd>`;
      html += `<dt>Hunter XP</dt><dd>${li.current_xp ?? '—'}</dd>`;
      html += `<dt>Compendium read</dt><dd>${compRead} / ${compTotal}${comp.completion_pct != null ? ` (${comp.completion_pct}%)` : ''}</dd>`;
      html += `<dt>Stories read</dt><dd>${storyRead}${storyPct ? ` (${storyPct}%)` : ''}</dd>`;
      html += `<dt>Monitor moves</dt><dd>${state.moves}</dd>`;
      html += '</dl>';
    } catch (e) {
      html = `<p>Could not load progress (${e.message})</p>`;
    }
    box.innerHTML = html;
  }

  function explorerReply(text) {
    const t = (text || '').toLowerCase();
    if (t.includes('help')) return 'Move on the grid (adjacent cells) toward the golden core. At the center, the final battle unfolds inside this monitor.';
    if (t.includes('battle') || t.includes('fight')) return 'Reach the center cell — your duel uses rock/paper/scissors against the AI.';
    if (t.includes('progress')) return 'Open the progress reader below; I refresh it when you finish a battle.';
    if (t.includes('aggregator') || t.includes('intel'))
      return 'Scroll to Encoded lists & intelligence — links open panels on this page or the API.';
    return 'I map the monitor. Try: help, battle, progress, aggregator.';
  }

  function appendChat(who, text, isUser) {
    const log = el('agg-chat-log');
    if (!log) return;
    const row = document.createElement('div');
    row.className = 'agg-chat-msg' + (isUser ? ' user' : '');
    row.innerHTML = `<span class="who">${who}:</span> ${text.replace(/</g, '&lt;')}`;
    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
  }

  function initChat() {
    const btn = el('agg-chat-send');
    const input = el('agg-chat-input');
    if (!btn || !input) return;
    appendChat('Explorer', 'Coordinates online. Ask about battle or progress.', false);
    btn.addEventListener('click', () => {
      const v = input.value.trim();
      if (!v) return;
      appendChat('You', v, true);
      eg('explorer_chat');
      input.value = '';
      setTimeout(() => appendChat('Explorer', explorerReply(v), false), 280);
    });
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') btn.click();
    });
  }

  function initEncoder() {
    const encBtn = el('agg-encode-btn');
    const decBtn = el('agg-decode-btn');
    const ta = el('agg-encoder-json');
    const out = el('agg-encoder-out');
    const list = el('agg-link-list');

    function defaultLinks() {
      return [
        { label: 'Monitor playfield', href: '#agg-monitor-anchor' },
        { label: 'List encoder', href: '#agg-encoder-block' },
        { label: 'Intelligence API (all)', href: '/api/aggregators/intelligence/all', external: true },
        { label: 'Battle stats (JSON)', href: '/api/battle/stats', external: true },
      ];
    }

    if (ta && !ta.value.trim()) {
      fetch('/api/aggregators/hub/links')
        .then(function (r) {
          return r.json();
        })
        .then(function (d) {
          if (d.success && d.panels && d.panels.length) {
            ta.value = JSON.stringify(
              d.panels.map(function (p) {
                return { label: p.label, href: p.href, external: !!p.external };
              }),
              null,
              2
            );
          } else {
            ta.value = JSON.stringify(defaultLinks(), null, 2);
          }
        })
        .catch(function () {
          ta.value = JSON.stringify(defaultLinks(), null, 2);
        });
    }

    if (encBtn) {
      encBtn.addEventListener('click', () => {
        try {
          const links = JSON.parse(ta.value || '[]');
          const payload = btoa(unescape(encodeURIComponent(JSON.stringify(links))));
          out.value = payload;
          const share = `${location.origin}${location.pathname}#l=${payload}`;
          el('agg-share-url').textContent = share;
          logPrint('encoded link list (' + links.length + ' items)');
          eg('link_encode');
        } catch (e) {
          out.value = 'Error: ' + e.message;
        }
      });
    }

    if (decBtn) {
      decBtn.addEventListener('click', () => {
        try {
          const raw = out.value.trim();
          const json = decodeURIComponent(escape(atob(raw)));
          const links = JSON.parse(json);
          renderLinkList(links);
          eg('link_decode');
        } catch (e) {
          list.innerHTML = '<p style="color:#f88">Decode error: ' + e.message + '</p>';
        }
      });
    }

    function renderLinkList(links) {
      list.innerHTML = '';
      (links || []).forEach((item) => {
        const a = document.createElement('a');
        a.href = item.href || '#';
        if (item.external) a.target = '_blank';
        a.rel = 'noopener noreferrer';
        a.textContent = item.label || item.href;
        list.appendChild(a);
      });
    }

    const hash = location.hash || '';
    if (hash.startsWith('#l=')) {
      try {
        const payload = hash.slice(3);
        const json = decodeURIComponent(escape(atob(payload)));
        const links = JSON.parse(json);
        ta.value = JSON.stringify(links, null, 2);
        out.value = payload;
        renderLinkList(links);
        eg('link_decode');
      } catch (e) {
        console.warn('hash list decode', e);
      }
    }
  }

  function initKeys() {
    document.addEventListener('keydown', (e) => {
      const t = e.target && e.target.tagName;
      if (t === 'INPUT' || t === 'TEXTAREA') return;
      if (state.phase === 'battle') return;
      if (e.key === 'ArrowUp' || e.key === 'w' || e.key === 'W') tryMove(0, -1);
      else if (e.key === 'ArrowDown' || e.key === 's' || e.key === 'S') tryMove(0, 1);
      else if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') tryMove(-1, 0);
      else if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') tryMove(1, 0);
    });
  }

  function initUserStrip() {
    const uid = getUserId();
    logPrint(`session user_id=${uid}`);
    const strip = el('agg-user-strip-meta');
    if (strip) strip.textContent = `user_id: ${uid}`;
  }

  document.addEventListener('DOMContentLoaded', () => {
    initUserStrip();
    updateDimReadout();
    renderGrid();
    refreshProgressReader();
    initChat();
    initEncoder();
    initKeys();

    el('agg-rps-rock') &&
      el('agg-rps-rock').addEventListener('click', () => runQuickBattle('rock'));
    el('agg-rps-paper') &&
      el('agg-rps-paper').addEventListener('click', () => runQuickBattle('paper'));
    el('agg-rps-scissors') &&
      el('agg-rps-scissors').addEventListener('click', () => runQuickBattle('scissors'));
    el('agg-battle-dismiss') &&
      el('agg-battle-dismiss').addEventListener('click', () => endBattleOverlay());

    setInterval(refreshProgressReader, 45000);
    window.__aggRefreshProgress = refreshProgressReader;
  });
})();
