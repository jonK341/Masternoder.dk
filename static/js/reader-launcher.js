/**
 * Reader Launcher — calm library entry on every page (via navigation toolbar).
 */
(function () {
    'use strict';

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

    function loadSession() {
        try {
            return JSON.parse(localStorage.getItem('mn2_reading_session') || 'null');
        } catch (e) {
            return null;
        }
    }

    function buildLauncher(session, progress) {
        if (document.getElementById('cr-launcher')) return;

        var read = (progress && progress.total_read) || 0;
        var total = (progress && progress.total_pages) || 25;
        var sub = read > 0 ? read + ' / ' + total + ' read' : 'Rulebooks & compendium';
        var resume = session && session.url ? session.url : '/compendium/page-1.html';
        var resumeTitle = (session && session.title) || 'Side 1';

        var wrap = document.createElement('div');
        wrap.id = 'cr-launcher';
        wrap.className = 'cr-launcher';
        wrap.innerHTML =
            '<button type="button" class="cr-launcher-btn" id="cr-launcher-open" aria-expanded="false" aria-controls="cr-launcher-menu">' +
            '<span class="cr-launcher-icon" aria-hidden="true">📖</span>' +
            '<span class="cr-launcher-text">' +
            '<span class="cr-launcher-title">Library</span>' +
            '<span class="cr-launcher-sub" id="cr-launcher-sub">' + sub + '</span>' +
            '</span></button>' +
            '<div class="cr-launcher-menu" id="cr-launcher-menu" role="menu">' +
            '<a role="menuitem" href="/compendium/?calm=1">Open library (calm)</a>' +
            '<a role="menuitem" href="' + resume + '">Continue · ' + esc(resumeTitle) + '</a>' +
            '<a role="menuitem" href="/compendium/page-1.html?calm=1">Start from Side 1</a>' +
            '<a role="menuitem" href="/trophies#compendium">Trophies · Compendium tab</a>' +
            '</div>';

        document.body.appendChild(wrap);

        var btn = document.getElementById('cr-launcher-open');
        var menu = document.getElementById('cr-launcher-menu');
        btn.addEventListener('click', function () {
            var open = menu.classList.toggle('open');
            btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        });
        document.addEventListener('click', function (e) {
            if (!wrap.contains(e.target)) {
                menu.classList.remove('open');
                btn.setAttribute('aria-expanded', 'false');
            }
        });
    }

    function esc(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
    }

    function init() {
        if (isCompendiumPath()) return;
        ensureCss();
        var session = loadSession();
        fetch('/api/user/compendium/progress?user_id=' + encodeURIComponent(getUserId()))
            .then(function (r) { return r.json(); })
            .then(function (progress) { buildLauncher(session, progress); })
            .catch(function () { buildLauncher(session, null); });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
