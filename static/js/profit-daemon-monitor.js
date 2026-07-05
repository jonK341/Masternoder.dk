(function () {
    'use strict';
    const BASE = window.location.origin || '';
    const REFRESH_MS = 8000;
    const CINEMA_ROTATE_MS = 7000;
    const STEP_ROTATE_MS = 4000;

    const CATEGORY_LABELS = {
        daemon: 'Daemon health',
        arb: 'Arbitrage engine',
        fast: 'Fast rescan',
        casino: 'Casino agents',
        funding: 'Venue funding',
        treasury: 'Treasury',
        ppp: 'Profit path (24h)',
        payout: 'PayPal / bank wire',
        venues: 'Venues',
        ops: 'Ops readiness',
        search: 'Pair search',
    };

    const TICKER_IDS = [
        'best_bps', 'best_net', 'live_stash', 'pair_search_hot', 'shared_hot',
        'fast_best_bps', 'arb_fills', 'cross_actions', 'sweepable_usd',
        'exchange_tick_age', 'fast_tick_age', 'casino_tick_age',
    ];

    let lastData = null;
    let cinemaIndex = 0;
    let cinemaTimer = null;
    let stepIndex = 0;
    let stepTimer = null;

    function $(id) { return document.getElementById(id); }

    function statById(stats, id) {
        if (!Array.isArray(stats)) return null;
        return stats.find(function (s) { return s.id === id; }) || null;
    }

    function fmtVal(stat) {
        const v = stat.value;
        if (v == null || v === '') return '—';
        if (stat.unit === 'USD' && typeof v === 'number') {
            return '$' + v.toLocaleString(undefined, { maximumFractionDigits: 2 });
        }
        return String(v);
    }

    function initMatrixRain() {
        const root = $('pdm-matrix');
        if (!root || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        const chars = '01₿Ξ$bpsUSDC';
        const cols = Math.min(18, Math.floor(window.innerWidth / 48));
        for (let i = 0; i < cols; i++) {
            const col = document.createElement('div');
            col.className = 'pdm-matrix-col';
            col.style.left = (i * (100 / cols)) + '%';
            col.style.animationDuration = (8 + Math.random() * 14) + 's';
            col.style.animationDelay = (-Math.random() * 12) + 's';
            let text = '';
            for (let j = 0; j < 28; j++) {
                text += chars[Math.floor(Math.random() * chars.length)] + '\n';
            }
            col.textContent = text;
            root.appendChild(col);
        }
    }

    function buildNarratives(data) {
        const stats = data.stats || [];
        const h = data.highlights || {};
        const treasury = data.treasury || {};
        const payout = data.payout || {};
        const bestBps = statById(stats, 'best_bps');
        const minMargin = statById(stats, 'min_margin');
        const stash = statById(stats, 'live_stash');
        const hot = statById(stats, 'pair_search_hot') || statById(stats, 'shared_hot');
        const fastBps = statById(stats, 'fast_best_bps');
        const bn = statById(stats, 'binance_usdc');
        const sweep = statById(stats, 'sweepable_usd');

        const bpsVal = bestBps ? fmtVal(bestBps) : (h.best_bps != null ? h.best_bps : '18');
        const marginVal = minMargin ? fmtVal(minMargin) : '18';
        const stashVal = stash ? fmtVal(stash) : (treasury.live_stash_usd != null ? '$' + treasury.live_stash_usd : '$0');
        const hotVal = hot && hot.value !== '—' ? hot.value : 'top pairs';
        const fastVal = fastBps ? fmtVal(fastBps) : '—';
        const bnVal = bn ? fmtVal(bn) : '$25+';
        const sweepVal = sweep ? fmtVal(sweep) : (payout.paypal_sweepable_usd != null ? '$' + payout.paypal_sweepable_usd : '$0');

        return [
            {
                tag: 'Arbitrage',
                title: 'Catch the spread → fill → profit',
                body: 'Fund Binance USDC (' + bnVal + ') → daemon scans ' + marginVal + '+ bps min margin → best spread ' + bpsVal + ' bps → arb agents execute when buy leg funded.',
            },
            {
                tag: 'Live stash',
                title: 'Treasury compounds every fill',
                body: 'Each successful arb leg adds to live stash (' + stashVal + '). Compound-on-trade keeps capital working 24/7 without manual transfers.',
            },
            {
                tag: 'Pair search',
                title: 'Hot symbols drive faster fills',
                body: 'Ledger + catalog ranking surfaces hot pairs (' + hotVal + ') → prefund buy leg → reduce zero-fill streaks and catch micro windows.',
            },
            {
                tag: 'Fast rescan',
                title: 'Micro-spreads between exchange ticks',
                body: 'Fast loop rescans every ~60s — best spread ' + fastVal + ' bps vs threshold. Near-ready = imminent fill when venues align.',
            },
            {
                tag: 'Sweep & payout',
                title: 'Cash out when threshold hits',
                body: 'Sweepable ' + sweepVal + ' → auto PayPal sweep or Binance bank wire when minimum reached. Mode: ' + (payout.mode || 'live') + '.',
            },
            {
                tag: 'Casino parallel',
                title: 'Backup yield when exchange stale',
                body: 'Casino agents run 3/3 parallel loops — MN2 mirror accrues even if exchange loop degrades. Check casino tick age in stream.',
            },
        ];
    }

    function renderCinema(data) {
        const stage = $('pdm-cinema-stage');
        const dotsEl = $('pdm-cinema-dots');
        if (!stage) return;

        const narratives = buildNarratives(data);
        stage.innerHTML = narratives.map(function (n, i) {
            return '<article class="pdm-cinema-card' + (i === cinemaIndex ? ' active' : '') + '" data-cinema-idx="' + i + '">' +
                '<span class="pdm-cinema-card__tag">' + n.tag + '</span>' +
                '<h3 class="pdm-cinema-card__title">' + n.title + '</h3>' +
                '<p class="pdm-cinema-card__body">' + n.body + '</p></article>';
        }).join('');

        if (dotsEl) {
            dotsEl.innerHTML = narratives.map(function (_, i) {
                return '<button type="button" class="pdm-cinema-dot' + (i === cinemaIndex ? ' active' : '') +
                    '" data-cinema-dot="' + i + '" aria-label="Narrative ' + (i + 1) + '"></button>';
            }).join('');
            dotsEl.querySelectorAll('[data-cinema-dot]').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    cinemaIndex = parseInt(btn.getAttribute('data-cinema-dot'), 10) || 0;
                    renderCinema(data);
                    resetCinemaTimer();
                });
            });
        }
    }

    function setCinemaActive(idx) {
        const cards = document.querySelectorAll('.pdm-cinema-card');
        const dots = document.querySelectorAll('.pdm-cinema-dot');
        cards.forEach(function (c, i) { c.classList.toggle('active', i === idx); });
        dots.forEach(function (d, i) { d.classList.toggle('active', i === idx); });
    }

    function resetCinemaTimer() {
        if (cinemaTimer) clearInterval(cinemaTimer);
        cinemaTimer = setInterval(function () {
            if (!lastData) return;
            const count = document.querySelectorAll('.pdm-cinema-card').length || 6;
            cinemaIndex = (cinemaIndex + 1) % count;
            setCinemaActive(cinemaIndex);
        }, CINEMA_ROTATE_MS);
    }

    function initStepRotation() {
        const steps = document.querySelectorAll('.pdm-step');
        if (!steps.length) return;
        if (stepTimer) clearInterval(stepTimer);
        stepTimer = setInterval(function () {
            stepIndex = (stepIndex + 1) % steps.length;
            steps.forEach(function (s, i) { s.classList.toggle('active', i === stepIndex); });
        }, STEP_ROTATE_MS);
    }

    function renderHero(stats, readinessPct) {
        const row = $('pdm-hero-row');
        if (!row) return;

        const heroDefs = [
            { id: 'live_stash', fallbackLabel: 'Live stash' },
            { id: 'best_bps', fallbackLabel: 'Best spread' },
            { id: 'arb_fills', fallbackLabel: 'Arb fills' },
            { id: 'profit_readiness', fallbackLabel: 'Readiness', value: readinessPct != null ? readinessPct + '%' : '—', unit: '' },
        ];

        row.innerHTML = heroDefs.map(function (def) {
            let stat = statById(stats, def.id);
            let val, unit = '', status = 'neutral', label = def.fallbackLabel;
            if (def.value != null) {
                val = def.value;
            } else if (stat) {
                val = fmtVal(stat);
                unit = stat.unit && stat.unit !== 'USD' ? stat.unit : '';
                status = stat.status || 'neutral';
                label = stat.label;
            } else {
                val = '—';
            }
            const unitHtml = unit === '%' ? '%' : (unit && unit !== 'USD' ? ' <span class="pdm-unit">' + unit + '</span>' : '');
            return '<div class="pdm-hero-stat status-' + status + '">' +
                '<span class="pdm-label">' + label + '</span>' +
                '<strong>' + val + unitHtml + '</strong></div>';
        }).join('');
    }

    function renderTicker(stats, loops) {
        const track = $('pdm-ticker-track');
        if (!track) return;

        const items = [];
        TICKER_IDS.forEach(function (id) {
            const s = statById(stats, id);
            if (s) {
                const hot = (id === 'best_bps' || id === 'pair_search_hot' || id === 'fast_best_bps') &&
                    s.status === 'good';
                items.push({ key: s.label, val: fmtVal(s) + (s.unit === 'bps' ? ' bps' : s.unit === 's' ? 's' : ''), hot: hot });
            }
        });

        if (Array.isArray(loops)) {
            loops.forEach(function (row) {
                const age = row.age_sec != null ? Math.round(row.age_sec) + 's' : '—';
                items.push({
                    key: row.loop + ' loop',
                    val: age + (row.stale ? ' stale' : ' ok'),
                    hot: !row.stale,
                });
            });
        }

        if (!items.length) {
            track.innerHTML = '<span class="pdm-ticker-item"><span class="pdm-ticker-key">Status</span> <span class="pdm-ticker-val">waiting…</span></span>';
            return;
        }

        const html = items.map(function (it) {
            return '<span class="pdm-ticker-item' + (it.hot ? ' hot' : '') + '">' +
                '<span class="pdm-ticker-key">' + it.key + '</span> ' +
                '<span class="pdm-ticker-val">' + it.val + '</span></span>';
        }).join('');

        track.innerHTML = html + html;
    }

    function wireTabs() {
        const tabs = document.querySelectorAll('.pdm-tab');
        const panels = document.querySelectorAll('.pdm-panel');
        tabs.forEach(function (tab) {
            tab.addEventListener('click', function () {
                const name = tab.getAttribute('data-pdm-tab');
                tabs.forEach(function (t) { t.classList.toggle('active', t === tab); });
                panels.forEach(function (p) {
                    const on = p.getAttribute('data-pdm-panel') === name;
                    p.classList.toggle('active', on);
                    p.hidden = !on;
                });
                if (name === 'news') loadNews();
                if (name === 'rent') loadRentals();
            });
        });
    }

    function renderStats(stats) {
        const root = $('pdm-stats-sections');
        const countEl = $('pdm-stat-count');
        if (!root || !Array.isArray(stats)) return;
        if (countEl) countEl.textContent = stats.length + ' live stats · updates every 8s';

        const byCat = {};
        stats.forEach(function (s) {
            const c = s.category || 'daemon';
            if (!byCat[c]) byCat[c] = [];
            byCat[c].push(s);
        });

        const order = ['ops', 'daemon', 'search', 'arb', 'fast', 'funding', 'treasury', 'ppp', 'payout', 'casino', 'venues'];
        const mobileCls = 'pdm-grid pdm-grid--mobile';
        root.innerHTML = order.filter(function (c) { return byCat[c]; }).map(function (cat) {
            const cards = byCat[cat].map(function (s) {
                const unit = s.unit && s.unit !== 'USD' && s.unit !== '%'
                    ? ' <span class="pdm-unit">' + s.unit + '</span>' : (s.unit === '%' ? '%' : '');
                const hint = s.hint ? '<span class="pdm-hint">' + s.hint + '</span>' : '';
                return '<div class="pdm-card status-' + (s.status || 'neutral') + '" title="' + (s.hint || '') + '">' +
                    '<span class="pdm-label">' + s.label + '</span>' +
                    '<strong>' + fmtVal(s) + unit + '</strong>' + hint + '</div>';
            }).join('');
            return '<div class="pdm-stat-section"><h3>' + (CATEGORY_LABELS[cat] || cat) + '</h3><div class="' + mobileCls + '">' + cards + '</div></div>';
        }).join('');
    }

    function renderStashChart(series) {
        const wrap = $('pdm-stash-chart-wrap');
        const chart = $('pdm-stash-chart');
        if (!wrap || !chart || !Array.isArray(series) || !series.length) return;
        wrap.hidden = false;
        const vals = series.map(function (p) { return Number(p.stash_usd) || 0; });
        const max = Math.max.apply(null, vals.concat([1]));
        chart.innerHTML = series.map(function (p) {
            const h = Math.max(4, Math.round((Number(p.stash_usd) || 0) / max * 64));
            return '<div class="pdm-stash-bar" style="height:' + h + 'px" title="' + (p.ts || '') + ': $' + (p.stash_usd || 0) + '"></div>';
        }).join('');
    }

    function renderSkipGroups(groups) {
        const el = $('pdm-skip-groups');
        if (!el || !groups || !groups.tiles || !groups.tiles.length) return;
        el.hidden = false;
        el.innerHTML = '<span class="pdm-muted">AI skip groups · </span>' + groups.tiles.map(function (t) {
            return '<span class="pdm-skip-chip">' + t.label + ' ' + t.count + '</span>';
        }).join('');
    }

    function renderBlockers(blockers) {
        const ul = $('pdm-blockers');
        if (!ul) return;
        if (!blockers || !blockers.length) {
            ul.innerHTML = '<li class="pdm-muted">All critical items done — focus on spreads ≥ min margin and XeggeX if dual-venue needed.</li>';
            return;
        }
        ul.innerHTML = blockers.map(function (b) {
            return '<li><span class="pdm-blocker-pri">#' + (b.priority || '?') + '</span>' +
                '<span><strong>' + (b.title || b.id) + '</strong><br><span class="pdm-muted">' + (b.category || '') + '</span></span></li>';
        }).join('');
    }

    function updateLastRefresh() {
        const el = $('pdm-last-update');
        if (el) {
            const now = new Date();
            el.textContent = 'Live · ' + now.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        }
    }

    async function loadStatus() {
        try {
            const res = await fetch(BASE + '/api/profit-daemon/status');
            const data = await res.json();
            lastData = data;

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

            const stats = data.stats || [];
            renderHero(stats, pct);
            renderTicker(stats, data.loops);
            renderStats(stats);
            renderCinema(data);
            renderBlockers(data.blockers || []);

            if (data.stash_history && data.stash_history.series) {
                renderStashChart(data.stash_history.series);
            }
            if (data.ai_skip_groups) renderSkipGroups(data.ai_skip_groups);

            const mirror = $('pdm-mn2-mirror');
            if (mirror && data.mn2_mirror && data.mn2_mirror.mirror_label) {
                mirror.textContent = 'Casino MN2 mirror: ' + data.mn2_mirror.mirror_label;
                $('pdm-stash-chart-wrap').hidden = false;
            }

            const loopsEl = $('pdm-loops');
            if (loopsEl && Array.isArray(data.loops)) {
                loopsEl.innerHTML = data.loops.map(function (row) {
                    const age = row.age_sec != null ? Math.round(row.age_sec) + 's ago' : '—';
                    return '<div class="pdm-loop-row' + (row.stale ? ' stale' : '') + '">' +
                        '<strong>' + row.loop + '</strong> · ' + age + '<br>' +
                        '<span>' + (row.summary || '') + '</span></div>';
                }).join('');
            }

            updateLastRefresh();
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
            ul.innerHTML = items.map(function (n) {
                return '<li><a href="' + (n.href || '/profit/') + '">' + (n.title || 'Update') + '</a>' +
                    '<div class="pdm-muted">' + (n.date || '') + ' · ' + (n.summary || '') + '</div></li>';
            }).join('');
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
            el.innerHTML = rows.map(function (r) {
                return '<div class="pdm-rent-card"><strong>' + (r.name || r.id) + '</strong>' +
                    '<p class="pdm-muted">' + (r.description || '') + '</p>' +
                    '<p>' + (r.price_mn2 || '?') + ' MN2 · ' + (r.days || '?') + ' days · reward ' +
                    (r.completion_reward_mn2 || 0) + ' MN2</p></div>';
            }).join('');
        } catch (_) {
            el.textContent = 'Rentals unavailable.';
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        initMatrixRain();
        wireTabs();
        initStepRotation();
        loadStatus();
        resetCinemaTimer();
        setInterval(loadStatus, REFRESH_MS);
    });
})();
