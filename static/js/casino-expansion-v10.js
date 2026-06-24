(function () {
    'use strict';

    var userId = localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
    var progression = null;
    var status = null;
    var _casinoChatPortal = null;

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

    function setTab(tab) {
        document.body.setAttribute('data-casino-v10-tab', tab);
        document.querySelectorAll('.casino-v10-main-tab').forEach(function (btn) {
            btn.classList.toggle('active', btn.getAttribute('data-v10-tab') === tab);
        });
        ['walk', 'agents', 'trophies', 'levels', 'social'].forEach(function (name) {
            var el = $('casino-v10-' + name);
            if (el) el.classList.toggle('hidden', tab !== name);
        });
    }

    function applyFxTier(fx) {
        document.body.classList.remove('casino-fx-minimal', 'casino-fx-glow', 'casino-fx-neon', 'casino-fx-hologram', 'casino-fx-cinematic');
        if (fx) document.body.classList.add('casino-fx-' + fx);
    }

    function renderLevelBadge() {
        var el = $('casino-v10-level-badge');
        if (!el || !status) return;
        var fx = (status.fx_tier && status.fx_tier.label) || 'Rookie';
        el.textContent = 'Level ' + (status.level || 1) + ' · ' + fx + ' · ' + (status.xp || 0) + ' XP';
        applyFxTier((status.fx_tier && status.fx_tier.fx) || 'minimal');
    }

    function renderWalk() {
        var root = $('casino-v10-walk');
        if (!root || !status) return;
        var walk = status.walk || {};
        var steps = walk.steps || [];
        root.innerHTML = '<h2 class="casino-subheading">Daily walk — ' + (walk.completed_count || 0) + '/' + (walk.total || 0) + '</h2>' +
            '<div class="casino-walk-track"></div>';
        var track = root.querySelector('.casino-walk-track');
        steps.forEach(function (step) {
            var card = document.createElement('article');
            card.className = 'casino-walk-step' + (step.completed ? ' done' : '') + (step.active ? ' active' : '');
            card.innerHTML =
                '<div class="casino-walk-clip"><img src="' + (step.clip || '/static/img/casino/previews/game-loop.svg') + '" alt="" width="100" height="72"></div>' +
                '<div><strong>' + step.title + '</strong><p>' + step.description + '</p>' +
                '<div class="casino-walk-actions"></div></div>';
            var actions = card.querySelector('.casino-walk-actions');
            if (!step.completed) {
                if (step.assign_agent) {
                    var sel = document.createElement('select');
                    sel.setAttribute('aria-label', 'Assign agent');
                    (step.agent_pool || []).forEach(function (aid) {
                        var role = (progression.agent_casino_roles || []).find(function (a) { return a.id === aid; });
                        var opt = document.createElement('option');
                        opt.value = aid;
                        opt.textContent = role ? role.name : aid;
                        sel.appendChild(opt);
                    });
                    var assignBtn = document.createElement('button');
                    assignBtn.type = 'button';
                    assignBtn.textContent = 'Assign advisor';
                    assignBtn.addEventListener('click', function () {
                        api('POST', '/api/casino/progression/agent/assign', { agent_id: sel.value }).then(refresh);
                    });
                    actions.appendChild(sel);
                    actions.appendChild(assignBtn);
                }
                var goBtn = document.createElement('button');
                goBtn.type = 'button';
                goBtn.textContent = step.click_action === 'open_games' ? 'Go to games' : 'Complete step';
                goBtn.addEventListener('click', function () {
                    if (step.click_action === 'open_games') setTab('games');
                    else if (step.click_action === 'open_lobby') setTab('lobby');
                    else if (step.click_action === 'open_quests') setTab('lobby');
                    api('POST', '/api/casino/progression/walk/complete', { step_id: step.id }).then(function (res) {
                        if (res.success) refresh();
                        else if (res.error) alert(res.error);
                    });
                });
                actions.appendChild(goBtn);
            }
            track.appendChild(card);
        });
    }

    function renderAgents() {
        var root = $('casino-v10-agents');
        if (!root || !progression) return;
        var roles = progression.agent_casino_roles || [];
        root.innerHTML = '<h2 class="casino-subheading">Strategy advisors</h2><p style="opacity:0.85;font-size:0.88rem;">Assign traders or camgirls to coach your casino session.</p><div class="casino-agents-grid"></div>';
        var grid = root.querySelector('.casino-agents-grid');
        roles.forEach(function (role) {
            var card = document.createElement('article');
            card.className = 'casino-agent-card' + (status && status.assigned_agent === role.id ? ' assigned' : '');
            card.innerHTML = '<div class="casino-agent-type">' + role.type + '</div><h3>' + role.name + '</h3><p><em>' + role.focus + '</em></p><p>' + role.strategy_tip + '</p>';
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'casino-open-game-btn';
            btn.textContent = status && status.assigned_agent === role.id ? 'Assigned' : 'Assign';
            btn.disabled = status && status.assigned_agent === role.id;
            btn.addEventListener('click', function () {
                api('POST', '/api/casino/progression/agent/assign', { agent_id: role.id }).then(refresh);
            });
            card.appendChild(btn);
            grid.appendChild(card);
        });
    }

    function renderTrophies() {
        var root = $('casino-v10-trophies');
        if (!root || !status) return;
        var trophies = status.trophies || [];
        root.innerHTML = '<h2 class="casino-subheading">Trophy hall</h2><div class="casino-trophy-grid"></div><h3 class="casino-subheading">Achievement history</h3><ul class="casino-achievement-history"></ul>';
        var grid = root.querySelector('.casino-trophy-grid');
        trophies.forEach(function (tr) {
            var pct = Math.min(100, Math.round((tr.progress / Math.max(1, tr.target)) * 100));
            var card = document.createElement('article');
            card.className = 'casino-trophy-card' + (tr.earned ? ' earned' : '');
            card.innerHTML = '<div style="font-size:2rem">' + (tr.icon || '🏆') + '</div><strong>' + tr.name + '</strong><p style="font-size:0.82rem">' + tr.description + '</p>' +
                '<div class="casino-trophy-progress"><span style="width:' + pct + '%"></span></div><small>' + tr.progress + '/' + tr.target + '</small>';
            grid.appendChild(card);
        });
        var hist = root.querySelector('.casino-achievement-history');
        (status.achievement_history || []).slice().reverse().forEach(function (row) {
            var li = document.createElement('li');
            li.textContent = (row.at || '') + ' — ' + (row.type || '') + (row.trophy_id ? ' (' + row.trophy_id + ')' : '');
            hist.appendChild(li);
        });
    }

    function renderSocial() {
        var root = $('casino-v10-social');
        if (!root) return;
        if (_casinoChatPortal && _casinoChatPortal.destroy) {
            _casinoChatPortal.destroy();
            _casinoChatPortal = null;
        }
        root.innerHTML = '<p class="casino-social-loading">Loading social lounge…</p>';
        api('GET', '/api/casino/social/hub').then(function (hub) {
            if (!hub.success) {
                root.innerHTML = '<p>' + (hub.error || 'Social unavailable') + '</p>';
                return;
            }
            var summary = hub.summary || {};
            var crew = summary.crew || {};
            root.innerHTML =
                '<h2 class="casino-subheading">Social lounge</h2>' +
                '<div class="casino-social-summary">' +
                '<span>' + (summary.friends_count || 0) + ' friends</span>' +
                '<span>' + (crew.name ? 'Crew: ' + crew.name : 'No crew') + '</span>' +
                '<span>' + (summary.pending_challenges_count || 0) + ' challenges</span>' +
                '</div>' +
                '<div class="casino-social-grid">' +
                '<section class="casino-social-card"><h3>Friends</h3>' +
                '<div class="casino-social-add"><input type="text" id="casino-social-friend-id" placeholder="Friend user id" aria-label="Friend user id">' +
                '<button type="button" id="casino-social-friend-add">Add friend</button></div>' +
                '<ul class="casino-social-friends" id="casino-social-friends"></ul></section>' +
                '<section class="casino-social-card"><h3>Crew board</h3>' +
                '<ul class="casino-social-mini-board" id="casino-social-mini-board"></ul></section>' +
                '<section class="casino-social-card casino-social-card-wide"><h3>Activity feed</h3>' +
                '<ul class="casino-social-feed" id="casino-social-feed"></ul></section>' +
                '<section class="casino-social-card"><h3>Challenge a friend</h3>' +
                '<select id="casino-social-challenge-friend" aria-label="Friend to challenge"></select>' +
                '<select id="casino-social-challenge-type" aria-label="Challenge type"></select>' +
                '<button type="button" id="casino-social-challenge-send">Send challenge</button>' +
                '<ul class="casino-social-challenges" id="casino-social-challenges"></ul></section>' +
                '<section class="casino-social-card"><h3>Share</h3>' +
                '<p class="casino-social-share-note">Share wins when enabled in preferences.</p>' +
                '<div class="casino-social-share-btns" id="casino-social-share-btns"></div></section>' +
                '<section class="casino-social-card casino-social-card-wide"><h3>Cross-network chat</h3>' +
                '<p class="casino-social-share-note">Post to casino lounge and all linked social networks.</p>' +
                '<div id="casino-social-chat-portal"></div></section>' +
                '</div>';
            var friendsUl = $('casino-social-friends');
            (hub.friends || []).forEach(function (fr) {
                var li = document.createElement('li');
                li.textContent = fr.display_name + ' (' + fr.user_id + ')';
                friendsUl.appendChild(li);
            });
            var boardUl = $('casino-social-mini-board');
            (hub.mini_board || []).forEach(function (row, i) {
                var li = document.createElement('li');
                li.textContent = '#' + (i + 1) + ' ' + (row.display_name || row.user_id) + ' — net ' + (row.net || 0);
                boardUl.appendChild(li);
            });
            if (!(hub.mini_board || []).length) {
                boardUl.innerHTML = '<li>No peer scores yet — add friends first.</li>';
            }
            var feedUl = $('casino-social-feed');
            (hub.feed || []).forEach(function (item) {
                var li = document.createElement('li');
                li.innerHTML = '<time>' + (item.ts || '') + '</time> <strong>' + (item.display_name || item.user_id) + '</strong> — ' + (item.label || item.action_type);
                feedUl.appendChild(li);
            });
            if (!(hub.feed || []).length) {
                feedUl.innerHTML = '<li>Play and complete walk steps to populate the feed.</li>';
            }
            var friendSel = $('casino-social-challenge-friend');
            var typeSel = $('casino-social-challenge-type');
            (hub.friends || []).forEach(function (fr) {
                var opt = document.createElement('option');
                opt.value = fr.user_id;
                opt.textContent = fr.display_name;
                friendSel.appendChild(opt);
            });
            (hub.challenge_types || []).forEach(function (ct) {
                var opt = document.createElement('option');
                opt.value = ct.id;
                opt.textContent = ct.label;
                typeSel.appendChild(opt);
            });
            var challUl = $('casino-social-challenges');
            (hub.challenges || []).slice(0, 10).forEach(function (ch) {
                var li = document.createElement('li');
                li.textContent = (ch.challenge_type || 'challenge') + ' · ' + (ch.status || 'pending') + ' · ' + (ch.from_user_id || '') + ' → ' + (ch.to_user_id || '');
                challUl.appendChild(li);
            });
            var shareRoot = $('casino-social-share-btns');
            var networks = (hub.share_networks && hub.share_networks.networks) || [];
            var shareText = encodeURIComponent(hub.share_default_text || 'MasterNoder Casino');
            var shareUrl = encodeURIComponent('https://masternoder.dk/casino/?tab=social');
            networks.forEach(function (net) {
                var a = document.createElement('a');
                a.className = 'casino-social-share-btn';
                a.target = '_blank';
                a.rel = 'noopener';
                a.textContent = net.name || net.id;
                var tpl = net.share_url || '';
                a.href = tpl.replace('{url}', shareUrl).replace('{text}', shareText);
                shareRoot.appendChild(a);
            });
            var addBtn = $('casino-social-friend-add');
            if (addBtn) {
                addBtn.addEventListener('click', function () {
                    var fid = ($('casino-social-friend-id').value || '').trim();
                    if (!fid) return;
                    fetch('/api/social/friends/add', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'same-origin',
                        body: JSON.stringify({ user_id: userId, friend_id: fid }),
                    }).then(function (r) { return r.json(); }).then(function (res) {
                        if (res.success) renderSocial();
                        else alert(res.error || 'Could not add friend');
                    });
                });
            }
            var sendCh = $('casino-social-challenge-send');
            if (sendCh) {
                sendCh.addEventListener('click', function () {
                    api('POST', '/api/casino/social/challenge', {
                        to_user_id: friendSel.value,
                        challenge_type: typeSel.value,
                    }).then(function (res) {
                        if (res.success) renderSocial();
                        else alert(res.error || 'Challenge failed');
                    });
                });
            }
            var chatMount = $('casino-social-chat-portal');
            if (chatMount && window.SocialChatPortal) {
                _casinoChatPortal = SocialChatPortal.mount(chatMount, { mode: 'compact', site: 'casino', limit: 35 });
            }
        });
    }

    function renderLevels() {
        var root = $('casino-v10-levels');
        if (!root || !progression || !status) return;
        var levels = progression.levels || [];
        var claimed = status.claimed_levels || [];
        var current = status.level || 1;
        root.innerHTML = '<h2 class="casino-subheading">Level rewards (crypto + coins)</h2><div class="casino-levels-ladder"></div>';
        var ladder = root.querySelector('.casino-levels-ladder');
        levels.forEach(function (lv) {
            var lvl = lv.level;
            var row = document.createElement('div');
            row.className = 'casino-level-row' + (lvl === current ? ' current' : '') + (claimed.indexOf(lvl) >= 0 ? ' claimed' : '');
            var rewards = [];
            if (lv.reward_coins) rewards.push(lv.reward_coins + ' coins');
            if (lv.reward_mn2) rewards.push(lv.reward_mn2 + ' MN2');
            row.innerHTML = '<strong>L' + lvl + '</strong><div><strong>' + lv.title + '</strong><br><small>' + (lv.xp_required || 0) + ' XP · FX: ' + (lv.fx_unlock || '') + '</small><br><small>' + rewards.join(' · ') + '</small></div>';
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'casino-level-claim-btn';
            btn.textContent = claimed.indexOf(lvl) >= 0 ? 'Claimed' : 'Claim';
            btn.disabled = lvl > current || claimed.indexOf(lvl) >= 0;
            btn.addEventListener('click', function () {
                api('POST', '/api/casino/progression/level/claim', { level: lvl }).then(refresh);
            });
            row.appendChild(btn);
            ladder.appendChild(row);
        });
    }

    function enhanceGameCards() {
        var media = (progression && progression.game_media) || {};
        document.querySelectorAll('[data-casino-game]').forEach(function (card) {
            if (card.querySelector('.casino-card-preview')) return;
            var gid = card.getAttribute('data-casino-game');
            var m = media[gid] || {};
            var preview = document.createElement('div');
            preview.className = 'casino-card-preview';
            preview.innerHTML = '<img src="' + (m.preview_gif || '/static/img/casino/previews/game-loop.svg') + '" alt="' + (m.clip_label || gid) + '">';
            card.insertBefore(preview, card.querySelector('h2'));
            var openBtn = document.createElement('button');
            openBtn.type = 'button';
            openBtn.className = 'casino-open-game-btn';
            openBtn.textContent = 'Open game page';
            openBtn.addEventListener('click', function (e) {
                e.preventDefault();
                openGamePage(card, gid, m);
            });
            card.appendChild(openBtn);
        });
    }

    function openGamePage(card, gid, media) {
        var page = $('casino-game-page');
        var body = $('casino-game-page-body');
        var heroMedia = $('casino-game-page-media');
        if (!page || !body) return;
        var label = card.getAttribute('data-casino-label') || gid;
        heroMedia.innerHTML = '<img src="' + (media.preview_gif || '/static/img/casino/previews/game-loop.svg') + '" alt="">';
        body.innerHTML = '<div class="casino-game-page-hero"><div></div><div><h2 class="casino-game-page-title">' + label + '</h2><p>' + (media.clip_label || '') + '</p></div></div>';
        var clone = card.cloneNode(true);
        clone.querySelectorAll('.casino-open-game-btn, .casino-card-preview').forEach(function (n) { n.remove(); });
        body.appendChild(clone);
        page.classList.remove('hidden');
        page.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
    }

    function closeGamePage() {
        var page = $('casino-game-page');
        if (!page) return;
        page.classList.add('hidden');
        page.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
    }

    function tagLobbySections() {
        var lobbyIds = [
            'casino-ticker', 'casino-jackpot-bar', 'casino-disclaimer-text', 'casino-rg-banner',
            'casino-currency-bar', 'casino-paypal-deposit', 'casino-mn2-buyin', 'casino-security-bar',
            'casino-balance', 'casino-house-stats', 'casino-rank-bar', 'casino-double-bar',
            'casino-personal-bests', 'casino-side-panels', 'casino-history',
        ];
        lobbyIds.forEach(function (id) {
            var el = $(id);
            if (el) el.classList.add('casino-v10-lobby-only');
        });
        var gn = $('casino-games-nav');
        var gg = $('casino-games-grid');
        if (gn) gn.classList.add('casino-v10-games-only');
        if (gg) gg.classList.add('casino-v10-games-only');
    }

    function refresh() {
        return Promise.all([
            fetch('/api/casino/progression').then(function (r) { return r.json(); }),
            api('GET', '/api/casino/progression/status'),
        ]).then(function (results) {
            progression = results[0];
            status = results[1];
            renderLevelBadge();
            renderWalk();
            renderAgents();
            renderTrophies();
            renderLevels();
            renderSocial();
            enhanceGameCards();
        }).catch(function () { /* silent */ });
    }

    function init() {
        tagLobbySections();
        document.body.setAttribute('data-casino-v10-tab', 'lobby');
        document.querySelectorAll('.casino-v10-main-tab').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var tab = btn.getAttribute('data-v10-tab') || 'lobby';
                setTab(tab);
                if (tab === 'social') renderSocial();
            });
        });
        var params = new URLSearchParams(window.location.search);
        var startTab = params.get('tab');
        if (startTab) {
            setTab(startTab);
            if (startTab === 'social') renderSocial();
        }
        var back = $('casino-game-page-back');
        if (back) back.addEventListener('click', closeGamePage);
        refresh();
        window.addEventListener('casino-bet-complete', function () {
            refresh();
            if (document.body.getAttribute('data-casino-v10-tab') === 'social') renderSocial();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
