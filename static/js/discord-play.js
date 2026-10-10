(function () {
    'use strict';

    var params = new URLSearchParams(window.location.search);
    var token = params.get('token') || '';
    var venueParam = params.get('venue') || '';
    var currencyParam = params.get('currency') || 'usd';
    var userId = localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';

    function $(id) {
        return document.getElementById(id);
    }

    function api(method, path, body) {
        var opts = {
            method: method,
            headers: { Accept: 'application/json' },
            credentials: 'same-origin',
        };
        if (body) {
            opts.headers['Content-Type'] = 'application/json';
            opts.body = JSON.stringify(body);
        }
        return fetch(path, opts).then(function (r) { return r.json(); });
    }

    function loadConfig() {
        var q = '/api/discord/play/config';
        if (token) q += '?token=' + encodeURIComponent(token);
        return api('GET', q);
    }

    function renderPayments(payments) {
        var root = $('dp-payment-chips');
        if (!root) return;
        root.innerHTML = '';
        (payments || []).forEach(function (p) {
            var chip = document.createElement('span');
            chip.className = 'dp-chip' + (p.status === 'planned' ? ' planned' : '');
            chip.textContent = p.label + (p.status === 'planned' ? ' (soon)' : '');
            root.appendChild(chip);
        });
        if (!payments || !payments.length) {
            root.textContent = 'PayPal USD · MN2 wallet · USD balance · on-chain MN2';
        }
    }

    function renderVenues(venues) {
        var root = $('dp-venues');
        if (!root) return;
        root.innerHTML = '';
        (venues || []).forEach(function (v) {
            var card = document.createElement('article');
            card.className = 'dp-card';
            card.innerHTML =
                '<h3>' + (v.icon || '🎲') + ' ' + (v.name || v.id) + '</h3>' +
                '<p>' + (v.description || '') + '</p>';
            root.appendChild(card);
        });
    }

    function renderGames(games, sessionUserId) {
        var root = $('dp-games');
        var curSel = $('dp-currency');
        if (curSel && currencyParam) curSel.value = currencyParam;
        if (!root) return;
        root.innerHTML = '';
        (games || []).forEach(function (g) {
            var card = document.createElement('article');
            card.className = 'dp-card';
            var min = g.min_bet_usd || 5;
            card.innerHTML =
                '<h3>' + (g.icon || '💎') + ' ' + (g.title || g.id) + '</h3>' +
                '<p>' + (g.description || '') + '</p>' +
                '<input type="number" min="' + min + '" value="' + min + '" aria-label="Bet amount" data-bet-input>' +
                '<button type="button" class="dp-btn" data-game-id="' + g.id + '">Play</button>';
            var btn = card.querySelector('.dp-btn');
            btn.addEventListener('click', function () {
                if (!sessionUserId) {
                    alert('Open this page from Discord /playnow or link your account on the casino.');
                    return;
                }
                var bet = parseFloat(card.querySelector('[data-bet-input]').value) || min;
                var currency = (curSel && curSel.value) || 'usd';
                btn.disabled = true;
                btn.textContent = 'Playing…';
                api('POST', '/api/casino/uber/play?user_id=' + encodeURIComponent(sessionUserId), {
                    user_id: sessionUserId,
                    game_id: g.id,
                    bet: bet,
                    currency: currency,
                }).then(function (out) {
                    var res = $('dp-play-result');
                    if (!res) return;
                    if (out.success) {
                        var bonus = out.network_bonus_mn2 ? ' · Network bonus +' + out.network_bonus_mn2 + ' MN2' : '';
                        res.textContent = (out.outcome || 'done') + ' · net ' + (out.net || 0) + ' ' + currency + bonus;
                    } else {
                        res.textContent = out.error || 'Play failed';
                    }
                }).catch(function () {
                    var res = $('dp-play-result');
                    if (res) res.textContent = 'Network error';
                }).finally(function () {
                    btn.disabled = false;
                    btn.textContent = 'Play';
                });
            });
            root.appendChild(card);
        });
    }

    function renderAi(hostsData) {
        var root = $('dp-ai-hosts');
        if (!root) return;
        var hosts = (hostsData && hostsData.hosts) || [];
        if (!hosts.length) {
            root.textContent = 'Meet Nova, Luna, Sage & more on the casino floor after linking Discord.';
            return;
        }
        root.innerHTML = '';
        hosts.slice(0, 6).forEach(function (h) {
            var el = document.createElement('div');
            el.className = 'dp-ai-host';
            el.innerHTML = '<strong>' + h.name + '</strong><br><small>' + (h.persona || '') + '</small>';
            root.appendChild(el);
        });
    }

    function renderNetwork(net) {
        var root = $('dp-network');
        if (!root || !net) {
            return;
        }
        root.innerHTML =
            'Today: <strong>' + (net.bonus_mn2_today || 0) + '</strong> / ' + (net.daily_cap_mn2 || 0.5) + ' MN2<br>' +
            'Lifetime: <strong>' + (net.lifetime_bonus_mn2 || 0) + '</strong> MN2';
    }

    function init() {
        loadConfig().then(function (cfg) {
            renderPayments(cfg.payment_options);
            var uber = cfg.uber || {};
            renderVenues(uber.venues);
            var session = cfg.session;
            var uid = (session && session.user_id) || userId;
            if (session && session.success) {
                var badge = $('dp-session-badge');
                if (badge) {
                    badge.classList.remove('hidden');
                    badge.textContent = 'Session active · venue ' + (session.venue || venueParam || 'uber');
                }
            }
            renderGames(uber.games, session && session.success ? uid : null);
            if (cfg.ai_hosts) renderAi(cfg.ai_hosts);
            if (cfg.network) renderNetwork(cfg.network);
        }).catch(function () {
            var res = $('dp-play-result');
            if (res) res.textContent = 'Could not load play site config.';
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
