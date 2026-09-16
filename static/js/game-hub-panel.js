/**

 * Game Hub — unified frontpage panel (Trophies · Quests · Game · Battle · Story)

 */

(function () {

    'use strict';



    const HUB = {

        userId: localStorage.getItem('game_user_id') || 'default_user',

        data: null,

        tab: 'trophies',

        questFilter: 'all',

    };



    function esc(s) {

        return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

    }



    function fmt(n, d) {

        return (parseFloat(n) || 0).toLocaleString(undefined, { maximumFractionDigits: d == null ? 2 : d });

    }



    async function loadOverview() {

        const r = await fetch('/api/game-hub/overview?user_id=' + encodeURIComponent(HUB.userId));

        if (!r.ok) throw new Error('overview ' + r.status);

        const d = await r.json();

        if (!d.success) throw new Error(d.error || 'overview failed');

        HUB.data = d;

        render();

    }



    async function claimQuest(questId, btn) {

        if (!questId || !btn) return;

        btn.disabled = true;

        btn.textContent = 'Claiming…';

        try {

            const r = await fetch('/api/game-hub/quests/claim', {

                method: 'POST',

                headers: { 'Content-Type': 'application/json' },

                body: JSON.stringify({ user_id: HUB.userId, quest_id: questId }),

            });

            const d = await r.json();

            if (d.success) {

                btn.textContent = d.streak_bonus_mn2 ? 'Claimed ✓ +' + fmt(d.streak_bonus_mn2, 4) + ' MN2 streak' : 'Claimed ✓';

                btn.classList.add('is-claimed');

                await loadOverview();

            } else {

                btn.disabled = false;

                btn.textContent = d.error || 'Retry';

            }

        } catch (e) {

            btn.disabled = false;

            btn.textContent = 'Retry';

        }

    }



    function updateNotificationDot(root) {

        const claimable = (HUB.data && HUB.data.summary && HUB.data.summary.claimable) || 0;

        root.querySelectorAll('[data-gh-tab]').forEach(function (btn) {

            const tab = btn.getAttribute('data-gh-tab');

            let dot = btn.querySelector('.gh-tab-dot');

            if (tab === 'quests' && claimable > 0) {

                if (!dot) {

                    dot = document.createElement('span');

                    dot.className = 'gh-tab-dot';

                    dot.setAttribute('aria-label', claimable + ' ready to claim');

                    btn.appendChild(dot);

                }

                dot.textContent = claimable > 9 ? '9+' : String(claimable);

            } else if (dot) {

                dot.remove();

            }

        });

    }



    function bindTabs(root) {

        root.querySelectorAll('[data-gh-tab]').forEach(function (btn) {

            btn.addEventListener('click', function () {

                HUB.tab = btn.getAttribute('data-gh-tab') || 'trophies';

                root.querySelectorAll('[data-gh-tab]').forEach(function (b) {

                    b.classList.toggle('is-active', b === btn);

                    b.setAttribute('aria-selected', b === btn ? 'true' : 'false');

                });

                renderPanel(root);

            });

        });

    }



    function filterQuests(quests, filter) {

        if (!quests) return [];

        if (filter === 'all') return quests;

        return quests.filter(function (q) { return q.source === filter; });

    }



    function renderQuestRows(quests) {

        if (!quests || !quests.length) {

            return '<p class="gh-empty">No quests in this category right now.</p>';

        }

        return quests.map(function (q) {

            const pct = q.target ? Math.min(100, Math.round(((q.progress || 0) / q.target) * 100)) : 0;

            const isAi = q.source === 'ai';

            const canClaim = (q.complete && !q.claimed) || (isAi && !q.claimed);

            const src = q.source || 'trophy';

            const mn2 = q.mn2_reward ? ' · +' + fmt(q.mn2_reward, 4) + ' MN2' : '';

            const xp = q.xp_reward ? ' · +' + q.xp_reward + ' XP' : '';

            const coins = q.coin_reward ? ' · +' + q.coin_reward + ' coins' : '';

            const btnLabel = isAi && !q.complete ? 'Complete' : 'Claim';

            return (

                '<article class="gh-quest-row ' + (q.claimed ? 'is-claimed' : q.complete ? 'is-done' : '') + '">' +

                '<div class="gh-quest-head">' +

                '<span class="gh-quest-badge gh-quest-badge--' + esc(src) + '">' + esc(q.scope || src) + '</span>' +

                '<strong>' + esc(q.title) + '</strong>' +

                '</div>' +

                (q.description ? '<p class="gh-quest-desc">' + esc(q.description) + '</p>' : '') +

                '<div class="gh-progress"><div class="gh-progress-fill" style="width:' + pct + '%"></div></div>' +

                '<div class="gh-quest-meta">' +

                '<span>' + (q.progress || 0) + ' / ' + q.target + '</span>' +

                '<span>+' + (q.reward || 0) + ' pts' + mn2 + xp + coins + '</span>' +

                '</div>' +

                (canClaim

                    ? '<button type="button" class="gh-claim-btn" data-quest-id="' + esc(q.id) + '">' + btnLabel + '</button>'

                    : (q.claimed ? '<span class="gh-claimed-label">Claimed</span>' : '')) +

                '</article>'

            );

        }).join('');

    }



    function renderQuestSubTabs(qd) {

        const counts = {

            all: (qd.quests || []).length,

            trophy: (qd.trophy_quests || []).length,

            platform: (qd.platform_quests || []).length,

            ai: (qd.ai_quests || []).length,

            casino: (qd.casino_quests || []).length,

        };

        const filters = [

            ['all', 'All'],

            ['trophy', 'Trophy'],

            ['platform', 'Platform'],

            ['ai', 'AI daily'],

            ['casino', 'Casino'],

        ];

        return (

            '<div class="gh-quest-filters" role="tablist" aria-label="Quest categories">' +

            filters.map(function (pair) {

                const id = pair[0];

                const label = pair[1];

                const n = counts[id] || 0;

                if (id !== 'all' && n === 0) return '';

                return (

                    '<button type="button" class="gh-quest-filter' + (HUB.questFilter === id ? ' is-active' : '') + '" data-gh-quest-filter="' + id + '">' +

                    esc(label) + (n ? ' <span class="gh-filter-count">' + n + '</span>' : '') +

                    '</button>'

                );

            }).join('') +

            '</div>'

        );

    }



    function renderStreakStrip(streak) {

        if (!streak) return '';

        const days = streak.days || 0;

        const target = streak.bonus_at_day || 7;

        const pct = Math.min(100, Math.round((days / target) * 100));

        return (

            '<div class="gh-streak">' +

            '<div class="gh-streak-head"><span>Claim streak</span><span>' + days + ' / ' + target + ' days</span></div>' +

            '<div class="gh-progress"><div class="gh-progress-fill gh-progress-fill--streak" style="width:' + pct + '%"></div></div>' +

            '<p class="gh-streak-note">Claim any quest daily — day ' + target + ' awards +' + fmt(streak.bonus_mn2 || 0.007, 4) + ' MN2</p>' +

            '</div>'

        );

    }



    function renderLeaderboard(entries, yourRank) {

        if (!entries || !entries.length) {

            return '<p class="gh-empty gh-lb-empty">Leaderboard fills as collectors earn trophy points.</p>';

        }

        const rankLine = yourRank ? '<p class="gh-lb-you">Your rank: #' + yourRank + '</p>' : '';

        return (

            rankLine +

            '<ol class="gh-lb">' +

            entries.slice(0, 5).map(function (e) {

                const medal = e.rank === 1 ? '🥇' : e.rank === 2 ? '🥈' : e.rank === 3 ? '🥉' : e.rank + '.';

                return (

                    '<li><span class="gh-lb-rank">' + medal + '</span>' +

                    '<span class="gh-lb-user">' + esc(e.user_id) + '</span>' +

                    '<span class="gh-lb-pts">' + fmt(e.trophy_points, 0) + ' pts</span></li>'

                );

            }).join('') +

            '</ol>'

        );

    }



    function renderBattleMatches(matches) {

        if (!matches || !matches.length) {

            return '<p class="gh-empty">No recent battles yet — jump into the arena!</p>';

        }

        return (

            '<ul class="gh-match-list">' +

            matches.map(function (m) {

                const res = (m.result || 'unknown').toLowerCase();

                const cls = res === 'win' ? 'is-win' : res === 'loss' ? 'is-loss' : 'is-draw';

                const delta = m.points_delta != null ? (m.points_delta >= 0 ? '+' : '') + m.points_delta + ' pts' : '';

                return (

                    '<li class="gh-match ' + cls + '">' +

                    '<span class="gh-match-result">' + esc(res) + '</span>' +

                    '<span class="gh-match-meta">' + esc(m.difficulty || m.opponent_type || 'battle') + '</span>' +

                    (delta ? '<span class="gh-match-delta">' + esc(delta) + '</span>' : '') +

                    '</li>'

                );

            }).join('') +

            '</ul>'

        );

    }



    function renderPanel(root) {

        const panel = root.querySelector('#gh-panel');

        if (!panel || !HUB.data) return;

        const t = HUB.data.tabs || {};

        let html = '';



        if (HUB.tab === 'trophies') {

            const tr = t.trophies || {};

            html =

                '<div class="gh-stat-grid">' +

                '<div class="gh-stat"><span class="gh-stat-v">' + esc(tr.level_name || '—') + '</span><span class="gh-stat-l">Collector</span></div>' +

                '<div class="gh-stat"><span class="gh-stat-v">' + fmt(tr.unlocked_count, 0) + '</span><span class="gh-stat-l">Unlocked</span></div>' +

                '<div class="gh-stat"><span class="gh-stat-v">' + fmt(tr.pending_income, 0) + '</span><span class="gh-stat-l">Pending pts</span></div>' +

                '<div class="gh-stat"><span class="gh-stat-v">' + fmt(tr.pending_income_mn2, 4) + '</span><span class="gh-stat-l">Pending MN2</span></div>' +

                '</div>' +

                '<div class="gh-lb-block">' +

                '<p class="gh-block-title">Top collectors</p>' +

                renderLeaderboard(tr.leaderboard, tr.your_rank) +

                '</div>' +

                '<a class="gh-open-link" href="' + esc(tr.link || '/trophies/') + '">Open trophy room →</a>';

        } else if (HUB.tab === 'quests') {

            const qd = t.quests || {};

            const filtered = filterQuests(qd.quests, HUB.questFilter);

            html =

                '<p class="gh-summary">' + (qd.claimable || 0) + ' ready to claim · ' + (qd.active || 0) + ' active</p>' +

                renderStreakStrip(qd.claim_streak) +

                renderQuestSubTabs(qd) +

                renderQuestRows(filtered.slice(0, 8)) +

                '<a class="gh-open-link" href="' + esc(qd.link || '/quests/') + '">Full quest board →</a>';

        } else if (HUB.tab === 'game') {

            const g = t.game || {};

            const mission = g.active_mission;

            html =

                '<div class="gh-stat-grid">' +

                '<div class="gh-stat"><span class="gh-stat-v">Lv ' + fmt(g.hunter_level || g.level, 0) + '</span><span class="gh-stat-l">Hunter</span></div>' +

                '<div class="gh-stat"><span class="gh-stat-v">' + esc(g.hunter_title || 'Novice') + '</span><span class="gh-stat-l">Title</span></div>' +

                '<div class="gh-stat"><span class="gh-stat-v">' + fmt(g.xp_total, 0) + '</span><span class="gh-stat-l">XP</span></div>' +

                '<div class="gh-stat"><span class="gh-stat-v">' + fmt(g.game_points, 0) + '</span><span class="gh-stat-l">Game pts</span></div>' +

                '</div>' +

                (mission

                    ? '<div class="gh-mission"><p class="gh-block-title">Active mission</p>' +

                      '<p class="gh-mission-title">' + esc(mission.title) + '</p>' +

                      '<p class="gh-mission-meta">' + esc(mission.source || 'quest') + ' · ' + (mission.progress || 0) + ' / ' + (mission.target || 1) + '</p></div>'

                    : '<p class="gh-empty">All missions complete — new quests refresh daily.</p>') +

                '<a class="gh-open-link" href="' + esc(g.link || '/game/') + '">Enter game hub →</a>';

        } else if (HUB.tab === 'battle') {

            const b = t.battle || {};

            html =

                '<div class="gh-stat-grid gh-stat-grid-2">' +

                '<div class="gh-stat"><span class="gh-stat-v">' + fmt(b.battle_points, 0) + '</span><span class="gh-stat-l">Battle pts</span></div>' +

                '<div class="gh-stat"><span class="gh-stat-v">' + fmt(b.wins, 0) + '</span><span class="gh-stat-l">Recent wins</span></div>' +

                '</div>' +

                '<div class="gh-match-block"><p class="gh-block-title">Last 3 matches</p>' +

                renderBattleMatches(b.recent_matches) + '</div>' +

                '<div class="gh-action-row">' +

                '<a class="gh-open-link" href="' + esc(b.link || '/battle/') + '">Battle arena →</a>' +

                '<a class="gh-secondary-link" href="' + esc(b.quick_battle || '/battle/#quick') + '">Quick battle</a>' +

                '</div>';

        } else if (HUB.tab === 'story') {

            const st = t.story || {};

            const cont = st.continue_story || {};

            html =

                '<div class="gh-stat-grid gh-stat-grid-2">' +

                '<div class="gh-stat"><span class="gh-stat-v">' + (st.read_count || 0) + ' / ' + (st.count || 0) + '</span><span class="gh-stat-l">Stories read</span></div>' +

                '<div class="gh-stat"><span class="gh-stat-v">' + (st.read_percent || 0) + '%</span><span class="gh-stat-l">Progress</span></div>' +

                '</div>' +

                (cont.title

                    ? '<a class="gh-continue-cta" href="' + esc(st.continue_link || st.link || '/trophies/#stories') + '">' +

                      '<span class="gh-continue-icon">' + esc(cont.icon || '📖') + '</span>' +

                      '<span><strong>Continue reading</strong><br><span class="gh-continue-sub">' + esc(cont.title) + '</span></span></a>'

                    : '') +

                '<a class="gh-open-link" href="' + esc(st.link || '/game/#stories') + '">All stories →</a>';

        }

        html += '<a class="gh-secondary-link gh-library-link" href="/compendium/?calm=1">📖 Calm library — rulebooks &amp; compendium</a>';

        panel.innerHTML = html;

        panel.querySelectorAll('.gh-claim-btn').forEach(function (btn) {

            btn.addEventListener('click', function () {

                claimQuest(btn.getAttribute('data-quest-id'), btn);

            });

        });

        panel.querySelectorAll('[data-gh-quest-filter]').forEach(function (btn) {

            btn.addEventListener('click', function () {

                HUB.questFilter = btn.getAttribute('data-gh-quest-filter') || 'all';

                renderPanel(root);

            });

        });

    }



    function render() {

        const root = document.getElementById('fp-game-hub');

        if (!root) return;

        updateNotificationDot(root);

        renderPanel(root);

    }



    function init() {

        const root = document.getElementById('fp-game-hub');

        if (!root) return;

        bindTabs(root);

        const status = root.querySelector('#gh-status');

        loadOverview()

            .then(function () {

                if (status) status.textContent = 'Live';

            })

            .catch(function (e) {

                if (status) status.textContent = 'Offline';

                const panel = root.querySelector('#gh-panel');

                if (panel) panel.innerHTML = '<p class="gh-empty">Game hub loading failed. Try refresh.</p>';

                console.warn('[GameHub]', e);

            });

        setInterval(loadOverview, 60000);

    }



    if (document.readyState === 'loading') {

        document.addEventListener('DOMContentLoaded', init);

    } else {

        init();

    }

})();


