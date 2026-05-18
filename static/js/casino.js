(function () {
    'use strict';

    const userId = localStorage.getItem('game_user_id') || 'default_user';
    const baseUrl = window.location.origin;

    function $(id) {
        return document.getElementById(id);
    }

    async function api(path, options) {
        const url = baseUrl + path + (path.includes('?') ? '&' : '?') + 'user_id=' + encodeURIComponent(userId);
        const res = await fetch(url, options);
        const data = await res.json().catch(function () { return {}; });
        if (!res.ok && !data.error) {
            data.error = 'Request failed (' + res.status + ')';
        }
        return data;
    }

    function setResult(el, data) {
        if (!el) return;
        el.classList.remove('win', 'loss', 'draw');
        if (!data.success) {
            el.textContent = data.error || 'Play failed';
            el.classList.add('loss');
            return;
        }
        el.classList.add(data.outcome || 'draw');
        const details = data.details || {};
        if (data.game === 'coin_flip') {
            el.textContent = data.outcome.toUpperCase() + ': ' + details.result + ' (picked ' + details.choice + ') — net ' + data.net;
        } else if (data.game === 'dice') {
            el.textContent = data.outcome.toUpperCase() + ': rolled ' + details.roll + ' (guessed ' + details.guess + ') — net ' + data.net;
        } else {
            el.textContent = data.outcome.toUpperCase() + ': you ' + details.choice + ' vs ' + details.opponent + ' — net ' + data.net;
        }
    }

    async function refreshBalance() {
        const data = await api('/api/casino/balance');
        const el = $('casino-balance');
        if (el) {
            if (data.success) {
                el.textContent = 'Balance: ' + Math.round(data.balance) + ' coins · Bets today: ' + data.bets_today + '/' + data.max_bets_per_day;
            } else {
                el.textContent = data.error || 'Could not load balance';
            }
        }
        const disclaimer = $('casino-disclaimer-text');
        if (disclaimer && data.disclaimer) {
            disclaimer.textContent = data.disclaimer;
        }
    }

    async function refreshHistory() {
        const data = await api('/api/casino/history?limit=10');
        const tbody = $('casino-history-body');
        if (!tbody || !data.success) return;
        tbody.innerHTML = '';
        (data.history || []).forEach(function (row) {
            const tr = document.createElement('tr');
            tr.innerHTML = '<td>' + row.game + '</td><td>' + row.bet + '</td><td>' + row.outcome + '</td><td>' + row.net + '</td><td>' + (row.created_at || '') + '</td>';
            tbody.appendChild(tr);
        });
    }

    async function playCoinFlip() {
        const bet = parseInt($('coin-flip-bet').value, 10);
        const choice = $('coin-flip-choice').value;
        const data = await api('/api/casino/play/coin-flip', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bet: bet, choice: choice, user_id: userId }),
        });
        setResult($('coin-flip-result'), data);
        await refreshBalance();
        await refreshHistory();
    }

    async function playDice() {
        const bet = parseInt($('dice-bet').value, 10);
        const guess = parseInt($('dice-guess').value, 10);
        const data = await api('/api/casino/play/dice', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bet: bet, guess: guess, user_id: userId }),
        });
        setResult($('dice-result'), data);
        await refreshBalance();
        await refreshHistory();
    }

    async function playRps() {
        const bet = parseInt($('rps-bet').value, 10);
        const choice = $('rps-choice').value;
        const data = await api('/api/casino/play/rps-bet', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bet: bet, choice: choice, user_id: userId }),
        });
        setResult($('rps-result'), data);
        await refreshBalance();
        await refreshHistory();
    }

    document.addEventListener('DOMContentLoaded', function () {
        $('coin-flip-play')?.addEventListener('click', playCoinFlip);
        $('dice-play')?.addEventListener('click', playDice);
        $('rps-play')?.addEventListener('click', playRps);
        refreshBalance();
        refreshHistory();
    });
})();
