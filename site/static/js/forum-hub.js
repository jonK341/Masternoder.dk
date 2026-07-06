/**
 * MasterNoder unified Forum hub — upgraded client.
 */
(function () {
  'use strict';

  const API = window.location.origin;
  const uid = () => localStorage.getItem('user_id') || 'default_user';

  const TAB_IDS = [
    'home', 'discussions', 'news', 'articles', 'chat', 'podcast', 'rulebooks',
    'paragraphs', 'docs', 'support', 'social', 'wikipedia', 'search',
  ];
  const REACTIONS = [
    { key: 'like', icon: '👍' },
    { key: 'helpful', icon: '🙌' },
    { key: 'insightful', icon: '💡' },
    { key: 'celebrate', icon: '🎉' },
  ];

  let topicsCache = [];
  let selectedTopicId = '';
  let selectedSubforumId = '';
  let openThreadId = '';
  let currentSort = 'new';
  let currentTag = '';
  let currentFilter = '';
  let threadOffset = 0;
  const PAGE = 12;

  // ---- Multi-language grammar assistant ----
  let LANGS = [];
  async function ensureLangs() {
    if (LANGS.length) return LANGS;
    try {
      const d = await api('/api/forum/languages');
      LANGS = d.languages || [];
    } catch (_) { LANGS = []; }
    return LANGS;
  }
  function savedLang() { return localStorage.getItem('forum_lang') || 'auto'; }

  async function attachGrammar(textarea) {
    if (!textarea || textarea.dataset.grammarBound) return;
    textarea.dataset.grammarBound = '1';
    await ensureLangs();
    const bar = document.createElement('div');
    bar.className = 'forum-grammar-bar';
    const opts = LANGS.map((l) => `<option value="${l.code}">${l.flag} ${l.native}</option>`).join('');
    bar.innerHTML = `
      <label class="grammar-lang"><span class="sr-only">Language</span>
        <select class="grammar-lang-select" aria-label="Writing language">${opts}</select>
      </label>
      <button type="button" class="forum-btn secondary sm grammar-check">✓ Grammar</button>
      <span class="grammar-status meta"></span>
      <div class="grammar-suggestion" hidden></div>`;
    textarea.insertAdjacentElement('afterend', bar);
    const sel = bar.querySelector('.grammar-lang-select');
    sel.value = savedLang();
    sel.addEventListener('change', () => localStorage.setItem('forum_lang', sel.value));
    const status = bar.querySelector('.grammar-status');
    const sugg = bar.querySelector('.grammar-suggestion');
    bar.querySelector('.grammar-check').addEventListener('click', async () => {
      const text = (textarea.value || '').trim();
      if (!text) { toast('Write something first', 'err'); return; }
      status.textContent = 'Checking…';
      sugg.hidden = true;
      const d = await api('/api/forum/grammar', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, language: sel.value }),
      });
      if (!d.success) { status.textContent = d.error || 'Failed'; return; }
      status.textContent = `${d.language_name}${d.engine === 'fallback' ? ' · basic' : ' · AI'}`;
      if (!d.changed) { sugg.hidden = false; sugg.innerHTML = `<p class="meta">${esc(d.note)} ✅</p>`; return; }
      sugg.hidden = false;
      sugg.innerHTML = `
        <p class="meta">${esc(d.note)} (${esc(d.language_name)})</p>
        <div class="grammar-corrected">${esc(d.corrected)}</div>
        <div class="grammar-actions">
          <button type="button" class="forum-btn sm grammar-apply">Apply</button>
          <button type="button" class="forum-btn secondary sm grammar-dismiss">Dismiss</button>
        </div>`;
      sugg.querySelector('.grammar-apply').addEventListener('click', () => {
        textarea.value = d.corrected;
        sugg.hidden = true;
        status.textContent = 'Applied ✓';
        toast('Grammar applied', 'ok');
      });
      sugg.querySelector('.grammar-dismiss').addEventListener('click', () => { sugg.hidden = true; });
    });
  }

  function $(sel) { return document.querySelector(sel); }
  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function mdBasic(md) {
    return esc(md)
      .replace(/^### (.+)$/gm, '<h4>$1</h4>')
      .replace(/^## (.+)$/gm, '<h3>$1</h3>')
      .replace(/^# (.+)$/gm, '<h2>$1</h2>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/`(.+?)`/g, '<code>$1</code>')
      .replace(/\[(.+?)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
      .replace(/\n/g, '<br>');
  }

  function timeAgo(iso) {
    if (!iso) return '';
    const then = new Date(iso).getTime();
    if (isNaN(then)) return esc(iso);
    const s = Math.max(1, Math.floor((Date.now() - then) / 1000));
    const units = [[31536000, 'y'], [2592000, 'mo'], [604800, 'w'], [86400, 'd'], [3600, 'h'], [60, 'm']];
    for (const [sec, label] of units) {
      if (s >= sec) return Math.floor(s / sec) + label + ' ago';
    }
    return s + 's ago';
  }

  function sonic(name) { try { if (window.SonicEngine) window.SonicEngine.cue(name); } catch (_) {} }

  function toast(msg, kind) {
    const el = $('#forum-toast');
    if (!el) return;
    el.textContent = msg;
    el.className = 'forum-toast show' + (kind ? ' ' + kind : '');
    clearTimeout(el._t);
    el._t = setTimeout(() => { el.className = 'forum-toast'; }, 2600);
  }

  function skeleton(n) {
    let h = '';
    for (let i = 0; i < (n || 3); i++) h += '<div class="forum-card forum-skel"><div class="skel-line w60"></div><div class="skel-line w90"></div><div class="skel-line w40"></div></div>';
    return h;
  }

  async function api(path, opts) {
    const r = await fetch(API + path, opts);
    const ct = r.headers.get('content-type') || '';
    if (ct.includes('application/json')) return r.json();
    return { success: r.ok, _text: await r.text() };
  }

  function badges(t) {
    let b = '';
    if (t.pinned) b += '<span class="forum-badge pin">📌 Pinned</span>';
    if (t.solved) b += '<span class="forum-badge solved">✅ Solved</span>';
    if (t.locked) b += '<span class="forum-badge lock">🔒 Locked</span>';
    return b;
  }

  function tagChips(tags) {
    return (tags || []).map((tg) =>
      `<button type="button" class="forum-tag tag-filter" data-tag="${esc(tg)}">#${esc(tg)}</button>`
    ).join('');
  }

  // Normalize for comparison: lowercase, collapse whitespace, drop trailing punctuation.
  function _normText(s) {
    return String(s || '').toLowerCase().replace(/\s+/g, ' ').replace(/[?!.…]+$/, '').trim();
  }

  // Only render a preview paragraph when it adds information beyond the title.
  // Seeded threads often set summary/excerpt ≈ title, which would otherwise
  // show the same text twice (title + preview).
  function previewP(title, text, limit) {
    const body = String(text || '').trim();
    if (!body) return '';
    const nt = _normText(title);
    const nb = _normText(body);
    if (!nb || nb === nt || nb.startsWith(nt) || nt.startsWith(nb)) return '';
    return `<p>${esc(body.slice(0, limit || 180))}</p>`;
  }

  function excerptHtml(t) {
    return previewP(t.title, t.excerpt);
  }

  function threadCard(t) {
    const net = (t.net_votes != null) ? t.net_votes : (t.votes || 0);
    const rt = t.reading_time_min ? ` · ⏱ ${esc(t.reading_time_min)}m` : '';
    return `<div class="forum-card thread-card${t.solved ? ' is-solved' : ''}" data-id="${esc(t.id)}" tabindex="0" role="button" aria-label="Open thread ${esc(t.title)}">
      <div class="thread-stats">
        <span class="ts-vote${net < 0 ? ' neg' : ''}" title="Net votes">⬆ ${esc(net)}</span>
        <span class="ts-reply" title="Replies">💬 ${esc(t.reply_count || 0)}</span>
        <span class="ts-view" title="Views">👁 ${esc(t.views || 0)}</span>
      </div>
      <div class="thread-body">
        <div class="meta">${esc(t.theme_title)} → ${esc(t.subforum_title)} · ${timeAgo(t.updated_at)}${rt}</div>
        <h3>${badges(t)} ${esc(t.title)}</h3>
        ${excerptHtml(t)}
        <div class="thread-foot">
          <span class="meta">${esc(t.avatar || '')} ${esc(t.author_name || '')}</span>
          <span class="forum-tag-row">${tagChips(t.tags)}</span>
        </div>
      </div>
    </div>`;
  }

  function setTab(tabId) {
    const parts = (location.hash || '#home').replace(/^#/, '').split('/');
    const base = parts[0] || 'home';
    const id = TAB_IDS.includes(tabId) ? tabId : (TAB_IDS.includes(base) ? base : 'home');
    if (parts[1] && id === 'discussions') openThreadId = parts[1];
    document.querySelectorAll('.forum-tab').forEach((btn) => {
      const on = btn.dataset.tab === id;
      btn.classList.toggle('active', on);
      btn.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    document.querySelectorAll('.forum-panel').forEach((p) => {
      p.classList.toggle('active', p.id === 'panel-' + id);
    });
    if (!location.hash.startsWith('#' + id)) {
      history.replaceState(null, '', '#' + id + (openThreadId && id === 'discussions' ? '/' + openThreadId : ''));
    }
    loadPanel(id);
  }

  async function loadPanel(tab) {
    switch (tab) {
      case 'home': return loadHome();
      case 'discussions': return loadDiscussions();
      case 'news': return loadNews();
      case 'articles': return loadArticles();
      case 'chat': return loadChat();
      case 'podcast': return loadPodcast();
      case 'rulebooks': return loadRulebooks();
      case 'paragraphs': return loadParagraphs();
      case 'docs': return loadDocs();
      case 'support': return loadSupport();
      case 'social': return loadSocial();
      case 'search': return; // triggered by search
      case 'wikipedia': return;
      default: return loadHome();
    }
  }

  // ---- Home: feed + sidebar (trending, leaderboard, tags) ----
  async function loadHome() {
    loadFeed();
    loadStats();
    loadTrending();
    loadLeaderboard();
    loadTagCloud();
  }

  async function loadStats() {
    const el = $('#stats-bar');
    if (!el) return;
    const d = await api('/api/forum/stats');
    if (!d.success) return;
    const s = d.stats || {};
    el.innerHTML = [
      ['💬', s.threads, 'threads'],
      ['✉️', s.posts, 'posts'],
      ['✅', s.solved, 'solved'],
      ['👥', s.contributors, 'members'],
      ['🏷️', s.tags, 'tags'],
    ].map(([i, n, l]) => `<span class="stat-pill"><b>${esc(n ?? 0)}</b> ${i} ${l}</span>`).join('');
  }

  async function loadTrending() {
    const el = $('#trending-list');
    if (!el) return;
    const d = await api('/api/forum/trending?limit=5');
    el.innerHTML = (d.threads || []).map((t) =>
      `<a href="#discussions/${esc(t.id)}" class="side-link">🔥 ${esc(t.title)}<span class="meta"> · ${esc(t.votes || 0)}▲</span></a>`
    ).join('') || '<div class="meta">No trending threads yet.</div>';
  }

  async function loadLeaderboard() {
    const el = $('#leaderboard-list');
    if (!el) return;
    const d = await api('/api/forum/leaderboard?limit=5');
    el.innerHTML = (d.leaderboard || []).map((m, i) =>
      `<div class="lb-row"><span>${['🥇', '🥈', '🥉'][i] || (i + 1 + '.')} ${esc(m.avatar || '')} ${esc(m.author_name)}</span><b>${esc(m.reputation)}</b></div>`
    ).join('') || '<div class="meta">No members yet.</div>';
  }

  async function loadTagCloud() {
    const el = $('#tag-cloud');
    if (!el) return;
    const d = await api('/api/forum/tags');
    el.innerHTML = (d.tags || []).slice(0, 16).map((t) =>
      `<button type="button" class="forum-tag tag-jump" data-tag="${esc(t.tag)}">#${esc(t.tag)} <span class="meta">${esc(t.count)}</span></button>`
    ).join('') || '<div class="meta">No tags yet.</div>';
    el.querySelectorAll('.tag-jump').forEach((b) => b.addEventListener('click', () => {
      currentTag = b.dataset.tag;
      setTab('discussions');
    }));
  }

  async function loadFeed() {
    const el = $('#feed-list');
    if (!el) return;
    el.innerHTML = skeleton(4);
    const data = await api('/api/forum/feed?limit=30');
    if (!data.success) {
      el.innerHTML = '<div class="forum-status">Could not load feed.</div>';
      return;
    }
    el.innerHTML = (data.feed || []).map((item) => `
      <div class="forum-card feed-item feed-${esc(item.type)}">
        <div class="meta"><span class="feed-tag">${esc(item.type)}</span> · ${timeAgo(item.created_at)}${item.author_name ? ' · ' + esc(item.author_name) : ''}</div>
        <h3>${esc(item.title)}</h3>
        ${previewP(item.title, item.summary)}
        ${item.href ? `<a href="${esc(item.href)}" class="forum-btn secondary feed-open">Open</a>` : ''}
      </div>
    `).join('') || '<div class="forum-status">No posts yet. Write an article!</div>';
  }

  async function loadNews() {
    const el = $('#news-list');
    if (!el) return;
    el.innerHTML = skeleton(3);
    const data = await api('/api/forum/news?limit=40');
    el.innerHTML = (data.news || []).map((n) => `
      <div class="forum-card">
        <div class="meta">${timeAgo(n.date) || esc(n.date)} · ${esc(n.channel || n.category || 'platform')}</div>
        <h3>${n.href ? `<a href="${esc(n.href)}" style="color:inherit">${esc(n.title)}</a>` : esc(n.title)}</h3>
        ${previewP(n.title, n.summary)}
      </div>
    `).join('') || '<div class="forum-status">No news items.</div>';
  }

  async function loadArticles() {
    const el = $('#articles-list');
    if (!el) return;
    el.innerHTML = skeleton(3);
    const data = await api('/api/forum/articles?limit=50');
    el.innerHTML = (data.articles || []).map((a) => `
      <div class="forum-card" data-article-id="${esc(a.id)}">
        <div class="meta">${esc(a.author_name)} · ${timeAgo(a.created_at)} · ${esc(a.category)}</div>
        <h3>${esc(a.title)}</h3>
        <p>${esc(a.summary || '')}</p>
        <button type="button" class="forum-btn secondary read-article" data-id="${esc(a.id)}">Read</button>
      </div>
    `).join('') || '<div class="forum-status">No articles yet.</div>';
    el.querySelectorAll('.read-article').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const d = await api('/api/forum/articles/' + btn.dataset.id);
        if (d.article) {
          $('#article-reader').innerHTML = `
            <div class="forum-card">
              <h3>${esc(d.article.title)}</h3>
              <div class="meta">by ${esc(d.article.author_name)}</div>
              <div class="article-body">${mdBasic(d.article.body_markdown || '')}</div>
            </div>`;
          $('#article-reader').scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });
  }

  async function submitArticle(ev) {
    ev.preventDefault();
    const title = $('#article-title').value.trim();
    const body = $('#article-body').value.trim();
    const status = $('#article-status');
    status.textContent = 'Publishing…';
    const data = await api('/api/forum/articles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: uid(), title, body, author_name: uid() }),
    });
    status.textContent = data.success ? 'Published!' : (data.error || 'Failed');
    if (data.success) {
      toast('Article published', 'ok');
      $('#article-title').value = '';
      $('#article-body').value = '';
      loadArticles();
      loadFeed();
    } else {
      toast(data.error || 'Publish failed', 'err');
    }
  }

  async function loadChat() {
    const box = $('#chat-messages');
    if (!box) return;
    const data = await api('/api/social/chat/messages?limit=40');
    const msgs = data.messages || data.chat_messages || [];
    box.innerHTML = msgs.map((m) => `
      <div class="forum-chat-msg"><span class="who">${esc(m.user_id || m.from || 'user')}:</span> ${esc(m.text || m.message || '')}</div>
    `).join('') || '<div class="forum-status">No messages yet. Say hello!</div>';
    box.scrollTop = box.scrollHeight;
  }

  async function sendChat() {
    const input = $('#chat-input');
    const text = (input.value || '').trim();
    if (!text) return;
    await api('/api/social/chat/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: uid(), text, message: text }),
    });
    input.value = '';
    loadChat();
  }

  async function sendAiChat() {
    const input = $('#ai-chat-input');
    const text = (input.value || '').trim();
    const out = $('#ai-chat-reply');
    if (!text) return;
    out.textContent = 'Thinking…';
    const data = await api('/api/chat/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: uid(), message: text }),
    });
    out.textContent = data.reply || data.response || data.error || JSON.stringify(data);
    input.value = '';
  }

  async function loadPodcast() {
    const el = $('#podcast-panel-body');
    if (!el) return;
    el.innerHTML = skeleton(2);
    try {
      const ch = await api('/api/podcast/channels');
      const episodes = await api('/api/podcast/episodes?limit=12');
      let html = '<p><a href="/podcast/" class="forum-btn secondary" style="text-decoration:none">Open full Podcast player →</a></p>';
      if (ch.channels) {
        html += '<div class="forum-grid-2">' + ch.channels.slice(0, 6).map((c) => `
          <div class="forum-card"><h3>${esc(c.name || c.id)}</h3><p>${esc(c.description || '')}</p></div>
        `).join('') + '</div>';
      }
      if (episodes.episodes) {
        html += episodes.episodes.map((e) => `
          <div class="forum-card"><h3>${esc(e.title)}</h3><p>${esc(e.description || '')}</p></div>
        `).join('');
      }
      el.innerHTML = html;
    } catch (e) {
      el.innerHTML = '<div class="forum-status">Podcast API unavailable. <a href="/podcast/">Try full player</a></div>';
    }
  }

  async function loadRulebooks() {
    const el = $('#rulebooks-list');
    if (!el) return;
    const data = await api('/api/forum/rulebooks/index');
    const versions = (data.index && data.index.versions) || data.index || [];
    const list = Array.isArray(versions) ? versions : Object.values(versions);
    el.innerHTML = list.map((rb) => {
      const v = rb.version || rb.id || rb;
      const label = rb.title || rb.name || String(v);
      const href = typeof v === 'string' ? `/compendium/rulebook-${v.replace(/^v/, 'v')}` : '/compendium/';
      return `<div class="forum-card"><h3><a href="${esc(href)}" style="color:#00ff88">${esc(label)}</a></h3><p>${esc(rb.summary || rb.description || '')}</p></div>`;
    }).join('') || `<p><a href="/compendium/?calm=1" class="forum-btn secondary" style="text-decoration:none">Open Compendium library →</a></p>`;
  }

  async function loadParagraphs() {
    const el = $('#paragraphs-list');
    if (!el) return;
    const data = await api('/api/forum/paragraphs');
    el.innerHTML = (data.paragraphs || []).map((p) => `
      <div class="forum-card"><h3>${esc(p.number)} ${esc(p.title)}</h3><p>${esc(p.body)}</p></div>
    `).join('');
  }

  async function loadDocs() {
    const el = $('#docs-list');
    if (!el) return;
    const data = await api('/api/forum/docs');
    el.innerHTML = (data.docs || []).map((d) => `
      <div class="forum-card"><h3><a href="${esc(d.href)}" style="color:#00d4ff">${esc(d.title)}</a></h3><p>Source: ${esc(d.source)}</p></div>
    `).join('');
  }

  async function loadSupport() {
    const el = $('#support-panel-body');
    if (!el) return;
    el.innerHTML = `
      <div class="forum-card">
        <h3>Agent Support</h3>
        <p>Tickets, API keys, and troubleshooting tools.</p>
        <a href="/agent_support/" class="forum-btn secondary" style="text-decoration:none;margin-top:8px;display:inline-block">Open Agent Support →</a>
      </div>
      <div class="forum-card">
        <h3>FAQ</h3>
        <p id="faq-list">Loading…</p>
      </div>`;
    try {
      const faq = await api('/api/support/faq/list');
      const items = faq.items || faq.faqs || [];
      $('#faq-list').innerHTML = items.slice(0, 8).map((f) => `<strong>${esc(f.q || f.question)}</strong><br>${esc(f.a || f.answer)}<br><br>`).join('') || 'No FAQ loaded.';
    } catch (e) {
      $('#faq-list').textContent = 'FAQ API not available.';
    }
  }

  function shareUrlValue() {
    const v = ($('#share-url') || {}).value;
    return (v && v.trim()) || (location.origin + '/forum/');
  }
  function shareTextValue() {
    const v = ($('#share-text') || {}).value;
    return (v && v.trim()) || 'MasterNoder — AI video, game, battle & community forum';
  }

  async function loadSocial() {
    const el = $('#social-networks');
    if (!el) return;
    el.innerHTML = skeleton(2);
    const data = await api('/api/forum/social-networks');
    const nets = data.networks || [];
    const cats = data.categories || [{ id: '', label: 'Networks' }];
    if ($('#share-text') && !$('#share-text').value) $('#share-text').value = data.default_share_text || '';

    const groups = {};
    nets.forEach((n) => { const c = n.category || 'other'; (groups[c] = groups[c] || []).push(n); });

    el.innerHTML = cats.filter((c) => groups[c.id] && groups[c.id].length).map((c) => `
      <div class="forum-social-group">
        <h3>${esc(c.label)}</h3>
        <div class="forum-social-row">
          ${groups[c.id].map((n) => `
            <button type="button" class="forum-social-btn share-net" data-net="${esc(n.id)}" data-type="${esc(n.type || 'share')}" style="border-color:${esc(n.color || '#666')}" title="${esc(n.type === 'follow' ? 'Open ' + n.name : 'Share to ' + n.name)}">
              <span class="social-ic" aria-hidden="true">${esc(n.icon)}</span> ${esc(n.name)}${n.type === 'follow' ? ' <span class="social-follow">↗</span>' : ''}
            </button>`).join('')}
        </div>
      </div>`).join('') || '<div class="forum-status">No networks configured.</div>';

    el.querySelectorAll('.share-net').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const d = await api('/api/forum/share', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ network: btn.dataset.net, url: shareUrlValue(), text: shareTextValue() }),
        });
        if (d.share_url) { window.open(d.share_url, '_blank', 'noopener'); sonic('navigate'); }
        else toast(d.error || 'Could not build share link', 'err');
      });
    });
  }

  function wireShareControls() {
    const nativeBtn = $('#native-share');
    if (nativeBtn && navigator.share) {
      nativeBtn.hidden = false;
      nativeBtn.addEventListener('click', async () => {
        try {
          await navigator.share({ title: 'MasterNoder', text: shareTextValue(), url: shareUrlValue() });
          sonic('success');
        } catch (_) {}
      });
    }
    $('#copy-share-link')?.addEventListener('click', () => {
      const url = shareUrlValue();
      (navigator.clipboard?.writeText(url) || Promise.reject()).then(() => toast('Link copied', 'ok')).catch(() => toast(url));
    });
  }

  async function searchWiki() {
    const q = ($('#wiki-query') || {}).value.trim();
    const el = $('#wiki-result');
    if (!q || !el) return;
    el.innerHTML = '<div class="forum-status">Searching Wikipedia…</div>';
    const data = await api('/api/forum/wikipedia?title=' + encodeURIComponent(q));
    if (!data.success) {
      el.innerHTML = '<div class="forum-status">' + esc(data.error || 'Not found') + '</div>';
      return;
    }
    el.innerHTML = `<div class="forum-card forum-wiki-result">
      ${data.thumbnail ? `<img src="${esc(data.thumbnail)}" alt="">` : ''}
      <h3>${esc(data.title)}</h3>
      <p>${esc(data.extract || data.description || '')}</p>
      ${data.content_urls && data.content_urls.desktop ? `<a href="${esc(data.content_urls.desktop.page)}" target="_blank" rel="noopener" class="forum-btn secondary" style="text-decoration:none">Read on Wikipedia →</a>` : ''}
    </div>`;
  }

  // ---- Global search ----
  async function globalSearch() {
    const q = ($('#global-search') || {}).value.trim();
    if (!q) return;
    setTab('search');
    const el = $('#search-results');
    el.innerHTML = skeleton(4);
    const d = await api('/api/forum/search?q=' + encodeURIComponent(q));
    if (!d.success) { el.innerHTML = '<div class="forum-status">No results.</div>'; return; }
    let html = `<p class="meta">${d.counts.threads} threads · ${d.counts.articles} articles for "<b>${esc(q)}</b>"</p>`;
    html += (d.threads || []).map(threadCard).join('');
    html += (d.articles || []).map((a) => `
      <div class="forum-card"><div class="meta">article · ${esc(a.author_name)}</div><h3>${esc(a.title)}</h3><p>${esc(a.summary || '')}</p></div>
    `).join('');
    el.innerHTML = html || '<div class="forum-status">No results.</div>';
    bindThreadCards(el);
  }

  // ---- Discussions ----
  async function loadTopicsNav() {
    const nav = $('#topics-nav');
    const topicSel = $('#thread-topic');
    if (!nav) return;
    const data = await api('/api/forum/topics');
    topicsCache = data.themes || [];
    nav.innerHTML = topicsCache.map((th) => `
      <div class="forum-card topic-card${selectedTopicId === th.id ? ' selected' : ''}" data-topic="${esc(th.id)}" role="button" tabindex="0">
        <h3>${esc(th.icon || '')} ${esc(th.title)}</h3>
        <p>${esc(th.description || '')}</p>
        <p class="meta">${(th.subforums || []).map((s) => esc(s.title)).join(' · ')}</p>
      </div>
    `).join('') + `<div class="forum-card topic-card${!selectedTopicId ? ' selected' : ''}" data-topic="" role="button" tabindex="0"><h3>🗂️ All themes</h3><p>Show threads from every theme.</p></div>`;
    nav.querySelectorAll('.topic-card').forEach((card) => {
      const act = () => {
        selectedTopicId = card.dataset.topic;
        threadOffset = 0;
        loadThreadsList();
        fillTopicSelects();
        nav.querySelectorAll('.topic-card').forEach((c) => c.classList.toggle('selected', c === card));
      };
      card.addEventListener('click', act);
      card.addEventListener('keydown', (e) => { if (e.key === 'Enter') act(); });
    });
    if (topicSel) {
      topicSel.innerHTML = '<option value="">Theme…</option>' + topicsCache.map((th) =>
        `<option value="${esc(th.id)}">${esc(th.title)}</option>`
      ).join('');
      topicSel.onchange = () => { selectedTopicId = topicSel.value; fillSubforumSelect(); };
    }
    fillTopicSelects();
  }

  function fillTopicSelects() {
    const topicSel = $('#thread-topic');
    if (topicSel && selectedTopicId) topicSel.value = selectedTopicId;
    fillSubforumSelect();
  }

  function fillSubforumSelect() {
    const subSel = $('#thread-subforum');
    const th = topicsCache.find((t) => t.id === (selectedTopicId || $('#thread-topic')?.value));
    if (!subSel) return;
    const subs = th?.subforums || [];
    subSel.innerHTML = '<option value="">Sub-forum…</option>' + subs.map((s) =>
      `<option value="${esc(s.id)}">${esc(s.title)}</option>`
    ).join('');
  }

  function bindThreadCards(scope) {
    (scope || document).querySelectorAll('.thread-card').forEach((card) => {
      card.addEventListener('click', (e) => {
        if (e.target.closest('.tag-filter')) return;
        openThread(card.dataset.id);
      });
      card.addEventListener('keydown', (e) => { if (e.key === 'Enter') openThread(card.dataset.id); });
    });
    (scope || document).querySelectorAll('.tag-filter').forEach((b) => {
      b.addEventListener('click', (e) => {
        e.stopPropagation();
        currentTag = b.dataset.tag;
        threadOffset = 0;
        updateActiveTagFilter();
        loadThreadsList();
      });
    });
  }

  function updateActiveTagFilter() {
    const el = $('#active-tag-filter');
    if (!el) return;
    if (currentTag) {
      el.hidden = false;
      el.innerHTML = `#${esc(currentTag)} <button type="button" id="clear-tag" aria-label="Clear tag filter">✕</button>`;
      $('#clear-tag').addEventListener('click', () => { currentTag = ''; threadOffset = 0; updateActiveTagFilter(); loadThreadsList(); });
    } else {
      el.hidden = true;
      el.innerHTML = '';
    }
  }

  async function loadThreadsList(append) {
    const el = $('#threads-list');
    if (!el) return;
    if (!append) { el.innerHTML = skeleton(4); threadOffset = 0; }
    let path = `/api/forum/threads?limit=${PAGE}&offset=${threadOffset}&sort=${encodeURIComponent(currentSort)}`;
    if (selectedTopicId) path += '&topic_id=' + encodeURIComponent(selectedTopicId);
    if (selectedSubforumId) path += '&subforum_id=' + encodeURIComponent(selectedSubforumId);
    if (currentTag) path += '&tag=' + encodeURIComponent(currentTag);
    if (currentFilter) path += '&q=' + encodeURIComponent(currentFilter);
    const data = await api(path);
    const cards = (data.threads || []).map(threadCard).join('');
    if (append) el.insertAdjacentHTML('beforeend', cards);
    else el.innerHTML = cards || '<div class="forum-status">No threads yet — be the first!</div>';
    bindThreadCards(el);
    const more = $('#threads-loadmore');
    if (more) more.hidden = !data.has_more;
  }

  async function openThread(id) {
    openThreadId = id;
    history.replaceState(null, '', '#discussions/' + id);
    const view = $('#thread-view');
    if (!view) return;
    view.innerHTML = skeleton(2);
    view.scrollIntoView({ behavior: 'smooth', block: 'start' });
    const data = await api('/api/forum/threads/' + encodeURIComponent(id));
    if (!data.thread) {
      view.innerHTML = '<div class="forum-status">Thread not found.</div>';
      return;
    }
    const t = data.thread;
    const related = data.related || [];
    const net = (t.net_votes != null) ? t.net_votes : (t.votes || 0);
    const following = !!data.following;
    const bookmarked = !!data.bookmarked;
    view.innerHTML = `
      <div class="forum-card thread-head">
        <button type="button" id="thread-close" class="forum-btn secondary sm">← Back</button>
        <h3>${badges(t)} ${esc(t.title)}</h3>
        <div class="meta">${esc(t.theme_title)} → ${esc(t.subforum_title)} · 👁 ${esc(t.views)} views · ⏱ ${esc(t.reading_time_min || 1)} min read</div>
        <div class="forum-tag-row">${tagChips(t.tags)}</div>
        <div class="thread-actions">
          <div class="vote-stack" role="group" aria-label="Vote on thread">
            <button type="button" id="vote-up" class="vote-arrow" aria-label="Upvote" aria-pressed="false">▲</button>
            <span id="vote-net" class="vote-net">${esc(net)}</span>
            <button type="button" id="vote-down" class="vote-arrow" aria-label="Downvote" aria-pressed="false">▼</button>
          </div>
          <button type="button" id="bookmark-btn" class="forum-btn secondary sm" aria-pressed="${bookmarked}">${bookmarked ? '🔖 Saved' : '🔖 Save'}</button>
          <button type="button" id="follow-btn" class="forum-btn secondary sm" aria-pressed="${following}">${following ? '🔔 Following' : '🔔 Follow'}</button>
          <button type="button" id="copy-link" class="forum-btn secondary sm">🔗 Copy link</button>
          <button type="button" id="report-btn" class="forum-btn secondary sm">🚩 Report</button>
        </div>
      </div>
      ${pollCard(data.poll)}
      ${(t.posts || []).map((p, i) => postCard(t, p, i)).join('')}
      ${t.locked ? '<div class="forum-status">🔒 This thread is locked.</div>' : `
      <div class="forum-compose">
        <textarea id="reply-body" placeholder="Write a reply… (Markdown, @mentions & #tags supported)"></textarea>
        <button type="button" id="reply-submit" class="forum-btn secondary">Reply</button>
      </div>`}
      ${related.length ? `<div class="forum-related"><h4>Related threads</h4>${related.map((r) => `<a href="#discussions/${esc(r.id)}" class="side-link">${esc(r.title)}</a>`).join('')}</div>` : ''}
    `;
    bindThreadView(id, t, { following, bookmarked });
  }

  function pollCard(poll) {
    if (!poll) return '';
    const opts = (poll.options || []).map((o) => `
      <button type="button" class="poll-option${poll.your_vote === o.id ? ' voted' : ''}" data-opt="${esc(o.id)}" ${poll.closed ? 'disabled' : ''}>
        <span class="poll-bar" style="width:${esc(o.pct || 0)}%"></span>
        <span class="poll-label">${esc(o.text)}</span>
        <span class="poll-pct">${esc(o.pct || 0)}% · ${esc(o.votes || 0)}</span>
      </button>`).join('');
    return `<div class="forum-card poll-card" id="poll-card">
      <div class="poll-q">📊 ${esc(poll.question || 'Poll')}</div>
      <div class="poll-options">${opts}</div>
      <div class="meta">${esc(poll.total_votes || 0)} votes${poll.closed ? ' · closed' : ''}</div>
    </div>`;
  }

  function postCard(t, p, i) {
    const accepted = p.is_accepted ? ' accepted' : '';
    const reactBtns = REACTIONS.map((r) =>
      `<button type="button" class="react-btn" data-post="${esc(p.id)}" data-react="${r.key}">${r.icon} <span>${esc((p.reactions || {})[r.key] || 0)}</span></button>`
    ).join('');
    const acceptBtn = (i > 0 && t.kind === 'question')
      ? `<button type="button" class="forum-btn secondary sm accept-btn" data-post="${esc(p.id)}">${p.is_accepted ? '✅ Accepted' : 'Accept answer'}</button>`
      : '';
    return `<div class="forum-card post-card${accepted}" id="post-${esc(p.id)}">
      <div class="meta">${esc(p.avatar || '')} <strong>${esc(p.author_name)}</strong> · <span class="post-kind">${esc(p.kind)}</span> · ${timeAgo(p.created_at)}${p.edited_at ? ' · edited' : ''}${p.is_accepted ? ' · <span class="accepted-tag">✅ accepted answer</span>' : ''}</div>
      <div class="post-body">${mdBasic(p.body)}</div>
      <div class="post-foot">
        <span class="react-row">${reactBtns}</span>
        ${acceptBtn}
      </div>
    </div>`;
  }

  function bindThreadView(id, t, state) {
    state = state || {};
    let voteState = 0;
    if (!t.locked) attachGrammar($('#reply-body'));
    $('#thread-close')?.addEventListener('click', () => {
      openThreadId = '';
      $('#thread-view').innerHTML = '';
      history.replaceState(null, '', '#discussions');
    });
    async function castVote(direction) {
      const d = await api('/api/forum/threads/' + id + '/vote', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: uid(), direction }),
      });
      if (d.success) {
        voteState = d.vote_state != null ? d.vote_state : (d.voted ? 1 : 0);
        if ($('#vote-net')) $('#vote-net').textContent = d.net_votes != null ? d.net_votes : d.votes;
        $('#vote-up')?.setAttribute('aria-pressed', String(voteState === 1));
        $('#vote-down')?.setAttribute('aria-pressed', String(voteState === -1));
        $('#vote-up')?.classList.toggle('on', voteState === 1);
        $('#vote-down')?.classList.toggle('on', voteState === -1);
        sonic('vote');
      }
    }
    $('#vote-up')?.addEventListener('click', () => castVote(voteState === 1 ? 0 : 1));
    $('#vote-down')?.addEventListener('click', () => castVote(voteState === -1 ? 0 : -1));
    $('#bookmark-btn')?.addEventListener('click', async () => {
      const d = await api('/api/forum/threads/' + id + '/bookmark', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: uid() }) });
      if (d.success) { const b = d.bookmarked; $('#bookmark-btn').textContent = b ? '🔖 Saved' : '🔖 Save'; $('#bookmark-btn').setAttribute('aria-pressed', String(b)); toast(b ? 'Saved to bookmarks' : 'Removed bookmark', 'ok'); sonic('click'); }
    });
    $('#follow-btn')?.addEventListener('click', async () => {
      const d = await api('/api/forum/threads/' + id + '/follow', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: uid() }) });
      if (d.success) { const f = d.following; $('#follow-btn').textContent = f ? '🔔 Following' : '🔔 Follow'; $('#follow-btn').setAttribute('aria-pressed', String(f)); toast(f ? 'Following — you\'ll get replies' : 'Unfollowed', 'ok'); sonic('click'); }
    });
    document.querySelectorAll('.poll-option').forEach((b) => b.addEventListener('click', async () => {
      const d = await api('/api/forum/threads/' + id + '/poll/vote', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: uid(), option_id: b.dataset.opt }) });
      if (d.success && d.poll) { const card = $('#poll-card'); if (card) card.outerHTML = pollCard(d.poll); document.querySelectorAll('.poll-option').forEach((x) => x.addEventListener('click', () => openThread(id))); toast('Vote counted', 'ok'); sonic('vote'); }
      else toast(d.error || 'Poll vote failed', 'err');
    }));
    $('#copy-link')?.addEventListener('click', () => {
      const url = location.origin + '/forum#discussions/' + id;
      (navigator.clipboard?.writeText(url) || Promise.reject()).then(() => toast('Link copied', 'ok')).catch(() => toast(url));
    });
    $('#report-btn')?.addEventListener('click', async () => {
      const reason = prompt('Reason for report?') || '';
      const d = await api('/api/forum/report', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: uid(), thread_id: id, reason }),
      });
      toast(d.success ? 'Reported — thanks' : (d.error || 'Failed'), d.success ? 'ok' : 'err');
    });
    document.querySelectorAll('.react-btn').forEach((b) => b.addEventListener('click', async () => {
      const d = await api(`/api/forum/threads/${id}/posts/${b.dataset.post}/react`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reaction: b.dataset.react }),
      });
      if (d.success) {
        const span = b.querySelector('span');
        span.textContent = (d.reactions || {})[b.dataset.react] || 0;
        sonic('click');
      }
    }));
    document.querySelectorAll('.accept-btn').forEach((b) => b.addEventListener('click', async () => {
      const d = await api('/api/forum/threads/' + id + '/accept', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ post_id: b.dataset.post }),
      });
      if (d.success) { toast('Answer accepted', 'ok'); sonic('reward'); openThread(id); }
    }));
    $('#reply-submit')?.addEventListener('click', async () => {
      const body = ($('#reply-body') || {}).value.trim();
      if (!body) return;
      const d = await api('/api/forum/threads/' + encodeURIComponent(id) + '/reply', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: uid(), author_name: uid(), body }),
      });
      if (d.success) { toast('Reply posted', 'ok'); sonic('post'); openThread(id); loadThreadsList(); }
      else toast(d.error || 'Reply failed', 'err');
    });
  }

  async function submitThread() {
    const status = $('#thread-status');
    const body = ($('#thread-body') || {}).value.trim();
    const title = ($('#thread-title') || {}).value.trim();
    const topic_id = ($('#thread-topic') || {}).value;
    const subforum_id = ($('#thread-subforum') || {}).value;
    const kind = ($('#thread-kind') || {}).value || 'question';
    const tagsRaw = ($('#thread-tags') || {}).value.trim();
    const tags = tagsRaw ? tagsRaw.split(',').map((s) => s.trim()).filter(Boolean) : undefined;
    if (!body) { toast('Write something first', 'err'); return; }
    status.textContent = 'Posting…';
    const data = await api('/api/forum/threads', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: uid(), author_name: uid(), body,
        title: title || undefined, topic_id: topic_id || undefined,
        subforum_id: subforum_id || undefined, kind, tags,
      }),
    });
    status.textContent = data.success ? 'Posted!' : (data.error || 'Failed');
    if (data.success) {
      toast('Thread posted', 'ok');
      sonic('post');
      $('#thread-body').value = '';
      $('#thread-title').value = '';
      if ($('#thread-tags')) $('#thread-tags').value = '';
      $('#thread-preview').hidden = true;
      if ($('#thread-compose-wrap')) $('#thread-compose-wrap').open = false;
      loadThreadsList();
      if (data.thread?.id) openThread(data.thread.id);
    } else {
      toast(data.error || 'Post failed', 'err');
    }
  }

  async function loadDiscussions() {
    await loadTopicsNav();
    updateActiveTagFilter();
    await loadThreadsList();
    if (openThreadId) openThread(openThreadId);
  }

  async function loadRules() {
    const el = $('#rules-list');
    if (!el) return;
    const data = await api('/api/forum/rules');
    el.innerHTML = (data.sections || []).map((s) =>
      `<li><strong>${esc(s.title)}</strong><br>${esc(s.body)}</li>`
    ).join('');
  }

  // ---- Theme toggle ----
  function applyTheme(theme) {
    document.body.classList.toggle('forum-light', theme === 'light');
    const btn = $('#theme-toggle');
    if (btn) btn.textContent = theme === 'light' ? '☀️' : '🌙';
  }
  function initTheme() {
    const saved = localStorage.getItem('forum_theme') || 'dark';
    applyTheme(saved);
    $('#theme-toggle')?.addEventListener('click', () => {
      const next = document.body.classList.contains('forum-light') ? 'dark' : 'light';
      localStorage.setItem('forum_theme', next);
      applyTheme(next);
    });
  }

  // ---- Notifications ----
  async function refreshNotifBadge() {
    try {
      const d = await api('/api/forum/notifications?limit=1');
      const badge = $('#notif-badge');
      if (badge) {
        const n = d.unread || 0;
        badge.textContent = n > 99 ? '99+' : n;
        badge.hidden = n === 0;
      }
    } catch (_) {}
  }
  async function toggleNotifPanel() {
    const panel = $('#notif-panel');
    const btn = $('#notif-btn');
    if (!panel) return;
    const open = panel.hidden;
    panel.hidden = !open;
    btn?.setAttribute('aria-expanded', String(open));
    if (!open) return;
    panel.innerHTML = '<div class="forum-status">Loading…</div>';
    const d = await api('/api/forum/notifications?limit=30');
    const items = d.notifications || [];
    const icon = { reply: '💬', mention: '@', accepted: '✅', system: '🔔' };
    panel.innerHTML = `
      <div class="notif-head"><strong>Notifications</strong>${items.some((n) => !n.read) ? '<button type="button" id="notif-read-all" class="forum-btn secondary sm">Mark all read</button>' : ''}</div>
      ${items.length ? items.map((n) => `
        <a class="notif-item${n.read ? '' : ' unread'}" href="#discussions/${esc(n.thread_id)}" data-tid="${esc(n.thread_id)}">
          <span class="notif-ic">${icon[n.type] || '🔔'}</span>
          <span class="notif-txt">${esc(n.text || n.type)}<span class="meta"> · ${timeAgo(n.at)}</span></span>
        </a>`).join('') : '<div class="forum-status">No notifications yet.</div>'}`;
    $('#notif-read-all')?.addEventListener('click', async () => {
      await api('/api/forum/notifications/read', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: uid() }) });
      refreshNotifBadge(); toggleNotifPanel(); toggleNotifPanel();
    });
    panel.querySelectorAll('.notif-item').forEach((a) => a.addEventListener('click', () => {
      panel.hidden = true; setTab('discussions'); if (a.dataset.tid) openThread(a.dataset.tid);
      api('/api/forum/notifications/read', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: uid() }) }).then(refreshNotifBadge);
    }));
  }

  // ---- Composer: live duplicate detection ----
  let simT;
  async function checkSimilar(title) {
    const box = $('#thread-similar');
    if (!box) return;
    if (!title || title.length < 6) { box.hidden = true; return; }
    const d = await api('/api/forum/threads/similar?title=' + encodeURIComponent(title));
    const items = d.threads || [];
    if (!items.length) { box.hidden = true; return; }
    box.hidden = false;
    box.innerHTML = `<div class="meta">Similar existing threads — maybe join one?</div>` +
      items.map((t) => `<a href="#discussions/${esc(t.id)}" class="side-link">${esc(t.title)} <span class="meta">· ${Math.round((t.similarity || 0) * 100)}% match</span></a>`).join('');
  }

  async function loadMyThreads(kind) {
    const el = $('#threads-list');
    if (!el) return;
    el.innerHTML = skeleton(3);
    const d = await api('/api/forum/' + (kind === 'following' ? 'following' : 'bookmarks'));
    const cards = (d.threads || []).map(threadCard).join('');
    el.innerHTML = cards || `<div class="forum-status">${kind === 'following' ? 'You are not following any threads yet.' : 'No bookmarks yet — tap 🔖 Save on a thread.'}</div>`;
    bindThreadCards(el);
    const more = $('#threads-loadmore'); if (more) more.hidden = true;
  }

  function init() {
    initTheme();
    document.querySelectorAll('.forum-tab').forEach((btn) => {
      btn.addEventListener('click', () => { openThreadId = ''; setTab(btn.dataset.tab); });
    });
    const hash = (location.hash || '#home').replace(/^#/, '').split('/')[0];
    setTab(TAB_IDS.includes(hash) ? hash : 'home');
    window.addEventListener('hashchange', () => {
      const parts = (location.hash || '#home').replace(/^#/, '').split('/');
      const h = parts[0];
      if (parts[1]) openThreadId = parts[1];
      setTab(TAB_IDS.includes(h) ? h : 'home');
    });

    $('#article-form')?.addEventListener('submit', submitArticle);
    $('#chat-send')?.addEventListener('click', sendChat);
    $('#chat-input')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendChat(); });
    $('#ai-chat-send')?.addEventListener('click', sendAiChat);
    $('#wiki-search')?.addEventListener('click', searchWiki);
    $('#wiki-query')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') searchWiki(); });
    $('#thread-submit')?.addEventListener('click', submitThread);
    $('#global-search-btn')?.addEventListener('click', globalSearch);
    $('#global-search')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') globalSearch(); });

    // Sort chips
    document.querySelectorAll('.forum-sort .forum-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        document.querySelectorAll('.forum-sort .forum-chip').forEach((c) => c.classList.toggle('active', c === chip));
        currentSort = chip.dataset.sort;
        threadOffset = 0;
        loadThreadsList();
      });
    });
    // Filter box (debounced)
    let ft;
    $('#thread-search')?.addEventListener('input', (e) => {
      clearTimeout(ft);
      ft = setTimeout(() => { currentFilter = e.target.value.trim(); threadOffset = 0; loadThreadsList(); }, 300);
    });
    // Load more
    $('#threads-loadmore')?.addEventListener('click', () => { threadOffset += PAGE; loadThreadsList(true); });
    // Markdown preview
    $('#thread-preview-btn')?.addEventListener('click', () => {
      const pv = $('#thread-preview');
      const body = ($('#thread-body') || {}).value;
      pv.innerHTML = mdBasic(body || '_Nothing to preview_');
      pv.hidden = !pv.hidden;
    });

    // Back to top
    const fab = $('#back-to-top');
    window.addEventListener('scroll', () => { if (fab) fab.hidden = window.scrollY < 400; });
    fab?.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

    // Keyboard: "/" focuses global search
    document.addEventListener('keydown', (e) => {
      if (e.key === '/' && !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName)) {
        e.preventDefault();
        $('#global-search')?.focus();
      }
    });

    attachGrammar($('#thread-body'));
    attachGrammar($('#article-body'));
    wireShareControls();

    // Notifications bell
    $('#notif-btn')?.addEventListener('click', toggleNotifPanel);
    document.addEventListener('click', (e) => {
      const panel = $('#notif-panel');
      if (panel && !panel.hidden && !panel.contains(e.target) && e.target.id !== 'notif-btn' && !$('#notif-btn')?.contains(e.target)) panel.hidden = true;
    });
    refreshNotifBadge();
    setInterval(refreshNotifBadge, 60000);

    // Composer duplicate detection
    $('#thread-title')?.addEventListener('input', (e) => {
      clearTimeout(simT);
      simT = setTimeout(() => checkSimilar(e.target.value.trim()), 400);
    });

    // Saved / Following quick views
    $('#my-bookmarks-btn')?.addEventListener('click', () => { setTab('discussions'); loadMyThreads('bookmarks'); });
    $('#my-following-btn')?.addEventListener('click', () => { setTab('discussions'); loadMyThreads('following'); });

    loadRules();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
