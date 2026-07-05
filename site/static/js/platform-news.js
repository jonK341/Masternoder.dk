/* Platform news page — loads items from GET /api/news/platform?channel=* */
(function () {
  'use strict';

  var activeChannel = '';
  var channels = [];

  function q(id) { return document.getElementById(id); }

  function esc(s) {
    return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function renderItem(item) {
    var href = item.href || '/';
    var ch = item.channel || item.category || '';
    return '<div class="news-card">' +
      '<h3><a href="' + esc(href) + '">' + esc(item.title || 'Update') + '</a>' +
      (ch ? '<span class="channel">' + esc(ch) + '</span>' : '') +
      '</h3>' +
      '<div class="date">' + esc(item.date || '') + '</div>' +
      '<p>' + esc(item.summary || '') + '</p>' +
      '</div>';
  }

  function renderFeed(items) {
    var feed = q('news-feed');
    var status = q('news-status');
    if (!feed) return;
    if (!items || !items.length) {
      feed.innerHTML = '<div class="news-card"><p>No news items for this channel yet.</p></div>';
      if (status) status.textContent = '0 items';
      return;
    }
    feed.innerHTML = items.map(renderItem).join('');
    if (status) status.textContent = items.length + ' item(s)' + (activeChannel ? (' · channel: ' + activeChannel) : '');
  }

  function renderFilters() {
    var el = q('news-filters');
    if (!el) return;
    var html = '<button type="button" class="' + (activeChannel === '' ? 'active' : '') + '" data-channel="">All</button>';
    channels.forEach(function (ch) {
      html += '<button type="button" class="' + (activeChannel === ch.id ? 'active' : '') + '" data-channel="' + esc(ch.id) + '">' +
        esc(ch.id) + ' (' + ch.count + ')</button>';
    });
    el.innerHTML = html;
    el.querySelectorAll('button').forEach(function (btn) {
      btn.addEventListener('click', function () {
        activeChannel = btn.getAttribute('data-channel') || '';
        renderFilters();
        loadNews();
      });
    });
  }

  function loadChannels() {
    return fetch('/api/news/channels', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        channels = (d && d.success && d.channels) ? d.channels : [];
        renderFilters();
      })
      .catch(function () { renderFilters(); });
  }

  function loadNews() {
    var url = '/api/news/platform?limit=30';
    if (activeChannel) url += '&channel=' + encodeURIComponent(activeChannel);
    if (q('news-status')) q('news-status').textContent = 'Loading…';
    return fetch(url, { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) { renderFeed((d && d.success && d.news) ? d.news : []); })
      .catch(function () {
        if (q('news-feed')) q('news-feed').innerHTML = '<div class="news-card"><p>Could not load news feed.</p></div>';
        if (q('news-status')) q('news-status').textContent = 'Error loading feed';
      });
  }

  loadChannels().then(loadNews);
})();
