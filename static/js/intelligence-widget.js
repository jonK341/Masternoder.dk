/**
 * Intelligence Widget - Research, News, Trending from aggregator API
 * Reusable across aggregator and vidgenerator pages. Auto-refresh every 30 min.
 */
(function () {
    'use strict';

    var INTEL_API_BASE = '/api/aggregators/intelligence';
    var REFRESH_INTERVAL_MS = 30 * 60 * 1000;
    var refreshTimer = null;

    function getApiUrl(path, params) {
        var base = INTEL_API_BASE + (path || '');
        if (params) {
            var parts = [];
            for (var k in params) { if (params.hasOwnProperty(k)) parts.push(k + '=' + encodeURIComponent(params[k])); }
            return base + (base.indexOf('?') !== -1 ? '&' : '?') + parts.join('&');
        }
        return base;
    }

    function escapeHtml(s) {
        if (s == null) return '';
        var div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML;
    }

    function renderResearch(papers) {
        if (!papers || !papers.length) return '<div class="intel-empty">No research papers available.</div>';
        var html = '<div class="intel-panel intel-research" data-panel="research"><div class="intel-cards">';
        for (var i = 0; i < papers.length; i++) {
            var p = papers[i];
            var title = escapeHtml(p.title || 'Untitled');
            var authors = Array.isArray(p.authors) ? p.authors.join(', ') : (p.authors || '');
            var abstract = escapeHtml((p.abstract || '').substring(0, 200)) + (p.abstract && p.abstract.length > 200 ? '...' : '');
            var url = p.url || '#';
            var source = escapeHtml(p.source || '');
            var published = p.published ? new Date(p.published).toLocaleDateString() : '';
            html += '<article class="intel-card intel-card-research">';
            html += '<span class="intel-badge intel-badge-source">' + source + '</span>';
            html += '<h3 class="intel-card-title"><a href="' + escapeHtml(url) + '" target="_blank" rel="noopener">' + title + '</a></h3>';
            if (authors) html += '<p class="intel-card-meta">' + escapeHtml(authors) + '</p>';
            if (abstract) html += '<p class="intel-card-abstract">' + abstract + '</p>';
            if (published) html += '<p class="intel-card-date">' + published + '</p>';
            html += '</article>';
        }
        html += '</div></div>';
        return html;
    }

    function renderNews(news) {
        if (!news || !news.length) return '<div class="intel-empty">No news available.</div>';
        var html = '<div class="intel-panel intel-news" data-panel="news"><div class="intel-cards">';
        for (var i = 0; i < news.length; i++) {
            var n = news[i];
            var title = escapeHtml(n.title || 'Untitled');
            var summary = escapeHtml((n.summary || '').substring(0, 180)) + (n.summary && n.summary.length > 180 ? '...' : '');
            var url = n.url || '#';
            var source = escapeHtml(n.source || '');
            var published = n.published ? new Date(n.published).toLocaleDateString() : '';
            html += '<article class="intel-card intel-card-news">';
            html += '<span class="intel-badge intel-badge-source">' + source + '</span>';
            html += '<h3 class="intel-card-title"><a href="' + escapeHtml(url) + '" target="_blank" rel="noopener">' + title + '</a></h3>';
            if (summary) html += '<p class="intel-card-summary">' + summary + '</p>';
            if (published) html += '<p class="intel-card-date">' + published + '</p>';
            html += '</article>';
        }
        html += '</div></div>';
        return html;
    }

    function renderTrending(trending) {
        if (!trending || !trending.length) return '<div class="intel-empty">No trending topics.</div>';
        var html = '<div class="intel-panel intel-trending" data-panel="trending"><ul class="intel-trending-list">';
        for (var i = 0; i < trending.length; i++) {
            var t = trending[i];
            var topic = escapeHtml(t.topic || '');
            var score = t.trend_score != null ? t.trend_score : '';
            var growth = t.growth ? escapeHtml(t.growth) : '';
            html += '<li class="intel-trending-item">';
            html += '<span class="intel-trend-topic">' + topic + '</span>';
            if (score !== '') html += ' <span class="intel-trend-score">' + score + '</span>';
            if (growth) html += ' <span class="intel-trend-growth">' + growth + '</span>';
            html += '</li>';
        }
        html += '</ul></div>';
        return html;
    }

    function showPanel(panelsEl, activePanel) {
        if (!panelsEl) return;
        var panels = panelsEl.querySelectorAll('.intel-panel');
        for (var j = 0; j < panels.length; j++) {
            panels[j].classList.toggle('active', panels[j].getAttribute('data-panel') === activePanel);
        }
    }

    function bindSubTabs(container, panelsId) {
        if (!container) return;
        panelsId = panelsId || 'intelligence-panels';
        var tabs = container.querySelectorAll('.intel-tab');
        var panelsEl = document.getElementById(panelsId);
        for (var i = 0; i < tabs.length; i++) {
            tabs[i].addEventListener('click', function () {
                var panel = this.getAttribute('data-intel');
                container.querySelectorAll('.intel-tab').forEach(function (t) { t.classList.remove('active'); });
                this.classList.add('active');
                showPanel(panelsEl, panel);
            });
        }
    }

    /**
     * Load intelligence and render into #intelligence-panels. Hides .intel-loading when done.
     * Optional: pass opts.containerSelector and opts.hideLoadingSelector.
     */
    function loadIntelligence(opts) {
        opts = opts || {};
        var panelsId = opts.panelsSelector || 'intelligence-panels';
        var loadingSelector = opts.loadingSelector || '.intel-loading';
        var panelsEl = document.getElementById(panelsId);
        var loadingEl = document.querySelector(loadingSelector);

        if (loadingEl) loadingEl.style.display = 'block';
        if (panelsEl) panelsEl.innerHTML = '';

        var url = getApiUrl('/all', { research_limit: 5, news_limit: 5, trending_limit: 5 });

        fetch(url)
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (loadingEl) loadingEl.style.display = 'none';
                if (!panelsEl) return;
                if (!data.success) {
                    panelsEl.innerHTML = '<div class="intel-error">' + escapeHtml(data.error || 'Failed to load intelligence') + '</div>';
                    return;
                }
                var research = data.research || [];
                var news = data.news || [];
                var trending = data.trending || [];
                panelsEl.innerHTML = renderResearch(research) + renderNews(news) + renderTrending(trending);
                showPanel(panelsEl, 'research');
                var contentRoot = panelsEl.closest('#intelligence-content') || panelsEl.parentElement;
                if (contentRoot) bindSubTabs(contentRoot, panelsId);
            })
            .catch(function (err) {
                if (loadingEl) loadingEl.style.display = 'none';
                if (panelsEl) panelsEl.innerHTML = '<div class="intel-error">Failed to load: ' + escapeHtml(err.message) + '</div>';
            });
    }

    function startAutoRefresh(opts) {
        if (refreshTimer) clearInterval(refreshTimer);
        refreshTimer = setInterval(function () { loadIntelligence(opts); }, REFRESH_INTERVAL_MS);
    }

    function stopAutoRefresh() {
        if (refreshTimer) {
            clearInterval(refreshTimer);
            refreshTimer = null;
        }
    }

    window.IntelligenceWidget = {
        load: loadIntelligence,
        startAutoRefresh: startAutoRefresh,
        stopAutoRefresh: stopAutoRefresh
    };
})();
