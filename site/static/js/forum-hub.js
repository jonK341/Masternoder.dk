/**
 * MasterNoder unified Forum hub
 */
(function () {
  'use strict';

  const API = window.location.origin;
  const uid = () => localStorage.getItem('user_id') || 'default_user';

  const TAB_IDS = [
    'home', 'news', 'articles', 'chat', 'podcast', 'rulebooks',
    'paragraphs', 'docs', 'support', 'social', 'wikipedia',
  ];

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
      .replace(/\n/g, '<br>');
  }

  function setTab(tabId) {
    const id = TAB_IDS.includes(tabId) ? tabId : 'home';
    document.querySelectorAll('.forum-tab').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.tab === id);
    });
    document.querySelectorAll('.forum-panel').forEach((p) => {
      p.classList.toggle('active', p.id === 'panel-' + id);
    });
    if (location.hash !== '#' + id) {
      history.replaceState(null, '', '#'+ id);
    }
    loadPanel(id);
  }

  async function api(path, opts) {
    const r = await fetch(API + path, opts);
    return r.json();
  }

  async function loadPanel(tab) {
    switch (tab) {
      case 'home': return loadFeed();
      case 'news': return loadNews();
      case 'articles': return loadArticles();
      case 'chat': return loadChat();
      case 'podcast': return loadPodcast();
      case 'rulebooks': return loadRulebooks();
      case 'paragraphs': return loadParagraphs();
      case 'docs': return loadDocs();
      case 'support': return loadSupport();
      case 'social': return loadSocial();
      case 'wikipedia': return; // on demand
      default: return loadFeed();
    }
  }

  async function loadFeed() {
    const el = $('#feed-list');
    if (!el) return;
    el.innerHTML = '<div class="forum-status">Loading feed…</div>';
    const data = await api('/api/forum/feed?limit=30');
    if (!data.success) {
      el.innerHTML = '<div class="forum-status">Could not load feed.</div>';
      return;
    }
    el.innerHTML = (data.feed || []).map((item) => `
      <div class="forum-card">
        <div class="meta">${esc(item.type)} · ${esc(item.created_at || '')}</div>
        <h3>${esc(item.title)}</h3>
        <p>${esc(item.summary || '')}</p>
        ${item.href ? `<a href="${esc(item.href)}" class="forum-btn secondary" style="margin-top:8px;display:inline-block;text-decoration:none;">Open</a>` : ''}
      </div>
    `).join('') || '<div class="forum-status">No posts yet. Write an article!</div>';
  }

  async function loadNews() {
    const el = $('#news-list');
    if (!el) return;
    el.innerHTML = '<div class="forum-status">Loading news…</div>';
    const data = await api('/api/forum/news?limit=40');
    el.innerHTML = (data.news || []).map((n) => `
      <div class="forum-card">
        <div class="meta">${esc(n.date)} · ${esc(n.channel || n.category || 'platform')}</div>
        <h3>${n.href ? `<a href="${esc(n.href)}" style="color:inherit">${esc(n.title)}</a>` : esc(n.title)}</h3>
        <p>${esc(n.summary || '')}</p>
      </div>
    `).join('') || '<div class="forum-status">No news items.</div>';
  }

  async function loadArticles() {
    const el = $('#articles-list');
    if (!el) return;
    const data = await api('/api/forum/articles?limit=50');
    el.innerHTML = (data.articles || []).map((a) => `
      <div class="forum-card" data-article-id="${esc(a.id)}">
        <div class="meta">${esc(a.author_name)} · ${esc(a.created_at)} · ${esc(a.category)}</div>
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
      $('#article-title').value = '';
      $('#article-body').value = '';
      loadArticles();
      loadFeed();
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
    el.innerHTML = '<div class="forum-status">Loading podcast…</div>';
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

  async function loadSocial() {
    const el = $('#social-networks');
    if (!el) return;
    const data = await api('/api/forum/social-networks');
    el.innerHTML = (data.networks || []).map((n) => `
      <button type="button" class="forum-social-btn share-net" data-net="${esc(n.id)}" style="border-color:${esc(n.color || '#666')}">${esc(n.icon)} ${esc(n.name)}</button>
    `).join('');
    el.querySelectorAll('.share-net').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const d = await api('/api/forum/share', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ network: btn.dataset.net, url: location.origin + '/forum/', text: 'MasterNoder Forum' }),
        });
        if (d.share_url) window.open(d.share_url, '_blank', 'noopener');
      });
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

  async function loadRules() {
    const el = $('#rules-list');
    if (!el) return;
    const data = await api('/api/forum/rules');
    el.innerHTML = '<ul class="forum-rules-list">' + (data.sections || []).map((s) =>
      `<li><strong>${esc(s.title)}</strong><br>${esc(s.body)}</li>`
    ).join('') + '</ul>';
  }

  function init() {
    document.querySelectorAll('.forum-tab').forEach((btn) => {
      btn.addEventListener('click', () => setTab(btn.dataset.tab));
    });
    const hash = (location.hash || '#home').replace(/^#/, '').split('/')[0];
    setTab(TAB_IDS.includes(hash) ? hash : 'home');
    window.addEventListener('hashchange', () => {
      const h = (location.hash || '#home').replace(/^#/, '').split('/')[0];
      setTab(TAB_IDS.includes(h) ? h : 'home');
    });
    $('#article-form')?.addEventListener('submit', submitArticle);
    $('#chat-send')?.addEventListener('click', sendChat);
    $('#ai-chat-send')?.addEventListener('click', sendAiChat);
    $('#wiki-search')?.addEventListener('click', searchWiki);
    loadRules();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
