(function () {
    'use strict';
    const BASE = window.location.origin || '';

    const CATEGORY_LABELS = {
        daemon: 'Daemon health',
        arb: 'Arbitrage engine',
        fast: 'Fast rescan',
        casino: 'Casino agents',
        funding: 'Venue funding',
        treasury: 'Treasury',
        ppp: 'Profit path (24h)',
        payout: 'PayPal sweep',
        venues: 'Venues',
        ops: 'Ops readiness',
    };

    function $(id) { return document.getElementById(id); }

    function wireTabs() {
        const tabs = document.querySelectorAll('.pdm-tab');
        const panels = document.querySelectorAll('.pdm-panel');
        tabs.forEach((tab) => {
            tab.addEventListener('click', () => {
                const name = tab.getAttribute('data-pdm-tab');
                tabs.forEach((t) => t.classList.toggle('active', t === tab));
                panels.forEach((p) => {
                    const on = p.getAttribute('data-pdm-panel') === name;
                    p.classList.toggle('active', on);
                    p.hidden = !on;
                });
                if (name === 'news') loadNews();
                if (name === 'rent') loadRentals();
                if (name === 'level') loadLevel();
                if (name === 'blockers') { /* filled on status load */ }
            });
        });
    }

    function fmtVal(stat) {
        const v = stat.value;
        if (v == null || v === '') return '—';
        if (stat.unit === 'USD' && typeof v === 'number') {
            return '$' + v.toLocaleString(undefined, { maximumFractionDigits: 2 });
        }
        return String(v);
    }

    function renderStats(stats) {
        const root = $('pdm-stats-sections');
        const countEl = $('pdm-stat-count');
        if (!root || !Array.isArray(stats)) return;
        if (countEl) countEl.textContent = stats.length + ' live stats · updates every 30s';

        const byCat = {};
        stats.forEach((s) => {
            const c = s.category || 'daemon';
            if (!byCat[c]) byCat[c] = [];
            byCat[c].push(s);
        });

        const order = ['ops', 'daemon', 'arb', 'fast', 'funding', 'treasury', 'ppp', 'payout', 'casino', 'venues'];
        root.innerHTML = order.filter((c) => byCat[c]).map((cat) => {
            const cards = byCat[cat].map((s) => {
                const unit = s.unit && s.unit !== 'USD' && s.unit !== '%'
                    ? ' <span class="pdm-unit">' + s.unit + '</span>' : (s.unit === '%' ? '%' : '');
                const hint = s.hint ? '<span class="pdm-hint">' + s.hint + '</span>' : '';
                return '<div class="pdm-card status-' + (s.status || 'neutral') + '" title="' + (s.hint || '') + '">' +
                    '<span class="pdm-label">' + s.label + '</span>' +
                    '<strong>' + fmtVal(s) + unit + '</strong>' + hint + '</div>';
            }).join('');
            return '<div class="pdm-stat-section"><h3>' + (CATEGORY_LABELS[cat] || cat) + '</h3><div class="pdm-grid">' + cards + '</div></div>';
        }).join('');
    }

    function renderBlockers(blockers) {
        const ul = $('pdm-blockers');
        if (!ul) return;
        if (!blockers || !blockers.length) {
            ul.innerHTML = '<li class="pdm-muted">All critical items done — focus on spreads ≥ min margin and XeggeX if dual-venue needed.</li>';
            return;
        }
        ul.innerHTML = blockers.map((b) =>
            '<li><span class="pdm-blocker-pri">#' + (b.priority || '?') + '</span>' +
            '<span><strong>' + (b.title || b.id) + '</strong><br><span class="pdm-muted">' + (b.category || '') + '</span></span></li>'
        ).join('');
    }

    async function loadStatus() {
        try {
            const res = await fetch(BASE + '/api/profit-daemon/status');
            const data = await res.json();
            const pill = $('pdm-running-pill');
            if (pill) {
                pill.textContent = data.running ? 'Daemon online · ' + (data.mode || 'live') : 'Daemon stale / offline';
                pill.classList.toggle('on', !!data.running);
                pill.classList.toggle('off', !data.running);
            }
            const pct = data.profit_readiness_pct;
            const fill = $('pdm-readiness-fill');
            const pctEl = $('pdm-readiness-pct');
            if (fill && pct != null) fill.style.width = Math.min(100, Math.max(0, pct)) + '%';
            if (pctEl && pct != null) pctEl.textContent = pct + '%';

            renderStats(data.stats || []);
            renderBlockers(data.blockers || []);

            const loopsEl = $('pdm-loops');
            if (loopsEl && Array.isArray(data.loops)) {
                loopsEl.innerHTML = data.loops.map((row) => {
                    const age = row.age_sec != null ? Math.round(row.age_sec) + 's ago' : '—';
                    return '<div class="pdm-loop-row' + (row.stale ? ' stale' : '') + '">' +
                        '<strong>' + row.loop + '</strong> · ' + age + '<br>' +
                        '<span>' + (row.summary || '') + '</span></div>';
                }).join('');
            }
        } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'profit-daemon-monitor.js', context: 'catch' }); }
            const pill = $('pdm-running-pill');
            if (pill) { pill.textContent = 'Status unavailable'; pill.classList.add('off'); }
        }
    }

    async function loadNews() {
        const ul = $('pdm-news-list');
        if (!ul) return;
        ul.innerHTML = '<li class="pdm-muted">Loading…</li>';
        try {
            const res = await fetch(BASE + '/api/profit-daemon/news?limit=20');
            const data = await res.json();
            const items = data.news || [];
            if (!items.length) {
                ul.innerHTML = '<li class="pdm-muted">No profit news yet — daemon publishes on fills &amp; sweeps.</li>';
                return;
            }
            ul.innerHTML = items.map((n) =>
                '<li><a href="' + (n.href || '/profit/') + '">' + (n.title || 'Update') + '</a>' +
                '<div class="pdm-muted">' + (n.date || '') + ' · ' + (n.summary || '') + '</div></li>'
            ).join('');
        } catch (_) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(_ instanceof Error ? _ : new Error(String(_)), { source: 'profit-daemon-monitor.js', context: 'catch' }); }
            ul.innerHTML = '<li class="pdm-muted">Could not load profit news.</li>';
        }
    }

    async function loadRentals() {
        const el = $('pdm-rentals');
        if (!el) return;
        try {
            const res = await fetch(BASE + '/api/profit-daemon/rentals');
            const data = await res.json();
            const rows = data.rentals || [];
            el.innerHTML = rows.map((r) =>
                '<div class="pdm-rent-card"><strong>' + (r.name || r.id) + '</strong>' +
                '<p class="pdm-muted">' + (r.description || '') + '</p>' +
                '<p>' + (r.price_mn2 || '?') + ' MN2 · ' + (r.days || '?') + ' days · reward ' +
                (r.completion_reward_mn2 || 0) + ' MN2</p></div>'
            ).join('');
        } catch (_) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(_ instanceof Error ? _ : new Error(String(_)), { source: 'profit-daemon-monitor.js', context: 'catch' }); }
            el.textContent = 'Rentals unavailable.';
        }
    }

    function esc(text) {
        return String(text == null ? '' : text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function renderLevel(data) {
        const summary = $('pdm-level-summary');
        const active = $('pdm-level-active');
        const yt = $('pdm-level-youtube');
        const list = $('pdm-level-assigns');
        if (!summary || !list) return;
        const level = data.level || 0;
        const progress = data.progress || {};
        const board = data.board || {};
        const editing = data.editing_level || (level + 1);
        if (level > 0 && data.defined) {
            summary.textContent = 'Level ' + level + ' earned. Assign all 20 slots to earn level ' + editing + '.';
        } else {
            summary.textContent = 'Level 0. Set the vision, the next profit move, and all 20 assignments to earn level 1. '
                + (progress.filled || 0) + '/' + (progress.required || 20) + ' filled.';
        }
        if (active) {
            if (data.defined) {
                active.innerHTML = '<strong>Vision.</strong> ' + esc(data.vision)
                    + '<br><strong>Next profit move.</strong> ' + esc(data.next_profit_move);
            } else {
                active.textContent = 'The daemon has no vision yet. It follows a level only after all 20 assignments are set.';
            }
        }
        const youtube = data.youtube || {};
        if (yt) {
            if (!youtube.checked_at) {
                yt.textContent = 'YouTube: not checked yet.';
            } else {
                const live = youtube.live ? 'Live now' : 'Not live';
                const title = youtube.title ? ' · ' + esc(youtube.title) : '';
                const note = youtube.note ? ' ' + esc(youtube.note) : '';
                const href = youtube.watch_url
                    ? ' <a href="' + esc(youtube.watch_url) + '" target="_blank" rel="noopener">Watch</a>'
                    : '';
                yt.innerHTML = 'YouTube: ' + live + title + '.' + note + href;
            }
        }
        const vision = $('pdm-level-vision');
        const move = $('pdm-level-move');
        if (vision && document.activeElement !== vision) vision.value = board.vision || '';
        if (move && document.activeElement !== move) move.value = board.next_profit_move || '';
        const rows = board.assignments || data.slots || [];
        list.innerHTML = rows.map((row) =>
            '<label>' + esc(row.slot) + '. ' + esc(row.label || row.key)
            + '<textarea data-slot="' + esc(row.slot) + '" rows="2" maxlength="280">'
            + esc(row.text || '') + '</textarea></label>'
        ).join('');
        const msg = $('pdm-level-msg');
        if (msg && !msg.dataset.lock) msg.textContent = '';
    }

    async function loadLevel() {
        try {
            const res = await fetch(BASE + '/api/profit-daemon/level?check_youtube=1');
            const data = await res.json();
            renderLevel(data);
        } catch (e) {
            const summary = $('pdm-level-summary');
            if (summary) summary.textContent = 'Level board unavailable.';
        }
    }

    async function saveLevel() {
        const msg = $('pdm-level-msg');
        const assignments = Array.from(document.querySelectorAll('#pdm-level-assigns textarea')).map((el) => ({
            slot: Number(el.getAttribute('data-slot')),
            text: el.value,
        }));
        const headers = { 'Content-Type': 'application/json' };
        const key = ($('pdm-level-admin') || {}).value || '';
        if (key) headers['X-Profit-Daemon-Admin'] = key;
        if (msg) {
            msg.dataset.lock = '1';
            msg.textContent = 'Saving…';
        }
        try {
            const res = await fetch(BASE + '/api/profit-daemon/level', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    vision: ($('pdm-level-vision') || {}).value || '',
                    next_profit_move: ($('pdm-level-move') || {}).value || '',
                    assignments: assignments,
                }),
            });
            const data = await res.json();
            if (!res.ok || data.success === false) {
                if (msg) msg.textContent = data.error || 'Save failed.';
                return;
            }
            if (msg) {
                msg.textContent = data.earned
                    ? 'Level ' + data.saved_level + ' earned. The daemon now follows this vision and next profit move.'
                    : 'Draft saved. Still need ' + ((data.missing || []).length) + ' field(s): ' + (data.missing || []).join(', ');
            }
            renderLevel(data);
        } catch (e) {
            if (msg) msg.textContent = 'Save failed.';
        } finally {
            if (msg) delete msg.dataset.lock;
        }
    }

    async function checkYoutube() {
        const yt = $('pdm-level-youtube');
        if (yt) yt.textContent = 'Checking YouTube…';
        try {
            const res = await fetch(BASE + '/api/profit-daemon/level/youtube-check', { method: 'POST' });
            const data = await res.json();
            const live = data.live ? 'Live now' : 'Not live';
            const title = data.title ? ' · ' + esc(data.title) : '';
            const note = data.note ? ' ' + esc(data.note) : '';
            const href = data.watch_url
                ? ' <a href="' + esc(data.watch_url) + '" target="_blank" rel="noopener">Watch</a>'
                : '';
            if (yt) yt.innerHTML = 'YouTube: ' + live + title + '.' + note + href;
        } catch (e) {
            if (yt) yt.textContent = 'YouTube check failed.';
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        wireTabs();
        loadStatus();
        setInterval(loadStatus, 30000);
        const save = $('pdm-level-save');
        const ytBtn = $('pdm-level-yt');
        if (save) save.addEventListener('click', saveLevel);
        if (ytBtn) ytBtn.addEventListener('click', checkYoutube);
    });
})();
