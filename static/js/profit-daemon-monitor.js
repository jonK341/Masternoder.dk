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
        search: 'Pair search',
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

        const order = ['ops', 'daemon', 'search', 'arb', 'fast', 'funding', 'treasury', 'ppp', 'payout', 'casino', 'venues'];
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
                const health = data.health || (data.running ? 'online' : 'offline');
                if (health === 'online') {
                    pill.textContent = 'Daemon online · ' + (data.mode || 'live');
                    pill.classList.add('on');
                    pill.classList.remove('off', 'warn');
                } else if (health === 'degraded') {
                    pill.textContent = 'Degraded — exchange loop stale (casino only)';
                    pill.classList.add('warn');
                    pill.classList.remove('on', 'off');
                } else {
                    pill.textContent = 'Daemon stale / offline';
                    pill.classList.add('off');
                    pill.classList.remove('on', 'warn');
                }
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
        } catch (e) {
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
        } catch (_) {
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
        } catch (_) {
            el.textContent = 'Rentals unavailable.';
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        wireTabs();
        loadStatus();
        setInterval(loadStatus, 30000);
    });
})();
