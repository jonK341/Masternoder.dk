(function () {
    'use strict';
    const BASE = window.location.origin || '';

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
            });
        });
    }

    function fmtUsd(v) {
        if (v == null || v === '') return '—';
        const n = Number(v);
        if (Number.isNaN(n)) return String(v);
        return '$' + n.toLocaleString(undefined, { maximumFractionDigits: 2 });
    }

    async function loadStatus() {
        try {
            const res = await fetch(BASE + '/api/profit-daemon/status');
            const data = await res.json();
            const pill = $('pdm-running-pill');
            if (pill) {
                pill.textContent = data.running ? 'Daemon online' : 'Daemon stale / offline';
                pill.classList.toggle('on', !!data.running);
                pill.classList.toggle('off', !data.running);
            }
            const h = data.highlights || {};
            if ($('pdm-arb-exec')) $('pdm-arb-exec').textContent = h.arb_exec || '0/11';
            if ($('pdm-best-bps')) $('pdm-best-bps').textContent = h.best_bps != null ? h.best_bps + ' bps' : '—';
            if ($('pdm-cross')) $('pdm-cross').textContent = h.cross_actions != null ? String(h.cross_actions) : '—';
            const tre = data.treasury || {};
            if ($('pdm-stash')) $('pdm-stash').textContent = fmtUsd(tre.live_stash_usd);
            const ppp = data.ppp_24h || {};
            if ($('pdm-ppp-fills')) $('pdm-ppp-fills').textContent = ppp.fill_count != null ? String(ppp.fill_count) : '—';
            const pay = data.payout || {};
            const sweep = pay.ready_to_sweep ? 'ready' : (pay.auto_sweep ? 'auto on' : 'manual');
            if ($('pdm-sweep')) {
                $('pdm-sweep').textContent = (pay.mode || '?') + ' · ' + sweep;
            }
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
                ul.innerHTML = '<li class="pdm-muted">No profit news yet — daemon will publish on fills &amp; sweeps.</li>';
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
