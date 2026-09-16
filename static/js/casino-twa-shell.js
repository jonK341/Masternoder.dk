(function () {
    'use strict';

    var params = new URLSearchParams(window.location.search);
    if (params.get('app') !== 'casino-twa') return;

    document.documentElement.classList.add('casino-twa-active');

    var nav = document.createElement('nav');
    nav.className = 'casino-twa-bottom-nav';
    nav.setAttribute('aria-label', 'Casino app navigation');
    var tabs = [
        { id: 'lobby', label: 'Lobby', icon: '🏠', tab: 'home' },
        { id: 'games', label: 'Games', icon: '🎮', tab: 'crash' },
        { id: 'social', label: 'Social', icon: '🌐', tab: 'social' },
        { id: 'walk', label: 'Walk', icon: '🚶', tab: 'walk' }
    ];
    var activeTab = params.get('tab') || 'lobby';
    tabs.forEach(function (t) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'casino-twa-nav-btn' + (activeTab === t.id || activeTab === t.tab ? ' active' : '');
        btn.setAttribute('data-twa-tab', t.tab);
        btn.innerHTML = '<span class="casino-twa-nav-icon">' + t.icon + '</span><span>' + t.label + '</span>';
        btn.addEventListener('click', function () {
            var url = new URL(window.location.href);
            url.searchParams.set('app', 'casino-twa');
            url.searchParams.set('tab', t.id === 'games' ? 'crash' : t.tab);
            if (t.id === 'games') url.searchParams.set('game', 'crash');
            window.location.href = url.pathname + url.search + url.hash;
        });
        nav.appendChild(btn);
    });

    function mount() {
        if (document.body.querySelector('.casino-twa-bottom-nav')) return;
        document.body.appendChild(nav);
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', mount);
    } else {
        mount();
    }
})();
