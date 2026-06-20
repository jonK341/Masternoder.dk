(function () {
    'use strict';

    const userId = localStorage.getItem('game_user_id') || 'default_user';
    const baseUrl = window.location.origin;
    let leaderboardPeriod = 'today';
    let lastDoubleBetId = null;
    let activeCurrency = localStorage.getItem('casino_currency') || 'coins';
    let realMoneyEnabled = false;
    let paypalEnabled = false;
    let mn2Limits = { min: 0.05, max: 5 };
    let usdLimits = { min: 0.5, max: 25 };
    let disclaimers = { coins: '', mn2: '', paypal: '' };
    let securityToken = localStorage.getItem('casino_security_token') || '';
    let securityExpires = localStorage.getItem('casino_security_expires') || '';

    function securityTokenValid() {
        if (!securityToken || !securityExpires) return false;
        try {
            return new Date(securityExpires) > new Date();
        } catch (e) {
            return false;
        }
    }

    function betPayload(extra) {
        const body = Object.assign({ user_id: userId, currency: activeCurrency }, extra || {});
        if ((activeCurrency === 'mn2' || activeCurrency === 'usd') && securityTokenValid()) {
            body.verification_token = securityToken;
        }
        return body;
    }

    function currencyLabel(cur) {
        const c = cur || activeCurrency;
        if (c === 'mn2') return 'MN2';
        if (c === 'usd') return 'USD';
        return 'coins';
    }

    function apiPathWithCurrency(path) {
        const sep = path.includes('?') ? '&' : '?';
        return path + sep + 'currency=' + encodeURIComponent(activeCurrency);
    }

    let soundEnabled = localStorage.getItem('casino_sound') === 'on';
    let audioCtx = null;

    function prefersReducedMotion() {
        try {
            return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        } catch (e) {
            return false;
        }
    }

    function playSound(type) {
        if (!soundEnabled) return;
        try {
            audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
            var notes = { tick: [660, 0.04, 0.05], win: [880, 0.06, 0.16], big: [1200, 0.09, 0.32], bust: [180, 0.07, 0.3] };
            var spec = notes[type] || notes.win;
            var osc = audioCtx.createOscillator();
            var gain = audioCtx.createGain();
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.type = type === 'bust' ? 'sawtooth' : 'sine';
            osc.frequency.value = spec[0];
            gain.gain.value = spec[1];
            osc.start();
            osc.stop(audioCtx.currentTime + spec[2]);
        } catch (e) { /* optional sound */ }
    }

    function updateSoundToggle() {
        var btn = $('casino-sound-toggle');
        if (!btn) return;
        btn.textContent = soundEnabled ? '🔊 Sound on' : '🔇 Sound off';
        btn.setAttribute('aria-pressed', soundEnabled ? 'true' : 'false');
    }

    function toggleSound() {
        soundEnabled = !soundEnabled;
        localStorage.setItem('casino_sound', soundEnabled ? 'on' : 'off');
        updateSoundToggle();
        if (soundEnabled) playSound('win');
    }

    function celebrate(title, subtitle, tier) {
        var overlay = $('casino-celebration');
        if (!overlay) return;
        var t = $('casino-celebration-title');
        var s = $('casino-celebration-sub');
        if (t) t.textContent = title;
        if (s) s.textContent = subtitle || '';
        overlay.classList.remove('hidden', 'tier-mega', 'tier-big');
        overlay.classList.add(tier === 'mega' ? 'tier-mega' : 'tier-big');
        if (!prefersReducedMotion()) overlay.classList.add('animate');
        playSound(tier === 'mega' ? 'big' : 'win');
        setTimeout(function () {
            overlay.classList.add('hidden');
            overlay.classList.remove('animate');
        }, tier === 'mega' ? 2600 : 1800);
    }

    function maybeCelebrate(data) {
        if (!data || !data.success || data.outcome !== 'win') return;
        var bet = Number(data.bet || 0);
        var payout = Number(data.payout || 0);
        if (bet <= 0 || payout <= 0) return;
        var multiple = payout / bet;
        if (multiple >= 10) {
            celebrate('MEGA WIN', '+' + formatNet(data.net) + ' ' + currencyLabel(data.currency) + ' · ' + multiple.toFixed(2) + '×', 'mega');
        } else if (multiple >= 3) {
            celebrate('BIG WIN', '+' + formatNet(data.net) + ' ' + currencyLabel(data.currency) + ' · ' + multiple.toFixed(2) + '×', 'big');
        }
    }

    function showToast(message) {
        const toast = $('casino-toast');
        if (!toast) return;
        toast.textContent = message;
        toast.classList.remove('hidden');
        playSound('tick');
        setTimeout(function () { toast.classList.add('hidden'); }, 3200);
    }

    function applyCurrencyUi() {
        document.querySelectorAll('.casino-currency-btn').forEach(function (btn) {
            btn.classList.toggle('active', btn.getAttribute('data-currency') === activeCurrency);
        });
        const mn2Btn = $('casino-mn2-toggle');
        const usdBtn = $('casino-usd-toggle');
        if (mn2Btn) mn2Btn.disabled = !realMoneyEnabled;
        if (usdBtn) usdBtn.disabled = !paypalEnabled;
        const depositPanel = $('casino-paypal-deposit');
        if (depositPanel) {
            depositPanel.classList.toggle('hidden', activeCurrency !== 'usd' || !paypalEnabled);
        }
        const secBar = $('casino-security-bar');
        if (secBar) {
            const needsSec = (activeCurrency === 'mn2' || activeCurrency === 'usd') && !securityTokenValid();
            secBar.classList.toggle('hidden', !needsSec);
        }
        const isMn2 = activeCurrency === 'mn2';
        const isUsd = activeCurrency === 'usd';
        document.querySelectorAll('.casino-controls input[type="number"]').forEach(function (input) {
            if (isMn2) {
                input.min = String(mn2Limits.min);
                input.max = String(mn2Limits.max);
                input.step = '0.01';
                if (parseFloat(input.value) > mn2Limits.max) input.value = String(mn2Limits.min);
            } else if (isUsd) {
                input.min = String(usdLimits.min);
                input.max = String(usdLimits.max);
                input.step = '0.01';
                if (parseFloat(input.value) > usdLimits.max) input.value = String(usdLimits.min);
            } else {
                input.min = '5';
                input.max = '500';
                input.step = '1';
            }
        });
        const disclaimer = $('casino-disclaimer-text');
        if (disclaimer) {
            if (activeCurrency === 'usd' && disclaimers.paypal) disclaimer.textContent = disclaimers.paypal;
            else if (activeCurrency === 'mn2' && disclaimers.mn2) disclaimer.textContent = disclaimers.mn2;
            else if (disclaimers.coins) disclaimer.textContent = disclaimers.coins;
        }
    }

    function setActiveCurrency(currency) {
        if (currency === 'mn2' && !realMoneyEnabled) return;
        if (currency === 'usd' && !paypalEnabled) return;
        if (currency === 'mn2') activeCurrency = 'mn2';
        else if (currency === 'usd') activeCurrency = 'usd';
        else activeCurrency = 'coins';
        localStorage.setItem('casino_currency', activeCurrency);
        applyCurrencyUi();
        refreshBalance();
        refreshLeaderboard();
        refreshHouseStats();
        refreshSocialBoard();
        safeRefresh('jackpotMeter', refreshJackpotMeter);
        safeRefresh('tournaments', refreshTournaments);
        safeRefresh('rg', refreshRgStatus);
    }

    function showDoubleOffer(data) {
        try { maybeCelebrate(data); } catch (e) { /* celebration optional */ }
        if (data && data.success && data.trophy_rebate && data.trophy_rebate.rebate > 0) {
            var tr = data.trophy_rebate;
            showToast('Trophy rebate +' + tr.rebate + ' ' + currencyLabel(tr.currency || data.currency) +
                ' (' + Math.round((tr.rebate_pct || 0) * 100) + '% back on loss)');
        }
        const bar = $('casino-double-bar');
        if (!bar) return;
        if (data && data.success && data.can_double && data.bet_id) {
            lastDoubleBetId = data.bet_id;
            bar.classList.remove('hidden');
            bar.innerHTML =
                'You won ' + data.payout + ' ' + currencyLabel(data.currency) + '! Double-or-nothing: risk ' + data.double_stake +
                ' to win ' + (data.double_stake * 2) + '. ' +
                '<button type="button" id="casino-double-btn" class="casino-double-btn">Double</button>' +
                '<button type="button" id="casino-double-skip" class="casino-double-skip">Keep</button>';
            $('casino-double-btn')?.addEventListener('click', playDouble);
            $('casino-double-skip')?.addEventListener('click', function () {
                bar.classList.add('hidden');
                lastDoubleBetId = null;
            });
        } else {
            bar.classList.add('hidden');
        }
    }

    function $(id) {
        return document.getElementById(id);
    }

    async function api(path, options, timeoutMs) {
        const url = baseUrl + path + (path.includes('?') ? '&' : '?') + 'user_id=' + encodeURIComponent(userId);
        const ms = timeoutMs || 20000;
        const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
        let timer = null;
        const fetchOpts = Object.assign({}, options || {});
        if (controller) {
            fetchOpts.signal = controller.signal;
            timer = setTimeout(function () { controller.abort(); }, ms);
        }
        try {
            const res = await fetch(url, fetchOpts);
            const data = await res.json().catch(function () { return {}; });
            if (!res.ok && !data.error) {
                data.error = 'Request failed (' + res.status + ')';
            }
            if (!res.ok && data.success == null) {
                data.success = false;
            }
            return data;
        } catch (err) {
            var msg = (err && err.name === 'AbortError') ? 'Request timed out' : ((err && err.message) || 'Network error');
            return { success: false, error: msg };
        } finally {
            if (timer) clearTimeout(timer);
        }
    }

    function bindClick(id, handler) {
        var el = $(id);
        if (el) el.addEventListener('click', handler);
    }

    function bindChange(id, handler) {
        var el = $(id);
        if (el) el.addEventListener('change', handler);
    }

    function markStaleLoadingPanels() {
        var stale = [
            ['casino-balance', 'Could not load balance — refresh the page'],
            ['casino-house-stats', 'House stats unavailable'],
            ['casino-rank-bar', 'Rank unavailable'],
            ['casino-personal-bests', 'Records unavailable'],
            ['casino-hall-of-fame', 'Hall of fame unavailable'],
            ['casino-disclaimer-text', 'Casino data unavailable — refresh the page'],
            ['casino-slots-grid', 'Slot machines unavailable — refresh the page'],
            ['casino-deposit-packs', 'PayPal deposits unavailable'],
            ['casino-social-board', 'Social board unavailable'],
            ['counter-pick-hint', 'Counter hint unavailable'],
            ['rps-distribution-stats', 'Battle stats unavailable'],
            ['outcome-distribution-stats', 'Battle outcomes unavailable'],
        ];
        stale.forEach(function (pair) {
            var node = $(pair[0]);
            if (!node) return;
            var txt = (node.textContent || '').toLowerCase();
            if (txt.indexOf('loading') >= 0 || txt.indexOf('henter') >= 0) {
                node.textContent = pair[1];
            }
        });
    }

    function safeRefresh(name, fn) {
        try {
            return Promise.resolve(fn()).catch(function (err) {
                console.warn('[casino] ' + name + ' failed:', err);
            });
        } catch (err) {
            console.warn('[casino] ' + name + ' sync failed:', err);
            return Promise.resolve();
        }
    }

    function shortUser(uid) {
        if (!uid) return '—';
        if (uid.length <= 14) return uid;
        return uid.slice(0, 10) + '…';
    }

    function setResult(el, data) {
        if (data && data.success && data.jackpot) {
            try { jackpotCelebrate(data.jackpot); } catch (e) { /* optional */ }
            try { safeRefresh('jackpotMeter', refreshJackpotMeter); } catch (e) { /* optional */ }
        }
        if (!el) return;
        el.classList.remove('win', 'loss', 'draw');
        if (!data.success) {
            el.textContent = data.error || 'Play failed';
            el.classList.add('loss');
            if (data.error && String(data.error).toLowerCase().indexOf('responsible gaming') >= 0) {
                safeRefresh('rg', refreshRgStatus);
            }
            return;
        }
        el.classList.add(data.outcome || 'draw');
        const details = data.details || {};
        if (data.game === 'coin_flip') {
            el.textContent = data.outcome.toUpperCase() + ': ' + details.result + ' (picked ' + details.choice + ') — net ' + data.net;
        } else if (data.game === 'dice') {
            el.textContent = data.outcome.toUpperCase() + ': rolled ' + details.roll + ' (guessed ' + details.guess + ') — net ' + data.net;
        } else if (data.game === 'rps_distribution') {
            el.textContent = data.outcome.toUpperCase() + ': predicted ' + details.prediction + ', house played ' + details.actual +
                ' (' + (details.multiplier || '?') + '×) — net ' + data.net;
        } else if (data.game === 'free_daily_bet') {
            el.textContent = data.outcome.toUpperCase() + ': FREE flip ' + details.result + ' (picked ' + details.choice + ') — net ' + data.net;
        } else if (data.game === 'double_or_nothing') {
            el.textContent = data.outcome.toUpperCase() + ': doubled stake ' + data.bet + ' — net ' + data.net;
        } else if (data.game === 'mystery_coin_flip') {
            el.textContent = data.outcome.toUpperCase() + ': ' + details.result + ' @ ' + details.multiplier + '× (picked ' + details.choice + ') — net ' + data.net;
        } else if (data.game === 'scratch_card') {
            el.textContent = data.outcome.toUpperCase() + ': ' + (details.tiles || []).join(' ') + ' (' + details.match_label + ') — net ' + data.net;
        } else if (data.game === 'battle_outcome') {
            el.textContent = data.outcome.toUpperCase() + ': predicted ' + details.prediction + ', actual ' + details.actual +
                ' (' + (details.multiplier || '?') + '×) — net ' + data.net + ' ' + (data.currency || currencyLabel());
        } else if (data.game === 'rps_counter_pick') {
            el.textContent = data.outcome.toUpperCase() + ': you ' + details.choice + ' vs house ' + details.house_move +
                ' (counter to ' + details.common_opener + ') — net ' + data.net + ' ' + (data.currency || currencyLabel());
        } else if (data.game === 'plinko') {
            var pd = data.details || {};
            el.textContent = data.outcome.toUpperCase() + ': bin ' + pd.bin + ' @ ' + Number(pd.multiplier || 0) +
                '× (' + (pd.risk || 'medium') + ' risk) — net ' + formatNet(data.net) + ' ' + currencyLabel(data.currency);
        } else if (data.game === 'wheel') {
            var wd = data.details || {};
            el.textContent = data.outcome.toUpperCase() + ': landed ' + Number(wd.multiplier || 0) +
                '× (' + (wd.risk || 'medium') + ' risk) — net ' + formatNet(data.net) + ' ' + currencyLabel(data.currency);
        } else if (data.game === 'mines') {
            if (data.hit_mine) {
                el.textContent = 'BOOM: hit a mine — net ' + formatNet(data.net) + ' ' + currencyLabel(data.currency);
            } else {
                el.textContent = data.outcome.toUpperCase() + ': cashed out @ ' + Number(data.multiplier || 0) +
                    '× — net ' + formatNet(data.net) + ' ' + currencyLabel(data.currency);
            }
        } else if (data.game === 'keno') {
            var kd = data.details || {};
            el.textContent = data.outcome.toUpperCase() + ': ' + (kd.hits || 0) + '/' + (kd.spots || []).length +
                ' hits @ ' + Number(kd.multiplier || 0) + '× (drew ' + (kd.drawn || []).join(',') + ') — net ' +
                formatNet(data.net) + ' ' + currencyLabel(data.currency);
        } else if (data.game === 'roulette') {
            var rdt = data.details || {};
            el.textContent = data.outcome.toUpperCase() + ': landed ' + rdt.pocket + ' (' + rdt.color + ') on ' +
                rdt.bet_type + (rdt.selection != null ? ' ' + rdt.selection : '') + ' — net ' +
                formatNet(data.net) + ' ' + currencyLabel(data.currency);
        } else if (data.game === 'hilo') {
            if (data.busted) {
                el.textContent = 'BUST: wrong call — net ' + formatNet(data.net) + ' ' + currencyLabel(data.currency);
            } else {
                el.textContent = data.outcome.toUpperCase() + ': cashed out @ ' + Number(data.multiplier || 0).toFixed(2) +
                    '× — net ' + formatNet(data.net) + ' ' + currencyLabel(data.currency);
            }
        } else if (data.game === 'crash') {
            if (data.outcome === 'win') {
                el.textContent = 'WIN: cashed out @ ' + Number(data.multiplier || data.cashout || 0).toFixed(2) +
                    '× (rocket would have crashed @ ' + Number(data.bust || 0).toFixed(2) + '×) — net ' +
                    formatNet(data.net) + ' ' + currencyLabel(data.currency);
            } else {
                el.textContent = 'CRASH: rocket busted @ ' + Number(data.bust || 0).toFixed(2) +
                    '× before you cashed out — net ' + formatNet(data.net) + ' ' + currencyLabel(data.currency);
            }
        } else if (data.game && String(data.game).indexOf('slot_') === 0) {
            var det = data.details || {};
            var reelsTxt = (det.reels || []).map(function (s) {
                return displaySymbol(s, det.symbol_display);
            }).join(' | ');
            var extra = det.match === 'jackpot' ? ' JACKPOT!' : (det.scatter_bonus ? ' +scatter ' + det.scatter_bonus : '');
            var near = det.near_miss ? ' (near miss!)' : '';
            el.textContent = data.outcome.toUpperCase() + ': ' + reelsTxt +
                ' (' + (det.match || 'none') + (det.multiplier ? ' @ ' + det.multiplier + '×' : '') + extra + near + ') — net ' + data.net;
        } else if (data.game === 'slot_classic' || data.game === 'slot_diamond') {
            el.textContent = data.outcome.toUpperCase() + ': ' + (details.reels || []).join(' | ') +
                ' (' + (details.match || 'none') + (details.multiplier ? ' @ ' + details.multiplier + '×' : '') + ') — net ' + data.net;
        } else {
            el.textContent = data.outcome.toUpperCase() + ': you ' + details.choice + ' vs ' + details.opponent +
                ' — net ' + data.net + ' ' + (data.currency || currencyLabel());
        }
    }

    function formatNet(value) {
        if (activeCurrency === 'mn2') return Number(value).toFixed(4);
        if (activeCurrency === 'usd') return Number(value).toFixed(2);
        return Math.round(value);
    }

    async function refreshDepositPacks() {
        const el = $('casino-deposit-packs');
        if (!el) return;
        const data = await api('/api/casino/paypal/deposit-packs');
        if (!data.success || !(data.packs || []).length) {
            el.textContent = 'PayPal deposits unavailable';
            return;
        }
        el.innerHTML = '';
        (data.packs || []).forEach(function (pack) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'casino-deposit-pack-btn';
            btn.textContent = pack.label + ' ($' + Number(pack.amount_usd).toFixed(2) + ')';
            btn.addEventListener('click', function () { startPayPalDeposit(pack.id); });
            el.appendChild(btn);
        });
    }

    async function refreshMn2BuyinPacks() {
        const el = $('casino-mn2-buyin-packs');
        if (!el) return;
        const data = await api('/api/casino/mn2-buyin-packs');
        if (!data.success || !(data.packs || []).length) {
            el.textContent = 'MN2 buy-in packs unavailable';
            return;
        }
        el.innerHTML = '';
        (data.packs || []).forEach(function (pack) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'casino-deposit-pack-btn';
            btn.textContent = (pack.label || pack.id) + ' (' + Number(pack.price_mn2).toFixed(2) + ' MN2 → $' + Number(pack.casino_usd_credit).toFixed(2) + ')';
            btn.addEventListener('click', function () { purchaseMn2BuyinPack(pack.id); });
            el.appendChild(btn);
        });
    }

    async function purchaseMn2BuyinPack(packId) {
        const data = await api('/api/casino/mn2-buyin/purchase', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, pack_id: packId }),
        });
        if (data.success) {
            showToast('MN2 buy-in complete! USD balance: $' + Number(data.casino_usd_credited || 0).toFixed(2));
            setActiveCurrency('usd');
            refreshBalance();
        } else {
            alert(data.error || 'Could not purchase MN2 buy-in pack');
        }
    }

    async function startPayPalDeposit(packId) {
        const data = await api('/api/casino/paypal/deposit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, pack_id: packId }),
        });
        if (data.success && data.approve_url) {
            window.location.href = data.approve_url;
        } else {
            alert(data.error || 'Could not start PayPal checkout');
        }
    }

    async function handlePayPalReturn() {
        const params = new URLSearchParams(window.location.search);
        if (params.get('paypal') !== 'success') return;
        const orderId = params.get('token');
        const packId = params.get('pack_id');
        if (!orderId) return;
        const data = await api('/api/casino/paypal/capture', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, order_id: orderId, pack_id: packId }),
        });
        if (data.success) {
            showToast('PayPal deposit complete! USD balance: $' + Number(data.fiat_balance || 0).toFixed(2));
            setActiveCurrency('usd');
        } else {
            alert(data.error || 'PayPal capture failed');
        }
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    async function refreshBalance() {
        const data = await api('/api/casino/balance', null, 12000);
        const el = $('casino-balance');
        if (el) {
            if (data.success) {
                el.textContent =
                    'Coins: ' + Math.round(data.balance) +
                    ' · MN2: ' + Number(data.mn2_balance || 0).toFixed(4) +
                    ' · USD: $' + Number(data.fiat_balance || 0).toFixed(2) +
                    ' · Bets today: ' + data.bets_today + '/' + data.max_bets_per_day +
                    ' · Staking: ' + currencyLabel();
            } else {
                el.textContent = data.error || 'Could not load balance';
            }
        }
        const disclaimer = $('casino-disclaimer-text');
        if (disclaimer) {
            if (data.success && data.disclaimer && activeCurrency === 'coins') {
                disclaimer.textContent = data.disclaimer;
            } else if (!data.success) {
                disclaimer.textContent = data.error || 'Casino unavailable — try refreshing.';
            }
        }
        if (!data.success) return;
        try {
            realMoneyEnabled = !!(data.real_money && data.real_money.enabled);
            paypalEnabled = realMoneyEnabled && (data.real_money.rails || []).indexOf('paypal') >= 0;
            if (data.real_money) {
                mn2Limits.min = data.real_money.mn2_min_bet || 0.05;
                mn2Limits.max = data.real_money.mn2_max_bet || 5;
                usdLimits.min = data.real_money.paypal_min_bet || 0.5;
                usdLimits.max = data.real_money.paypal_max_bet || 25;
                disclaimers.coins = data.disclaimer || '';
                disclaimers.mn2 = data.real_money.disclaimer_mn2 || disclaimers.coins;
                disclaimers.paypal = data.real_money.disclaimer_paypal || disclaimers.coins;
            }
            applyCurrencyUi();
        } catch (uiErr) {
            console.warn('[casino] currency ui failed:', uiErr);
        }
        if (data.games) {
            try {
                renderSlotMachinesFromGames(data.games);
            } catch (slotErr) {
                console.warn('[casino] slot render failed:', slotErr);
                var grid = $('casino-slots-grid');
                if (grid) grid.textContent = 'Slot machines failed to render.';
            }
            if (data.games.plinko) {
                try {
                    plinko.rows = data.games.plinko.rows || 12;
                    plinko.riskTables = data.games.plinko.risk_tables || {};
                    if (!plinko.drawing) drawPlinkoBoard(null, null);
                } catch (plinkoErr) {
                    console.warn('[casino] plinko init failed:', plinkoErr);
                }
            }
            if (data.games.wheel) {
                try {
                    wheel.riskTables = data.games.wheel.risk_tables || {};
                    if (!wheel.spinning) drawWheel(wheel.rotation, -1);
                } catch (wheelErr) {
                    console.warn('[casino] wheel init failed:', wheelErr);
                }
            }
            if (data.games.mines) {
                try {
                    mines.tiles = data.games.mines.tiles || 25;
                    if (!mines.active) buildMinesGrid();
                } catch (minesErr) {
                    console.warn('[casino] mines init failed:', minesErr);
                }
            }
            if (data.games.keno) {
                try {
                    keno.pool = data.games.keno.pool || 40;
                    keno.maxSpots = data.games.keno.max_spots || 6;
                    keno.drawCount = data.games.keno.draw || 10;
                    if (!keno.playing) buildKenoGrid();
                } catch (kenoErr) {
                    console.warn('[casino] keno init failed:', kenoErr);
                }
            }
        }
    }

    async function refreshHouseStats() {
        const el = $('casino-house-stats');
        if (!el) return;
        const data = await api(apiPathWithCurrency('/api/casino/house-stats'));
        if (!data.success) {
            el.textContent = data.error || 'House stats unavailable';
            return;
        }
        el.textContent =
            'Today (' + data.currency + ') — Your net: ' + formatNet(data.your_net) +
            ' · Games: ' + data.your_games +
            ' · All players net: ' + formatNet(data.global_player_net) +
            ' · House net: ' + formatNet(data.house_net) +
            ' · Total wagered: ' + formatNet(data.total_wagered);
    }

    async function refreshSocialBoard() {
        const el = $('casino-social-board');
        if (!el) return;
        const data = await api(apiPathWithCurrency('/api/casino/social-mini-board?period=' + encodeURIComponent(leaderboardPeriod)));
        if (!data.success) {
            el.textContent = 'Social board unavailable';
            return;
        }
        if (!(data.leaderboard || []).length) {
            el.textContent = data.peer_count > 0
                ? 'No friend/crew bets yet this period (' + data.peer_count + ' peers)'
                : 'Add friends or join a crew to see a mini-board';
            return;
        }
        el.innerHTML = '';
        (data.leaderboard || []).forEach(function (row) {
            const line = document.createElement('div');
            line.className = 'casino-social-row';
            line.textContent = '#' + row.rank + ' ' + shortUser(row.user_id) + ' · net ' + formatNet(row.net);
            el.appendChild(line);
        });
    }

    async function refreshCounterHint() {
        const el = $('counter-pick-hint');
        if (!el) return;
        const data = await api('/api/casino/counter-pick-hint');
        if (!data.success) {
            el.textContent = 'Counter hint unavailable';
            return;
        }
        el.textContent = data.hint || ('Suggested counter: ' + data.counter_pick);
    }

    async function refreshHistory() {
        const data = await api('/api/casino/history?limit=10');
        const tbody = $('casino-history-body');
        if (!tbody) return;
        if (!data.success) {
            tbody.innerHTML = '<tr><td colspan="5">' + (data.error || 'History unavailable') + '</td></tr>';
            return;
        }
        tbody.innerHTML = '';
        (data.history || []).forEach(function (row) {
            const tr = document.createElement('tr');
            tr.innerHTML = '<td>' + row.game + '</td><td>' + row.bet + '</td><td>' + row.outcome + '</td><td>' + row.net + '</td><td>' + (row.created_at || '') + '</td>';
            tbody.appendChild(tr);
        });
    }

    async function refreshDistribution() {
        const el = $('rps-distribution-stats');
        if (!el) return;
        const lane = $('rps-dist-lane')?.value || '';
        const ctx = $('rps-dist-context')?.value || '';
        let path = '/api/casino/battle-rps-distribution';
        const params = [];
        if (lane) params.push('difficulty=' + encodeURIComponent(lane));
        if (ctx) params.push('player_move=' + encodeURIComponent(ctx));
        if (params.length) path += '?' + params.join('&');
        const data = await api(path);
        if (!data.success) {
            el.textContent = 'Battle stats unavailable';
            return;
        }
        const pct = data.percentages || {};
        const mult = data.payout_multipliers || {};
        el.innerHTML =
            (data.window_label || 'Live window') + ' · ' + (data.difficulty_label || 'all lanes') +
            ' · ' + (data.signal_label || 'all openers') + ' (n=' + data.total + ')<br>' +
            'Rock ' + Math.round((pct.rock || 0) * 100) + '% (' + (mult.rock || '?') + '×) · ' +
            'Paper ' + Math.round((pct.paper || 0) * 100) + '% (' + (mult.paper || '?') + '×) · ' +
            'Scissors ' + Math.round((pct.scissors || 0) * 100) + '% (' + (mult.scissors || '?') + '×)' +
            (data.source === 'uniform_fallback' ? '<br><em>No recent battle data — even odds fallback.</em>' : '') +
            (data.source === 'dual_signal' ? '<br><em>Dual-signal: opponent moves after selected player opener.</em>' : '');
    }

    async function refreshOutcomeDistribution() {
        const el = $('outcome-distribution-stats');
        if (!el) return;
        const lane = $('outcome-dist-lane')?.value || '';
        let path = '/api/casino/battle-outcome-distribution';
        if (lane) path += '?difficulty=' + encodeURIComponent(lane);
        const data = await api(path);
        if (!data.success) {
            el.textContent = 'Battle outcomes unavailable';
            return;
        }
        const pct = data.percentages || {};
        const mult = data.payout_multipliers || {};
        el.innerHTML =
            (data.window_label || 'Live window') + ' · ' + (data.difficulty_label || 'all lanes') + ' (n=' + data.total + ')<br>' +
            'Win ' + Math.round((pct.win || 0) * 100) + '% (' + (mult.win || '?') + '×) · ' +
            'Draw ' + Math.round((pct.draw || 0) * 100) + '% (' + (mult.draw || '?') + '×) · ' +
            'Loss ' + Math.round((pct.loss || 0) * 100) + '% (' + (mult.loss || '?') + '×)' +
            (data.source === 'uniform_fallback' ? '<br><em>No recent battle data — even odds fallback.</em>' : '');
    }

    function renderBonusItem(bonus) {
        const li = document.createElement('li');
        li.className = 'casino-quest-item casino-bonus-item' + (bonus.eligible ? ' completed' : '') + (bonus.claimed ? ' claimed' : '');
        let action = '';
        if (bonus.claimed) {
            action = '<span class="casino-quest-claimed">Claimed</span>';
        } else if (bonus.eligible) {
            action = '<button type="button" class="casino-quest-claim" data-quest-id="' + bonus.id + '">Claim +' + bonus.reward_coins + '</button>';
        } else {
            action = '<span class="casino-quest-reward">+' + bonus.reward_coins + ' coins</span>';
        }
        const streakNote = bonus.id === 'bonus_streak_3' ? ' · Streak ' + (bonus.streak_days || 0) + '/' + (bonus.streak_required || 3) : '';
        li.innerHTML =
            '<div class="casino-quest-title">' + bonus.title + '</div>' +
            '<div class="casino-quest-desc">' + bonus.description + streakNote + '</div>' +
            action;
        return li;
    }

    async function refreshQuests() {
        const list = $('casino-quests-list');
        const bonusList = $('casino-bonus-list');
        const weeklyList = $('casino-weekly-list');
        if (!list) return;
        const data = await api('/api/casino/quests');
        list.innerHTML = '';
        if (bonusList) bonusList.innerHTML = '';
        if (weeklyList) weeklyList.innerHTML = '';
        if (!data.success) {
            list.innerHTML = '<li>Could not load quests</li>';
            return;
        }
        if (data.weekly && weeklyList) {
            const w = data.weekly;
            const li = document.createElement('li');
            li.className = 'casino-quest-item casino-weekly-item' + (w.completed ? ' completed' : '') + (w.claimed ? ' claimed' : '');
            let action = '';
            if (w.claimed) {
                action = '<span class="casino-quest-claimed">Claimed</span>';
            } else if (w.completed) {
                action = '<button type="button" class="casino-quest-claim" data-quest-id="' + w.id + '">Claim +' + w.reward_coins + ' 🏅</button>';
            } else {
                action = '<span class="casino-quest-reward">+' + w.reward_coins + ' coins</span>';
            }
            li.innerHTML =
                '<div class="casino-quest-title">' + w.title + ' <span class="casino-week-tag">' + w.week + '</span></div>' +
                '<div class="casino-quest-desc">' + w.description + ' (' + w.progress + '/' + w.target + ')</div>' +
                action;
            weeklyList.appendChild(li);
        }
        refreshFreeBetStatus(data.free_daily_bet);
        (data.quests || []).forEach(function (quest) {
            const li = document.createElement('li');
            li.className = 'casino-quest-item' + (quest.completed ? ' completed' : '') + (quest.claimed ? ' claimed' : '') +
                (quest.rotating ? ' casino-rotating-item' : '');
            const progress = quest.progress + '/' + quest.target;
            let action = '';
            if (quest.claimed) {
                action = '<span class="casino-quest-claimed">Claimed</span>';
            } else if (quest.completed) {
                action = '<button type="button" class="casino-quest-claim" data-quest-id="' + quest.id + '">Claim +' + quest.reward_coins + '</button>';
            } else {
                action = '<span class="casino-quest-reward">+' + quest.reward_coins + ' coins</span>';
            }
            li.innerHTML =
                '<div class="casino-quest-title">' + quest.title + '</div>' +
                '<div class="casino-quest-desc">' + quest.description + ' (' + progress + ')</div>' +
                action;
            list.appendChild(li);
        });
        (data.bonuses || []).forEach(function (bonus) {
            if (bonusList) bonusList.appendChild(renderBonusItem(bonus));
        });
        document.querySelectorAll('.casino-quest-claim').forEach(function (btn) {
            btn.addEventListener('click', function () {
                claimQuest(btn.getAttribute('data-quest-id'));
            });
        });
    }

    async function claimQuest(questId) {
        const data = await api('/api/casino/quests/claim', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ quest_id: questId, user_id: userId }),
        });
        if (!data.success) {
            alert(data.error || 'Could not claim quest');
            return;
        }
        showToast('Quest claimed! +' + (data.reward_coins || 0) + ' coins');
        await refreshBalance();
        await refreshQuests();
    }

    async function refreshLeaderboard() {
        const tbody = $('casino-leaderboard-body');
        const rankBar = $('casino-rank-bar');
        if (!tbody) return;
        const data = await api(apiPathWithCurrency('/api/casino/leaderboard?period=' + encodeURIComponent(leaderboardPeriod) + '&limit=10'));
        tbody.innerHTML = '';
        if (!data.success) {
            tbody.innerHTML = '<tr><td colspan="5">' + (data.error || 'Leaderboard unavailable') + '</td></tr>';
            if (rankBar) rankBar.textContent = data.error || 'Rank unavailable';
            return;
        }
        (data.leaderboard || []).forEach(function (row) {
            const tr = document.createElement('tr');
            const highlight = row.user_id === userId ? ' class="casino-you"' : '';
            tr.innerHTML =
                '<td' + highlight + '>' + row.rank + '</td>' +
                '<td' + highlight + '>' + shortUser(row.user_id) + '</td>' +
                '<td' + highlight + '>' + row.net + '</td>' +
                '<td' + highlight + '>' + (row.win_rate != null ? row.win_rate + '%' : '—') + '</td>' +
                '<td' + highlight + '>' + (row.roi != null ? row.roi + '%' : '—') + '</td>';
            tbody.appendChild(tr);
        });
        if (!(data.leaderboard || []).length) {
            tbody.innerHTML = '<tr><td colspan="5">No bets yet for this period</td></tr>';
        }
        if (rankBar) {
            const you = data.your_rank;
            if (!you) {
                rankBar.textContent = 'Your rank: unranked this period — place a bet to appear.';
            } else {
                rankBar.textContent =
                    'Your rank #' + you.rank + ' · Net ' + you.net + ' · Win ' + you.win_rate + '% · ROI ' + you.roi + '%' +
                    (you.gap_to_first > 0 ? ' · ' + you.gap_to_first + ' behind #1' : ' · Leading!');
            }
        }
    }

    function refreshFreeBetStatus(status) {
        const el = $('free-bet-status');
        const btn = $('free-bet-play');
        if (!el || !status) return;
        if (status.available) {
            el.textContent = 'Available: free ' + status.coins + '-coin flip today';
            if (btn) btn.disabled = false;
        } else {
            el.textContent = 'Free flip used today — come back tomorrow';
            if (btn) btn.disabled = true;
        }
    }

    async function refreshPersonalBests() {
        const el = $('casino-personal-bests');
        if (!el) return;
        const data = await api('/api/casino/personal-bests');
        if (!data.success) {
            el.textContent = 'Records unavailable';
            return;
        }
        el.textContent =
            'Personal bests — Best day: +' + data.best_day_net + ' coins' +
            (data.best_day ? ' (' + data.best_day + ')' : '') +
            ' · Longest win streak: ' + data.longest_win_streak +
            ' · Biggest win: ' + data.biggest_single_win + ' coins';
    }

    async function refreshHallOfFame() {
        const el = $('casino-hall-of-fame');
        if (!el) return;
        const data = await api('/api/casino/hall-of-fame?limit=2');
        if (!data.success || !(data.weeks || []).length) {
            el.textContent = 'No hall of fame snapshots yet';
            return;
        }
        el.innerHTML = '';
        (data.weeks || []).forEach(function (week) {
            const block = document.createElement('div');
            block.className = 'casino-hof-week';
            const names = (week.leaderboard || []).slice(0, 3).map(function (r) {
                return '#' + r.rank + ' ' + shortUser(r.user_id) + ' (' + r.net + ')';
            }).join(' · ');
            block.textContent = week.week + ': ' + (names || 'No bets');
            el.appendChild(block);
        });
    }

    async function playDouble() {
        if (!lastDoubleBetId) return;
        const data = await api('/api/casino/double-or-nothing', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bet_id: lastDoubleBetId, user_id: userId }),
        });
        const bar = $('casino-double-bar');
        if (bar && !data.success) {
            bar.textContent = data.error || 'Double failed';
        }
        showDoubleOffer(data);
        await afterPlay();
    }

    async function playFreeBet() {
        const data = await api('/api/casino/play/free-daily-bet', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ choice: $('free-bet-choice').value, user_id: userId }),
        });
        setResult($('free-bet-result'), data);
        await afterPlay();
    }

    async function playCounterPick() {
        const data = await api('/api/casino/play/rps-counter-pick', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(betPayload({
                bet: parseFloat($('counter-bet').value),
                choice: $('counter-choice').value,
            })),
        });
        setResult($('counter-result'), data);
        showDoubleOffer(data);
        await afterPlay();
    }

    async function afterPlay() {
        await refreshBalance();
        await refreshHistory();
        await refreshQuests();
        await refreshLeaderboard();
        await refreshPersonalBests();
        await refreshHouseStats();
        await refreshSocialBoard();
        safeRefresh('rg', refreshRgStatus);
        safeRefresh('activityFeed', refreshActivityFeed);
        safeRefresh('jackpotMeter', refreshJackpotMeter);
    }

    async function refreshRgStatus() {
        var el = $('casino-rg-banner');
        if (!el) return;
        var data = await api('/api/casino/responsible-gaming/status?currency=' + encodeURIComponent(activeCurrency));
        if (!data || !data.success || !data.enabled) {
            el.classList.add('hidden');
            return;
        }
        if (data.cooldown_active) {
            el.textContent = 'Responsible gaming pause active until ' + (data.cooldown_until || 'later') +
                '. Take a break — limits scale with XP.';
            el.style.cssText = 'padding:10px 14px;margin:8px 0;border-radius:8px;background:rgba(255,100,80,0.15);border-left:4px solid #ff6655;font-size:0.9em;';
            el.classList.remove('hidden');
            return;
        }
        if (data.session_cap != null && data.session_loss > 0) {
            var pct = Math.min(100, Math.round((data.session_loss / data.session_cap) * 100));
            if (pct >= 70) {
                el.textContent = 'Session loss ' + formatNet(data.session_loss) + ' / ' + data.session_cap +
                    ' ' + currencyLabel(data.currency) + ' (' + pct + '% of limit).';
                el.style.cssText = 'padding:10px 14px;margin:8px 0;border-radius:8px;background:rgba(255,170,68,0.12);border-left:4px solid #ffaa44;font-size:0.9em;';
                el.classList.remove('hidden');
                return;
            }
        }
        el.classList.add('hidden');
    }

    async function playCoinFlip() {
        const data = await api('/api/casino/play/coin-flip', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(betPayload({
                bet: parseFloat($('coin-flip-bet').value),
                choice: $('coin-flip-choice').value,
            })),
        });
        setResult($('coin-flip-result'), data);
        showDoubleOffer(data);
        await afterPlay();
    }

    async function playDice() {
        const data = await api('/api/casino/play/dice', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(betPayload({
                bet: parseFloat($('dice-bet').value),
                guess: parseInt($('dice-guess').value, 10),
            })),
        });
        setResult($('dice-result'), data);
        showDoubleOffer(data);
        await afterPlay();
    }

    async function playRps() {
        const data = await api('/api/casino/play/rps-bet', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(betPayload({
                bet: parseFloat($('rps-bet').value),
                choice: $('rps-choice').value,
            })),
        });
        setResult($('rps-result'), data);
        showDoubleOffer(data);
        await afterPlay();
    }

    async function playRpsDistribution() {
        const body = betPayload({
            bet: parseFloat($('rps-dist-bet').value),
            prediction: $('rps-dist-prediction').value,
        });
        const lane = $('rps-dist-lane')?.value;
        const ctx = $('rps-dist-context')?.value;
        if (lane) body.difficulty = lane;
        if (ctx) body.player_move = ctx;
        const data = await api('/api/casino/play/rps-distribution', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        setResult($('rps-dist-result'), data);
        showDoubleOffer(data);
        await afterPlay();
    }

    async function playMysteryFlip() {
        const data = await api('/api/casino/play/mystery-coin-flip', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(betPayload({
                bet: parseFloat($('mystery-bet').value),
                choice: $('mystery-choice').value,
            })),
        });
        setResult($('mystery-result'), data);
        showDoubleOffer(data);
        await afterPlay();
    }

    function renderScratchTiles(tiles) {
        const el = $('scratch-tiles');
        if (!el) return;
        el.innerHTML = '';
        (tiles || []).forEach(function (sym) {
            const tile = document.createElement('span');
            tile.className = 'casino-scratch-tile';
            tile.textContent = sym;
            el.appendChild(tile);
        });
    }

    async function playScratch() {
        const data = await api('/api/casino/play/scratch-card', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(betPayload({
                bet: parseFloat($('scratch-bet').value),
            })),
        });
        if (data.success && data.details) {
            renderScratchTiles(data.details.tiles);
        }
        setResult($('scratch-result'), data);
        showDoubleOffer(data);
        await afterPlay();
    }

    let slotCatalog = [];

    function displaySymbol(sym, symbolDisplay) {
        if (symbolDisplay && symbolDisplay[sym]) return symbolDisplay[sym];
        var fallbacks = {
            '7': '7️⃣', bar: '🎰', cherry: '🍒', bell: '🔔', lemon: '🍋',
            diamond: '💎', star: '⭐', gem: '💠', coin: '🪙', wild: '⭐',
            neon: '🌃', bolt: '⚡', chip: '💾', wave: '〰️', dot: '🔵',
            sun: '☀️', moon: '🌙', comet: '☄️', orbit: '🪐', void: '🕳️',
            sword: '⚔️', shield: '🛡️', crown: '👑', banner: '🚩', skull: '💀',
            chest: '🧰', map: '🗺️', anchor: '⚓', rum: '🍾', parrot: '🦜',
            mega7: '7️⃣', fire: '🔥', gold: '🥇', blank: '⬜'
        };
        return fallbacks[sym] || sym || '?';
    }

    function slotDomId(slotId) {
        return String(slotId).replace(/[^a-z0-9_-]/gi, '-');
    }

    function renderSlotReels(containerId, reels, symbolDisplay, winPositions) {
        const el = $(containerId);
        if (!el) return;
        el.innerHTML = '';
        var wins = winPositions || [];
        (reels || ['?', '?', '?']).forEach(function (sym, idx) {
            const reel = document.createElement('div');
            reel.className = 'casino-slot-reel';
            if (wins.indexOf(idx) >= 0) reel.classList.add('win');
            const inner = document.createElement('span');
            inner.className = 'casino-slot-reel-symbol';
            inner.textContent = sym === '?' ? '❓' : displaySymbol(sym, symbolDisplay);
            reel.appendChild(inner);
            el.appendChild(reel);
        });
    }

    function spinPlaceholder(containerId) {
        renderSlotReels(containerId, ['?', '?', '?'], {}, []);
    }

    function delay(ms) {
        return new Promise(function (resolve) { setTimeout(resolve, ms); });
    }

    async function animateSlotSpin(containerId, finalReels, symbolDisplay, winPositions) {
        const el = $(containerId);
        if (!el) return;
        const pool = Object.values(symbolDisplay || {});
        const flicker = pool.length ? pool : ['🍒', '7️⃣', '💎', '⭐', '🔔', '🎰'];
        const reels = el.querySelectorAll('.casino-slot-reel');
        if (!reels.length) {
            renderSlotReels(containerId, ['?', '?', '?'], symbolDisplay, []);
        }
        const cols = el.querySelectorAll('.casino-slot-reel');
        for (var pass = 0; pass < 8; pass++) {
            cols.forEach(function (col, idx) {
                col.classList.add('spinning');
                var sym = col.querySelector('.casino-slot-reel-symbol');
                if (sym) sym.textContent = flicker[(pass + idx) % flicker.length];
            });
            await delay(70 + pass * 8);
        }
        for (var stop = 0; stop < (finalReels || []).length; stop++) {
            cols[stop]?.classList.remove('spinning');
            cols[stop]?.classList.add('stopping');
            var symEl = cols[stop]?.querySelector('.casino-slot-reel-symbol');
            if (symEl) symEl.textContent = displaySymbol(finalReels[stop], symbolDisplay);
            await delay(280);
            cols[stop]?.classList.remove('stopping');
        }
        renderSlotReels(containerId, finalReels, symbolDisplay, winPositions);
    }

    function volatilityClass(v) {
        var map = { low: 'vol-low', medium: 'vol-med', high: 'vol-high', extreme: 'vol-extreme' };
        return map[(v || '').toLowerCase()] || 'vol-med';
    }

    function buildSlotMachineCard(slot) {
        var sid = slot.id;
        var dom = slotDomId(sid);
        return '<article class="casino-slot-machine" data-slot-id="' + sid + '">' +
            '<div class="casino-slot-machine-head">' +
            '<span class="casino-slot-icon">' + (slot.icon || '🎰') + '</span>' +
            '<div><h3>' + (slot.label || sid) + '</h3>' +
            '<div class="casino-slot-meta">' +
            '<span class="casino-slot-vol ' + volatilityClass(slot.volatility) + '">' + (slot.volatility || 'medium') + '</span>' +
            (slot.rtp_estimate ? '<span class="casino-slot-rtp">RTP ~' + slot.rtp_estimate + '%</span>' : '') +
            (slot.has_wild ? '<span class="casino-slot-tag">WILD</span>' : '') +
            (slot.has_scatter ? '<span class="casino-slot-tag">SCATTER</span>' : '') +
            (slot.jackpot_symbol ? '<span class="casino-slot-tag jackpot">JACKPOT ' + (slot.jackpot_multiplier || '') + '×</span>' : '') +
            '</div></div></div>' +
            '<div class="casino-slot-cabinet">' +
            '<div id="slot-reels-' + dom + '" class="casino-slot-reels"></div>' +
            '</div>' +
            '<div class="casino-controls">' +
            '<input id="slot-bet-' + dom + '" type="number" min="5" max="500" value="25" aria-label="' + (slot.label || sid) + ' bet">' +
            '<button type="button" class="casino-slot-spin-btn" data-slot-id="' + sid + '">Spin</button>' +
            '</div>' +
            '<div id="slot-result-' + dom + '" class="casino-result"></div>' +
            '</article>';
    }

    function gamesToSlotCatalog(games) {
        if (!games || typeof games !== 'object') return [];
        return Object.keys(games).filter(function (k) { return k.indexOf('slot_') === 0; }).sort().map(function (k) {
            var g = games[k] || {};
            return {
                id: k,
                label: g.label || k,
                icon: g.icon || '🎰',
                volatility: g.volatility || 'medium',
                rtp_estimate: g.rtp_estimate,
                symbol_display: g.symbol_display || {},
                has_wild: !!(g.has_wild || (g.wild_symbols && g.wild_symbols.length)),
                has_scatter: !!(g.has_scatter || g.scatter_symbol),
                jackpot_symbol: g.jackpot_symbol,
                jackpot_multiplier: g.jackpot_multiplier,
            };
        });
    }

    function renderSlotMachinesFromGames(games) {
        const grid = $('casino-slots-grid');
        if (!grid) return;
        var catalog = gamesToSlotCatalog(games);
        if (!catalog.length) {
            grid.textContent = 'No slot machines configured.';
            return;
        }
        slotCatalog = catalog;
        grid.innerHTML = catalog.map(buildSlotMachineCard).join('');
        catalog.forEach(function (slot) {
            spinPlaceholder('slot-reels-' + slotDomId(slot.id));
        });
        grid.querySelectorAll('.casino-slot-spin-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                playSlot(btn.getAttribute('data-slot-id'));
            });
        });
    }

    async function loadSlotMachines() {
        const grid = $('casino-slots-grid');
        if (!grid) return;
        if (slotCatalog.length) return;
        try {
            var data = await api('/api/casino/slots', null, 8000);
            if (data.success && (data.slots || []).length) {
                slotCatalog = data.slots;
                grid.innerHTML = slotCatalog.map(buildSlotMachineCard).join('');
                slotCatalog.forEach(function (slot) {
                    spinPlaceholder('slot-reels-' + slotDomId(slot.id));
                });
                grid.querySelectorAll('.casino-slot-spin-btn').forEach(function (btn) {
                    btn.addEventListener('click', function () {
                        playSlot(btn.getAttribute('data-slot-id'));
                    });
                });
                return;
            }
            var settings = await api('/api/casino/settings', null, 8000);
            if (settings.success && settings.games) {
                renderSlotMachinesFromGames(settings.games);
                return;
            }
            grid.textContent = 'Slot machines unavailable — refresh the page.';
        } catch (e) {
            grid.textContent = 'Slot machines unavailable.';
        }
    }

    async function playSlot(slotId) {
        if (!slotId) return;
        var dom = slotDomId(slotId);
        var reelsId = 'slot-reels-' + dom;
        var resultId = 'slot-result-' + dom;
        var betInput = $('slot-bet-' + dom);
        var btn = document.querySelector('.casino-slot-spin-btn[data-slot-id="' + slotId + '"]');
        if (btn) btn.disabled = true;
        spinPlaceholder(reelsId);
        var reelEl = $(reelsId);
        if (reelEl) {
            reelEl.querySelectorAll('.casino-slot-reel').forEach(function (c) { c.classList.add('spinning'); });
        }

        const data = await api('/api/casino/play/slot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(betPayload({
                slot_id: slotId,
                bet: parseFloat(betInput ? betInput.value : 25),
            })),
        });

        if (data.success && data.details) {
            await animateSlotSpin(
                reelsId,
                data.details.reels || [],
                data.details.symbol_display || {},
                data.details.win_positions || []
            );
        } else {
            spinPlaceholder(reelsId);
        }
        setResult($(resultId), data);
        showDoubleOffer(data);
        await afterPlay();
        if (btn) btn.disabled = false;
    }

    async function verifyCasinoSecurity() {
        const pwd = ($('casino-security-password') || {}).value || '';
        const status = $('casino-security-status');
        if (!pwd) {
            if (status) status.textContent = 'Enter your account password.';
            return;
        }
        if (status) status.textContent = 'Verifying…';
        const res = await fetch(baseUrl + '/api/user/security/verify?user_id=' + encodeURIComponent(userId), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, password: pwd }),
        });
        const data = await res.json().catch(function () { return {}; });
        if (data.success && data.verification_token) {
            securityToken = data.verification_token;
            securityExpires = data.expires_at || '';
            localStorage.setItem('casino_security_token', securityToken);
            localStorage.setItem('casino_security_expires', securityExpires);
            if (status) status.textContent = 'Verified until ' + (securityExpires || '').slice(0, 16);
            applyCurrencyUi();
        } else if (status) {
            status.textContent = data.error || 'Verification failed';
        }
    }

    async function playBattleOutcome() {
        const body = betPayload({
            bet: parseFloat($('outcome-bet').value),
            prediction: $('outcome-prediction').value,
        });
        const laneEl = $('outcome-dist-lane');
        const lane = laneEl ? laneEl.value : '';
        if (lane) body.difficulty = lane;
        const data = await api('/api/casino/play/battle-outcome', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        setResult($('outcome-result'), data);
        showDoubleOffer(data);
        await afterPlay();
    }

    // -- Progressive jackpot meter -----------------------------------------
    function jackpotAmount(currency, value) {
        var v = Number(value || 0);
        if (currency === 'mn2') return v.toFixed(4) + ' MN2';
        if (currency === 'usd') return '$' + v.toFixed(2);
        return Math.round(v).toLocaleString() + ' coins';
    }

    async function refreshJackpotMeter() {
        var bar = $('casino-jackpot-bar');
        var el = $('casino-jackpot-pools');
        if (!bar || !el) return;
        var data = await api('/api/casino/jackpots', null, 8000);
        if (!data.success || !data.enabled || !data.pools) {
            bar.classList.add('hidden');
            return;
        }
        var order = ['coins', 'mn2', 'usd'];
        var parts = [];
        order.forEach(function (cur) {
            var p = data.pools[cur];
            if (!p) return;
            var cls = cur === activeCurrency ? ' active' : '';
            parts.push('<span class="casino-jackpot-pool' + cls + '">' + jackpotAmount(cur, p.pool) + '</span>');
        });
        if (!parts.length) {
            bar.classList.add('hidden');
            return;
        }
        el.innerHTML = parts.join('<span class="casino-jackpot-sep">·</span>');
        bar.classList.remove('hidden');
    }

    function jackpotCelebrate(award) {
        if (!award) return;
        celebrate('💰 JACKPOT! 💰', 'You won ' + jackpotAmount(award.currency, award.amount) + '!', 'mega');
        showToast('JACKPOT! You won ' + jackpotAmount(award.currency, award.amount));
    }

    // -- Live winners ticker ------------------------------------------------
    function prettyGame(game) {
        if (!game) return 'a game';
        if (game === 'crash') return 'Crash';
        if (game === 'coin_flip') return 'Coin flip';
        if (game === 'dice') return 'Lucky dice';
        if (game === 'scratch_card') return 'Pick-3 scratch';
        if (game === 'mystery_coin_flip') return 'Mystery flip';
        if (String(game).indexOf('rps') === 0) return 'RPS';
        if (String(game).indexOf('battle') === 0) return 'Battle bet';
        if (String(game).indexOf('slot_') === 0) {
            return 'Slots (' + String(game).replace('slot_', '') + ')';
        }
        return game;
    }

    function formatFeedAmount(value, currency) {
        var v = Number(value || 0);
        if (currency === 'mn2') return v.toFixed(4) + ' MN2';
        if (currency === 'usd') return '$' + v.toFixed(2);
        return Math.round(v) + ' coins';
    }

    async function refreshActivityFeed() {
        var track = $('casino-ticker-track');
        if (!track) return;
        var data = await api('/api/casino/activity-feed?limit=12', null, 8000);
        if (!data.success || !(data.feed || []).length) {
            track.innerHTML = '<span class="casino-ticker-item">Be the first big win today…</span>';
            return;
        }
        var items = data.feed.map(function (f) {
            var mult = f.multiplier ? (' @ ' + Number(f.multiplier).toFixed(2) + '×') : '';
            return '<span class="casino-ticker-item">🏆 ' + shortUser(f.user_id) + ' won ' +
                formatFeedAmount(f.net, f.currency) + ' on ' + prettyGame(f.game) + mult + '</span>';
        });
        track.innerHTML = items.join('') + items.join('');
    }

    // -- Crash --------------------------------------------------------------
    var crash = {
        active: false, roundId: null, bet: 0, currency: 'coins',
        growth: 0.13863, startMs: 0, raf: null, maxSeconds: 60, cashed: false, auto: null,
    };

    function crashCurrentMultiplier() {
        var elapsed = (performance.now() - crash.startMs) / 1000;
        var m = Math.exp(crash.growth * elapsed);
        return Math.max(1, Math.floor(m * 100) / 100);
    }

    function drawCrashCurve(currentMult, crashed) {
        var canvas = $('crash-canvas');
        if (!canvas || !canvas.getContext) return;
        var ctx = canvas.getContext('2d');
        var W = canvas.width;
        var H = canvas.height;
        ctx.clearRect(0, 0, W, H);
        var growth = crash.growth || 0.13863;
        var mult = Math.max(1.01, currentMult || 1.01);
        var maxM = Math.max(2, mult * 1.12);
        var totalT = Math.log(mult) / growth;

        ctx.strokeStyle = 'rgba(255,255,255,0.07)';
        ctx.lineWidth = 1;
        for (var g = 1; g <= 4; g++) {
            var gy = H - (H * (g / 5));
            ctx.beginPath();
            ctx.moveTo(0, gy);
            ctx.lineTo(W, gy);
            ctx.stroke();
        }

        var steps = 64;
        var line = crashed ? '#ff5470' : '#21d07a';
        var fill = crashed ? 'rgba(255,84,112,0.18)' : 'rgba(33,208,122,0.18)';
        ctx.beginPath();
        ctx.moveTo(0, H);
        for (var i = 0; i <= steps; i++) {
            var tt = totalT * (i / steps);
            var m = Math.exp(growth * tt);
            var x = W * (i / steps);
            var y = H - H * ((m - 1) / (maxM - 1));
            ctx.lineTo(x, Math.max(2, y));
        }
        var lastX = W;
        var lastY = H - H * ((mult - 1) / (maxM - 1));
        ctx.lineTo(lastX, H);
        ctx.closePath();
        ctx.fillStyle = fill;
        ctx.fill();

        ctx.beginPath();
        for (var j = 0; j <= steps; j++) {
            var tt2 = totalT * (j / steps);
            var m2 = Math.exp(growth * tt2);
            var x2 = W * (j / steps);
            var y2 = H - H * ((m2 - 1) / (maxM - 1));
            if (j === 0) ctx.moveTo(x2, Math.max(2, y2));
            else ctx.lineTo(x2, Math.max(2, y2));
        }
        ctx.strokeStyle = line;
        ctx.lineWidth = 3;
        ctx.stroke();

        ctx.font = '20px sans-serif';
        ctx.fillText(crashed ? '💥' : '🚀', Math.min(W - 24, lastX - 14), Math.max(18, lastY));
    }

    function crashLoop() {
        if (!crash.active) return;
        var m = crashCurrentMultiplier();
        var disp = $('crash-multiplier');
        if (disp) disp.textContent = m.toFixed(2) + '×';
        var stage = $('crash-multiplier');
        if (stage) stage.classList.toggle('hot', m >= 5);
        drawCrashCurve(m, false);
        if (crash.auto && m >= crash.auto && !crash.cashed) {
            doCrashCashout(crash.auto);
            return;
        }
        var elapsed = (performance.now() - crash.startMs) / 1000;
        if (elapsed >= crash.maxSeconds) {
            doCrashCashout(null);
            return;
        }
        if (prefersReducedMotion()) {
            crash.raf = setTimeout(crashLoop, 120);
        } else {
            crash.raf = requestAnimationFrame(crashLoop);
        }
    }

    function stopCrashLoop() {
        if (crash.raf) {
            if (prefersReducedMotion()) clearTimeout(crash.raf);
            else cancelAnimationFrame(crash.raf);
            crash.raf = null;
        }
    }

    function setCrashButtons(launchEnabled) {
        var launch = $('crash-launch');
        var cashout = $('crash-cashout');
        if (launch) launch.disabled = !launchEnabled;
        if (cashout) cashout.disabled = launchEnabled;
    }

    async function launchCrash() {
        if (crash.active) return;
        var betInput = $('crash-bet');
        var autoInput = $('crash-auto');
        var bet = parseFloat(betInput ? betInput.value : 25);
        var autoVal = parseFloat(autoInput ? autoInput.value : '');
        var body = betPayload({ bet: bet });
        if (autoVal && autoVal >= 1.01) body.auto_cashout = autoVal;
        setCrashButtons(false);
        var status = $('crash-status');
        if (status) status.textContent = 'Launching…';
        $('crash-result') && ($('crash-result').textContent = '');
        var data = await api('/api/casino/play/crash', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!data.success) {
            setCrashButtons(true);
            setResult($('crash-result'), data);
            if (status) status.textContent = 'Ready.';
            return;
        }
        crash.active = true;
        crash.roundId = data.round_id;
        crash.bet = data.bet;
        crash.currency = data.currency;
        crash.growth = data.growth_per_second || 0.13863;
        crash.maxSeconds = data.max_round_seconds || 60;
        crash.startMs = performance.now();
        crash.cashed = false;
        crash.auto = data.auto_cashout || (autoVal >= 1.01 ? autoVal : null);
        if (status) status.textContent = crash.auto ? ('Climbing — auto cash-out @ ' + crash.auto.toFixed(2) + '×') : 'Climbing — cash out before it crashes!';
        playSound('tick');
        crashLoop();
        safeRefresh('balance', refreshBalance);
    }

    async function doCrashCashout(targetMultiplier) {
        if (!crash.active || crash.cashed) return;
        crash.cashed = true;
        crash.active = false;
        stopCrashLoop();
        setCrashButtons(true);
        var m = targetMultiplier || crashCurrentMultiplier();
        var data = await api('/api/casino/play/crash/cashout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, round_id: crash.roundId, multiplier: m }),
        });
        var status = $('crash-status');
        var disp = $('crash-multiplier');
        if (data.success && data.outcome === 'win') {
            if (disp) disp.textContent = Number(data.multiplier || m).toFixed(2) + '×';
            drawCrashCurve(Number(data.multiplier || m), false);
            if (status) status.textContent = 'Cashed out @ ' + Number(data.multiplier || m).toFixed(2) + '× ✅';
            playSound('win');
            maybeCelebrate(data);
        } else {
            var bust = Number((data && data.bust) || m);
            if (disp) { disp.textContent = bust.toFixed(2) + '× 💥'; disp.classList.remove('hot'); }
            drawCrashCurve(bust, true);
            if (status) status.textContent = data && data.error ? data.error : 'Crashed @ ' + bust.toFixed(2) + '×';
            playSound('bust');
        }
        setResult($('crash-result'), data);
        await afterPlay();
        safeRefresh('activityFeed', refreshActivityFeed);
        refreshFairnessState();
    }

    async function refreshFairnessState() {
        var el = $('crash-fairness-state');
        if (!el) return;
        var data = await api('/api/casino/fairness/seed', null, 8000);
        if (!data.success) {
            el.textContent = 'Fairness info unavailable';
            return;
        }
        el.innerHTML = 'Server seed hash: <code>' + (data.server_seed_hash || '').slice(0, 24) + '…</code><br>' +
            'Client seed: <code>' + (data.client_seed || '') + '</code> · Nonce: ' + (data.nonce || 0);
        var input = $('crash-client-seed');
        if (input && !input.value) input.placeholder = data.client_seed || 'Your client seed';
    }

    async function rotateCrashSeed() {
        var input = $('crash-client-seed');
        var body = { user_id: userId };
        if (input && input.value.trim()) body.client_seed = input.value.trim();
        var data = await api('/api/casino/fairness/rotate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        var reveal = $('crash-reveal');
        if (!data.success) {
            if (reveal) reveal.textContent = data.error || 'Could not rotate seed';
            return;
        }
        var prev = data.revealed || {};
        if (reveal) {
            reveal.innerHTML = 'Revealed previous server seed (verify past rounds with it):<br>' +
                '<code>' + (prev.server_seed || '') + '</code><br>' +
                'It hashes to <code>' + (prev.server_seed_hash || '').slice(0, 24) + '…</code> over ' +
                (prev.nonce_count || 0) + ' rounds.';
        }
        showToast('Seed rotated — new server seed committed');
        refreshFairnessState();
    }

    // -- Plinko -------------------------------------------------------------
    var plinko = { rows: 12, riskTables: {}, drawing: false };

    function plinkoLayout(canvas) {
        var W = canvas.width;
        var H = canvas.height;
        var rows = plinko.rows;
        var bins = rows + 1;
        var binW = W / bins;
        var topY = 22;
        var binArea = 44;
        var rowH = (H - topY - binArea) / rows;
        return { W: W, H: H, rows: rows, bins: bins, binW: binW, topY: topY, binArea: binArea, rowH: rowH };
    }

    function plinkoBinColor(bin, bins) {
        var mid = (bins - 1) / 2;
        var dist = Math.abs(bin - mid) / mid; // 0 center .. 1 edge
        var r = Math.round(60 + dist * 195);
        var g = Math.round(200 - dist * 150);
        return 'rgb(' + r + ',' + g + ',80)';
    }

    function drawPlinkoBoard(landingBin, ball) {
        var canvas = $('plinko-canvas');
        if (!canvas || !canvas.getContext) return;
        var ctx = canvas.getContext('2d');
        var L = plinkoLayout(canvas);
        ctx.clearRect(0, 0, L.W, L.H);

        // Peg lattice (decorative triangle).
        ctx.fillStyle = 'rgba(255,255,255,0.55)';
        for (var i = 0; i < L.rows; i++) {
            var count = i + 2;
            for (var k = 0; k < count; k++) {
                var px = L.W / 2 + (k - (count - 1) / 2) * L.binW;
                var py = L.topY + (i + 0.5) * L.rowH;
                ctx.beginPath();
                ctx.arc(px, py, 2.4, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        // Bins with multiplier labels.
        var table = plinko.riskTables[($('plinko-risk') || {}).value || 'medium'] || [];
        var binTop = L.H - L.binArea;
        ctx.font = '11px sans-serif';
        ctx.textAlign = 'center';
        for (var b = 0; b < L.bins; b++) {
            var bx = b * L.binW;
            ctx.fillStyle = b === landingBin ? '#ffce4d' : plinkoBinColor(b, L.bins);
            ctx.fillRect(bx + 1, binTop, L.binW - 2, L.binArea - 4);
            ctx.fillStyle = '#10130f';
            var label = table.length ? (table[b] + '×') : '';
            ctx.fillText(label, bx + L.binW / 2, binTop + L.binArea / 2 + 3);
        }
        ctx.textAlign = 'left';

        if (ball) {
            ctx.beginPath();
            ctx.arc(ball.x, ball.y, 7, 0, Math.PI * 2);
            ctx.fillStyle = '#ffd23f';
            ctx.fill();
            ctx.lineWidth = 2;
            ctx.strokeStyle = '#a8730a';
            ctx.stroke();
        }
    }

    function plinkoPathPoints(path) {
        var canvas = $('plinko-canvas');
        var L = plinkoLayout(canvas);
        var pts = [{ x: L.W / 2, y: L.topY }];
        var x = L.W / 2;
        for (var i = 0; i < path.length; i++) {
            x += (path[i] === 'R' ? 0.5 : -0.5) * L.binW;
            pts.push({ x: x, y: L.topY + (i + 1) * L.rowH });
        }
        return pts;
    }

    function animatePlinkoDrop(path, landingBin) {
        return new Promise(function (resolve) {
            var pts = plinkoPathPoints(path);
            if (prefersReducedMotion()) {
                drawPlinkoBoard(landingBin, pts[pts.length - 1]);
                resolve();
                return;
            }
            var seg = 0;
            var segStart = performance.now();
            var segMs = 80;
            function frame(now) {
                var t = Math.min(1, (now - segStart) / segMs);
                var a = pts[seg];
                var b = pts[seg + 1];
                var ball = { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
                drawPlinkoBoard(t >= 1 && seg === pts.length - 2 ? landingBin : null, ball);
                if (t >= 1) {
                    seg++;
                    segStart = now;
                    if (seg >= pts.length - 1) {
                        drawPlinkoBoard(landingBin, pts[pts.length - 1]);
                        playSound('tick');
                        resolve();
                        return;
                    }
                    playSound('tick');
                }
                requestAnimationFrame(frame);
            }
            requestAnimationFrame(frame);
        });
    }

    async function playPlinko() {
        if (plinko.drawing) return;
        var betInput = $('plinko-bet');
        var risk = ($('plinko-risk') || {}).value || 'medium';
        var bet = parseFloat(betInput ? betInput.value : 25);
        plinko.drawing = true;
        var btn = $('plinko-drop');
        if (btn) btn.disabled = true;
        var resEl = $('plinko-result');
        if (resEl) { resEl.textContent = 'Dropping…'; resEl.classList.remove('win', 'loss', 'draw'); }
        var data = await api('/api/casino/play/plinko', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(betPayload({ bet: bet, risk: risk })),
        });
        if (!data.success) {
            setResult($('plinko-result'), data);
            if (btn) btn.disabled = false;
            plinko.drawing = false;
            return;
        }
        var path = (data.details && data.details.path) || [];
        var bin = data.details ? data.details.bin : null;
        await animatePlinkoDrop(path, bin);
        setResult($('plinko-result'), data);
        try { maybeCelebrate(data); } catch (e) { /* optional */ }
        await afterPlay();
        if (btn) btn.disabled = false;
        plinko.drawing = false;
    }

    // -- Wheel of Fortune ---------------------------------------------------
    var wheel = { riskTables: {}, rotation: 0, spinning: false };

    function wheelSegments() {
        return wheel.riskTables[($('wheel-risk') || {}).value || 'medium'] || [];
    }

    function wheelSegColor(mult) {
        if (mult <= 0) return '#3a2030';
        if (mult < 1.5) return '#2f8f5b';
        if (mult < 3) return '#21d07a';
        if (mult < 10) return '#ffce4d';
        return '#ff5470';
    }

    function drawWheel(rotation, highlightIndex) {
        var canvas = $('wheel-canvas');
        if (!canvas || !canvas.getContext) return;
        var ctx = canvas.getContext('2d');
        var W = canvas.width;
        var cx = W / 2;
        var cy = canvas.height / 2;
        var radius = Math.min(cx, cy) - 6;
        ctx.clearRect(0, 0, W, canvas.height);
        var segs = wheelSegments();
        if (!segs.length) return;
        var total = segs.reduce(function (a, s) { return a + (s.weight || 1); }, 0) || 1;
        var start = rotation;
        ctx.save();
        ctx.translate(cx, cy);
        for (var i = 0; i < segs.length; i++) {
            var size = (segs[i].weight || 1) / total * Math.PI * 2;
            var end = start + size;
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.arc(0, 0, radius, start, end);
            ctx.closePath();
            ctx.fillStyle = i === highlightIndex ? '#ffffff' : wheelSegColor(segs[i].multiplier);
            ctx.fill();
            ctx.strokeStyle = 'rgba(0,0,0,0.35)';
            ctx.lineWidth = 1.5;
            ctx.stroke();
            // Label
            var mid = start + size / 2;
            ctx.save();
            ctx.rotate(mid);
            ctx.translate(radius * 0.66, 0);
            ctx.rotate(Math.PI / 2);
            ctx.fillStyle = '#0c0f0b';
            ctx.font = 'bold 13px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(segs[i].multiplier + '×', 0, 0);
            ctx.restore();
            start = end;
        }
        ctx.beginPath();
        ctx.arc(0, 0, radius * 0.16, 0, Math.PI * 2);
        ctx.fillStyle = '#10130f';
        ctx.fill();
        ctx.restore();
    }

    function wheelSegmentMidAngle(index) {
        var segs = wheelSegments();
        var total = segs.reduce(function (a, s) { return a + (s.weight || 1); }, 0) || 1;
        var acc = 0;
        for (var i = 0; i < index; i++) acc += (segs[i].weight || 1);
        var size = (segs[index].weight || 1);
        return (acc + size / 2) / total * Math.PI * 2;
    }

    function animateWheelTo(index) {
        return new Promise(function (resolve) {
            var pointer = -Math.PI / 2;
            var mid = wheelSegmentMidAngle(index);
            var turns = 5;
            var target = pointer - mid + Math.PI * 2 * turns;
            var startRot = wheel.rotation % (Math.PI * 2);
            var dur = prefersReducedMotion() ? 0 : 3400;
            if (dur === 0) {
                wheel.rotation = target;
                drawWheel(target, index);
                resolve();
                return;
            }
            var t0 = performance.now();
            function frame(now) {
                var p = Math.min(1, (now - t0) / dur);
                var ease = 1 - Math.pow(1 - p, 3);
                wheel.rotation = startRot + (target - startRot) * ease;
                drawWheel(wheel.rotation, p >= 1 ? index : -1);
                if (p < 1) {
                    requestAnimationFrame(frame);
                } else {
                    playSound('win');
                    resolve();
                }
            }
            requestAnimationFrame(frame);
        });
    }

    async function playWheel() {
        if (wheel.spinning) return;
        var betInput = $('wheel-bet');
        var risk = ($('wheel-risk') || {}).value || 'medium';
        var bet = parseFloat(betInput ? betInput.value : 25);
        wheel.spinning = true;
        var btn = $('wheel-spin');
        if (btn) btn.disabled = true;
        var resEl = $('wheel-result');
        if (resEl) { resEl.textContent = 'Spinning…'; resEl.classList.remove('win', 'loss', 'draw'); }
        var data = await api('/api/casino/play/wheel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(betPayload({ bet: bet, risk: risk })),
        });
        if (!data.success) {
            setResult($('wheel-result'), data);
            if (btn) btn.disabled = false;
            wheel.spinning = false;
            return;
        }
        var index = (data.details && typeof data.details.index === 'number') ? data.details.index : 0;
        await animateWheelTo(index);
        setResult($('wheel-result'), data);
        try { maybeCelebrate(data); } catch (e) { /* optional */ }
        await afterPlay();
        if (btn) btn.disabled = false;
        wheel.spinning = false;
    }

    // -- Mines --------------------------------------------------------------
    var mines = { roundId: null, tiles: 25, count: 3, revealed: [], active: false, currency: 'coins', multiplier: 1 };

    function minesGridCols() {
        var c = Math.round(Math.sqrt(mines.tiles));
        return c > 0 ? c : 5;
    }

    function buildMinesGrid() {
        var grid = $('mines-grid');
        if (!grid) return;
        grid.style.gridTemplateColumns = 'repeat(' + minesGridCols() + ', 1fr)';
        grid.innerHTML = '';
        for (var i = 0; i < mines.tiles; i++) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'casino-mine-tile';
            btn.setAttribute('data-tile', String(i));
            btn.disabled = !mines.active;
            btn.addEventListener('click', (function (idx) {
                return function () { revealMineTile(idx); };
            })(i));
            grid.appendChild(btn);
        }
    }

    function setMinesTilesEnabled(enabled) {
        var grid = $('mines-grid');
        if (!grid) return;
        grid.querySelectorAll('.casino-mine-tile').forEach(function (b) {
            if (b.classList.contains('revealed') || b.classList.contains('mine')) {
                b.disabled = true;
            } else {
                b.disabled = !enabled;
            }
        });
    }

    function markMineTile(idx, type) {
        var grid = $('mines-grid');
        if (!grid) return;
        var btn = grid.querySelector('.casino-mine-tile[data-tile="' + idx + '"]');
        if (!btn) return;
        btn.classList.add(type === 'mine' ? 'mine' : 'revealed');
        btn.textContent = type === 'mine' ? '💣' : '💎';
        btn.disabled = true;
    }

    function revealAllMines(positions) {
        (positions || []).forEach(function (p) { markMineTile(p, 'mine'); });
    }

    function endMinesRound() {
        mines.active = false;
        mines.roundId = null;
        var cashBtn = $('mines-cashout');
        if (cashBtn) cashBtn.disabled = true;
        var startBtn = $('mines-start');
        if (startBtn) startBtn.disabled = false;
        setMinesTilesEnabled(false);
    }

    async function startMines() {
        if (mines.active) return;
        var betInput = $('mines-bet');
        var count = parseInt(($('mines-count') || {}).value || '3', 10);
        var bet = parseFloat(betInput ? betInput.value : 25);
        var startBtn = $('mines-start');
        if (startBtn) startBtn.disabled = true;
        var data = await api('/api/casino/play/mines', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(betPayload({ bet: bet, mines: count })),
        });
        if (!data.success) {
            setResult($('mines-result'), data);
            if (startBtn) startBtn.disabled = false;
            return;
        }
        mines.roundId = data.round_id;
        mines.tiles = data.tiles || 25;
        mines.count = data.mines || count;
        mines.revealed = [];
        mines.active = true;
        mines.currency = data.currency;
        mines.multiplier = 1;
        buildMinesGrid();
        setMinesTilesEnabled(true);
        var cashBtn = $('mines-cashout');
        if (cashBtn) cashBtn.disabled = false;
        var status = $('mines-status');
        if (status) status.textContent = mines.count + ' mines hidden — reveal a gem (next: ' + Number(data.next_multiplier).toFixed(2) + '×)';
        $('mines-result') && ($('mines-result').textContent = '');
        playSound('tick');
        safeRefresh('balance', refreshBalance);
    }

    async function revealMineTile(idx) {
        if (!mines.active || !mines.roundId) return;
        if (mines.revealed.indexOf(idx) >= 0) return;
        var data = await api('/api/casino/play/mines/reveal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, round_id: mines.roundId, tile: idx }),
        });
        if (!data.success) {
            var status0 = $('mines-status');
            if (status0) status0.textContent = data.error || 'Reveal failed';
            return;
        }
        if (data.hit_mine) {
            markMineTile(idx, 'mine');
            revealAllMines(data.mine_positions);
            playSound('bust');
            setResult($('mines-result'), data);
            endMinesRound();
            await afterPlay();
            return;
        }
        markMineTile(idx, 'gem');
        mines.revealed = data.revealed || mines.revealed;
        playSound('tick');
        if (data.cleared) {
            revealAllMines(data.mine_positions);
            setResult($('mines-result'), data);
            try { maybeCelebrate(data); } catch (e) { /* optional */ }
            endMinesRound();
            await afterPlay();
            return;
        }
        mines.multiplier = data.multiplier || mines.multiplier;
        var status = $('mines-status');
        if (status) {
            status.textContent = 'Safe! Cash out for ' + Number(data.multiplier).toFixed(2) + '× (' +
                formatNet(data.potential_payout) + ' ' + currencyLabel(mines.currency) + ') · next ' +
                Number(data.next_multiplier).toFixed(2) + '×';
        }
    }

    async function cashoutMines() {
        if (!mines.active || !mines.roundId) return;
        var data = await api('/api/casino/play/mines/cashout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, round_id: mines.roundId }),
        });
        if (!data.success) {
            var status = $('mines-status');
            if (status) status.textContent = data.error || 'Cash out failed';
            return;
        }
        revealAllMines(data.mine_positions);
        playSound('win');
        setResult($('mines-result'), data);
        try { maybeCelebrate(data); } catch (e) { /* optional */ }
        endMinesRound();
        await afterPlay();
    }

    // -- Keno ---------------------------------------------------------------
    var keno = { selected: [], pool: 40, maxSpots: 6, drawCount: 10, playing: false };

    function updateKenoSelectedLabel() {
        var el = $('keno-selected');
        if (el) el.textContent = keno.selected.length + ' / ' + keno.maxSpots + ' picked';
    }

    function buildKenoGrid() {
        var grid = $('keno-grid');
        if (!grid) return;
        var cols = Math.ceil(Math.sqrt(keno.pool));
        grid.style.gridTemplateColumns = 'repeat(' + cols + ', 1fr)';
        grid.innerHTML = '';
        for (var n = 1; n <= keno.pool; n++) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'casino-keno-cell';
            btn.textContent = String(n);
            btn.setAttribute('data-num', String(n));
            btn.addEventListener('click', (function (num) {
                return function () { toggleKenoNumber(num); };
            })(n));
            grid.appendChild(btn);
        }
        applyKenoSelection();
        updateKenoSelectedLabel();
    }

    function applyKenoSelection(drawn, hits) {
        var grid = $('keno-grid');
        if (!grid) return;
        var drawnSet = {};
        (drawn || []).forEach(function (d) { drawnSet[d] = true; });
        var hitSet = {};
        (hits || []).forEach(function (h) { hitSet[h] = true; });
        grid.querySelectorAll('.casino-keno-cell').forEach(function (b) {
            var num = parseInt(b.getAttribute('data-num'), 10);
            b.classList.toggle('selected', keno.selected.indexOf(num) >= 0);
            b.classList.toggle('drawn', !!drawnSet[num]);
            b.classList.toggle('hit', !!hitSet[num]);
        });
    }

    function toggleKenoNumber(n) {
        if (keno.playing) return;
        var i = keno.selected.indexOf(n);
        if (i >= 0) {
            keno.selected.splice(i, 1);
        } else {
            if (keno.selected.length >= keno.maxSpots) return;
            keno.selected.push(n);
        }
        applyKenoSelection();
        updateKenoSelectedLabel();
    }

    function kenoClear() {
        if (keno.playing) return;
        keno.selected = [];
        applyKenoSelection();
        updateKenoSelectedLabel();
    }

    function kenoQuickPick() {
        if (keno.playing) return;
        keno.selected = [];
        var avail = [];
        for (var n = 1; n <= keno.pool; n++) avail.push(n);
        for (var k = 0; k < keno.maxSpots && avail.length; k++) {
            var idx = Math.floor(Math.random() * avail.length);
            keno.selected.push(avail.splice(idx, 1)[0]);
        }
        applyKenoSelection();
        updateKenoSelectedLabel();
    }

    async function playKeno() {
        if (keno.playing) return;
        if (!keno.selected.length) {
            var rel = $('keno-result');
            if (rel) { rel.textContent = 'Pick at least one number first.'; rel.classList.add('loss'); }
            return;
        }
        keno.playing = true;
        var btn = $('keno-play');
        if (btn) btn.disabled = true;
        var resEl = $('keno-result');
        if (resEl) { resEl.textContent = 'Drawing…'; resEl.classList.remove('win', 'loss', 'draw'); }
        var bet = parseFloat(($('keno-bet') || {}).value || 25);
        var data = await api('/api/casino/play/keno', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(betPayload({ bet: bet, spots: keno.selected })),
        });
        if (data.success && data.details) {
            var drawn = data.details.drawn || [];
            var hitNums = keno.selected.filter(function (s) { return drawn.indexOf(s) >= 0; });
            applyKenoSelection(drawn, hitNums);
            playSound(data.outcome === 'win' ? 'win' : 'tick');
            try { maybeCelebrate(data); } catch (e) { /* optional */ }
            await afterPlay();
        }
        setResult($('keno-result'), data);
        if (btn) btn.disabled = false;
        keno.playing = false;
    }

    // -- Roulette -----------------------------------------------------------
    var roulette = { spinning: false };

    function updateRouletteSelectionField() {
        var type = ($('roulette-bet-type') || {}).value || 'red';
        var field = $('roulette-selection-field');
        var input = $('roulette-selection');
        var show = (type === 'straight' || type === 'dozen' || type === 'column');
        if (field) field.style.display = show ? '' : 'none';
        if (input) {
            if (type === 'straight') {
                input.min = 0; input.max = 36;
                if (parseInt(input.value, 10) > 36) input.value = 17;
            } else if (type === 'dozen' || type === 'column') {
                input.min = 1; input.max = 3;
                if (parseInt(input.value, 10) > 3 || parseInt(input.value, 10) < 1) input.value = 1;
            }
        }
    }

    async function playRoulette() {
        if (roulette.spinning) return;
        roulette.spinning = true;
        var btn = $('roulette-spin');
        if (btn) btn.disabled = true;
        var type = ($('roulette-bet-type') || {}).value || 'red';
        var bet = parseFloat(($('roulette-bet') || {}).value || 25);
        var pocketEl = $('roulette-pocket');
        if (pocketEl) { pocketEl.textContent = '…'; pocketEl.className = 'casino-roulette-pocket'; }
        var resEl = $('roulette-result');
        if (resEl) { resEl.textContent = 'Spinning…'; resEl.classList.remove('win', 'loss', 'draw'); }
        var payload = { bet: bet, bet_type: type };
        if (type === 'straight' || type === 'dozen' || type === 'column') {
            payload.selection = parseInt(($('roulette-selection') || {}).value || 0, 10);
        }
        var data = await api('/api/casino/play/roulette', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(betPayload(payload)),
        });
        if (data.success && data.details) {
            var pocket = data.details.pocket;
            var color = data.details.color;
            if (pocketEl) {
                pocketEl.textContent = String(pocket);
                pocketEl.className = 'casino-roulette-pocket pocket-' + color;
            }
            playSound(data.outcome === 'win' ? 'win' : 'tick');
            try { maybeCelebrate(data); } catch (e) { /* optional */ }
            await afterPlay();
        }
        setResult($('roulette-result'), data);
        if (btn) btn.disabled = false;
        roulette.spinning = false;
    }

    // -- Hi-Lo --------------------------------------------------------------
    var hilo = { roundId: null, active: false, currency: 'coins', multiplier: 1 };

    function hiloCardLabel(rank) {
        var m = { 1: 'A', 11: 'J', 12: 'Q', 13: 'K' };
        return m[rank] || String(rank);
    }

    function showHiloCard(rank) {
        var el = $('hilo-card');
        if (!el) return;
        el.textContent = hiloCardLabel(rank);
        el.classList.remove('low', 'high');
        el.classList.add(rank >= 8 ? 'high' : 'low');
    }

    function setHiloButtons(active) {
        hilo.active = active;
        var h = $('hilo-higher');
        var l = $('hilo-lower');
        var c = $('hilo-cashout');
        var s = $('hilo-start');
        if (h) h.disabled = !active;
        if (l) l.disabled = !active;
        if (c) c.disabled = !active;
        if (s) s.disabled = active;
    }

    function hiloLabelMultipliers(nm) {
        var h = $('hilo-higher');
        var l = $('hilo-lower');
        if (h && nm) h.textContent = 'Higher ▲ ' + Number(nm.higher).toFixed(2) + '×';
        if (l && nm) l.textContent = 'Lower ▼ ' + Number(nm.lower).toFixed(2) + '×';
    }

    async function startHilo() {
        if (hilo.active) return;
        var s = $('hilo-start');
        if (s) s.disabled = true;
        var bet = parseFloat(($('hilo-bet') || {}).value || 25);
        var data = await api('/api/casino/play/hilo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(betPayload({ bet: bet })),
        });
        if (!data.success) {
            setResult($('hilo-result'), data);
            if (s) s.disabled = false;
            return;
        }
        hilo.roundId = data.round_id;
        hilo.currency = data.currency;
        hilo.multiplier = 1;
        showHiloCard(data.card);
        hiloLabelMultipliers(data.next_multipliers);
        setHiloButtons(true);
        $('hilo-result') && ($('hilo-result').textContent = '');
        var status = $('hilo-status');
        if (status) status.textContent = 'Higher or lower than ' + hiloCardLabel(data.card) + '?';
        playSound('tick');
        safeRefresh('balance', refreshBalance);
    }

    async function hiloGuess(direction) {
        if (!hilo.active || !hilo.roundId) return;
        setHiloButtons(false);
        var data = await api('/api/casino/play/hilo/guess', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, round_id: hilo.roundId, direction: direction }),
        });
        if (!data.success) {
            var st = $('hilo-status');
            if (st) st.textContent = data.error || 'Guess failed';
            setHiloButtons(true);
            return;
        }
        showHiloCard(data.card);
        if (data.busted) {
            playSound('bust');
            setResult($('hilo-result'), data);
            hilo.active = false; hilo.roundId = null;
            setHiloButtons(false);
            var s0 = $('hilo-start'); if (s0) s0.disabled = false;
            var st0 = $('hilo-status'); if (st0) st0.textContent = 'Busted on ' + hiloCardLabel(data.card) + '. Deal again?';
            await afterPlay();
            return;
        }
        hilo.multiplier = data.multiplier;
        hiloLabelMultipliers(data.next_multipliers);
        setHiloButtons(true);
        playSound('tick');
        var status = $('hilo-status');
        if (status) {
            status.textContent = 'Safe! ' + Number(data.multiplier).toFixed(2) + '× (' +
                formatNet(data.potential_payout) + ' ' + currencyLabel(hilo.currency) +
                ') — higher or lower than ' + hiloCardLabel(data.card) + '?';
        }
    }

    async function hiloCashout() {
        if (!hilo.active || !hilo.roundId) return;
        setHiloButtons(false);
        var data = await api('/api/casino/play/hilo/cashout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, round_id: hilo.roundId }),
        });
        if (!data.success) {
            var st = $('hilo-status');
            if (st) st.textContent = data.error || 'Cash out failed';
            setHiloButtons(true);
            return;
        }
        playSound('win');
        setResult($('hilo-result'), data);
        try { maybeCelebrate(data); } catch (e) { /* optional */ }
        hilo.active = false; hilo.roundId = null;
        var s = $('hilo-start'); if (s) s.disabled = false;
        var st2 = $('hilo-status'); if (st2) st2.textContent = 'Cashed out. Deal again?';
        await afterPlay();
    }

    // -- Tournaments --------------------------------------------------------
    function tournamentAmount(currency, value) {
        var v = Number(value || 0);
        if (currency === 'mn2') return v.toFixed(4) + ' MN2';
        if (currency === 'usd') return '$' + v.toFixed(2);
        return Math.round(v).toLocaleString() + ' coins';
    }

    function timeLeftLabel(endIso) {
        try {
            var ms = new Date(endIso).getTime() - Date.now();
            if (ms <= 0) return 'ending…';
            var h = Math.floor(ms / 3600000);
            var m = Math.floor((ms % 3600000) / 60000);
            return h + 'h ' + m + 'm left';
        } catch (e) { return ''; }
    }

    function renderTournamentCard(t) {
        var lines = [];
        lines.push('<div class="casino-tourney-head">' +
            '<span class="casino-tourney-name">' + (t.name || 'Tournament') + '</span>' +
            '<span class="casino-tourney-pool">' + tournamentAmount(t.currency, t.prize_pool) + ' pool</span>' +
            '</div>');
        var meta = (t.status === 'running' ? timeLeftLabel(t.end_at) : 'ended') +
            ' · ' + t.entrants + ' entrants · buy-in ' + tournamentAmount(t.currency, t.buy_in);
        lines.push('<div class="casino-tourney-meta">' + meta + '</div>');
        var board = (t.leaderboard || []).slice(0, 5).map(function (r) {
            var you = (t.your_entry && r.user_id === userId) ? ' (you)' : '';
            var prize = (r.prize != null && r.prize > 0) ? ' — won ' + tournamentAmount(t.currency, r.prize) : '';
            return '<li><span>#' + r.rank + ' ' + r.user_id + you + '</span><span>' +
                formatScore(t.currency, r.score) + prize + '</span></li>';
        }).join('');
        lines.push('<ol class="casino-tourney-board">' + (board || '<li>No entrants yet — be first.</li>') + '</ol>');
        if (t.status === 'running') {
            if (t.joined) {
                var yr = t.your_entry ? ('You: #' + t.your_entry.rank + ' · ' + formatScore(t.currency, t.your_entry.score)) : 'Joined';
                lines.push('<div class="casino-tourney-you">' + yr + '</div>');
            } else if (t.currency === activeCurrency) {
                lines.push('<button type="button" class="casino-tourney-join" data-id="' + t.id + '">Join for ' + tournamentAmount(t.currency, t.buy_in) + '</button>');
            } else {
                lines.push('<div class="casino-tourney-you">Switch to ' + currencyLabel(t.currency) + ' to join.</div>');
            }
        }
        if (t.fairness && t.fairness.server_seed_hash) {
            var fairLine = 'Fairness: ' + String(t.fairness.server_seed_hash).slice(0, 12) + '…';
            if (t.fairness.server_seed) {
                fairLine += ' (revealed — <button type="button" class="casino-tourney-verify" data-id="' + t.id + '">verify</button>)';
            } else if (t.fairness.chain && !t.fairness.chain.genesis) {
                fairLine += ' (chained cup)';
            }
            lines.push('<div class="casino-tourney-fairness" style="font-size:0.78em;opacity:0.75;margin-top:6px;">' + fairLine + '</div>');
        }
        return '<div class="casino-tourney' + (t.status === 'ended' ? ' ended' : '') + '">' + lines.join('') + '</div>';
    }

    async function verifyTournamentFairness(id) {
        var data = await api('/api/casino/tournaments/' + encodeURIComponent(id) + '/fairness/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: '{}',
        });
        if (data && data.success) {
            showToast('Tournament fairness verified (hash + chain OK)');
        } else {
            alert((data && (data.error || (data.revealed === false ? 'Seed not revealed until cup ends' : 'Verification failed'))) || 'Verify failed');
        }
    }

    function formatScore(currency, value) {
        var v = Number(value || 0);
        var sign = v > 0 ? '+' : '';
        if (currency === 'mn2') return sign + v.toFixed(4);
        if (currency === 'usd') return sign + v.toFixed(2);
        return sign + Math.round(v);
    }

    async function refreshTournaments() {
        var el = $('casino-tournaments');
        if (!el) return;
        var data = await api('/api/casino/tournaments');
        if (!data.success || !data.enabled) {
            el.textContent = 'Tournaments are currently unavailable.';
            return;
        }
        if (!(data.tournaments || []).length) {
            el.textContent = 'No tournaments scheduled right now.';
            return;
        }
        el.innerHTML = data.tournaments.map(renderTournamentCard).join('');
        el.querySelectorAll('.casino-tourney-join').forEach(function (b) {
            b.addEventListener('click', function () { joinTournament(b.getAttribute('data-id')); });
        });
        el.querySelectorAll('.casino-tourney-verify').forEach(function (b) {
            b.addEventListener('click', function () { verifyTournamentFairness(b.getAttribute('data-id')); });
        });
    }

    async function joinTournament(id) {
        if ((activeCurrency === 'mn2' || activeCurrency === 'usd') && !securityTokenValid()) {
            alert('Verify your account (password) before joining a real-money tournament.');
            return;
        }
        var data = await api('/api/casino/tournaments/join', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(betPayload({ tournament_id: id })),
        });
        if (!data.success) {
            alert(data.error || 'Could not join tournament');
            return;
        }
        playSound('win');
        showToast('Joined! Your bets now score in the tournament.');
        await refreshTournaments();
        safeRefresh('balance', refreshBalance);
    }

    function initCasinoGamesTabs() {
        var nav = $('casino-games-nav');
        var grid = $('casino-games-grid');
        if (!nav || !grid) return;
        var cards = Array.prototype.slice.call(grid.querySelectorAll('[data-casino-game]'));
        if (!cards.length) return;

        function showGame(gameId) {
            cards.forEach(function (card) {
                card.classList.toggle('casino-game-active', card.getAttribute('data-casino-game') === gameId);
            });
            nav.querySelectorAll('.casino-game-tab').forEach(function (tab) {
                var on = tab.getAttribute('data-game') === gameId;
                tab.classList.toggle('active', on);
                tab.setAttribute('aria-selected', on ? 'true' : 'false');
            });
            try {
                var url = new URL(window.location.href);
                if (gameId === cards[0].getAttribute('data-casino-game')) url.searchParams.delete('game');
                else url.searchParams.set('game', gameId);
                window.history.replaceState({}, document.title, url.pathname + url.search + url.hash);
            } catch (e) { /* ignore */ }
        }

        nav.innerHTML = cards.map(function (card, i) {
            var id = card.getAttribute('data-casino-game');
            var label = card.getAttribute('data-casino-label') || id;
            return '<button type="button" class="casino-game-tab' + (i === 0 ? ' active' : '') + '" data-game="' + id + '" role="tab" aria-selected="' + (i === 0 ? 'true' : 'false') + '">' + label + '</button>';
        }).join('');

        nav.addEventListener('click', function (ev) {
            var btn = ev.target.closest('[data-game]');
            if (!btn) return;
            showGame(btn.getAttribute('data-game'));
        });

        var requested = new URLSearchParams(window.location.search).get('game');
        var valid = cards.some(function (c) { return c.getAttribute('data-casino-game') === requested; });
        showGame(valid ? requested : cards[0].getAttribute('data-casino-game'));
    }

    async function initCasino() {
        initCasinoGamesTabs();
        bindClick('coin-flip-play', playCoinFlip);
        bindClick('dice-play', playDice);
        bindClick('rps-play', playRps);
        bindClick('rps-dist-play', playRpsDistribution);
        bindClick('mystery-play', playMysteryFlip);
        bindClick('scratch-play', playScratch);
        bindClick('casino-security-verify', verifyCasinoSecurity);
        bindClick('outcome-play', playBattleOutcome);
        bindClick('counter-play', playCounterPick);
        bindClick('free-bet-play', playFreeBet);
        bindClick('crash-launch', launchCrash);
        bindClick('crash-cashout', function () { doCrashCashout(null); });
        bindClick('crash-rotate-seed', rotateCrashSeed);
        bindClick('plinko-drop', playPlinko);
        bindChange('plinko-risk', function () { if (!plinko.drawing) drawPlinkoBoard(null, null); });
        bindClick('wheel-spin', playWheel);
        bindChange('wheel-risk', function () { if (!wheel.spinning) drawWheel(wheel.rotation, -1); });
        bindClick('mines-start', startMines);
        bindClick('mines-cashout', cashoutMines);
        bindClick('keno-play', playKeno);
        bindClick('keno-clear', kenoClear);
        bindClick('keno-quick', kenoQuickPick);
        bindClick('roulette-spin', playRoulette);
        bindChange('roulette-bet-type', updateRouletteSelectionField);
        bindClick('hilo-start', startHilo);
        bindClick('hilo-higher', function () { hiloGuess('higher'); });
        bindClick('hilo-lower', function () { hiloGuess('lower'); });
        bindClick('hilo-cashout', hiloCashout);
        bindClick('casino-sound-toggle', toggleSound);
        updateSoundToggle();
        document.querySelectorAll('.casino-currency-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                setActiveCurrency(btn.getAttribute('data-currency') || 'coins');
            });
        });
        bindChange('rps-dist-lane', refreshDistribution);
        bindChange('rps-dist-context', refreshDistribution);
        bindChange('outcome-dist-lane', refreshOutcomeDistribution);
        document.querySelectorAll('.casino-tab').forEach(function (tab) {
            tab.addEventListener('click', function () {
                document.querySelectorAll('.casino-tab').forEach(function (t) { t.classList.remove('active'); });
                tab.classList.add('active');
                leaderboardPeriod = tab.getAttribute('data-period') || 'today';
                refreshLeaderboard();
                refreshSocialBoard();
            });
        });

        setTimeout(markStaleLoadingPanels, 15000);

        try {
            await refreshBalance();
        } catch (err) {
            console.warn('[casino] balance bootstrap failed:', err);
            var bal = $('casino-balance');
            if (bal) bal.textContent = 'Could not load balance — refresh the page';
        }

        safeRefresh('history', refreshHistory);
        safeRefresh('distribution', refreshDistribution);
        safeRefresh('outcomeDistribution', refreshOutcomeDistribution);
        safeRefresh('counterHint', refreshCounterHint);
        safeRefresh('quests', refreshQuests);
        safeRefresh('leaderboard', refreshLeaderboard);
        safeRefresh('personalBests', refreshPersonalBests);
        safeRefresh('hallOfFame', refreshHallOfFame);
        safeRefresh('houseStats', refreshHouseStats);
        safeRefresh('socialBoard', refreshSocialBoard);
        safeRefresh('depositPacks', refreshDepositPacks);
        safeRefresh('mn2BuyinPacks', refreshMn2BuyinPacks);
        safeRefresh('paypalReturn', handlePayPalReturn);
        safeRefresh('activityFeed', refreshActivityFeed);
        safeRefresh('jackpotMeter', refreshJackpotMeter);
        safeRefresh('tournaments', refreshTournaments);
        safeRefresh('rg', refreshRgStatus);
        safeRefresh('fairness', refreshFairnessState);
        try { drawCrashCurve(1.0, false); } catch (e) { /* canvas optional */ }
        try { drawPlinkoBoard(null, null); } catch (e) { /* canvas optional */ }
        try { drawWheel(wheel.rotation, -1); } catch (e) { /* canvas optional */ }
        try { buildMinesGrid(); } catch (e) { /* grid optional */ }
        try { buildKenoGrid(); } catch (e) { /* grid optional */ }
        try { updateRouletteSelectionField(); } catch (e) { /* optional */ }
        setInterval(function () { safeRefresh('activityFeed', refreshActivityFeed); }, 15000);
        setInterval(function () { safeRefresh('jackpotMeter', refreshJackpotMeter); }, 12000);
        setInterval(function () { safeRefresh('tournaments', refreshTournaments); }, 30000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCasino);
    } else {
        initCasino();
    }
})();
