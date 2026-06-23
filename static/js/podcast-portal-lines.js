(function () {
    'use strict';

    var script = document.currentScript;
    var siteId = (script && script.getAttribute('data-site')) || '';
    if (!siteId) {
        var path = (location.pathname || '').replace(/\/$/, '') || '/';
        var map = {
            '/': 'home', '/generator': 'generator', '/gallery': 'gallery', '/aggregator': 'aggregator',
            '/command-center': 'command-center', '/social': 'social', '/news': 'news', '/lab': 'lab',
            '/explorer': 'explorer', '/shop': 'shop', '/compendium': 'compendium', '/rights-law': 'rights-law',
            '/camgirls': 'camgirls', '/battle': 'battle', '/game': 'game', '/casino': 'casino',
            '/quests': 'quests', '/market': 'market', '/starmap25': 'starmap25', '/profile': 'profile',
            '/debugger': 'debugger', '/agent_support': 'agent_support', '/hosting': 'hosting', '/podcast': 'podcast'
        };
        siteId = map[path] || '';
    }

    function esc(s) {
        var d = document.createElement('div');
        d.textContent = s || '';
        return d.innerHTML;
    }

    function render(data) {
        if (!data || !data.success) return;
        var wrap = document.createElement('aside');
        wrap.className = 'podcast-portal-strip podcast-portal-max';
        wrap.setAttribute('aria-label', 'Podcast portal');

        var newsBit = data.latest_news
            ? '<p class="podcast-portal-news">📰 Latest: <a href="/podcast#news">' + esc(data.latest_news.title) + '</a> — <em>komment + MN2</em></p>'
            : '';
        var epBit = data.latest_episode
            ? '<p class="podcast-portal-latest">🎙️ Episode: <a href="/podcast">' + esc(data.latest_episode.title) + '</a></p>'
            : '';

        wrap.innerHTML =
            '<div class="podcast-portal-flavor">' + esc(data.flavor === 'blue_bubble_cheese_gum' ? '🫧 Blue Bubble Cheese Gum' : '🎙️ Podcast') + '</div>' +
            '<p class="podcast-portal-line">' + esc(data.line) + '</p>' +
            epBit + newsBit +
            '<p class="podcast-portal-hint">' + esc(data.comment_hint) + '</p>' +
            '<div class="podcast-portal-actions">' +
            '<a href="/podcast" class="podcast-portal-link podcast-portal-btn">Open Podcast</a>' +
            '<a href="/podcast#news" class="podcast-portal-link podcast-portal-btn podcast-portal-btn--news">News &amp; komment</a>' +
            '<a href="/podcast#episodes" class="podcast-portal-link podcast-portal-btn podcast-portal-btn--ghost">Listen</a>' +
            '</div>';

        if (script && script.parentNode) {
            script.parentNode.insertBefore(wrap, script.nextSibling);
        } else {
            var anchor = document.querySelector('.podcast-header') || document.querySelector('main') || document.body;
            anchor.insertBefore(wrap, anchor.firstChild);
        }
    }

    fetch('/api/podcast/portal-lines?site=' + encodeURIComponent(siteId))
        .then(function (r) { return r.json(); })
        .then(render)
        .catch(function () {});
})();
