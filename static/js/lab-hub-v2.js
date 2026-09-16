/**
 * Lab V2.1 hub — news, systems audit, idea board, AI panel, rewards.
 * Expects: userId, labPostJson, labEscape, labFormatDuration (from lab/index.html).
 */
(function (global) {
    'use strict';

    function esc(s) {
        if (typeof global.labEscape === 'function') return global.labEscape(s);
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function fmtDur(sec) {
        if (typeof global.labFormatDuration === 'function') return global.labFormatDuration(sec);
        return String(sec) + 's';
    }

    async function loadNews() {
        const list = document.getElementById('lab-news-list');
        if (!list) return;
        list.innerHTML = '<p class="lab-muted">Loading lab news…</p>';
        try {
            const r = await fetch('/api/lab/news?limit=12');
            const d = await r.json();
            const items = (d && d.news) || [];
            if (!items.length) {
                list.innerHTML = '<p class="lab-muted">No lab news yet.</p>';
                return;
            }
            list.innerHTML = items.map(function (n) {
                const href = n.href || '/lab/';
                const feat = n.featured ? ' <span class="lab-news-badge">Featured</span>' : '';
                return '<article class="lab-news-item">' +
                    '<h3><a href="' + esc(href) + '">' + esc(n.title || 'Update') + '</a>' + feat + '</h3>' +
                    '<p class="lab-news-meta">' + esc(n.date || '') + ' · ' + esc(n.category || 'lab') + '</p>' +
                    '<p>' + esc(n.summary || '') + '</p></article>';
            }).join('');
        } catch (e) {
            list.innerHTML = '<p class="lab-muted">Could not load news.</p>';
        }
    }

    async function runSystemsCheck() {
        const out = document.getElementById('lab-systems-output');
        const btn = document.getElementById('btn-lab-systems-check');
        if (btn) { btn.disabled = true; btn.textContent = '⏳ Checking…'; }
        if (out) out.innerHTML = '<p class="lab-muted">Running systems audit…</p>';
        try {
            const uid = global.userId || localStorage.getItem('game_user_id') || 'default_user';
            const r = await fetch('/api/lab/systems-check?user_id=' + encodeURIComponent(uid));
            const d = await r.json();
            const checks = (d && d.checks) || [];
            const summary = (d && d.all_ok)
                ? '✅ All ' + (d.passed || 0) + ' / ' + (d.total || 0) + ' checks passed.'
                : '⚠️ ' + (d.passed || 0) + ' / ' + (d.total || 0) + ' checks passed.';
            if (out) {
                out.innerHTML = '<p class="lab-systems-summary">' + esc(summary) + '</p>' +
                    '<table class="lab-systems-table"><thead><tr><th>Check</th><th>Status</th></tr></thead><tbody>' +
                    checks.map(function (c) {
                        return '<tr class="' + (c.ok ? 'ok' : 'fail') + '"><td>' + esc(c.label) + '</td><td>' +
                            (c.ok ? '✅' : '❌ ' + esc(String(c.status || ''))) + '</td></tr>';
                    }).join('') + '</tbody></table>';
            }
            if (d && d.all_ok && typeof global.loadLabV2Status === 'function') {
                global.loadLabV2Status();
            }
        } catch (e) {
            if (out) out.innerHTML = '<p class="lab-muted">Systems check failed.</p>';
        }
        if (btn) { btn.disabled = false; btn.textContent = '⚙️ Recheck all functions'; }
    }

    async function loadIdeaBoard() {
        const list = document.getElementById('lab-idea-list');
        const cdEl = document.getElementById('lab-idea-pin-cooldown');
        const uid = global.userId || localStorage.getItem('game_user_id') || 'default_user';
        try {
            const r = await fetch('/api/lab/idea-board?user_id=' + encodeURIComponent(uid));
            const d = await r.json();
            const cd = Number(d.pin_cooldown_remaining_sec) || 0;
            if (cdEl) {
                cdEl.textContent = cd > 0 ? ('Pin cooldown: ' + fmtDur(cd)) : '';
            }
            const ideas = (d && d.ideas) || [];
            if (!list) return;
            if (!ideas.length) {
                list.innerHTML = '<p class="lab-muted">No pinned ideas yet — add one below.</p>';
                return;
            }
            list.innerHTML = ideas.slice().reverse().map(function (idea) {
                return '<div class="lab-idea-row" data-idea-id="' + esc(idea.id) + '">' +
                    '<strong>' + esc(idea.title) + '</strong> ' +
                    '<span class="lab-idea-meta">(' + esc(idea.track || 'general') + ' · ' + esc(idea.status || 'pinned') + ')</span>' +
                    '<p>' + esc(idea.body || '') + '</p>' +
                    '<div class="lab-actions" style="margin:0;">' +
                    '<button type="button" class="lab-btn lab-btn-info lab-idea-status" data-id="' + esc(idea.id) + '" data-status="in_progress">In progress</button>' +
                    '<button type="button" class="lab-btn lab-btn-success lab-idea-status" data-id="' + esc(idea.id) + '" data-status="shipped">Shipped</button>' +
                    '<button type="button" class="lab-btn lab-btn-primary lab-idea-status" data-id="' + esc(idea.id) + '" data-status="archived">Archive</button>' +
                    '</div></div>';
            }).join('');
            list.querySelectorAll('.lab-idea-status').forEach(function (btn) {
                btn.addEventListener('click', async function () {
                    const iid = btn.getAttribute('data-id');
                    const status = btn.getAttribute('data-status');
                    if (!iid || !status || !global.labPostJson) return;
                    await global.labPostJson('/api/lab/idea-board/' + encodeURIComponent(iid) + '/status', {
                        user_id: uid,
                        status: status
                    });
                    loadIdeaBoard();
                });
            });
        } catch (e) {
            if (list) list.innerHTML = '<p class="lab-muted">Could not load idea board.</p>';
        }
    }

    async function pinIdea() {
        const titleEl = document.getElementById('lab-idea-title');
        const bodyEl = document.getElementById('lab-idea-body');
        const trackEl = document.getElementById('lab-idea-track');
        const statusEl = document.getElementById('lab-idea-form-status');
        const uid = global.userId || localStorage.getItem('game_user_id') || 'default_user';
        const title = (titleEl && titleEl.value || '').trim();
        const body = (bodyEl && bodyEl.value || '').trim();
        const track = (trackEl && trackEl.value) || 'general';
        if (title.length < 2 || body.length < 4) {
            if (statusEl) { statusEl.style.display = 'block'; statusEl.textContent = 'Title (2+) and body (4+) required.'; }
            return;
        }
        if (!global.labPostJson) return;
        const d = await global.labPostJson('/api/lab/idea-board', { user_id: uid, title, body, track });
        if (statusEl) {
            statusEl.style.display = 'block';
            statusEl.textContent = d && d.success ? 'Idea pinned.' : ((d && d.error) || 'Could not pin idea.');
        }
        if (d && d.success) {
            if (titleEl) titleEl.value = '';
            if (bodyEl) bodyEl.value = '';
            loadIdeaBoard();
        }
    }

    async function loadLabV2Status() {
        const panel = document.getElementById('lab-v2-status-panel');
        const aiPanel = document.getElementById('lab-ai-recommendations');
        const uid = global.userId || localStorage.getItem('game_user_id') || 'default_user';
        try {
            const r = await fetch('/api/lab/v2/status?user_id=' + encodeURIComponent(uid));
            const d = await r.json();
            if (!d || !d.success) return;
            if (panel) {
                const prog = d.progression || {};
                const miles = (d.milestones || []).filter(function (m) { return !m.complete; }).slice(0, 4);
                panel.innerHTML =
                    '<div class="lab-mini-grid">' +
                    '<div class="lab-mini-card"><strong>' + esc(prog.tier || 'Novice') + '</strong><span>Tier</span></div>' +
                    '<div class="lab-mini-card"><strong>' + esc(String(prog.researched_count || 0)) + '/' + esc(String(prog.total_research_nodes || 0)) + '</strong><span>Research</span></div>' +
                    '<div class="lab-mini-card"><strong>' + esc(String(prog.score || 0)) + '</strong><span>Score</span></div>' +
                    '<div class="lab-mini-card"><strong>' + esc(String((d.agent_knowledge && d.agent_knowledge.embedded_count) || 0)) + '</strong><span>Agent topics</span></div>' +
                    '</div>' +
                    '<h3 style="margin:14px 0 8px;color:#7fdbff;font-size:0.95rem;">Next milestones</h3>' +
                    '<ul class="lab-v2-milestones">' + miles.map(function (m) {
                        return '<li>' + esc(m.name) + ' (' + esc(String(m.progress)) + '/' + esc(String(m.target)) + ')</li>';
                    }).join('') + '</ul>';
            }
            if (aiPanel) {
                const next = (d.progression && d.progression.next_milestone) || {};
                const tools = ((d.tech && d.tech.tools) || []).slice(0, 6);
                aiPanel.innerHTML =
                    '<p><strong>AI Copilot:</strong> Focus on <em>' + esc(next.name || 'first research') + '</em>.</p>' +
                    '<p>Agent-owned tools: ' + tools.map(esc).join(', ') + '.</p>' +
                    '<p class="lab-muted">Agents summarize and recommend — mutating actions need your explicit click.</p>';
            }
        } catch (e) { /* ignore */ }
    }

    async function loadRewards() {
        const shopEl = document.getElementById('lab-rewards-shop');
        const trophyEl = document.getElementById('lab-rewards-trophies');
        const mn2El = document.getElementById('lab-rewards-mn2');
        const uid = global.userId || localStorage.getItem('game_user_id') || 'default_user';
        try {
            const [shopR, trophyR, mn2R] = await Promise.all([
                fetch('/api/game/shop/items').then(function (x) { return x.json(); }).catch(function () { return {}; }),
                fetch('/api/trophies/definitions').then(function (x) { return x.json(); }).catch(function () { return {}; }),
                fetch('/api/mn2/balance?user_id=' + encodeURIComponent(uid)).then(function (x) { return x.json(); }).catch(function () { return {}; })
            ]);
            const items = ((shopR.items || shopR.data || []) || []).filter(function (it) {
                return (it.category || '') === 'lab' || ((it.tags || []).indexOf('lab') >= 0);
            }).slice(0, 12);
            if (shopEl) {
                shopEl.innerHTML = items.length ? items.map(function (it) {
                    return '<div class="lab-reward-card"><span class="lab-reward-icon">' + esc(it.icon || '🛒') + '</span>' +
                        '<strong>' + esc(it.name) + '</strong><p>' + esc(it.description || '') + '</p>' +
                        '<a href="/shop/" class="lab-btn lab-btn-primary">Shop</a></div>';
                }).join('') : '<p class="lab-muted">No lab shop items loaded.</p>';
            }
            const trophies = (trophyR.trophies || []).filter(function (t) {
                return t.set === 'lab_mastery' || (t.id || '').indexOf('lab_') === 0;
            });
            if (trophyEl) {
                trophyEl.innerHTML = trophies.length ? trophies.map(function (t) {
                    const mn2 = t.mn2_reward ? (' · MN2 ' + t.mn2_reward) : '';
                    return '<div class="lab-reward-card"><span class="lab-reward-icon">' + esc(t.icon || '🏆') + '</span>' +
                        '<strong>' + esc(t.name) + '</strong><p>' + esc(t.description || '') + mn2 + '</p>' +
                        '<a href="/trophies" class="lab-btn lab-btn-info">Trophies</a></div>';
                }).join('') : '<p class="lab-muted">No lab trophies defined.</p>';
            }
            if (mn2El) {
                const bal = mn2R.balance != null ? mn2R.balance : (mn2R.available || '—');
                mn2El.innerHTML = '<div class="lab-mini-card"><strong>' + esc(String(bal)) + ' MN2</strong><span>Wallet balance</span></div>' +
                    '<p class="lab-muted">Crypto rewards are display + shop-grant only from Lab — no auto-spend.</p>';
            }
        } catch (e) {
            if (shopEl) shopEl.innerHTML = '<p class="lab-muted">Could not load rewards.</p>';
        }
    }

    function bindLabHubV2() {
        document.getElementById('btn-lab-systems-check')?.addEventListener('click', runSystemsCheck);
        document.getElementById('btn-lab-idea-pin')?.addEventListener('click', pinIdea);
        document.getElementById('btn-lab-refresh-v2')?.addEventListener('click', loadLabV2Status);
        document.getElementById('btn-lab-refresh-rewards')?.addEventListener('click', loadRewards);
        document.getElementById('btn-lab-refresh-news')?.addEventListener('click', loadNews);
        loadNews();
        loadIdeaBoard();
        loadLabV2Status();
        loadRewards();
    }

    global.LabHubV2 = {
        init: bindLabHubV2,
        loadNews: loadNews,
        runSystemsCheck: runSystemsCheck,
        loadIdeaBoard: loadIdeaBoard,
        loadLabV2Status: loadLabV2Status,
        loadRewards: loadRewards
    };
    global.loadLabV2Status = loadLabV2Status;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindLabHubV2);
    } else {
        bindLabHubV2();
    }
})(typeof window !== 'undefined' ? window : globalThis);
