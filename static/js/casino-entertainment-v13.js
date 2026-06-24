(function () {
    'use strict';

    var userId = localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';

    function $(id) {
        return document.getElementById(id);
    }

    function api(method, path, body) {
        var opts = {
            method: method,
            headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
            credentials: 'same-origin',
        };
        if (body) opts.body = JSON.stringify(Object.assign({ user_id: userId }, body));
        var url = path + (path.indexOf('?') >= 0 ? '&' : '?') + 'user_id=' + encodeURIComponent(userId);
        return fetch(url, opts).then(function (r) { return r.json(); });
    }

    function injectUberTab() {
        var nav = $('casino-v10-main-nav');
        if (!nav || nav.querySelector('[data-v10-tab="uber"]')) return;
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'casino-v10-main-tab';
        btn.setAttribute('data-v10-tab', 'uber');
        btn.setAttribute('role', 'tab');
        btn.textContent = 'Uber';
        var earnBtn = nav.querySelector('[data-v10-tab="earn"]');
        if (earnBtn && earnBtn.parentNode) {
            earnBtn.parentNode.insertBefore(btn, earnBtn.nextSibling);
        } else {
            nav.appendChild(btn);
        }
        var page = document.querySelector('.casino-page');
        if (!page || $('casino-v13-uber')) return;
        var sec = document.createElement('section');
        sec.id = 'casino-v13-uber';
        sec.className = 'casino-v13-panel casino-v10-panel hidden';
        sec.setAttribute('aria-label', 'Uber games');
        var agents = $('casino-v10-agents');
        if (agents && agents.parentNode) {
            agents.parentNode.insertBefore(sec, agents);
        } else {
            page.appendChild(sec);
        }
    }

    function injectPaymentBar() {
        var header = document.querySelector('.casino-header');
        if (!header || $('casino-v13-payments')) return;
        var bar = document.createElement('div');
        bar.id = 'casino-v13-payments';
        bar.className = 'casino-v13-payments';
        bar.innerHTML = '<span class="casino-v13-payments-label">Pay with:</span><span id="casino-v13-payment-chips"></span>';
        header.appendChild(bar);
        api('GET', '/api/casino/payment-options').then(function (d) {
            var chips = $('casino-v13-payment-chips');
            if (!chips) return;
            chips.innerHTML = '';
            (d.payment_options || []).forEach(function (p) {
                var span = document.createElement('span');
                span.className = 'casino-v13-pay-chip' + (p.status === 'planned' ? ' planned' : '');
                span.textContent = p.label;
                chips.appendChild(span);
            });
        });
    }

    function patchTabs() {
        document.querySelectorAll('.casino-v10-main-tab').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var tab = btn.getAttribute('data-v10-tab');
                var uber = $('casino-v13-uber');
                if (uber) uber.classList.toggle('hidden', tab !== 'uber');
                if (tab === 'uber') renderUber();
                if (tab === 'agents') renderAiHosts();
            });
        });
    }

    function renderUber() {
        var root = $('casino-v13-uber');
        if (!root) return;
        root.innerHTML = '<p>Loading uber lounge…</p>';
        Promise.all([
            api('GET', '/api/casino/uber/catalog'),
            api('GET', '/api/casino/network/status'),
        ]).then(function (parts) {
            var cat = parts[0] || {};
            var net = parts[1] || {};
            root.innerHTML =
                '<h2 class="casino-subheading">Uber games — USD/MN2 preferred</h2>' +
                '<p class="casino-v13-network-line">MN2 network bonus today: <strong>' +
                (net.bonus_mn2_today || 0) + '</strong> / ' + (net.daily_cap_mn2 || 0.5) + ' MN2</p>' +
                '<p><a href="/discord-play/" target="_blank" rel="noopener">Discord Play Site</a> — play from Discord with /playnow</p>' +
                '<div class="casino-v13-grid" id="casino-v13-uber-grid"></div>' +
                '<div id="casino-v13-uber-result" class="casino-v13-uber-result"></div>';
            var grid = $('casino-v13-uber-grid');
            (cat.games || []).forEach(function (g) {
                var card = document.createElement('article');
                card.className = 'casino-v13-card';
                card.innerHTML =
                    '<h3>' + (g.icon || '💎') + ' ' + (g.title || g.id) + '</h3>' +
                    '<p>' + (g.description || '') + '</p>' +
                    '<label>Currency <select data-currency><option value="usd">USD</option><option value="mn2">MN2</option></select></label>' +
                    '<input type="number" min="' + (g.min_bet_usd || 5) + '" value="' + (g.min_bet_usd || 5) + '" data-bet>' +
                    '<button type="button" class="casino-v13-btn" data-game="' + g.id + '">Play</button>';
                var playBtn = card.querySelector('[data-game]');
                playBtn.addEventListener('click', function () {
                    var bet = parseFloat(card.querySelector('[data-bet]').value) || 5;
                    var currency = card.querySelector('[data-currency]').value;
                    playBtn.disabled = true;
                    api('POST', '/api/casino/uber/play', { game_id: g.id, bet: bet, currency: currency })
                        .then(function (out) {
                            var res = $('casino-v13-uber-result');
                            if (!res) return;
                            if (out.success) {
                                var b = out.network_bonus_mn2 ? ' · +' + out.network_bonus_mn2 + ' MN2 network' : '';
                                res.textContent = (out.outcome || 'done') + ' net ' + (out.net || 0) + b;
                            } else {
                                res.textContent = out.error || 'Failed';
                            }
                        })
                        .finally(function () { playBtn.disabled = false; });
                });
                grid.appendChild(card);
            });
        });
    }

    function renderAiHosts() {
        var agents = $('casino-v10-agents');
        if (!agents || $('casino-v13-ai-hosts')) return;
        var box = document.createElement('div');
        box.id = 'casino-v13-ai-hosts';
        box.className = 'casino-v13-ai-hosts';
        agents.insertBefore(box, agents.firstChild);
        api('GET', '/api/casino/ai/hosts').then(function (d) {
            box.innerHTML = '<h3 class="casino-subheading">AI entertainment hosts</h3><div class="casino-v13-grid" id="casino-v13-ai-grid"></div>';
            var grid = $('casino-v13-ai-grid');
            (d.hosts || []).forEach(function (h) {
                var card = document.createElement('article');
                card.className = 'casino-v13-card' + (h.unlocked ? '' : ' locked');
                card.innerHTML =
                    '<h3>' + (h.avatar || '🤖') + ' ' + h.name + '</h3>' +
                    '<p>' + (h.persona || '') + '</p>' +
                    (h.unlocked
                        ? '<button type="button" class="casino-v13-btn secondary" data-host="' + h.id + '">Greet</button>' +
                          '<button type="button" class="casino-v13-btn" data-tip="' + h.id + '">Tip 25</button>'
                        : '<p><small>Unlock at level ' + h.min_level + '</small></p>');
                var greet = card.querySelector('[data-host]');
                if (greet) {
                    greet.addEventListener('click', function () {
                        api('POST', '/api/casino/ai/banter', { host_id: h.id, context: 'lobby' }).then(function (r) {
                            if (r.line) alert(r.line);
                        });
                    });
                }
                var tip = card.querySelector('[data-tip]');
                if (tip) {
                    tip.addEventListener('click', function () {
                        api('POST', '/api/casino/ai/tip', { host_id: h.id, coins: 25 }).then(function (r) {
                            if (r.banter) alert(r.banter);
                            else if (r.error) alert(r.error);
                        });
                    });
                }
                grid.appendChild(card);
            });
        });
    }

    function init() {
        injectUberTab();
        injectPaymentBar();
        patchTabs();
        if ((new URLSearchParams(window.location.search).get('tab') || '') === 'uber') {
            setTimeout(function () {
                var btn = document.querySelector('[data-v10-tab="uber"]');
                if (btn) btn.click();
            }, 800);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
