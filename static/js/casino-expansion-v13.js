(function () {
    'use strict';

    var userId = localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
    var guidesCache = null;

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

    function injectIntelTab() {
        var nav = $('casino-v10-main-nav');
        if (!nav || nav.querySelector('[data-v10-tab="intel"]')) return;
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'casino-v10-main-tab';
        btn.setAttribute('data-v10-tab', 'intel');
        btn.setAttribute('role', 'tab');
        btn.textContent = 'Intel & Bot';
        var agentsTab = nav.querySelector('[data-v10-tab="agents"]');
        if (agentsTab && agentsTab.parentNode) {
            agentsTab.parentNode.insertBefore(btn, agentsTab);
        } else {
            nav.appendChild(btn);
        }
        var page = document.querySelector('.casino-page');
        if (!page || $('casino-v13-intel')) return;
        var sec = document.createElement('section');
        sec.id = 'casino-v13-intel';
        sec.className = 'casino-v13-panel casino-v10-panel hidden';
        sec.setAttribute('aria-label', 'Casino intelligence');
        var agents = $('casino-v10-agents');
        if (agents && agents.parentNode) {
            agents.parentNode.insertBefore(sec, agents);
        } else {
            page.appendChild(sec);
        }
    }

    function patchTabs() {
        document.querySelectorAll('.casino-v10-main-tab').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var tab = btn.getAttribute('data-v10-tab');
                var intel = $('casino-v13-intel');
                if (intel) intel.classList.toggle('hidden', tab !== 'intel');
                if (tab === 'intel') renderIntel();
            });
        });
    }

    function loadGuides() {
        if (guidesCache) return Promise.resolve(guidesCache);
        return api('GET', '/api/casino/guides').then(function (d) {
            guidesCache = (d && d.games) || {};
            return guidesCache;
        });
    }

    function renderIntel() {
        var root = $('casino-v13-intel');
        if (!root) return;
        root.innerHTML = '<p>Loading calculators, future sights &amp; agent bot…</p>';
        Promise.all([
            api('GET', '/api/casino/intel/hub'),
            api('GET', '/api/agent/casino/agents'),
            loadGuides(),
        ]).then(function (parts) {
            var hub = parts[0] || {};
            var agents = parts[1] || {};
            var guides = parts[2] || {};
            var sample = hub.sample_game || {};
            var prog = (hub.prognosis && hub.prognosis.future_sights) || [];
            root.innerHTML =
                '<h2 class="casino-subheading">Calculators &amp; future sights</h2>' +
                '<div class="casino-v13-grid" id="casino-v13-calc"></div>' +
                '<h2 class="casino-subheading" style="margin-top:1.5rem">Win / lose guides</h2>' +
                '<div class="casino-v13-grid" id="casino-v13-guides"></div>' +
                '<h2 class="casino-subheading" style="margin-top:1.5rem">Prognoses</h2>' +
                '<div class="casino-v13-grid" id="casino-v13-prog"></div>' +
                '<h2 class="casino-subheading" style="margin-top:1.5rem">Agent bot — play for you</h2>' +
                '<div id="casino-v13-agents"></div>';

            var calcRoot = $('casino-v13-calc');
            if (calcRoot) {
                var card = document.createElement('article');
                card.className = 'casino-v13-card';
                card.innerHTML =
                    '<h3>' + (sample.label || sample.game_id || 'Sample game') + '</h3>' +
                    '<p>RTP ~' + ((sample.rtp && sample.rtp.rtp_percent) || '—') + '% · ' +
                    'Win ~' + (((sample.win_probability && sample.win_probability.win_probability) || 0) * 100).toFixed(1) + '%</p>' +
                    '<p>EV: ' + ((sample.expected_value && sample.expected_value.expected_net) || 0) + ' · ' +
                    'Kelly stake: ' + ((sample.kelly && sample.kelly.suggested_stake) || 0) + '</p>';
                calcRoot.appendChild(card);
                (hub.calculators || []).forEach(function (c) {
                    var ccard = document.createElement('article');
                    ccard.className = 'casino-v13-card';
                    ccard.innerHTML = '<h3>' + c.id + '</h3><p>' + c.description + '</p>';
                    calcRoot.appendChild(ccard);
                });
            }

            var guideRoot = $('casino-v13-guides');
            if (guideRoot) {
                Object.keys(guides).forEach(function (gid) {
                    var g = guides[gid];
                    var el = document.createElement('article');
                    el.className = 'casino-v13-card';
                    el.innerHTML =
                        '<h3>' + gid.replace(/_/g, ' ') + '</h3>' +
                        '<p class="casino-v13-win"><strong>Win:</strong> ' + (g.win || '') + '</p>' +
                        '<p class="casino-v13-lose"><strong>Lose:</strong> ' + (g.lose || '') + '</p>' +
                        '<p>' + (g.payout || '') + '</p>' +
                        '<p class="casino-v13-tip">' + (g.tip || '') + '</p>';
                    guideRoot.appendChild(el);
                });
            }

            var progRoot = $('casino-v13-prog');
            if (progRoot) {
                prog.forEach(function (p) {
                    var el = document.createElement('article');
                    el.className = 'casino-v13-card';
                    el.innerHTML =
                        '<h3>' + (p.title || p.id || 'Sight') + '</h3>' +
                        '<p>' + (p.play_hint || '') + '</p>' +
                        (p.signal ? '<p>Signal: <strong>' + p.signal + '</strong> (' + Math.round((p.confidence || 0) * 100) + '%)</p>' : '');
                    progRoot.appendChild(el);
                });
            }

            var agentRoot = $('casino-v13-agents');
            if (agentRoot) {
                var list = agents.agents || [];
                if (!list.length) {
                    agentRoot.innerHTML = '<p>No agents configured. Set AGENT_CASINO_SECRET and data/casino_agents.json on the server.</p>';
                    return;
                }
                agentRoot.innerHTML = '<div class="casino-v13-grid"></div>';
                var grid = agentRoot.querySelector('.casino-v13-grid');
                list.forEach(function (a) {
                    var card = document.createElement('article');
                    card.className = 'casino-v13-card';
                    card.innerHTML =
                        '<h3>' + (a.model_name || a.agent_id) + '</h3>' +
                        '<p>' + (a.spectator_persona || 'Auto-plays preferred games.') + '</p>' +
                        '<p><small>' + (a.enabled ? 'Enabled' : 'Disabled') + ' · user ' + (a.user_id || '') + '</small></p>' +
                        '<div class="casino-v13-agent-row">' +
                        '<button type="button" class="casino-v13-btn secondary" data-dry="1">Dry-run plan</button>' +
                        '</div>';
                    var dryBtn = card.querySelector('[data-dry="1"]');
                    dryBtn.addEventListener('click', function () {
                        dryBtn.disabled = true;
                        dryBtn.textContent = 'Planning…';
                        api('GET', '/api/casino/calculators/calculate_for_game?game_id=dice&bet=10&balance=1000')
                            .then(function () {
                                alert('Dry-run uses server cron with X-Agent-Casino-Key. Ask admin to POST /api/agent/casino/run-all');
                            })
                            .finally(function () {
                                dryBtn.disabled = false;
                                dryBtn.textContent = 'Dry-run plan';
                            });
                    });
                    grid.appendChild(card);
                });
            }
        }).catch(function () {
            root.innerHTML = '<p>Could not load intel hub.</p>';
        });
    }

    function injectGameGuides() {
        loadGuides().then(function (guides) {
            document.querySelectorAll('[data-casino-game]').forEach(function (card) {
                var gid = card.getAttribute('data-casino-game');
                var g = guides[gid];
                if (!g || card.querySelector('.casino-game-guide-banner')) return;
                var banner = document.createElement('div');
                banner.className = 'casino-game-guide-banner';
                banner.innerHTML =
                    '<strong>How to win / lose</strong>' +
                    '<span class="casino-v13-win">Win: ' + g.win + '</span> · ' +
                    '<span class="casino-v13-lose">Lose: ' + g.lose + '</span>';
                card.insertBefore(banner, card.firstChild);
            });
        });
    }

    function init() {
        injectIntelTab();
        patchTabs();
        setTimeout(injectGameGuides, 1200);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
