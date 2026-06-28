(function () {
    'use strict';

    const userId = localStorage.getItem('game_user_id') || 'default_user';
    const baseUrl = window.location.origin;
    let leaderboardPeriod = 'today';
    let leaderboardScope = 'local';
    let lastDoubleBetId = null;
    let activeCurrency = localStorage.getItem('casino_currency') || 'coins';
    let realMoneyEnabled = false;
    let paypalEnabled = false;
    let mn2Limits = { min: 0.05, max: 5 };
    let usdLimits = { min: 0.5, max: 25 };
    let disclaimers = { coins: '', mn2: '', paypal: '' };
    let securityToken = localStorage.getItem('casino_security_token') || '';
    let securityExpires = localStorage.getItem('casino_security_expires') || '';
    let activeMainTab = localStorage.getItem('casino_main_tab') || 'home';
    let featuredGames = [];
    let socialLinks = [];
    let shareNetworks = [];
    let lastBigWin = null;
    let mobileConfig = null;
    let deferredInstallPrompt = null;
    let metaPixelId = null;

    function initMetaPixel(pixelId) {
        if (!pixelId || metaPixelId || window.fbq) return;
        metaPixelId = String(pixelId);
        (function (f, b, e, v) {
            if (f.fbq) return;
            var n = f.fbq = function () {
                n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
            };
            if (!f._fbq) f._fbq = n;
            n.push = n;
            n.loaded = true;
            n.version = '2.0';
            n.queue = [];
            var t = b.createElement(e);
            t.async = true;
            t.src = v;
            var s = b.getElementsByTagName(e)[0];
            s.parentNode.insertBefore(t, s);
        })(window, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');
        window.fbq('init', metaPixelId);
        window.fbq('track', 'PageView');
    }

    function trackMetaEvent(name, params) {
        if (!metaPixelId || !window.fbq) return;
        try {
            window.fbq('trackCustom', name, params || {});
        } catch (e) { /* optional analytics */ }
    }

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
            var notes = {
                tick: [660, 0.04, 0.05], win: [880, 0.06, 0.16], big: [1200, 0.09, 0.32], bust: [180, 0.07, 0.3],
                spin: [520, 0.025, 0.03], stop: [320, 0.07, 0.09], scatter: [1040, 0.08, 0.22], jackpot: [880, 0.12, 0.45]
            };
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
            lastBigWin = { net: data.net, currency: data.currency, game: data.game, multiple: multiple };
            celebrate('MEGA WIN', '+' + formatNet(data.net) + ' ' + currencyLabel(data.currency) + ' · ' + multiple.toFixed(2) + '×', 'mega');
        } else if (multiple >= 3) {
            lastBigWin = { net: data.net, currency: data.currency, game: data.game, multiple: multiple };
            celebrate('BIG WIN', '+' + formatNet(data.net) + ' ' + currencyLabel(data.currency) + ' · ' + multiple.toFixed(2) + '×', 'big');
        }
        if (multiple >= 3) {
            trackMetaEvent('CasinoBigWin', {
                game: data.game || 'unknown',
                multiple: multiple,
                currency: data.currency || 'coins',
            });
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
        safeRefresh('rgBanner', refreshResponsibleGamingBanner);
        safeRefresh('tournaments', refreshTournaments);
    }

    function showDoubleOffer(data) {
        try { maybeCelebrate(data); } catch (e) { /* celebration optional */ }
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
            ['casino-featured-grid', 'Featured games unavailable'],
            ['casino-activity-charts', 'Activity monitor unavailable'],
            ['casino-social-follow-grid', 'Social links unavailable'],
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

    function avatarInitial(uid) {
        var s = String(uid || '?');
        return s.charAt(0).toUpperCase();
    }

    var TAB_ALIASES = { lobby: 'home', walk: 'home', lounge: 'home', games: 'home' };

    function normalizeDeepLinkTab(tab) {
        if (!tab) return null;
        var key = String(tab).toLowerCase();
        return TAB_ALIASES[key] || key;
    }

    function resolveDeepLinkTabFromUrl() {
        if (window.__casinoMobile && window.__casinoMobile.resolveDeepLinkTab) {
            return window.__casinoMobile.resolveDeepLinkTab();
        }
        var params = new URLSearchParams(window.location.search);
        var game = params.get('game');
        if (game && document.getElementById('casino-tab-' + game)) return game;
        var tab = normalizeDeepLinkTab(params.get('tab'));
        if (tab && document.getElementById('casino-tab-' + tab)) return tab;
        var hash = (window.location.hash || '').replace(/^#tab-/, '');
        if (hash && document.getElementById('casino-tab-' + hash)) return hash;
        return null;
    }

    function applyDeepLinks() {
        var target = resolveDeepLinkTabFromUrl();
        if (target) switchMainTab(target);
    }

    function isStandaloneDisplay() {
        return window.matchMedia('(display-mode: standalone)').matches ||
            window.navigator.standalone === true ||
            new URLSearchParams(window.location.search).get('app') === 'casino-twa';
    }

    function isAndroid() {
        return /Android/i.test(navigator.userAgent || '');
    }

    async function initMobileInstall() {
        var panel = $('casino-play-install');
        var badge = $('casino-play-store-badge');
        var pwaBtn = $('casino-pwa-install-btn');
        if (!panel) return;
        try {
            mobileConfig = await fetch(baseUrl + '/api/casino/mobile/config').then(function (r) { return r.json(); });
        } catch (e) {
            mobileConfig = null;
        }
        if (badge && mobileConfig && mobileConfig.play_store_url) {
            badge.href = mobileConfig.play_store_url;
        }
        if (!isStandaloneDisplay() && (isAndroid() || deferredInstallPrompt)) {
            panel.classList.remove('hidden');
        }
        if (pwaBtn && deferredInstallPrompt) {
            pwaBtn.classList.remove('hidden');
            pwaBtn.addEventListener('click', async function () {
                if (!deferredInstallPrompt) return;
                deferredInstallPrompt.prompt();
                try { await deferredInstallPrompt.userChoice; } catch (e) { /* ignore */ }
                deferredInstallPrompt = null;
                pwaBtn.classList.add('hidden');
            });
        }
    }

    window.addEventListener('beforeinstallprompt', function (e) {
        e.preventDefault();
        deferredInstallPrompt = e;
        var panel = $('casino-play-install');
        var pwaBtn = $('casino-pwa-install-btn');
        if (panel) panel.classList.remove('hidden');
        if (pwaBtn) pwaBtn.classList.remove('hidden');
    });

    function switchMainTab(tabId) {
        activeMainTab = tabId || 'home';
        localStorage.setItem('casino_main_tab', activeMainTab);
        document.querySelectorAll('.casino-main-tab').forEach(function (btn) {
            var on = btn.getAttribute('data-tab') === activeMainTab;
            btn.classList.toggle('active', on);
            btn.setAttribute('aria-selected', on ? 'true' : 'false');
        });
        document.querySelectorAll('.casino-tab-panel').forEach(function (panel) {
            var match = panel.id === 'casino-tab-' + activeMainTab;
            panel.classList.toggle('active', match);
            panel.hidden = !match;
        });
        if (activeMainTab === 'leaderboard') {
            safeRefresh('leaderboard', refreshLeaderboard);
        } else if (activeMainTab === 'activity') {
            safeRefresh('activityMonitor', refreshActivityMonitor);
            safeRefresh('revenueDashboard', refreshRevenueDashboard);
        } else if (activeMainTab === 'social') {
            safeRefresh('socialTab', initSocialTab);
        } else if (activeMainTab === 'compete') {
            safeRefresh('competeTab', refreshCompeteTab);
        }
        try {
            if (history.replaceState) {
                var qs = new URLSearchParams(window.location.search);
                if (qs.get('game')) {
                    history.replaceState(null, '', window.location.pathname + window.location.search + '#tab-' + activeMainTab);
                } else {
                    history.replaceState(null, '', '#tab-' + activeMainTab);
                }
            }
        } catch (e) { /* optional */ }
        try {
            if (window.__casinoMobile && window.__casinoMobile.hapticLight) {
                window.__casinoMobile.hapticLight();
            }
        } catch (e) { /* optional haptics */ }
    }

    window.__casinoSwitchTab = switchMainTab;

    function renderFeaturedGames() {
        var grid = $('casino-featured-grid');
        if (!grid) return;
        if (!featuredGames.length) {
            grid.textContent = 'No featured games configured.';
            return;
        }
        grid.innerHTML = '';
        featuredGames.forEach(function (fg) {
            var card = document.createElement('article');
            card.className = 'casino-featured-card';
            card.setAttribute('data-game', fg.id);
            card.innerHTML =
                '<div class="casino-featured-icon">' + (fg.icon || '🎮') + '</div>' +
                (fg.tag ? '<span class="casino-featured-tag">' + fg.tag + '</span>' : '') +
                '<div class="casino-featured-label">' + (fg.label || fg.id) + '</div>' +
                '<div class="casino-featured-blurb">' + (fg.blurb || 'Play now') + '</div>' +
                '<button type="button" class="casino-featured-play">Quick play</button>';
            card.querySelector('.casino-featured-play').addEventListener('click', function (e) {
                e.stopPropagation();
                switchMainTab(fg.id);
            });
            card.addEventListener('click', function () { switchMainTab(fg.id); });
            grid.appendChild(card);
        });
    }

    function initMainTabNav() {
        var nav = $('casino-main-tabs');
        var panelsRoot = $('casino-tab-panels');
        var grid = $('casino-games-grid');
        if (!nav || !panelsRoot) return;

        function addTabBtn(id, label, isActive) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'casino-main-tab' + (isActive ? ' active' : '');
            btn.id = 'casino-tab-btn-' + id;
            btn.setAttribute('role', 'tab');
            btn.setAttribute('data-tab', id);
            btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
            btn.textContent = label;
            btn.addEventListener('click', function () { switchMainTab(id); });
            nav.appendChild(btn);
            return btn;
        }

        nav.innerHTML = '';
        addTabBtn('home', '🏠 Home', activeMainTab === 'home');

        if (grid) {
            var cards = grid.querySelectorAll('.casino-card[data-casino-game]');
            cards.forEach(function (card) {
                var gameId = card.getAttribute('data-casino-game');
                var label = card.getAttribute('data-casino-label') || gameId;
                var panel = document.createElement('section');
                panel.className = 'casino-tab-panel';
                panel.id = 'casino-tab-' + gameId;
                panel.setAttribute('role', 'tabpanel');
                panel.hidden = true;
                panel.appendChild(card);
                panelsRoot.insertBefore(panel, $('casino-tab-leaderboard'));
                addTabBtn(gameId, label, activeMainTab === gameId);
            });
            grid.remove();
        }

        addTabBtn('leaderboard', '🏆 Leaderboard', activeMainTab === 'leaderboard');
        addTabBtn('activity', '📊 Activity', activeMainTab === 'activity');
        addTabBtn('compete', '⚔️ Compete', activeMainTab === 'compete');
        addTabBtn('social', '🌐 Social', activeMainTab === 'social');

        var deepTab = resolveDeepLinkTabFromUrl();
        if (deepTab) {
            activeMainTab = deepTab;
        } else {
            var hash = (window.location.hash || '').replace(/^#tab-/, '');
            if (hash && document.getElementById('casino-tab-' + hash)) {
                activeMainTab = hash;
            }
        }
        switchMainTab(activeMainTab);
        try {
            window.dispatchEvent(new CustomEvent('casino:ready'));
        } catch (e) { /* optional */ }
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
        featuredGames = data.featured_games || [];
        socialLinks = data.social_links || [];
        try { renderFeaturedGames(); } catch (e) { /* optional */ }
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
        var podium = $('casino-lb-podium');
        var list = $('casino-lb-list');
        var youEl = $('casino-lb-you');
        var rankBar = $('casino-rank-bar');
        if (!list && !podium) {
            return;
        }
        var lbPath = leaderboardScope === 'global'
            ? '/api/casino/global/leaderboard'
            : '/api/casino/leaderboard';
        var data = await api(apiPathWithCurrency(lbPath + '?period=' + encodeURIComponent(leaderboardPeriod) + '&limit=25'));
        var badge = $('casino-lb-network-badge');
        if (badge) {
            if (leaderboardScope === 'global' && data.network_label) {
                badge.textContent = data.network_label;
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }
        }
        if (!data.success) {
            if (list) list.innerHTML = '<li>' + (data.error || 'Leaderboard unavailable') + '</li>';
            if (podium) podium.innerHTML = '';
            if (youEl) youEl.textContent = '';
            if (rankBar) rankBar.textContent = data.error || 'Rank unavailable';
            return;
        }
        var rows = data.leaderboard || [];
        var medals = ['🥇', '🥈', '🥉'];

        if (podium) {
            podium.innerHTML = '';
            [1, 0, 2].forEach(function (idx) {
                var row = rows[idx];
                var rank = idx + 1;
                var slot = document.createElement('div');
                slot.className = 'casino-lb-podium-slot rank-' + rank;
                if (!row) {
                    slot.innerHTML = '<div class="casino-lb-medal">' + medals[idx] + '</div><div class="casino-lb-handle">—</div>';
                } else {
                    slot.innerHTML =
                        '<div class="casino-lb-medal">' + medals[idx] + '</div>' +
                        '<div class="casino-lb-avatar" aria-hidden="true">' + avatarInitial(row.user_id) + '</div>' +
                        '<div class="casino-lb-handle">' + shortUser(row.user_id) + '</div>' +
                        '<div class="casino-lb-net">+' + row.net + ' ' + currencyLabel(row.currency) + '</div>';
                }
                podium.appendChild(slot);
            });
        }

        if (list) {
            list.innerHTML = '';
            if (!rows.length) {
                list.innerHTML = '<li class="casino-lb-row">No bets yet for this period</li>';
            } else {
                rows.forEach(function (row) {
                    var li = document.createElement('li');
                    var extra = '';
                    if (row.rank === 1) extra = ' top-gold';
                    else if (row.rank === 2) extra = ' top-silver';
                    else if (row.rank === 3) extra = ' top-bronze';
                    if (row.user_id === userId) extra += ' you';
                    li.className = 'casino-lb-row' + extra;
                    li.innerHTML =
                        '<span class="casino-lb-rank-num">' + row.rank + '</span>' +
                        '<span class="casino-lb-mini-avatar" aria-hidden="true">' + avatarInitial(row.user_id) + '</span>' +
                        '<span class="casino-lb-handle">' + shortUser(row.user_id) + '</span>' +
                        '<span class="casino-lb-net">' + row.net + '</span>' +
                        '<span class="casino-lb-roi">' + (row.win_rate != null ? row.win_rate + '% win' : '') + '</span>';
                    list.appendChild(li);
                });
            }
        }

        if (youEl) {
            var you = data.your_rank;
            if (!you) {
                youEl.textContent = 'Your rank: unranked this period — place a bet to appear.';
            } else {
                youEl.textContent =
                    'You are #' + you.rank + ' · Net ' + you.net + ' · Win ' + you.win_rate + '% · ROI ' + you.roi + '%' +
                    (you.gap_to_first > 0 ? ' · ' + you.gap_to_first + ' behind #1' : ' · Leading!');
            }
        }
        if (rankBar) {
            var yr = data.your_rank;
            if (!yr) {
                rankBar.textContent = 'Your rank: unranked — open Leaderboard tab after your first bet.';
            } else {
                rankBar.textContent =
                    'Your rank #' + yr.rank + ' · Net ' + yr.net + ' · Win ' + yr.win_rate + '% · ROI ' + yr.roi + '%' +
                    (yr.gap_to_first > 0 ? ' · ' + yr.gap_to_first + ' behind #1' : ' · Leading!');
            }
        }
    }

    async function refreshActivityMonitor() {
        var charts = $('casino-activity-charts');
        var feedList = $('casino-activity-feed-list');
        if (!charts) return;
        var data = await api(apiPathWithCurrency('/api/casino/activity-stats?days=5'));
        if (!data.success || !(data.daily || []).length) {
            charts.textContent = data.error || 'Activity data unavailable';
            return;
        }
        var daily = data.daily;
        var metrics = [
            { key: 'bets', label: 'Bets', color: '#60a5fa' },
            { key: 'wins', label: 'Wins', color: '#34d399' },
            { key: 'unique_players', label: 'Unique players', color: '#c084fc' },
            { key: 'jackpot_hits', label: 'Jackpot hits', color: '#fbbf24' },
        ];
        charts.innerHTML = '';
        metrics.forEach(function (metric) {
            var max = 1;
            daily.forEach(function (d) { max = Math.max(max, Number(d[metric.key] || 0)); });
            var block = document.createElement('div');
            block.className = 'casino-activity-metric';
            block.innerHTML = '<h3>' + metric.label + '</h3><div class="casino-activity-bars"></div>';
            var bars = block.querySelector('.casino-activity-bars');
            daily.forEach(function (d) {
                var val = Number(d[metric.key] || 0);
                var wrap = document.createElement('div');
                wrap.className = 'casino-activity-bar-wrap';
                var bar = document.createElement('div');
                bar.className = 'casino-activity-bar';
                bar.style.height = Math.max(4, Math.round((val / max) * 64)) + 'px';
                bar.style.background = 'linear-gradient(180deg, ' + metric.color + ', #7c3aed)';
                bar.title = String(val);
                wrap.appendChild(bar);
                var lbl = document.createElement('span');
                lbl.textContent = (d.day || '').slice(5);
                wrap.appendChild(lbl);
                bars.appendChild(wrap);
            });
            charts.appendChild(block);
        });
        if (data.tournament_joins != null) {
            var tnote = document.createElement('p');
            tnote.className = 'casino-activity-sub';
            tnote.textContent = 'Tournament buy-ins (5d): ' + data.tournament_joins;
            charts.appendChild(tnote);
        }
        if (feedList) {
            var feed = await api('/api/casino/activity-feed?limit=8');
            if (!feed.success || !(feed.feed || []).length) {
                feedList.textContent = 'No recent wins yet.';
            } else {
                feedList.innerHTML = '<h3>Recent wins</h3>' + feed.feed.map(function (f) {
                    return '<div class="casino-activity-feed-item">🏆 ' + shortUser(f.user_id) + ' won ' +
                        formatFeedAmount(f.net, f.currency) + ' on ' + prettyGame(f.game) + '</div>';
                }).join('');
            }
        }
    }

    function buildSocialLinkCard(link, isShare) {
        var a = document.createElement('a');
        a.className = 'casino-social-link-card';
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        var href = link.url || '#';
        if (isShare && link.share_url) {
            var text = encodeURIComponent(shareNetworks.default_share_text || 'MasterNoder Casino');
            var url = encodeURIComponent((shareNetworks.share_base_url || baseUrl) + '/casino/');
            href = link.share_url.replace('{text}', text).replace('{url}', url);
        } else if (href.indexOf('/') === 0) {
            href = baseUrl + href;
        }
        a.href = href;
        a.innerHTML =
            '<span class="casino-social-link-icon">' + (link.icon || '🌐') + '</span>' +
            '<span class="casino-social-link-label">' + (link.label || link.name || link.id) + '</span>';
        return a;
    }

    async function initSocialTab() {
        var followGrid = $('casino-social-follow-grid');
        var shareGrid = $('casino-social-share-grid');
        if (!followGrid) return;

        var linksData = null;
        try {
            linksData = await api('/api/casino/social/links');
        } catch (e) {
            linksData = null;
        }
        if (linksData && linksData.success) {
            shareNetworks = {
                share_base_url: linksData.share_base_url || baseUrl,
                default_share_text: linksData.default_share_text || 'MasterNoder Casino',
                networks: linksData.share_networks || [],
            };
            socialLinks = linksData.follow_links || socialLinks;
            var discord = linksData.discord || {};
            var fb = linksData.facebook || {};
            var playBadge = $('casino-play-store-badge');
            if (playBadge && linksData.mobile && linksData.mobile.play_store_url) {
                playBadge.href = linksData.mobile.play_store_url;
            }
            var discordActivity = $('casino-discord-activity-link');
            if (discordActivity && discord.activity_invite_url) {
                discordActivity.href = discord.activity_invite_url;
                discordActivity.classList.remove('hidden');
            }
            if (fb.page_url) {
                var hasFb = socialLinks.some(function (l) { return l.id === 'facebook'; });
                if (!hasFb) {
                    socialLinks.push({ id: 'facebook', label: 'Facebook', icon: 'f', url: fb.page_url, type: 'follow' });
                }
            }
            if (fb.pixel_id) {
                initMetaPixel(fb.pixel_id);
            }
        } else if (!shareNetworks.networks) {
            try {
                var sn = await fetch(baseUrl + '/data/social_networks.json').then(function (r) { return r.json(); });
                shareNetworks = sn || {};
            } catch (e) {
                shareNetworks = {};
            }
        }

        followGrid.innerHTML = '';
        (socialLinks.length ? socialLinks : []).forEach(function (link) {
            if (link.type === 'play' || link.type === 'follow' || link.type === 'mobile') {
                followGrid.appendChild(buildSocialLinkCard(link, false));
            }
        });
        if (!socialLinks.length) {
            followGrid.textContent = 'Social links loading from config…';
        }

        if (shareGrid) {
            shareGrid.innerHTML = '';
            (shareNetworks.networks || []).forEach(function (net) {
                shareGrid.appendChild(buildSocialLinkCard(net, true));
            });
        }

        var prefs = await api('/api/casino/social/preferences');
        var toggle = $('casino-share-wins-toggle');
        if (toggle && prefs.success && prefs.preferences) {
            toggle.checked = !!prefs.preferences.share_wins;
        }
        var discordLink = $('casino-discord-play-link');
        if (discordLink) {
            if (prefs.discord_earn_href) discordLink.href = prefs.discord_earn_href;
            if (prefs.discord_earn_coins) {
                var earnStrip = $('casino-discord-earn');
                if (earnStrip) {
                    var p = earnStrip.querySelector('p');
                    if (p) {
                        p.textContent = 'Opt in to mirror big wins to Discord. Join the server to earn ' +
                            prefs.discord_earn_coins + ' bonus coins.';
                    }
                }
            }
        }
        initMobileInstall();
        await refreshReferralInvite();
        await refreshReferralLeaderboard();
        await refreshReferralQuests();
        await refreshFollowLeaders();
        await refreshCrewChallengeHook();
        await refreshSocialActivityFeed();
    }

    async function refreshReferralInvite() {
        var codeEl = $('casino-referral-code');
        if (!codeEl) return;
        var data = await api('/api/casino/social/referral?user_id=' + encodeURIComponent(userId));
        if (!data.success) {
            codeEl.textContent = data.error || 'Unavailable';
            return;
        }
        codeEl.textContent = data.referral_code || '—';
        codeEl.dataset.inviteUrl = data.invite_url || '';
        codeEl.dataset.copyText = data.copy_text || '';
        codeEl.dataset.whatsappUrl = data.whatsapp_url || '';
    }

    function copyReferralCode() {
        var codeEl = $('casino-referral-code');
        if (!codeEl || !codeEl.textContent || codeEl.textContent === 'Loading…') return;
        navigator.clipboard.writeText(codeEl.textContent).then(function () {
            showToast('Referral code copied');
        }).catch(function () {
            showToast('Copy: ' + codeEl.textContent);
        });
    }

    function copyReferralLink() {
        var codeEl = $('casino-referral-code');
        var link = (codeEl && codeEl.dataset.inviteUrl) || (baseUrl + '/casino/');
        navigator.clipboard.writeText(link).then(function () {
            showToast('Invite link copied');
        }).catch(function () {
            showToast('Copy link: ' + link);
        });
    }

    async function refreshFollowLeaders() {
        var list = $('casino-follow-leaders-list');
        if (!list) return;
        var data = await api('/api/casino/social/follow?user_id=' + encodeURIComponent(userId) + '&period=week&limit=5');
        if (!data.success || !(data.players || []).length) {
            list.textContent = 'No leaderboard players yet this week.';
            return;
        }
        list.innerHTML = '';
        data.players.forEach(function (p) {
            var row = document.createElement('div');
            row.className = 'casino-follow-row';
            row.innerHTML = '<span>#' + (p.rank || '?') + ' ' + (p.display || shortUser(p.user_id)) +
                ' (' + (p.net || 0) + ')</span>';
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'casino-share-site-btn';
            btn.textContent = p.following ? 'Following' : 'Follow';
            btn.disabled = !!p.following;
            btn.addEventListener('click', async function () {
                var res = await api('/api/casino/social/follow', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: userId, target_user_id: p.user_id }),
                });
                if (res.success) {
                    btn.textContent = 'Following';
                    btn.disabled = true;
                    showToast('Following ' + (p.display || 'player'));
                }
            });
            row.appendChild(btn);
            list.appendChild(row);
        });
    }

    async function refreshCrewChallengeHook() {
        var body = $('casino-crew-challenge-body');
        if (!body) return;
        var data = await api('/api/casino/social/crew-challenge?user_id=' + encodeURIComponent(userId));
        if (!data.success) {
            body.textContent = data.error || 'Crew data unavailable';
            return;
        }
        if (!data.in_crew) {
            body.innerHTML = '<p>Join a crew on the <a href="/game#social">game social hub</a> to compete in crew casino leaderboards.</p>';
            return;
        }
        var rank = data.your_crew_rank ? ('#' + data.your_crew_rank) : '—';
        body.innerHTML = '<p><strong>' + (data.crew_name || 'Your crew') + '</strong> · ' +
            (data.member_count || 0) + ' members · crew rank ' + rank + '</p>' +
            '<p>' + (data.compete_tab_hint || '') + '</p>' +
            '<button type="button" class="casino-share-site-btn" id="casino-goto-compete">Open Compete tab</button>';
        var go = $('casino-goto-compete');
        if (go) {
            go.addEventListener('click', function () {
                var tab = document.querySelector('[data-casino-tab="compete"]');
                if (tab) tab.click();
            });
        }
    }

    async function refreshSocialActivityFeed() {
        var list = $('casino-social-feed-list');
        if (!list) return;
        var feed = await api('/api/casino/activity-feed?limit=6');
        if (!feed.success || !(feed.feed || []).length) {
            list.textContent = 'No recent wins yet.';
            return;
        }
        var ids = feed.feed.map(function (f) { return f.bet_id || (f.user_id + '-' + (f.created_at || '')); }).join(',');
        var reactions = { reactions: {} };
        try {
            reactions = await api('/api/casino/social/feed/reactions?item_ids=' + encodeURIComponent(ids));
        } catch (e) { /* optional */ }
        list.innerHTML = '';
        feed.feed.forEach(function (f) {
            var itemId = f.bet_id || (f.user_id + '-' + (f.created_at || ''));
            var row = document.createElement('div');
            row.className = 'casino-social-feed-item';
            row.innerHTML = '<div>🏆 ' + shortUser(f.user_id) + ' · ' + formatFeedAmount(f.net, f.currency) +
                ' on ' + prettyGame(f.game) + '</div>';
            var reactBar = document.createElement('div');
            reactBar.className = 'casino-feed-reactions';
            ['fire', 'clap', 'wow'].forEach(function (emoji) {
                var b = document.createElement('button');
                b.type = 'button';
                b.className = 'casino-feed-react-btn';
                var counts = (reactions.reactions && reactions.reactions[itemId]) || {};
                b.textContent = emoji + (counts[emoji] ? ' ' + counts[emoji] : '');
                b.addEventListener('click', async function () {
                    var res = await api('/api/casino/social/feed/reactions', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: userId, item_id: itemId, reaction: emoji }),
                    });
                    if (res.success) {
                        b.textContent = emoji + (res.counts && res.counts[emoji] ? ' ' + res.counts[emoji] : '');
                    }
                });
                reactBar.appendChild(b);
            });
            row.appendChild(reactBar);
            list.appendChild(row);
        });
    }

    async function shareViaWhatsApp() {
        var codeEl = $('casino-referral-code');
        if (codeEl && codeEl.dataset.whatsappUrl) {
            window.open(codeEl.dataset.whatsappUrl, '_blank', 'noopener');
            return;
        }
        var url = (shareNetworks.share_base_url || baseUrl) + '/casino/';
        var text = shareNetworks.default_share_text || 'Play at MasterNoder Casino';
        window.open('https://wa.me/?text=' + encodeURIComponent(text + ' ' + url), '_blank', 'noopener');
    }

    async function shareXThread() {
        var payload = lastBigWin ? {
            user_id: userId,
            game: lastBigWin.game,
            net: lastBigWin.net,
            currency: lastBigWin.currency,
            multiplier: lastBigWin.multiple,
        } : { user_id: userId, game: 'casino', net: 0, currency: 'coins' };
        var card = await api('/api/casino/share/big-win', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (card && card.thread_share && card.thread_share.x_intent_url) {
            window.open(card.thread_share.x_intent_url, '_blank', 'noopener');
            showToast('X thread starter opened — paste follow-up lines from share card');
            return;
        }
        shareCasinoWin();
    }

    async function registerCasinoReferralFromUrl() {
        var params = new URLSearchParams(window.location.search);
        var ref = params.get('ref');
        if (!ref || userId === 'default_user') return;
        try {
            await api('/api/casino/social/referral/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, referral_code: ref }),
            });
        } catch (e) { /* best effort */ }
    }

    async function shareCasinoWin() {
        if (!lastBigWin) {
            showToast('Win something big first (3× or more), then share!');
            return;
        }
        var payload = {
            user_id: userId,
            game: lastBigWin.game,
            net: lastBigWin.net,
            currency: lastBigWin.currency,
            multiplier: lastBigWin.multiple,
        };
        var card = null;
        try {
            card = await api('/api/casino/share/big-win', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
        } catch (e) {
            card = null;
        }
        if (card && card.success && card.share_urls) {
            window.open(card.share_urls.twitter || card.share_urls.facebook, '_blank', 'noopener');
            showToast('Share card ready — pick your network');
            return;
        }
        var text = 'I just won ' + formatNet(lastBigWin.net) + ' ' + currencyLabel(lastBigWin.currency) +
            ' on ' + prettyGame(lastBigWin.game) + ' at MasterNoder Casino!';
        var url = (shareNetworks.share_base_url || baseUrl) + '/casino/';
        var xUrl = 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(text) + '&url=' + encodeURIComponent(url);
        window.open(xUrl, '_blank', 'noopener');
    }

    async function shareCasinoSite() {
        var text = shareNetworks.default_share_text || 'Play at MasterNoder Casino — coins, MN2, and USD rails.';
        var url = (shareNetworks.share_base_url || baseUrl) + '/casino/';
        try {
            var card = await api('/api/casino/share/big-win', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, game: 'casino', net: 0, currency: 'coins' }),
            });
            if (card && card.success && card.share_urls && card.share_urls.facebook) {
                window.open(card.share_urls.facebook, '_blank', 'noopener');
                showToast('Facebook share opened');
                return;
            }
        } catch (e) { /* fallback */ }
        var fb = 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(url);
        window.open(fb, '_blank', 'noopener');
        showToast('Share dialog opened — paste your message: ' + text);
    }

    async function toggleShareWins(enabled) {
        await api('/api/casino/social/preferences', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ share_wins: !!enabled, user_id: userId }),
        });
        showToast(enabled ? 'Discord win sharing enabled' : 'Discord win sharing off');
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

    async function refreshBigWinHallOfFame() {
        var el = $('casino-big-win-hof');
        if (!el) return;
        var data = await api('/api/casino/big-wins/hall-of-fame?days=7&limit=8');
        if (!data.success || !(data.wins || []).length) {
            el.textContent = 'No big multipliers in the last 7 days yet — be the first!';
            return;
        }
        el.innerHTML = (data.wins || []).map(function (w) {
            return '<div class="casino-big-win-row">#' + w.rank + ' ' + shortUser(w.user_id) +
                ' · ' + Number(w.multiplier).toFixed(2) + '× on ' + prettyGame(w.game) +
                ' · +' + formatFeedAmount(w.net, w.currency) + '</div>';
        }).join('');
    }

    async function refreshSlotOfTheDay() {
        var el = $('casino-slot-of-day');
        if (!el) return;
        var data = await api('/api/casino/slot-of-the-day');
        if (!data.success || !data.enabled || !data.slot) {
            el.classList.add('hidden');
            return;
        }
        var slot = data.slot;
        el.classList.remove('hidden');
        el.innerHTML = '<span>⭐ ' + (data.badge_label || 'Slot of the Day') + '</span>' +
            '<span>' + (slot.icon || '🎰') + ' ' + (slot.label || slot.id) + '</span>';
        el.title = slot.blurb || 'Play today\'s featured slot';
        el.onclick = function () { switchMainTab('slots'); };
    }

    async function refreshSeasonalBadge() {
        var el = $('casino-seasonal-badge');
        if (!el) return;
        var data = await api('/api/casino/seasonal/slots');
        if (!data.success || !data.enabled || !(data.slots || []).length) {
            el.classList.add('hidden');
            return;
        }
        el.classList.remove('hidden');
        var winLabel = (data.active_windows && data.active_windows[0]) ? data.active_windows[0].label : 'Seasonal';
        var slotLabels = (data.slots || []).slice(0, 3).map(function (s) {
            return (s.icon || '🎃') + ' ' + (s.label || s.id);
        }).join(' · ');
        el.innerHTML = '<span>🍂 ' + (data.badge_label || 'Seasonal') + '</span>' +
            '<span>' + winLabel + '</span>' +
            '<span class="casino-seasonal-slots">' + slotLabels + '</span>';
        el.title = 'Limited-time slot reskins — same RTP, new look';
        el.onclick = function () { switchMainTab('slots'); };
    }

    async function refreshVipLounge() {
        var wrap = $('casino-vip-lounge');
        var body = $('casino-vip-lounge-body');
        if (!wrap || !body) return;
        var data = await api('/api/casino/vip/lounge?user_id=' + encodeURIComponent(userId));
        if (!data.success || !data.enabled) {
            wrap.classList.add('hidden');
            return;
        }
        wrap.classList.remove('hidden');
        if (!data.unlocked) {
            body.innerHTML = '<p class="casino-vip-locked">🔒 Unlock at ' + Math.round(data.min_xp) +
                ' XP — you have ' + Math.round(data.user_xp || 0) + ' (' +
                Math.round(data.xp_to_unlock || 0) + ' to go). Cosmetic lounge only.</p>';
            return;
        }
        var frames = (data.frame_previews || []).map(function (f) {
            return '<span class="casino-vip-frame" style="--frame-color:' + (f.preview_color || '#ffd700') + '">' +
                (f.icon || '🖼️') + ' ' + (f.label || f.id) + '</span>';
        }).join('');
        var wheelNote = data.daily_wheel && data.daily_wheel.available
            ? 'Daily wheel ready — same odds for everyone.'
            : (data.daily_wheel && data.daily_wheel.spun_today ? 'Daily wheel spun today.' : '');
        body.innerHTML = '<p class="casino-vip-unlocked">✨ ' + (data.title || 'VIP Lounge') + ' — ' +
            (data.subtitle || '') + '</p>' +
            '<div class="casino-vip-frames">' + frames + '</div>' +
            '<p class="casino-vip-wheel-note">' + wheelNote + '</p>';
    }

    async function refreshReferralQuests() {
        var el = $('casino-referral-quests');
        if (!el) return;
        var data = await api('/api/casino/social/referral/quests?user_id=' + encodeURIComponent(userId));
        if (!data.success) {
            el.textContent = 'Referral quests unavailable.';
            return;
        }
        if (!(data.referrals || []).length) {
            el.innerHTML = '<p>Share your invite link — earn coin trophies when friends complete their first 10 bets. No RTP perks.</p>';
            return;
        }
        el.innerHTML = (data.referrals || []).map(function (r) {
            var tiers = (r.tiers || []).map(function (t) {
                var mark = t.claimed ? '✓' : (t.completed ? '○' : '·');
                return mark + ' ' + (t.badge || '') + ' ' + (t.label || t.bets_required) +
                    ' (' + t.bets_required + ' bets, +' + t.referrer_coins + ' coins)';
            }).join('<br>');
            return '<div class="casino-ref-quest-row"><strong>' + (r.display || 'Friend') +
                '</strong> · ' + r.bet_count + '/' + r.max_bets + ' bets<br>' + tiers + '</div>';
        }).join('');
        if (data.total_coins_earned) {
            el.innerHTML += '<p class="casino-ref-quest-total">Total quest coins earned: ' + data.total_coins_earned + '</p>';
        }
    }

    async function refreshCompeteTab() {
        var crewEl = $('casino-crew-board');
        if (crewEl) {
            var crew = await api('/api/casino/crew/leaderboard?user_id=' + encodeURIComponent(userId) +
                '&currency=' + encodeURIComponent(activeCurrency));
            if (!crew.success || !(crew.crew_leaderboard || []).length) {
                crewEl.textContent = 'No crew data yet — join a crew on the game social hub.';
            } else {
                crewEl.innerHTML = '<p class="casino-crew-week">Week ' + (crew.week_key || '') + ' · ' +
                    (crew.currency || 'coins') + '</p>' +
                    (crew.crew_leaderboard || []).map(function (c) {
                        var tag = c.is_yours ? ' ★' : '';
                        return '<div class="casino-crew-row">#' + c.rank + ' ' + (c.name || c.crew_id) +
                            tag + ' · net ' + c.week_net + ' · ' + (c.member_count || 0) + ' members</div>';
                    }).join('');
            }
        }
        var rivalsEl = $('casino-rivals');
        if (rivalsEl) {
            var rivals = await api('/api/casino/rival-board?user_id=' + encodeURIComponent(userId) +
                '&period=week&currency=' + encodeURIComponent(activeCurrency));
            if (!rivals.success || !(rivals.board || []).length) {
                rivalsEl.textContent = 'Rival board loads after you and friends place bets.';
            } else {
                rivalsEl.innerHTML = (rivals.board || []).slice(0, 8).map(function (r) {
                    return '<div>#' + (r.rank || '?') + ' ' + shortUser(r.user_id) +
                        (r.is_you ? ' (you)' : '') + ' · net ' + r.net + '</div>';
                }).join('');
            }
        }
        var racesEl = $('casino-achievement-races');
        if (racesEl) {
            var races = await api('/api/casino/achievement-races?user_id=' + encodeURIComponent(userId));
            if (!races.success || !(races.races || []).length) {
                racesEl.textContent = 'Achievement races — compete for cosmetic coin prizes.';
            } else {
                racesEl.innerHTML = (races.races || []).map(function (r) {
                    return '<div>' + (r.title || r.id) + ' — ' + (r.status || 'open') + '</div>';
                }).join('');
            }
        }
    }

    function setupFairnessExportLink() {
        var link = $('casino-fairness-export-link');
        if (!link) return;
        link.href = '/api/casino/fairness/export?user_id=' + encodeURIComponent(userId) + '&limit=100';
        link.setAttribute('download', 'casino-fairness-audit.csv');
    }

    var activityFeedEventSource = null;

    function renderActivityFeedItems(feed) {
        var track = $('casino-ticker-track');
        if (!track) return;
        if (!(feed || []).length) {
            track.innerHTML = '<span class="casino-ticker-item">Be the first big win today…</span>';
            return;
        }
        var items = feed.map(function (f) {
            var mult = f.multiplier ? (' @ ' + Number(f.multiplier).toFixed(2) + '×') : '';
            return '<span class="casino-ticker-item">🏆 ' + shortUser(f.user_id) + ' won ' +
                formatFeedAmount(f.net, f.currency) + ' on ' + prettyGame(f.game) + mult + '</span>';
        });
        track.innerHTML = items.join('') + items.join('');
    }

    function startActivityFeedStream() {
        if (typeof EventSource === 'undefined') return false;
        try {
            if (activityFeedEventSource) {
                activityFeedEventSource.close();
            }
            var url = '/api/casino/activity-feed/stream?limit=12&interval=8';
            if (activeCurrency) url += '&currency=' + encodeURIComponent(activeCurrency);
            activityFeedEventSource = new EventSource(url);
            activityFeedEventSource.onmessage = function (ev) {
                try {
                    var msg = JSON.parse(ev.data);
                    if (msg.type === 'wins' && msg.feed) {
                        renderActivityFeedItems(msg.feed);
                    }
                } catch (e) { /* ignore parse errors */ }
            };
            activityFeedEventSource.onerror = function () {
                if (activityFeedEventSource) {
                    activityFeedEventSource.close();
                    activityFeedEventSource = null;
                }
            };
            return true;
        } catch (e) {
            return false;
        }
    }

    async function refreshNewsTicker() {
        var bar = $('casino-news-ticker');
        var track = $('casino-news-ticker-track');
        if (!bar || !track) return;
        var data = await api('/api/casino/news/platform?limit=6', null, 8000);
        if (!data.success || !(data.news || []).length) {
            bar.classList.add('hidden');
            return;
        }
        var items = (data.news || []).map(function (n) {
            var title = n.title || n.summary || 'Casino update';
            return '<span class="casino-news-item">' + title + '</span>';
        });
        track.innerHTML = items.join('') + items.join('');
        bar.classList.remove('hidden');
    }

    async function refreshHomeAchievements() {
        var el = $('casino-home-achievements');
        if (!el) return;
        var data = await api('/api/casino/achievements?user_id=' + encodeURIComponent(userId));
        if (!data.success || !(data.achievements || []).length) {
            el.textContent = 'Complete quests and bets to unlock achievements.';
            return;
        }
        var rows = (data.achievements || []).slice(0, 4).map(function (a) {
            var pct = a.target ? Math.min(100, Math.round((a.progress / a.target) * 100)) : (a.unlocked ? 100 : 0);
            return '<div class="casino-home-ach-item"><span>' + (a.icon || '🏅') + ' ' + (a.name || a.id) +
                '</span><span>' + (a.unlocked ? '✓' : (a.progress || 0) + '/' + (a.target || '?')) + '</span></div>' +
                '<div class="casino-home-ach-bar"><span style="width:' + pct + '%"></span></div>';
        });
        el.innerHTML = rows.join('');
    }

    async function refreshResponsibleGamingBanner() {
        var el = $('casino-rg-banner');
        if (!el) return;
        var data = await api('/api/casino/responsible-gaming/status?user_id=' + encodeURIComponent(userId) +
            '&currency=' + encodeURIComponent(activeCurrency));
        if (!data.success || !data.enabled) {
            el.classList.add('hidden');
            return;
        }
        var parts = [];
        if (data.session_minutes > 0) {
            parts.push('Session ' + data.session_minutes + ' min');
        }
        if (data.session_loss_cap != null) {
            parts.push('Loss ' + data.session_loss + '/' + data.session_loss_cap + ' ' + data.currency);
        }
        if (data.nudge) {
            parts.push(data.nudge);
        }
        if (!parts.length) {
            el.classList.add('hidden');
            return;
        }
        el.innerHTML = parts.join(' · ') + ' · <a href="/profile">Responsible play</a>';
        el.classList.remove('hidden');
    }

    async function refreshRevenueDashboard() {
        var el = $('casino-revenue-dashboard');
        if (!el) return;
        var today = await api('/api/casino/revenue/report/today');
        var recon = await api('/api/casino/revenue/reconcile');
        if (!today.success) {
            el.textContent = today.error || 'Revenue data unavailable';
            return;
        }
        var s = today.summary || {};
        var coins = (today.by_currency || {}).coins || {};
        var html = [
            '<div class="casino-revenue-stat"><span>House edge (all rails)</span><strong>' +
                (today.house_edge_profit_total != null ? today.house_edge_profit_total : '—') + '</strong></div>',
            '<div class="casino-revenue-stat"><span>Big wins today</span><strong>' + (s.big_wins || 0) + '</strong></div>',
            '<div class="casino-revenue-stat"><span>Coins bets today</span><strong>' + (coins.bets || 0) + '</strong></div>',
            '<div class="casino-revenue-stat"><span>Quest rewards granted</span><strong>' + (s.reward_coins_granted || 0) + ' coins</strong></div>',
        ];
        if (recon.success) {
            html.push('<div class="casino-revenue-stat ' + (recon.ok ? 'ok' : 'warn') + '"><span>Ledger reconcile</span><strong>' +
                (recon.ok ? 'OK' : 'Drift ' + recon.drift) + '</strong></div>');
        }
        el.innerHTML = html.join('');
    }

    async function refreshReferralLeaderboard() {
        var el = $('casino-referral-leaderboard');
        if (!el) return;
        var data = await api('/api/casino/social/referral/leaderboard?limit=8');
        if (!data.success || !(data.leaderboard || []).length) {
            el.textContent = 'No referral signups yet — share your link to climb the board.';
            return;
        }
        el.innerHTML = (data.leaderboard || []).map(function (r) {
            return '<li>#' + r.rank + ' ' + shortUser(r.user_id) + ' · ' + r.referrals + ' invites</li>';
        }).join('');
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
        safeRefresh('activityFeed', refreshActivityFeed);
        safeRefresh('jackpotMeter', refreshJackpotMeter);
        safeRefresh('rgBanner', refreshResponsibleGamingBanner);
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

    var SLOT_FLICKER_DEFAULT = ['🍒', '7️⃣', '💎', '⭐', '🔔', '🎰', '⚡', '🌟'];

    function displaySymbol(sym, symbolDisplay) {
        if (symbolDisplay && symbolDisplay[sym]) return symbolDisplay[sym];
        var fallbacks = {
            '7': '7️⃣', bar: '🎰', cherry: '🍒', bell: '🔔', lemon: '🍋',
            diamond: '💎', star: '⭐', gem: '💠', coin: '🪙', wild: '⭐',
            neon: '🌃', bolt: '⚡', chip: '💾', wave: '〰️', dot: '🔵',
            sun: '☀️', moon: '🌙', comet: '☄️', orbit: '🪐', void: '🕳️',
            sword: '⚔️', shield: '🛡️', crown: '👑', banner: '🚩', skull: '💀',
            chest: '🧰', map: '🗺️', anchor: '⚓', rum: '🍾', parrot: '🦜',
            mega7: '7️⃣', fire: '🔥', gold: '🥇', blank: '⬜',
            ankh: '☥', scarab: '🪲', eye: '👁️', pyramid: '🔺', sand: '🏜️',
            pearl: '🔮', whale: '🐋', coral: '🪸', fish: '🐠', shell: '🐚',
            fairy: '🧚', mushroom: '🍄', owl: '🦉', leaf: '🍃', acorn: '🌰'
        };
        return fallbacks[sym] || sym || '?';
    }

    function slotDomId(slotId) {
        return String(slotId).replace(/[^a-z0-9_-]/gi, '-');
    }

    function getSlotMeta(slotId) {
        for (var i = 0; i < slotCatalog.length; i++) {
            if (slotCatalog[i].id === slotId) return slotCatalog[i];
        }
        return { id: slotId, reels: 3 };
    }

    function slotThemeStyle(slot) {
        if (!slot) return '';
        var parts = [];
        if (slot.theme_color) parts.push('--slot-theme:' + slot.theme_color);
        if (slot.accent) parts.push('--slot-accent:' + slot.accent);
        if (slot.glow_color) parts.push('--slot-glow:' + slot.glow_color);
        return parts.length ? ' style="' + parts.join(';') + '"' : '';
    }

    function computeNearMissPositions(reels) {
        if (!reels || reels.length !== 3) return [];
        if (reels[0] === reels[1] && reels[0] !== reels[2]) return [0, 1];
        if (reels[1] === reels[2] && reels[1] !== reels[0]) return [1, 2];
        if (reels[0] === reels[2] && reels[0] !== reels[1]) return [0, 2];
        return [];
    }

    function scatterPositions(reels, scatterSym) {
        if (!scatterSym || !reels) return [];
        var pos = [];
        reels.forEach(function (sym, idx) {
            if (sym === scatterSym) pos.push(idx);
        });
        return pos;
    }

    function renderSlotReels(containerId, reels, symbolDisplay, winPositions, nearMissPositions, scatterPos) {
        const el = $(containerId);
        if (!el) return;
        var wins = winPositions || [];
        var near = nearMissPositions || [];
        var scat = scatterPos || [];
        var count = (reels && reels.length) ? reels.length : 3;
        el.classList.remove('reels-3', 'reels-4', 'reels-5');
        el.classList.add('reels-' + Math.min(5, Math.max(3, count)));
        el.innerHTML = '';
        (reels || Array(count).fill('?')).forEach(function (sym, idx) {
            const reel = document.createElement('div');
            reel.className = 'casino-slot-reel';
            if (wins.indexOf(idx) >= 0) reel.classList.add('win');
            if (near.indexOf(idx) >= 0) reel.classList.add('near-miss');
            if (scat.indexOf(idx) >= 0) reel.classList.add('scatter-hit');
            const track = document.createElement('div');
            track.className = 'casino-slot-reel-track';
            const inner = document.createElement('span');
            inner.className = 'casino-slot-reel-symbol';
            inner.textContent = sym === '?' ? '❓' : displaySymbol(sym, symbolDisplay);
            track.appendChild(inner);
            reel.appendChild(track);
            el.appendChild(reel);
        });
    }

    function spinPlaceholder(containerId, reelCount) {
        var n = reelCount || 3;
        var blanks = [];
        for (var i = 0; i < n; i++) blanks.push('?');
        renderSlotReels(containerId, blanks, {}, [], [], []);
    }

    function delay(ms) {
        return new Promise(function (resolve) { setTimeout(resolve, ms); });
    }

    function rafDelay(ms) {
        return new Promise(function (resolve) {
            var start = performance.now();
            function tick(now) {
                if (now - start >= ms) resolve();
                else requestAnimationFrame(tick);
            }
            requestAnimationFrame(tick);
        });
    }

    function isMobileSlot() {
        try { return window.matchMedia && window.matchMedia('(max-width: 640px)').matches; } catch (e) { return false; }
    }

    function spawnSlotParticles(machineEl, kind, intensity) {
        if (!machineEl || prefersReducedMotion()) return;
        var layer = machineEl.querySelector('.casino-slot-fx-layer');
        if (!layer) return;
        var count = (intensity === 'mega' ? 28 : intensity === 'big' ? 16 : 8) * (isMobileSlot() ? 0.5 : 1);
        count = Math.max(4, Math.round(count));
        var coins = kind === 'coins';
        for (var i = 0; i < count; i++) {
            var p = document.createElement('span');
            p.className = coins ? 'casino-slot-coin' : 'casino-slot-confetti';
            p.textContent = coins ? '🪙' : ['✨', '⭐', '💫', '🎉'][i % 4];
            p.style.left = (10 + Math.random() * 80) + '%';
            p.style.animationDelay = (Math.random() * 0.35) + 's';
            p.style.animationDuration = (0.7 + Math.random() * 0.6) + 's';
            layer.appendChild(p);
            setTimeout(function (node) {
                if (node.parentNode) node.parentNode.removeChild(node);
            }, 1600, p);
        }
    }

    function flashWinLine(machineEl) {
        if (!machineEl || prefersReducedMotion()) return;
        var line = machineEl.querySelector('.casino-slot-win-line');
        if (!line) return;
        line.classList.add('active');
        setTimeout(function () { line.classList.remove('active'); }, 900);
    }

    function pulseSlotCabinet(machineEl, tier) {
        if (!machineEl) return;
        machineEl.classList.remove('slot-win-pulse', 'slot-mega-pulse', 'slot-scatter-pulse', 'slot-near-pulse');
        if (tier === 'mega') machineEl.classList.add('slot-mega-pulse');
        else if (tier === 'scatter') machineEl.classList.add('slot-scatter-pulse');
        else if (tier === 'near') machineEl.classList.add('slot-near-pulse');
        else machineEl.classList.add('slot-win-pulse');
        setTimeout(function () {
            machineEl.classList.remove('slot-win-pulse', 'slot-mega-pulse', 'slot-scatter-pulse', 'slot-near-pulse');
        }, tier === 'mega' ? 2200 : 1400);
    }

    async function animateSlotSpin(containerId, finalReels, symbolDisplay, details) {
        const el = $(containerId);
        if (!el) return;
        details = details || {};
        var winPositions = details.win_positions || [];
        var nearMiss = details.near_miss ? computeNearMissPositions(finalReels) : [];
        var scatPos = details.scatter_bonus ? scatterPositions(finalReels, details.scatter_symbol) : [];
        var machineEl = el.closest('.casino-slot-machine');

        if (prefersReducedMotion()) {
            renderSlotReels(containerId, finalReels, symbolDisplay, winPositions, nearMiss, scatPos);
            if (winPositions.length) flashWinLine(machineEl);
            return;
        }

        const pool = Object.values(symbolDisplay || {});
        const flicker = pool.length ? pool : SLOT_FLICKER_DEFAULT;
        const reelCount = (finalReels || []).length || 3;
        renderSlotReels(containerId, Array(reelCount).fill('?'), symbolDisplay, [], [], []);
        const cols = el.querySelectorAll('.casino-slot-reel');
        if (!cols.length) return;

        if (machineEl) machineEl.classList.add('is-spinning');
        var baseDuration = 900 + reelCount * 80;
        var stagger = 280;
        var stopped = {};
        var lastTick = 0;
        var startTime = performance.now();
        var spinSoundAt = 0;

        await new Promise(function (resolve) {
            function frame(now) {
                var elapsed = now - startTime;
                var allDone = true;
                cols.forEach(function (col, idx) {
                    var stopAt = baseDuration + idx * stagger;
                    if (stopped[idx]) {
                        return;
                    }
                    allDone = false;
                    if (elapsed >= stopAt) {
                        stopped[idx] = true;
                        col.classList.remove('spinning');
                        col.classList.add('stopping');
                        var symEl = col.querySelector('.casino-slot-reel-symbol');
                        if (symEl) {
                            symEl.textContent = displaySymbol(finalReels[idx], symbolDisplay);
                        }
                        playSound('stop');
                        setTimeout(function (c) {
                            c.classList.remove('stopping');
                            c.classList.add('landed');
                            setTimeout(function (cc) { cc.classList.remove('landed'); }, 320);
                        }, 280, col);
                        return;
                    }
                    col.classList.add('spinning');
                    var tick = Math.floor(elapsed / 55);
                    if (tick !== lastTick && idx === 0) {
                        lastTick = tick;
                        if (now - spinSoundAt > 95) {
                            playSound('spin');
                            spinSoundAt = now;
                        }
                    }
                    var symEl = col.querySelector('.casino-slot-reel-symbol');
                    if (symEl) symEl.textContent = flicker[(tick + idx * 3) % flicker.length];
                });
                if (allDone) {
                    resolve();
                } else {
                    requestAnimationFrame(frame);
                }
            }
            requestAnimationFrame(frame);
        });

        if (machineEl) machineEl.classList.remove('is-spinning');
        renderSlotReels(containerId, finalReels, symbolDisplay, winPositions, nearMiss, scatPos);

        if (winPositions.length) {
            flashWinLine(machineEl);
            await rafDelay(120);
        }
        if (nearMiss.length) {
            var nearCols = el.querySelectorAll('.casino-slot-reel');
            nearCols.forEach(function (c, i) {
                if (nearMiss.indexOf(i) >= 0) c.classList.add('near-miss-tease');
            });
            await rafDelay(500);
            el.querySelectorAll('.near-miss-tease').forEach(function (c) { c.classList.remove('near-miss-tease'); });
        }
    }

    function celebrateSlotOutcome(data, slotId) {
        if (!data || !data.success) return;
        var dom = slotDomId(slotId);
        var machineEl = document.querySelector('.casino-slot-machine[data-slot-id="' + slotId + '"]');
        var det = data.details || {};
        var bet = Number(data.bet || 0);
        var payout = Number(data.payout || 0);
        var multiple = bet > 0 ? payout / bet : Number(det.multiplier || 0);

        if (det.match === 'jackpot' || det.scatter_bonus) {
            playSound(det.match === 'jackpot' ? 'jackpot' : 'scatter');
            pulseSlotCabinet(machineEl, det.match === 'jackpot' ? 'mega' : 'scatter');
            spawnSlotParticles(machineEl, 'confetti', 'big');
        }
        if (det.near_miss && data.outcome !== 'win') {
            pulseSlotCabinet(machineEl, 'near');
            playSound('tick');
        }
        if (data.outcome === 'win') {
            if (multiple >= 10) {
                spawnSlotParticles(machineEl, 'coins', 'mega');
                pulseSlotCabinet(machineEl, 'mega');
            } else if (multiple >= 3) {
                spawnSlotParticles(machineEl, 'coins', 'big');
                pulseSlotCabinet(machineEl, 'win');
            } else if (winPositionsFromDetails(det).length) {
                playSound('win');
                spawnSlotParticles(machineEl, 'confetti', 'small');
            }
        }
    }

    function winPositionsFromDetails(det) {
        return det.win_positions || [];
    }

    function volatilityClass(v) {
        var map = { low: 'vol-low', medium: 'vol-med', high: 'vol-high', extreme: 'vol-extreme' };
        return map[(v || '').toLowerCase()] || 'vol-med';
    }

    function buildSlotMachineCard(slot) {
        var sid = slot.id;
        var dom = slotDomId(sid);
        var reelN = slot.reels || 3;
        var reelCls = 'reels-' + Math.min(5, Math.max(3, reelN));
        return '<article class="casino-slot-machine" data-slot-id="' + sid + '" data-slot="' + sid + '"' + slotThemeStyle(slot) + '>' +
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
            '<div class="casino-slot-win-line" aria-hidden="true"></div>' +
            '<div id="slot-reels-' + dom + '" class="casino-slot-reels ' + reelCls + '"></div>' +
            '<div class="casino-slot-fx-layer" aria-hidden="true"></div>' +
            '</div>' +
            '<div class="casino-controls">' +
            '<input id="slot-bet-' + dom + '" type="number" min="5" max="500" value="25" aria-label="' + (slot.label || sid) + ' bet">' +
            '<button type="button" class="casino-slot-spin-btn" data-slot-id="' + sid + '"><span class="casino-slot-spin-label">Spin</span></button>' +
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
                reels: g.reels || 3,
                symbol_display: g.symbol_display || {},
                has_wild: !!(g.has_wild || (g.wild_symbols && g.wild_symbols.length)),
                has_scatter: !!(g.has_scatter || g.scatter_symbol),
                scatter_symbol: g.scatter_symbol,
                jackpot_symbol: g.jackpot_symbol,
                jackpot_multiplier: g.jackpot_multiplier,
                theme_color: g.theme_color,
                accent: g.accent,
                glow_color: g.glow_color,
            };
        });
    }

    function bindSlotSpinButtons(grid) {
        grid.querySelectorAll('.casino-slot-spin-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                playSlot(btn.getAttribute('data-slot-id'));
            });
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
            spinPlaceholder('slot-reels-' + slotDomId(slot.id), slot.reels || 3);
        });
        bindSlotSpinButtons(grid);
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
                    spinPlaceholder('slot-reels-' + slotDomId(slot.id), slot.reels || 3);
                });
                bindSlotSpinButtons(grid);
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
        var meta = getSlotMeta(slotId);
        var dom = slotDomId(slotId);
        var reelsId = 'slot-reels-' + dom;
        var resultId = 'slot-result-' + dom;
        var betInput = $('slot-bet-' + dom);
        var btn = document.querySelector('.casino-slot-spin-btn[data-slot-id="' + slotId + '"]');
        var machineEl = document.querySelector('.casino-slot-machine[data-slot-id="' + slotId + '"]');
        if (btn) {
            btn.disabled = true;
            btn.classList.add('spinning');
        }
        spinPlaceholder(reelsId, meta.reels || 3);
        var reelEl = $(reelsId);
        if (reelEl && !prefersReducedMotion()) {
            reelEl.querySelectorAll('.casino-slot-reel').forEach(function (c) { c.classList.add('spinning'); });
        }
        playSound('spin');

        const data = await api('/api/casino/play/slot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(betPayload({
                slot_id: slotId,
                bet: parseFloat(betInput ? betInput.value : 25),
            })),
        });

        if (data.success && data.details) {
            var det = data.details;
            if (!det.scatter_symbol && meta.scatter_symbol) det.scatter_symbol = meta.scatter_symbol;
            await animateSlotSpin(reelsId, det.reels || [], det.symbol_display || {}, det);
            celebrateSlotOutcome(data, slotId);
        } else {
            spinPlaceholder(reelsId, meta.reels || 3);
        }
        setResult($(resultId), data);
        showDoubleOffer(data);
        await afterPlay();
        if (btn) {
            btn.disabled = false;
            btn.classList.remove('spinning');
        }
        if (machineEl) machineEl.classList.remove('is-spinning');
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
        var networkLabel = '';
        try {
            var gst = await api('/api/casino/global/stats', null, 6000);
            if (gst.success && gst.hub_id) {
                networkLabel = '<span class="casino-jackpot-network">🌐 ' +
                    (gst.network_label || 'Network') + ' · ' + (gst.totals && gst.totals.bets != null ? gst.totals.bets + ' bets' : 'live') +
                    '</span>';
            }
        } catch (e) { /* optional */ }
        el.innerHTML = parts.join('<span class="casino-jackpot-sep">·</span>') + networkLabel;
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
        if (activityFeedEventSource) return;
        var track = $('casino-ticker-track');
        if (!track) return;
        var data = await api('/api/casino/activity-feed?limit=12', null, 8000);
        if (!data.success || !(data.feed || []).length) {
            track.innerHTML = '<span class="casino-ticker-item">Be the first big win today…</span>';
            return;
        }
        renderActivityFeedItems(data.feed);
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

    // -- Blackjack / Baccarat / Video Poker / Duels / Progression ------------
    var bj = { roundId: null, active: false };
    var vp = { roundId: null, hold: [] };

    function setBjControls(active) {
        bj.active = active;
        ['bj-hit', 'bj-stand', 'bj-double'].forEach(function (id) {
            var el = $(id); if (el) el.disabled = !active;
        });
        var d = $('bj-deal'); if (d) d.disabled = active;
    }

    async function dealBlackjack() {
        var bet = parseFloat(($('bj-bet') || {}).value || 25);
        var data = await api('/api/casino/play/blackjack', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, bet: bet, currency: activeCurrency }),
        });
        if (!data.success) { $('bj-result') && ($('bj-result').textContent = data.error || 'Failed'); return; }
        if (data.bet_id) { setResult($('bj-result'), data); await afterPlay(); return; }
        bj.roundId = data.round_id;
        $('bj-player') && ($('bj-player').textContent = (data.player || []).join(' ') + ' (' + (data.player_value || '?') + ')');
        $('bj-dealer') && ($('bj-dealer').textContent = 'Dealer: ' + (data.dealer_up || '?'));
        setBjControls(true);
        $('bj-result') && ($('bj-result').textContent = '');
    }

    async function bjAction(path) {
        if (!bj.roundId) return;
        var data = await api(path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, round_id: bj.roundId }),
        });
        if (!data.success) { $('bj-result') && ($('bj-result').textContent = data.error || 'Failed'); return; }
        if (data.player) $('bj-player') && ($('bj-player').textContent = data.player.join(' ') + (data.player_value != null ? ' (' + data.player_value + ')' : ''));
        if (data.dealer) $('bj-dealer') && ($('bj-dealer').textContent = 'Dealer: ' + data.dealer.join(' ') + (data.dealer_value != null ? ' (' + data.dealer_value + ')' : ''));
        if (data.bet_id || data.outcome) {
            setResult($('bj-result'), data);
            bj.roundId = null; setBjControls(false);
            try { maybeCelebrate(data); } catch (e) { /* optional */ }
            await afterPlay();
        }
    }

    async function playBaccarat() {
        var bet = parseFloat(($('baccarat-bet') || {}).value || 25);
        var side = ($('baccarat-side') || {}).value || 'player';
        var data = await api('/api/casino/play/baccarat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, bet: bet, side: side, currency: activeCurrency }),
        });
        setResult($('baccarat-result'), data);
        if (data.success) { try { maybeCelebrate(data); } catch (e) { /* optional */ } await afterPlay(); }
    }

    function renderVpHold(hand) {
        var el = $('vp-hold');
        if (!el || !hand) return;
        el.innerHTML = hand.map(function (c, i) {
            return '<label><input type="checkbox" class="vp-hold-cb" value="' + i + '"> Hold ' + c + '</label>';
        }).join(' ');
    }

    async function dealVideoPoker() {
        var bet = parseFloat(($('vp-bet') || {}).value || 25);
        var data = await api('/api/casino/play/video-poker', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, bet: bet, currency: activeCurrency }),
        });
        if (!data.success) { setResult($('vp-result'), data); return; }
        vp.roundId = data.round_id;
        $('vp-hand') && ($('vp-hand').textContent = (data.hand || []).join(' '));
        renderVpHold(data.hand);
        var dr = $('vp-draw'); if (dr) dr.disabled = false;
        var de = $('vp-deal'); if (de) de.disabled = true;
        $('vp-result') && ($('vp-result').textContent = '');
    }

    async function drawVideoPoker() {
        if (!vp.roundId) return;
        var hold = [];
        document.querySelectorAll('.vp-hold-cb:checked').forEach(function (cb) { hold.push(parseInt(cb.value, 10)); });
        var data = await api('/api/casino/play/video-poker/draw', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, round_id: vp.roundId, hold: hold }),
        });
        setResult($('vp-result'), data);
        vp.roundId = null;
        var dr = $('vp-draw'); if (dr) dr.disabled = true;
        var de = $('vp-deal'); if (de) de.disabled = false;
        if (data.success) { try { maybeCelebrate(data); } catch (e) { /* optional */ } await afterPlay(); }
    }

    async function refreshDuels() {
        var el = $('duel-open-list');
        if (!el) return;
        var data = await api('/api/casino/duels?status=open');
        if (!data.success || !(data.duels || []).length) {
            el.textContent = 'No open duels — create one!';
            return;
        }
        el.innerHTML = data.duels.map(function (d) {
            return '<div class="casino-duel-row">' + d.game + ' · ' + d.bet + ' ' + currencyLabel(d.currency) +
                ' <button type="button" class="duel-accept-btn" data-id="' + d.duel_id + '">Accept</button></div>';
        }).join('');
        el.querySelectorAll('.duel-accept-btn').forEach(function (btn) {
            btn.addEventListener('click', function () { acceptDuel(btn.getAttribute('data-id')); });
        });
    }

    async function createDuel() {
        var game = ($('duel-game') || {}).value || 'coin_flip';
        var choice = ($('duel-choice') || {}).value || 'heads';
        if (game === 'rps') {
            choice = prompt('Pick rock, paper, or scissors', 'rock') || 'rock';
        } else if (game === 'dice') {
            choice = prompt('Pick high or low', 'high') || 'high';
        }
        var data = await api('/api/casino/duels/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, bet: parseFloat(($('duel-bet') || {}).value || 25), game: game, choice: choice, currency: activeCurrency }),
        });
        setResult($('duel-result'), data);
        if (data.success) await refreshDuels();
    }

    async function acceptDuel(duelId) {
        var gameEl = $('duel-game');
        var game = gameEl ? gameEl.value : 'coin_flip';
        var choice = ($('duel-choice') || {}).value || 'tails';
        if (game === 'rps') choice = prompt('Pick rock, paper, or scissors', 'rock') || 'rock';
        else if (game === 'dice') choice = prompt('Pick high or low (opposite of challenger)', 'low') || 'low';
        else choice = choice === 'heads' ? 'tails' : 'heads';
        var data = await api('/api/casino/duels/accept', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, duel_id: duelId, choice: choice }),
        });
        setResult($('duel-result'), data);
        if (data.success) { await refreshDuels(); await afterPlay(); }
    }

    async function refreshProgression() {
        var el = $('casino-progression');
        if (!el) return;
        var data = await api('/api/casino/progression?user_id=' + encodeURIComponent(userId));
        if (!data.success) { el.textContent = 'Progression unavailable.'; return; }
        var xp = data.xp || {};
        var vip = data.vip || {};
        el.innerHTML = '<div class="casino-prog-row">' + (vip.badge || '') + ' ' + (vip.label || 'Bronze') +
            ' · Level ' + (xp.level || 1) + ' ' + (xp.title || '') + '</div>' +
            '<div class="casino-prog-row">XP ' + Math.round(xp.xp || 0) +
            (xp.next_level_xp ? ' / ' + xp.next_level_xp : '') + '</div>';
    }

    async function spinDailyWheel() {
        var data = await api('/api/casino/daily-wheel/spin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId }),
        });
        if (data.success) showToast('Daily wheel: ' + (data.label || data.coins_awarded + ' coins'));
        else showToast(data.error || 'Wheel unavailable');
        await refreshProgression();
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
        return '<div class="casino-tourney' + (t.status === 'ended' ? ' ended' : '') + '">' + lines.join('') + '</div>';
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

    async function initCasino() {
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
        bindClick('bj-deal', dealBlackjack);
        bindClick('bj-hit', function () { bjAction('/api/casino/play/blackjack/hit'); });
        bindClick('bj-stand', function () { bjAction('/api/casino/play/blackjack/stand'); });
        bindClick('bj-double', function () { bjAction('/api/casino/play/blackjack/double'); });
        bindClick('baccarat-play', playBaccarat);
        bindClick('vp-deal', dealVideoPoker);
        bindClick('vp-draw', drawVideoPoker);
        bindClick('duel-create', createDuel);
        bindClick('casino-daily-wheel', spinDailyWheel);
        bindChange('duel-game', function () {
            var g = ($('duel-game') || {}).value;
            var sel = $('duel-choice');
            if (!sel) return;
            if (g === 'rps') sel.innerHTML = '<option value="rock">Rock</option><option value="paper">Paper</option><option value="scissors">Scissors</option>';
            else if (g === 'dice') sel.innerHTML = '<option value="high">High (4-6)</option><option value="low">Low (1-3)</option>';
            else sel.innerHTML = '<option value="heads">Heads</option><option value="tails">Tails</option>';
        });
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
        bindClick('casino-share-win-btn', shareCasinoWin);
        bindClick('casino-share-site-btn', shareCasinoSite);
        bindClick('casino-share-whatsapp-btn', shareViaWhatsApp);
        bindClick('casino-share-x-thread-btn', shareXThread);
        bindClick('casino-copy-referral-code', copyReferralCode);
        bindClick('casino-copy-referral-link', copyReferralLink);
        bindChange('casino-share-wins-toggle', function () {
            toggleShareWins($('casino-share-wins-toggle').checked);
        });
        document.querySelectorAll('.casino-lb-period-tabs .casino-tab').forEach(function (tab) {
            tab.addEventListener('click', function () {
                document.querySelectorAll('.casino-lb-period-tabs .casino-tab').forEach(function (t) { t.classList.remove('active'); });
                tab.classList.add('active');
                leaderboardPeriod = tab.getAttribute('data-period') || 'today';
                refreshLeaderboard();
                refreshSocialBoard();
            });
        });
        document.querySelectorAll('.casino-lb-scope-tabs .casino-tab').forEach(function (tab) {
            tab.addEventListener('click', function () {
                document.querySelectorAll('.casino-lb-scope-tabs .casino-tab').forEach(function (t) { t.classList.remove('active'); });
                tab.classList.add('active');
                leaderboardScope = tab.getAttribute('data-lb-scope') || 'local';
                refreshLeaderboard();
            });
        });

        setTimeout(markStaleLoadingPanels, 15000);

        try { initMainTabNav(); } catch (e) { console.warn('[casino] tab nav failed:', e); }
        try { applyDeepLinks(); } catch (e) { console.warn('[casino] deep links failed:', e); }
        try { registerCasinoReferralFromUrl(); } catch (e) { /* optional */ }

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
        safeRefresh('bigWinHof', refreshBigWinHallOfFame);
        safeRefresh('slotOfDay', refreshSlotOfTheDay);
        safeRefresh('seasonalBadge', refreshSeasonalBadge);
        safeRefresh('vipLounge', refreshVipLounge);
        safeRefresh('homeAchievements', refreshHomeAchievements);
        safeRefresh('newsTicker', refreshNewsTicker);
        safeRefresh('rgBanner', refreshResponsibleGamingBanner);
        safeRefresh('houseStats', refreshHouseStats);
        safeRefresh('socialBoard', refreshSocialBoard);
        safeRefresh('depositPacks', refreshDepositPacks);
        safeRefresh('paypalReturn', handlePayPalReturn);
        safeRefresh('activityFeed', refreshActivityFeed);
        safeRefresh('jackpotMeter', refreshJackpotMeter);
        safeRefresh('tournaments', refreshTournaments);
        safeRefresh('progression', refreshProgression);
        safeRefresh('duels', refreshDuels);
        safeRefresh('fairness', refreshFairnessState);
        try { drawCrashCurve(1.0, false); } catch (e) { /* canvas optional */ }
        try { drawPlinkoBoard(null, null); } catch (e) { /* canvas optional */ }
        try { drawWheel(wheel.rotation, -1); } catch (e) { /* canvas optional */ }
        try { buildMinesGrid(); } catch (e) { /* grid optional */ }
        try { buildKenoGrid(); } catch (e) { /* grid optional */ }
        try { updateRouletteSelectionField(); } catch (e) { /* optional */ }
        setupFairnessExportLink();
        if (!startActivityFeedStream()) {
            setInterval(function () { safeRefresh('activityFeed', refreshActivityFeed); }, 15000);
        } else {
            safeRefresh('activityFeed', refreshActivityFeed);
        }
        setInterval(function () { safeRefresh('jackpotMeter', refreshJackpotMeter); }, 12000);
        setInterval(function () { safeRefresh('tournaments', refreshTournaments); }, 30000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCasino);
    } else {
        initCasino();
    }
})();
