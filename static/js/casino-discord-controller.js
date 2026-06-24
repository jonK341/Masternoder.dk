(function () {
    'use strict';

    var userId = localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';

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

    function injectDiscordTab() {
        var nav = $('casino-v10-main-nav');
        if (!nav || nav.querySelector('[data-v10-tab="discord"]')) return;
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'casino-v10-main-tab';
        btn.setAttribute('data-v10-tab', 'discord');
        btn.setAttribute('role', 'tab');
        btn.textContent = 'Discord';
        var earnBtn = nav.querySelector('[data-v10-tab="earn"]');
        if (earnBtn && earnBtn.nextSibling) {
            earnBtn.parentNode.insertBefore(btn, earnBtn.nextSibling);
        } else {
            nav.appendChild(btn);
        }
        var page = document.querySelector('.casino-page');
        if (!page || $('casino-v12-discord')) return;
        var sec = document.createElement('section');
        sec.id = 'casino-v12-discord';
        sec.className = 'casino-v12-panel casino-v10-panel hidden';
        sec.setAttribute('aria-label', 'Discord controller');
        var agents = $('casino-v10-agents');
        if (agents && agents.parentNode) {
            agents.parentNode.insertBefore(sec, agents);
        } else {
            page.appendChild(sec);
        }
        btn.addEventListener('click', function () {
            document.querySelectorAll('.casino-v12-discord-only').forEach(function () {});
            ['hunt', 'shop', 'earn', 'walk', 'social', 'agents', 'trophies', 'levels'].forEach(function (name) {
                var el = $('casino-v12-' + name) || $('casino-v10-' + name);
                if (el) el.classList.add('hidden');
            });
            sec.classList.remove('hidden');
            renderDiscord();
        });
        document.querySelectorAll('.casino-v10-main-tab').forEach(function (tabBtn) {
            tabBtn.addEventListener('click', function () {
                var tab = tabBtn.getAttribute('data-v10-tab');
                if (tab !== 'discord' && sec) sec.classList.add('hidden');
            });
        });
    }

    function renderDiscord() {
        var root = $('casino-v12-discord');
        if (!root) return;
        root.innerHTML = '<p>Loading Discord controller…</p>';
        Promise.all([
            api('GET', '/api/discord/controller/status'),
            fetch('/api/discord/app/manifest').then(function (r) { return r.json(); }),
        ]).then(function (results) {
            var st = results[0];
            var manifest = results[1];
            var earn = st.earn || {};
            root.innerHTML =
                '<div class="casino-discord-hero">' +
                '<h2 class="casino-subheading">🕷️ Discord Controller</h2>' +
                '<p>Link Discord, use slash commands, and <strong>earn coins while playing casino on-site</strong>. ' +
                'New Discord links get a <strong>50 MN2 welcome bonus</strong>. ' +
                'Hosting, shop, and game hub activities included.</p></div>' +
                '<div class="casino-discord-grid">' +
                '<section class="casino-discord-card"><h3>Account link</h3>' +
                '<p id="casino-discord-link-status">…</p>' +
                '<div id="casino-discord-code-box" class="hidden"><div class="casino-discord-code" id="casino-discord-code"></div>' +
                '<p style="font-size:0.8rem">In Discord: <code>/link YOUR_CODE</code></p></div>' +
                '<button type="button" class="casino-discord-btn" id="casino-discord-gen-code">Generate link code</button></section>' +
                '<section class="casino-discord-card"><h3>Play-earn</h3>' +
                '<p>Lifetime: <strong id="casino-discord-lifetime">0</strong> coins</p>' +
                '<p>Today from casino bets: <strong id="casino-discord-today">0</strong> / <span id="casino-discord-cap">250</span></p>' +
                '<button type="button" class="casino-discord-btn" id="casino-discord-daily">Claim Discord daily</button></section>' +
                '<section class="casino-discord-card casino-social-card-wide"><h3>Discord app activities</h3>' +
                '<ul class="casino-discord-apps" id="casino-discord-apps"></ul>' +
                '<p style="font-size:0.78rem;opacity:0.75;margin-top:0.5rem">Bot commands: <code>/play</code> <code>/casino</code> <code>/hosting</code> <code>/shop</code> <code>/earn</code> <code>/quests</code></p></section>' +
                '</div>';
            var linkSt = $('casino-discord-link-status');
            if (st.linked) {
                var welcomeNote = earn.welcome_reward_claimed ? '' : ' · 50 MN2 welcome available on first /link';
                linkSt.textContent = '✅ Linked as ' + (st.discord_id || 'Discord user') + welcomeNote;
            } else {
                linkSt.textContent = 'Not linked — generate a code and run /link in Discord for **50 MN2** welcome bonus.';
            }
            $('casino-discord-lifetime').textContent = earn.lifetime_coins || 0;
            $('casino-discord-today').textContent = earn.today_coins || 0;
            $('casino-discord-cap').textContent = earn.daily_cap || 250;
            var dailyBtn = $('casino-discord-daily');
            if (dailyBtn) {
                dailyBtn.disabled = !st.linked || earn.daily_claimed_today;
                dailyBtn.textContent = earn.daily_claimed_today ? 'Daily claimed' : 'Claim Discord daily';
                dailyBtn.addEventListener('click', function () {
                    api('POST', '/api/discord/controller/daily-claim').then(function (res) {
                        if (res.success) renderDiscord();
                        else alert(res.error || 'Claim failed');
                    });
                });
            }
            var genBtn = $('casino-discord-gen-code');
            if (genBtn) {
                genBtn.addEventListener('click', function () {
                    api('POST', '/api/discord/controller/link-code').then(function (res) {
                        if (!res.success) {
                            alert(res.error || 'Could not generate code');
                            return;
                        }
                        $('casino-discord-code-box').classList.remove('hidden');
                        $('casino-discord-code').textContent = res.code;
                    });
                });
            }
            var appsUl = $('casino-discord-apps');
            (manifest.activities || []).forEach(function (act) {
                var li = document.createElement('li');
                li.innerHTML = (act.icon || '•') + ' <a href="' + (act.full_url || act.url) + '" target="_blank" rel="noopener">' +
                    (act.name || act.id) + '</a> — ' + (act.description || '');
                appsUl.appendChild(li);
            });
        });
    }

    function init() {
        injectDiscordTab();
        var params = new URLSearchParams(window.location.search);
        if (params.get('tab') === 'discord') {
            var btn = document.querySelector('.casino-v10-main-tab[data-v10-tab="discord"]');
            if (btn) btn.click();
        }
        window.addEventListener('casino-bet-complete', function () {
            if (document.body.getAttribute('data-casino-v10-tab') === 'discord') renderDiscord();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
