(function () {
    'use strict';

    var userId = localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
    var catalogCache = null;
    var activeCategory = '';

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

    function injectMultiPlayTab() {
        var nav = $('casino-v10-main-nav');
        if (!nav || nav.querySelector('[data-v10-tab="multiplay"]')) return;
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'casino-v10-main-tab';
        btn.setAttribute('data-v10-tab', 'multiplay');
        btn.setAttribute('role', 'tab');
        btn.textContent = 'MultiPlay';
        var gamesBtn = nav.querySelector('[data-v10-tab="games"]');
        if (gamesBtn && gamesBtn.nextSibling) {
            gamesBtn.parentNode.insertBefore(btn, gamesBtn.nextSibling);
        } else {
            nav.appendChild(btn);
        }
        var page = document.querySelector('.casino-page');
        if (!page || $('casino-v14-multiplay')) return;
        var sec = document.createElement('section');
        sec.id = 'casino-v14-multiplay';
        sec.className = 'casino-v14-multiplay casino-v10-panel hidden';
        sec.setAttribute('aria-label', 'MultiPlay games');
        var walk = $('casino-v10-walk') || $('casino-v10-lobby');
        if (walk && walk.parentNode) {
            walk.parentNode.insertBefore(sec, walk.nextSibling);
        } else {
            page.appendChild(sec);
        }
    }

    function patchTabs() {
        document.querySelectorAll('.casino-v10-main-tab').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var tab = btn.getAttribute('data-v10-tab');
                var panel = $('casino-v14-multiplay');
                if (panel) panel.classList.toggle('hidden', tab !== 'multiplay');
                document.body.setAttribute('data-casino-v10-tab', tab || '');
                if (tab === 'multiplay') renderMultiPlay();
            });
        });
    }

    function renderFacebookPanel(root, fbStatus, fbConfig) {
        var earn = (fbStatus && fbStatus.earn) || {};
        var makers = (fbConfig && fbConfig.money_makers) || [];
        var linked = fbStatus && fbStatus.linked;
        var html =
            '<div class="casino-v14-fb-panel">' +
            '<h3>📘 Facebook Casino Bot — gigantic seller</h3>' +
            '<p>Link Messenger, earn <strong>3 coins/bet + 12/win</strong> (cap ' + (earn.daily_cap || 400) + '/day). ' +
            'Sell packs from $0.99 in chat.</p>';
        if (linked) {
            html += '<p>✅ Linked · today ' + (earn.today_coins || 0) + ' / ' + (earn.daily_cap || 400) + ' earn coins</p>';
            html += '<button type="button" class="casino-v14-btn secondary" id="casino-v14-fb-claim">Claim daily FB coins</button>';
        } else {
            html += '<button type="button" class="casino-v14-btn secondary" id="casino-v14-fb-link">Get link code</button>' +
                '<div id="casino-v14-fb-code"></div>';
        }
        html += '<div class="casino-v14-seller-row">';
        makers.forEach(function (m) {
            if (m.price_usd) {
                html += '<span class="casino-v14-seller-chip">' + m.title + ' $' + m.price_usd + '</span>';
            }
        });
        html += '</div>';
        html += '<p style="margin-top:0.75rem;font-size:0.82rem;opacity:0.8;">Messenger: send MULTIPLAY · CASINO · SHOP · LINK CODE</p>';
        if (fbConfig && fbConfig.messenger_deep_link) {
            html += '<a href="' + fbConfig.messenger_deep_link + '" target="_blank" rel="noopener" class="casino-v14-btn secondary" style="display:inline-block;margin-top:0.5rem;text-decoration:none;">Open Messenger</a>';
        }
        html += '</div>';
        root.insertAdjacentHTML('afterbegin', html);
        var linkBtn = $('casino-v14-fb-link');
        if (linkBtn) {
            linkBtn.addEventListener('click', function () {
                linkBtn.disabled = true;
                api('POST', '/api/facebook/casino/link-code').then(function (d) {
                    var box = $('casino-v14-fb-code');
                    if (box && d.code) {
                        box.innerHTML = '<p class="casino-v14-link-code">' + d.code + '</p><p>Send to bot: <strong>LINK ' + d.code + '</strong></p>';
                    }
                }).finally(function () { linkBtn.disabled = false; });
            });
        }
        var claimBtn = $('casino-v14-fb-claim');
        if (claimBtn) {
            claimBtn.addEventListener('click', function () {
                api('POST', '/api/facebook/casino/daily-claim').then(function (d) {
                    alert(d.success ? 'Claimed +' + (d.granted_coins || 0) + ' coins' : (d.error || 'Failed'));
                    renderMultiPlay();
                });
            });
        }
    }

    function renderGameCard(g) {
        var card = document.createElement('article');
        card.className = 'casino-v14-card';
        card.setAttribute('data-mp-category', g.category || '');
        card.setAttribute('data-mp-title', (g.title || '').toLowerCase());
        card.innerHTML =
            '<span class="casino-v14-badge">' + (g.players_online || 0) + ' online</span>' +
            '<h3>' + (g.icon || '🎲') + ' ' + (g.title || g.id) + '</h3>' +
            '<p>' + (g.description || '') + '</p>' +
            '<p style="font-size:0.75rem;opacity:0.65;">Bet ' + g.min_bet + '–' + g.max_bet + ' · room ' + g.min_players + '–' + g.max_players + '</p>' +
            '<input type="number" min="' + g.min_bet + '" max="' + g.max_bet + '" value="' + g.min_bet + '" aria-label="Bet">' +
            '<button type="button" class="casino-v14-btn" data-game="' + g.id + '">Join &amp; Play</button>';
        var playBtn = card.querySelector('.casino-v14-btn');
        playBtn.addEventListener('click', function () {
            var bet = parseFloat(card.querySelector('input').value) || g.min_bet;
            playBtn.disabled = true;
            playBtn.textContent = 'Playing…';
            api('POST', '/api/casino/multiplay/play', { game_id: g.id, bet: bet, currency: 'coins' })
                .then(function (out) {
                    var res = $('casino-v14-mp-result');
                    if (!res) return;
                    if (out.success) {
                        var extra = '';
                        if (out.room_boost_bonus) extra += ' · room boost +' + out.room_boost_bonus;
                        if (out.community_pot_bonus) extra += ' · pot +' + out.community_pot_bonus;
                        res.textContent = (out.outcome || 'done') + ' · net ' + (out.net || 0) + extra +
                            ' · ' + (out.players_in_room || 0) + ' in room';
                    } else {
                        res.textContent = out.error || 'Play failed';
                    }
                })
                .finally(function () {
                    playBtn.disabled = false;
                    playBtn.textContent = 'Join & Play';
                });
        });
        return card;
    }

    function applyFilters() {
        var q = (($('casino-v14-mp-search') && $('casino-v14-mp-search').value) || '').toLowerCase();
        document.querySelectorAll('.casino-v14-card[data-mp-category]').forEach(function (card) {
            var cat = card.getAttribute('data-mp-category');
            var title = card.getAttribute('data-mp-title') || '';
            var catOk = !activeCategory || cat === activeCategory;
            var searchOk = !q || title.indexOf(q) >= 0;
            card.style.display = catOk && searchOk ? '' : 'none';
        });
    }

    function renderMultiPlay() {
        var root = $('casino-v14-multiplay');
        if (!root) return;
        root.innerHTML = '<p>Loading MultiPlay lounge…</p>';
        Promise.all([
            api('GET', '/api/casino/multiplay/catalog'),
            api('GET', '/api/facebook/casino/status'),
            fetch('/api/facebook/casino/config').then(function (r) { return r.json(); }),
        ]).then(function (parts) {
            var cat = parts[0] || {};
            catalogCache = cat;
            var fbSt = parts[1] || {};
            var fbCfg = parts[2] || {};
            var stats = cat.stats || {};
            root.innerHTML =
                '<div class="casino-v14-hero">' +
                '<h2 class="casino-subheading">🎉 ' + (cat.tab_label || 'MultiPlay') + '</h2>' +
                '<p>' + (cat.tagline || '30+ social room games') + '</p>' +
                '<div class="casino-v14-stats">' +
                '<span class="casino-v14-stat"><strong>' + (stats.games_count || 0) + '</strong> games</span>' +
                '<span class="casino-v14-stat"><strong>' + (stats.players_online || 0) + '</strong> players online</span>' +
                '<span class="casino-v14-stat"><strong>' + (stats.rooms_open || 0) + '</strong> rooms open</span>' +
                '<span class="casino-v14-stat">Pot <strong>' + (stats.community_pot_coins || 0) + '</strong> coins</span>' +
                '</div></div>' +
                '<div class="casino-v14-filters" id="casino-v14-filters"></div>' +
                '<div class="casino-v14-grid" id="casino-v14-grid"></div>' +
                '<div id="casino-v14-mp-result" class="casino-v14-result" role="status" aria-live="polite"></div>';
            renderFacebookPanel(root, fbSt, fbCfg);
            var filters = $('casino-v14-filters');
            var allBtn = document.createElement('button');
            allBtn.type = 'button';
            allBtn.className = 'casino-v14-filter-chip active';
            allBtn.textContent = 'All';
            allBtn.addEventListener('click', function () {
                activeCategory = '';
                filters.querySelectorAll('.casino-v14-filter-chip').forEach(function (c) { c.classList.remove('active'); });
                allBtn.classList.add('active');
                applyFilters();
            });
            filters.appendChild(allBtn);
            (cat.categories || []).forEach(function (c) {
                var chip = document.createElement('button');
                chip.type = 'button';
                chip.className = 'casino-v14-filter-chip';
                chip.textContent = (c.icon || '') + ' ' + c.label;
                chip.addEventListener('click', function () {
                    activeCategory = c.id;
                    filters.querySelectorAll('.casino-v14-filter-chip').forEach(function (x) { x.classList.remove('active'); });
                    chip.classList.add('active');
                    applyFilters();
                });
                filters.appendChild(chip);
            });
            var search = document.createElement('input');
            search.type = 'search';
            search.className = 'casino-v14-search';
            search.id = 'casino-v14-mp-search';
            search.placeholder = 'Search games…';
            search.addEventListener('input', applyFilters);
            filters.appendChild(search);
            var grid = $('casino-v14-grid');
            (cat.games || []).forEach(function (g) {
                grid.appendChild(renderGameCard(g));
            });
        }).catch(function () {
            root.innerHTML = '<p>Could not load MultiPlay catalog.</p>';
        });
    }

    function init() {
        injectMultiPlayTab();
        patchTabs();
        var params = new URLSearchParams(window.location.search);
        if (params.get('tab') === 'multiplay') {
            setTimeout(function () {
                var btn = document.querySelector('[data-v10-tab="multiplay"]');
                if (btn) btn.click();
            }, 900);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
