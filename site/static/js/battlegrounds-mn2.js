/**
 * Battlegrounds MN2 arena buy-in — tiers from /api/battle/arena/config
 */
(function (global) {
    'use strict';

    var bridge = global.Mn2SiteBridge;
    var arenaConfig = null;
    var TOURNAMENT_ID = 'bg_001';

    function uid() {
        return bridge ? bridge.uid() : (global.localStorage.getItem('game_user_id') || 'default_user');
    }

    function fmt(n) {
        return bridge ? bridge.fmtMn2(n) : String(n);
    }

    function setText(id, text) {
        var el = global.document.getElementById(id);
        if (el) el.textContent = text;
    }

    function showStatus(msg, ok) {
        var el = global.document.getElementById('bg-mn2-status');
        if (!el) return;
        el.textContent = msg;
        el.style.color = ok ? '#00ff88' : '#ff8888';
    }

    function renderTiers() {
        var wrap = global.document.getElementById('bg-mn2-tiers');
        if (!wrap || !arenaConfig) return;
        var tiers = ((arenaConfig.buy_in_tiers || {}).mn2) || [];
        wrap.innerHTML = tiers.map(function (amt) {
            return '<button type="button" class="bg-mn2-tier" data-amt="' + amt + '">' + fmt(amt) + ' MN2</button>';
        }).join('');
        wrap.querySelectorAll('.bg-mn2-tier').forEach(function (btn) {
            btn.addEventListener('click', function () {
                buyInMn2(parseFloat(btn.getAttribute('data-amt')));
            });
        });
        var ranked = arenaConfig.ranked || {};
        var casual = ranked.casual && ranked.casual.entry_fee && ranked.casual.entry_fee.mn2;
        var pro = ranked.pro && ranked.pro.entry_fee && ranked.pro.entry_fee.mn2;
        setText('bg-mn2-ranked-fees', [
            casual != null ? ('Casual ranked: ' + fmt(casual) + ' MN2') : '',
            pro != null ? ('Pro ranked: ' + fmt(pro) + ' MN2') : '',
        ].filter(Boolean).join(' · ') || '—');
    }

    function buyInMn2(amount) {
        if (!isFinite(amount)) return;
        showStatus('Processing MN2 buy-in…', true);
        fetch('/api/battle/tournaments/' + encodeURIComponent(TOURNAMENT_ID) + '/buy-in', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: uid(),
                amount: amount,
                currency: 'mn2',
            }),
        }).then(function (r) { return r.json(); }).then(function (d) {
            if (d.success) {
                showStatus(
                    'Buy-in OK · ' + fmt(d.amount) + ' MN2 · prize pool ' + fmt(d.prize_pool || 0) + ' MN2',
                    true
                );
                refreshBalance();
            } else {
                showStatus(d.error || 'Buy-in failed', false);
            }
        }).catch(function () {
            showStatus('Network error during buy-in', false);
        });
    }

    function refreshBalance() {
        if (!bridge) return Promise.resolve();
        return bridge.loadBalance().then(function (d) {
            var bal = (d && (d.balance != null ? d.balance : d.mn2_balance)) || 0;
            setText('bg-mn2-balance', fmt(bal) + ' MN2');
        }).catch(function () { setText('bg-mn2-balance', '—'); });
    }

    function loadArenaConfig() {
        return fetch('/api/battle/arena/config').then(function (r) { return r.json(); }).then(function (d) {
            if (!d.success) return;
            arenaConfig = d.config || d;
            renderTiers();
            var rake = arenaConfig.rake && arenaConfig.rake.tournaments;
            setText('bg-mn2-rake', rake != null ? (rake + '% house rake on tournaments') : '—');
        }).catch(function () { showStatus('Could not load arena config', false); });
    }

    function init() {
        refreshBalance();
        loadArenaConfig();
        if (bridge) {
            bridge.loadPrice().then(function (d) {
                var p = d && (d.price_usd != null ? d.price_usd : d.usd);
                setText('bg-mn2-rate', p != null ? ('$' + Number(p).toFixed(4) + ' / MN2') : '—');
            }).catch(function () { setText('bg-mn2-rate', '—'); });
        }
    }

    global.BattlegroundsMn2 = { init: init, buyInMn2: buyInMn2, refreshBalance: refreshBalance };
    global.document.addEventListener('DOMContentLoaded', init);
})(window);
