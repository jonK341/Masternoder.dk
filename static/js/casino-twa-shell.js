(function () {
    'use strict';

    var params = new URLSearchParams(window.location.search);
    var twaMode = params.get('app') === 'casino-twa' ||
        window.matchMedia('(display-mode: standalone)').matches;

    if (!twaMode) return;

    document.documentElement.classList.add('casino-twa-ready');
    document.addEventListener('DOMContentLoaded', function () {
        document.body.classList.add('casino-twa-mode');
        injectBottomNav();
        injectBanner();
    });

    function setTab(tab) {
        document.querySelectorAll('.casino-twa-bottom-nav button').forEach(function (btn) {
            btn.classList.toggle('active', btn.getAttribute('data-v10-tab') === tab);
        });
        var mainBtn = document.querySelector('.casino-v10-main-tab[data-v10-tab="' + tab + '"]');
        if (mainBtn) mainBtn.click();
    }

    function injectBanner() {
        var banner = document.createElement('div');
        banner.className = 'casino-twa-install-banner';
        banner.textContent = 'MasterNoder Casino Social — virtual coins · friends & crews';
        var header = document.querySelector('.casino-header');
        if (header && header.parentNode) {
            header.parentNode.insertBefore(banner, header);
        }
    }

    function injectBottomNav() {
        var nav = document.createElement('nav');
        nav.className = 'casino-twa-bottom-nav';
        nav.setAttribute('aria-label', 'Casino app navigation');
        var tabs = [
            ['lobby', 'Lobby'],
            ['games', 'Games'],
            ['social', 'Social'],
            ['walk', 'Walk'],
            ['trophies', 'Trophies'],
        ];
        tabs.forEach(function (pair) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.setAttribute('data-v10-tab', pair[0]);
            btn.textContent = pair[1];
            btn.addEventListener('click', function () { setTab(pair[0]); });
            nav.appendChild(btn);
        });
        document.body.appendChild(nav);
        var startTab = params.get('tab') || 'lobby';
        setTab(startTab);
    }
})();
