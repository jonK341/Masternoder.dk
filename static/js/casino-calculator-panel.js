(function () {
    'use strict';

    var GAMES = [
        'coin_flip', 'dice', 'crash', 'mines', 'plinko', 'wheel',
        'slot_classic', 'battle_outcome', 'rps_distribution', 'scratch_card',
        'keno', 'roulette', 'hilo'
    ];

    function $(id) {
        return document.getElementById(id);
    }

    function api(path) {
        return fetch(path, { headers: { Accept: 'application/json' }, credentials: 'same-origin' })
            .then(function (r) { return r.json(); });
    }

    function renderMetrics(data) {
        var root = $('casino-calc-metrics');
        var guideRoot = $('casino-calc-guide');
        var progRoot = $('casino-calc-prognosis');
        if (!root || !data || !data.success) return;

        var rtp = (data.rtp && data.rtp.rtp_percent) || '—';
        var wp = ((data.win_probability && data.win_probability.win_probability) || 0) * 100;
        var ev = (data.expected_value && data.expected_value.expected_net) || 0;
        var roi = (data.expected_value && data.expected_value.expected_roi_percent) || 0;
        var kelly = (data.kelly && data.kelly.suggested_stake) || 0;

        root.innerHTML =
            '<div class="casino-calc-metric"><div class="label">RTP</div><div class="value">' + rtp + '%</div></div>' +
            '<div class="casino-calc-metric"><div class="label">Win chance</div><div class="value">' + wp.toFixed(1) + '%</div></div>' +
            '<div class="casino-calc-metric"><div class="label">Expected net</div><div class="value">' + ev + '</div></div>' +
            '<div class="casino-calc-metric"><div class="label">ROI</div><div class="value">' + roi + '%</div></div>' +
            '<div class="casino-calc-metric"><div class="label">Kelly stake</div><div class="value">' + kelly + '</div></div>';

        var g = data.guide || {};
        if (guideRoot && g.win) {
            guideRoot.innerHTML =
                '<strong>' + (data.label || data.game_id) + ' — how to win / lose</strong>' +
                '<p class="win"><strong>Win:</strong> ' + g.win + '</p>' +
                '<p class="lose"><strong>Lose:</strong> ' + g.lose + '</p>' +
                '<p>' + (g.payout || '') + '</p>' +
                '<p style="opacity:0.85;margin-top:8px;">' + (g.tip || '') + '</p>';
            guideRoot.style.display = 'block';
        } else if (guideRoot) {
            guideRoot.style.display = 'none';
        }

        if (progRoot) {
            progRoot.innerHTML = '';
        }
    }

    function runCalculate() {
        var game = ($('casino-calc-game') && $('casino-calc-game').value) || 'coin_flip';
        var bet = parseFloat(($('casino-calc-bet') && $('casino-calc-bet').value) || 10);
        var balance = parseFloat(($('casino-calc-balance') && $('casino-calc-balance').value) || 1000);
        var q = '/api/casino/calculators/calculate_for_game?game_id=' + encodeURIComponent(game) +
            '&bet=' + encodeURIComponent(bet) + '&balance=' + encodeURIComponent(balance);
        api(q).then(renderMetrics).catch(function () {
            var root = $('casino-calc-metrics');
            if (root) root.innerHTML = '<p style="color:#f87171;">Calculator API unavailable.</p>';
        });
    }

    function loadPrognosis() {
        var progRoot = $('casino-calc-prognosis');
        if (!progRoot) return;
        progRoot.innerHTML = '<p>Loading future sights…</p>';
        api('/api/casino/prognosis').then(function (d) {
            var sights = (d && d.future_sights) || [];
            if (!sights.length) {
                progRoot.innerHTML = '<p>No prognosis data yet.</p>';
                return;
            }
            progRoot.innerHTML = '<h3 style="color:#00d4ff;margin:0 0 10px;font-size:1rem;">Future sights</h3>' +
                sights.map(function (s) {
                    return '<div class="casino-prognosis-item"><strong>' + (s.title || s.id) + '</strong><br>' +
                        (s.play_hint || '') + (s.signal ? ' · Signal: <strong>' + s.signal + '</strong>' : '') + '</div>';
                }).join('');
        });
    }

    function loadCalculatorList() {
        var root = $('casino-calc-funcs');
        if (!root) return;
        api('/api/casino/calculators').then(function (d) {
            var list = (d && d.calculators) || [];
            root.innerHTML = list.map(function (c) {
                return '<span class="casino-calc-func-chip" title="' + c.description + '">' + c.id + '</span>';
            }).join('');
        });
    }

    function init() {
        var select = $('casino-calc-game');
        if (select && !select.options.length) {
            GAMES.forEach(function (g) {
                var opt = document.createElement('option');
                opt.value = g;
                opt.textContent = g.replace(/_/g, ' ');
                select.appendChild(opt);
            });
        }
        var runBtn = $('casino-calc-run');
        var progBtn = $('casino-calc-prognosis-btn');
        if (runBtn) runBtn.addEventListener('click', runCalculate);
        if (progBtn) progBtn.addEventListener('click', loadPrognosis);
        loadCalculatorList();
        runCalculate();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
