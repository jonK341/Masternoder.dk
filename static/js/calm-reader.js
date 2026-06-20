/**
 * Calm Reader — steady navigation, progress, and focus mode on /compendium/* pages.
 * See docs/RULEBOOK_READERS.md
 */
(function () {
    'use strict';

    var STORAGE_SESSION = 'mn2_reading_session';
    var STORAGE_CALM = 'mn2_calm_reading_on';
    var CSS_HREF = '/static/css/calm-reader.css?v=20260617';

    function isCompendiumPath() {
        return /\/compendium(\/|$)/.test(window.location.pathname || '');
    }

    function ensureCss() {
        if (document.querySelector('link[href*="calm-reader.css"]')) return;
        var link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = CSS_HREF;
        document.head.appendChild(link);
    }

    function getUserId() {
        try {
            return localStorage.getItem('game_user_id') || 'default_user';
        } catch (e) {
            return 'default_user';
        }
    }

    function normalizeUrl(url) {
        var u = String(url || '').replace(/\/+$/, '');
        if (u.endsWith('.html')) u = u.slice(0, -5);
        return u;
    }

    function parsePosition() {
        var path = (window.location.pathname || '').replace(/\/+$/, '');
        var m;
        if (/hunters-rulebook/i.test(path)) {
            return { kind: 'page', number: 11, url: '/compendium/hunters-rulebook.html', title: 'Hunters Rulebook' };
        }
        if (/rulebook-v3-2/i.test(path)) {
            return { kind: 'extra', url: '/compendium/rulebook-v3-2.html', title: 'V3.2 Systemic Protocols' };
        }
        m = path.match(/rulebook-v(\d+)/i);
        if (m) {
            return { kind: 'rulebook', version: parseInt(m[1], 10), url: '/compendium/rulebook-v' + m[1] + '.html', title: 'Rulebook V' + m[1] };
        }
        m = path.match(/page-(\d+)/i);
        if (m) {
            var n = parseInt(m[1], 10);
            return { kind: 'page', number: n, url: '/compendium/page-' + n + '.html', title: 'Side ' + n };
        }
        if (path === '/compendium' || path === '/compendium/index.html') {
            return { kind: 'index', url: '/compendium/', title: 'Library' };
        }
        return null;
    }

    function saveSession(pos, pages) {
        if (!pos || !pos.url) return;
        try {
            var idx = -1;
            if (pages && pages.length) {
                idx = pages.findIndex(function (p) { return normalizeUrl(p.url) === normalizeUrl(pos.url); });
            }
            localStorage.setItem(STORAGE_SESSION, JSON.stringify({
                url: pos.url,
                title: pos.title || '',
                index: idx,
                at: Date.now()
            }));
        } catch (e) {}
    }

    function loadSession() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_SESSION) || 'null');
        } catch (e) {
            return null;
        }
    }

    function fetchPages() {
        return fetch('/api/compendium/pages')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var pages = (data && data.pages) || [];
                var extras = (data && data.extras) || [];
                extras.forEach(function (ex) {
                    pages.push({ number: null, title: ex.title, url: ex.url, section: ex.section || 'III' });
                });
                return pages;
            })
            .catch(function () { return []; });
    }

    function fetchProgress() {
        var uid = encodeURIComponent(getUserId());
        return fetch('/api/user/compendium/progress?user_id=' + uid)
            .then(function (r) { return r.json(); })
            .catch(function () { return {}; });
    }

    function nextUnreadUrl(pages, progress) {
        var read = new Set((progress && progress.pages_read) || []);
        for (var i = 0; i < pages.length; i++) {
            var p = pages[i];
            if (p.number && !read.has(p.number)) {
                return p.url;
            }
        }
        return pages.length ? pages[0].url : '/compendium/page-1.html';
    }

    function applyCalmMode(on) {
        document.body.classList.toggle('calm-reading-active', on);
        try { localStorage.setItem(STORAGE_CALM, on ? '1' : '0'); } catch (e) {}
        var focusBtn = document.getElementById('cr-focus-toggle');
        if (focusBtn) focusBtn.textContent = document.body.classList.contains('calm-reading-focus') ? 'Show chrome' : 'Focus';
    }

    function toggleFocus() {
        document.body.classList.toggle('calm-reading-focus');
        var btn = document.getElementById('cr-focus-toggle');
        if (btn) btn.textContent = document.body.classList.contains('calm-reading-focus') ? 'Show chrome' : 'Focus';
    }

    function buildChrome(pages, pos, progress) {
        var readCount = (progress && progress.total_read) || 0;
        var total = (progress && progress.total_pages) || pages.length || 25;
        var pct = total ? Math.min(100, Math.round((readCount / total) * 100)) : 0;
        var idx = pages.findIndex(function (p) { return normalizeUrl(p.url) === normalizeUrl(pos && pos.url); });
        var prev = idx > 0 ? pages[idx - 1] : null;
        var next = idx >= 0 && idx < pages.length - 1 ? pages[idx + 1] : null;

        var top = document.createElement('div');
        top.className = 'cr-chrome';
        top.innerHTML =
            '<div class="cr-chrome-inner">' +
            '<div class="cr-progress-wrap" role="status" aria-live="polite">' +
            '<div class="cr-progress-label">Your reading · ' + readCount + ' / ' + total + ' (' + pct + '%)</div>' +
            '<div class="cr-progress-track" aria-hidden="true"><div class="cr-progress-fill" style="width:' + pct + '%"></div></div>' +
            '</div>' +
            '<div class="cr-chrome-actions">' +
            '<a class="cr-btn cr-btn--ghost" href="/compendium/">Library</a>' +
            '<button type="button" class="cr-btn cr-btn--ghost" id="cr-focus-toggle">Focus</button>' +
            '<button type="button" class="cr-btn cr-btn--primary" id="cr-calm-toggle">Calm mode</button>' +
            '</div></div>';

        var foot = document.createElement('nav');
        foot.className = 'cr-footer-nav';
        foot.setAttribute('aria-label', 'Reading navigation');
        foot.innerHTML =
            '<div class="cr-footer-inner">' +
            (prev
                ? '<a class="cr-btn" href="' + prev.url + '" rel="prev">← ' + esc(prev.title || ('Page ' + prev.number)) + '</a>'
                : '<span class="cr-btn cr-btn--ghost" aria-hidden="true">Start</span>') +
            '<div class="cr-footer-meta"><strong>' + esc((pos && pos.title) || 'Reading') + '</strong></div>' +
            (next
                ? '<a class="cr-btn cr-btn--primary" href="' + next.url + '" rel="next">' + esc(next.title || ('Page ' + next.number)) + ' →</a>'
                : '<a class="cr-btn cr-btn--primary" href="/compendium/">Done · Library</a>') +
            '</div>';

        document.body.classList.add('calm-reader-page');
        document.body.insertBefore(top, document.body.firstChild);
        document.body.appendChild(foot);

        document.getElementById('cr-calm-toggle').addEventListener('click', function () {
            var on = !document.body.classList.contains('calm-reading-active');
            applyCalmMode(on);
            document.getElementById('cr-calm-toggle').textContent = on ? 'Calm on' : 'Calm mode';
        });
        document.getElementById('cr-focus-toggle').addEventListener('click', toggleFocus);

        var calmOn = false;
        try { calmOn = localStorage.getItem(STORAGE_CALM) !== '0'; } catch (e) { calmOn = true; }
        if (calmOn || window.location.search.indexOf('calm=1') !== -1) {
            applyCalmMode(true);
            var t = document.getElementById('cr-calm-toggle');
            if (t) t.textContent = 'Calm on';
        }

        document.addEventListener('keydown', function (e) {
            if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
            if (e.key === 'ArrowLeft' && prev) window.location.href = prev.url;
            if (e.key === 'ArrowRight' && next) window.location.href = next.url;
            if (e.key === 'Escape') {
                document.body.classList.remove('calm-reading-focus');
                var fb = document.getElementById('cr-focus-toggle');
                if (fb) fb.textContent = 'Focus';
            }
        });

        return { prev: prev, next: next };
    }

    function esc(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
    }

    function injectContinueCard(pages, progress) {
        if (!/\/compendium\/?$/.test(window.location.pathname.replace(/\/+$/, '') + '/')) return;
        var main = document.querySelector('.comp-main');
        if (!main || document.getElementById('cr-continue-card')) return;

        var session = loadSession();
        var nextUrl = nextUnreadUrl(pages, progress);
        var readCount = (progress && progress.total_read) || 0;
        var total = (progress && progress.total_pages) || 25;

        var card = document.createElement('section');
        card.id = 'cr-continue-card';
        card.className = 'cr-continue-card';
        card.innerHTML =
            '<h2>Continue calmly</h2>' +
            '<p>' + readCount + ' of ' + total + ' volumes visited. Pick up where you left off — steady pace, no rush.</p>' +
            '<div class="cr-continue-actions">' +
            (session && session.url
                ? '<a class="cr-btn cr-btn--primary" href="' + esc(session.url) + '">Resume · ' + esc(session.title || 'last page') + '</a>'
                : '') +
            '<a class="cr-btn" href="' + esc(nextUrl) + '">Next unread</a>' +
            '<a class="cr-btn cr-btn--ghost" href="' + esc(nextUrl) + '?calm=1">Start calm session</a>' +
            '</div>';
        main.insertBefore(card, main.firstChild);
    }

    function init() {
        if (!isCompendiumPath()) return;
        ensureCss();
        var pos = parsePosition();

        Promise.all([fetchPages(), fetchProgress()]).then(function (res) {
            var pages = res[0];
            var progress = res[1];
            if (pos && pos.url) saveSession(pos, pages);
            if (pos && pos.kind !== 'index') buildChrome(pages, pos, progress);
            injectContinueCard(pages, progress);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    window.MN2CalmReader = {
        continueUrl: function () {
            return fetchPages().then(function (pages) {
                return fetchProgress().then(function (progress) {
                    return nextUnreadUrl(pages, progress);
                });
            });
        },
        loadSession: loadSession
    };
})();
