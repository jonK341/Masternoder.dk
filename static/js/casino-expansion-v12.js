(function () {
    'use strict';

    var userId = localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
    var earningsHub = null;

    function $(id) {
        return document.getElementById(id);
    }

    function api(method, path, body) {
        var opts = {
            method: method,
            headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
            credentials: 'same-origin',
        };
        if (body) opts.body = JSON.stringify(Object.assign({ user_id: userId }, body));
        var url = path + (path.indexOf('?') >= 0 ? '&' : '?') + 'user_id=' + encodeURIComponent(userId);
        return fetch(url, opts).then(function (r) { return r.json(); });
    }

    function injectTabs() {
        var nav = $('casino-v10-main-nav');
        if (!nav || nav.querySelector('[data-v10-tab="hunt"]')) return;
        var tabs = [
            ['hunt', 'Hunt'],
            ['shop', 'Shop'],
            ['earn', 'Earn'],
        ];
        var socialBtn = nav.querySelector('[data-v10-tab="social"]');
        var ref = socialBtn;
        tabs.forEach(function (pair) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'casino-v10-main-tab';
            btn.setAttribute('data-v10-tab', pair[0]);
            btn.setAttribute('role', 'tab');
            btn.textContent = pair[1];
            if (ref && ref.parentNode) {
                ref.parentNode.insertBefore(btn, ref.nextSibling);
                ref = btn;
            } else {
                nav.appendChild(btn);
            }
        });
        var page = document.querySelector('.casino-page');
        if (!page) return;
        ['hunt', 'shop', 'earn'].forEach(function (name) {
            if ($(('casino-v12-' + name))) return;
            var sec = document.createElement('section');
            sec.id = 'casino-v12-' + name;
            sec.className = 'casino-v12-panel casino-v10-panel hidden';
            sec.setAttribute('aria-label', name);
            var agents = $('casino-v10-agents');
            if (agents && agents.parentNode) {
                agents.parentNode.insertBefore(sec, agents);
            } else {
                page.insertBefore(sec, page.firstChild);
            }
        });
    }

    function patchSetTab() {
        document.querySelectorAll('.casino-v10-main-tab').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var tab = btn.getAttribute('data-v10-tab');
                ['hunt', 'shop', 'earn'].forEach(function (name) {
                    var el = $('casino-v12-' + name);
                    if (el) el.classList.toggle('hidden', tab !== name);
                });
                if (tab === 'hunt') renderHunt();
                if (tab === 'shop') renderShop();
                if (tab === 'earn') renderEarn();
                if (tab === 'levels') enhanceLevels();
            });
        });
    }

    function loadHub() {
        return api('GET', '/api/casino/earnings/hub').then(function (hub) {
            earningsHub = hub;
            return hub;
        });
    }

    function renderEarn() {
        var root = $('casino-v12-earn');
        if (!root) return;
        root.innerHTML = '<p>Loading earn features…</p>';
        loadHub().then(function (hub) {
            var feats = (hub.features && hub.features.features) || [];
            root.innerHTML = '<h2 class="casino-subheading">25 ways to earn, revalue &amp; grow</h2><div class="casino-earn-grid"></div>';
            var grid = root.querySelector('.casino-earn-grid');
            feats.forEach(function (f) {
                var card = document.createElement('article');
                card.className = 'casino-earn-card' + (f.unlocked ? '' : ' locked');
                card.innerHTML =
                    '<div class="casino-earn-cat">' + (f.category || 'earn') + ' · L' + (f.min_level || 1) + '+</div>' +
                    '<h3>' + f.title + '</h3><p>' + f.description + '</p>' +
                    '<small>' + (f.unlocked ? '✓ Unlocked' : 'Unlock at level ' + f.min_level) + '</small>';
                grid.appendChild(card);
            });
            if (new URLSearchParams(window.location.search).get('app') === 'casino-twa') {
                var chest = document.createElement('button');
                chest.type = 'button';
                chest.className = 'casino-play-chest-btn';
                chest.textContent = 'Open Play App daily chest';
                chest.addEventListener('click', function () {
                    api('POST', '/api/casino/earnings/play-app-chest?app=casino-twa', { from_play_app: true })
                        .then(function (res) {
                            if (res.success) alert('+' + res.reward_coins + ' coins!');
                            else alert(res.error || 'Chest unavailable');
                        });
                });
                root.appendChild(chest);
            }
        });
    }

    function renderShop() {
        var root = $('casino-v12-shop');
        if (!root) return;
        root.innerHTML = '<p>Loading casino shop…</p>';
        loadHub().then(function (hub) {
            var shop = hub.shop || {};
            var items = shop.items || [];
            root.innerHTML = '<h2 class="casino-subheading">Casino shop — boosters, trophies &amp; cosmetics</h2><div class="casino-shop-grid"></div>';
            var grid = root.querySelector('.casino-shop-grid');
            items.forEach(function (item) {
                var card = document.createElement('article');
                card.className = 'casino-shop-card' + (item.owned ? ' owned' : '');
                var price = item.discounted_price != null ? item.discounted_price : item.price_coins;
                card.innerHTML =
                    '<div style="font-size:2rem">' + (item.icon || '🛒') + '</div>' +
                    '<h3>' + item.name + '</h3><p>' + item.description + '</p>' +
                    '<small>' + (item.owned ? 'Owned' : price + ' coins') + '</small>';
                if (!item.owned && item.purchasable) {
                    var btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'casino-shop-buy';
                    btn.textContent = 'Buy · ' + price + ' coins';
                    btn.addEventListener('click', function () {
                        api('POST', '/api/casino/shop/purchase', { item_id: item.id }).then(function (res) {
                            if (res.success) renderShop();
                            else alert(res.error || 'Purchase failed');
                        });
                    });
                    card.appendChild(btn);
                }
                grid.appendChild(card);
            });
        });
    }

    function renderHunt() {
        var root = $('casino-v12-hunt');
        if (!root) return;
        root.innerHTML = '<p>Loading gaming hunt…</p>';
        loadHub().then(function (hub) {
            var hunt = hub.hunt || {};
            var quests = hunt.quests || [];
            root.innerHTML =
                '<h2 class="casino-subheading">Gaming hunt — clues across casino &amp; game hub</h2>' +
                '<p style="font-size:0.88rem;opacity:0.85">Bridge to <a href="' + (hunt.game_hub_href || '/game/') + '">Hunters Game</a> and social quests.</p>' +
                '<div class="casino-hunt-list"></div>';
            var list = root.querySelector('.casino-hunt-list');
            quests.forEach(function (q) {
                var card = document.createElement('article');
                card.className = 'casino-hunt-card' + (q.claimable ? ' claimable' : '') + (q.claimed ? ' done' : '');
                card.innerHTML =
                    '<h3>' + q.title + '</h3>' +
                    '<p class="casino-hunt-clue">' + q.clue + '</p>' +
                    '<small>Progress ' + q.progress + '/' + q.target + ' · L' + q.min_level + '+</small>';
                if (q.game_hub_link) {
                    var link = document.createElement('a');
                    link.href = q.game_hub_link;
                    link.textContent = 'Open game hub →';
                    link.style.display = 'inline-block';
                    link.style.marginTop = '0.35rem';
                    card.appendChild(link);
                }
                if (q.claimable) {
                    var btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'casino-shop-buy';
                    btn.textContent = 'Claim reward';
                    btn.addEventListener('click', function () {
                        api('POST', '/api/casino/hunt/claim', { quest_id: q.id }).then(function (res) {
                            if (res.success) renderHunt();
                            else alert(res.error || 'Not claimable yet');
                        });
                    });
                    card.appendChild(btn);
                }
                list.appendChild(card);
            });
        });
    }

    function enhanceLevels() {
        var root = $('casino-v10-levels');
        if (!root) return;
        fetch('/api/casino/progression').then(function (r) { return r.json(); }).then(function (prog) {
            root.querySelectorAll('.casino-level-row').forEach(function (row, i) {
                var lv = (prog.levels || [])[i];
                if (!lv || row.querySelector('.casino-level-rich')) return;
                var rich = document.createElement('div');
                rich.className = 'casino-level-rich';
                rich.innerHTML =
                    '<p>' + (lv.story || '') + '</p>' +
                    '<p><strong>Social:</strong> ' + (lv.social_perk || '') + '</p>' +
                    '<p><strong>Hunt:</strong> ' + (lv.hunt_clue || '') + '</p>' +
                    '<p><strong>Earn:</strong> ' + (lv.earn_tip || '') + '</p>';
                row.querySelector('div').appendChild(rich);
            });
        });
    }

    function init() {
        injectTabs();
        patchSetTab();
        var params = new URLSearchParams(window.location.search);
        var tab = params.get('tab');
        if (tab === 'hunt' || tab === 'shop' || tab === 'earn') {
            document.querySelector('.casino-v10-main-tab[data-v10-tab="' + tab + '"]').click();
        }
        window.addEventListener('casino-bet-complete', function () {
            if (document.body.getAttribute('data-casino-v10-tab') === 'hunt') renderHunt();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
