/**
 * Frontpage interactive film monitor — canvas stage + prompt + play.
 * Uses /api/film-canvas/interactive-movie (plan → pipeline render).
 * Prompt extras: + face reference and 2–120s duration.
 */
(function () {
    'use strict';

    var pollTimer = null;
    var animFrame = null;
    var idle = true;
    var t0 = performance.now();
    var billing = null;
    var billingTimer = null;
    var faceDataUrl = null;
    var activeFx = null;
    var shopSfx = [];
    var shopSfxIndex = 0;
    var voiceReady = false;
    var TRIAL_KEY = 'fp_film_trial_id';
    var MIN_DURATION = 2;
    var MAX_DURATION = 120;
    var DEFAULT_DURATION = 8;
    var LIVE_FX_COUNT = 107;

    var FX_BACKGROUNDS = [
        'aurora', 'rain', 'grid', 'ember', 'plasma', 'fog',
        'signal', 'hex', 'glitch', 'ocean', 'chrome', 'violet',
    ];
    var FX_SOUNDS = [
        'harbour', 'storm', 'neon', 'drone', 'pulse', 'battle',
        'stars', 'focus', 'market', 'fog', 'chrome', 'rain',
        'ember', 'signal', 'ocean', 'voice_soft', 'voice_bright', 'voice_deep',
    ];
    var FX_EFFECT_FAMILIES = [
        'scan', 'sparks', 'rain', 'glitch', 'chromatic', 'hex', 'embers', 'streaks',
        'noise', 'bloom', 'ripple', 'shards', 'orbit', 'pulse', 'static', 'flare',
        'mist', 'beam', 'dust', 'wave', 'crack', 'veil', 'sparkle', 'trail',
        'echo', 'frost', 'heat', 'signal', 'pixel', 'drift',
    ];
    var FX_EFFECTS = (function buildFxCatalog() {
        var names = [];
        var i = 0;
        while (names.length < LIVE_FX_COUNT) {
            var family = FX_EFFECT_FAMILIES[i % FX_EFFECT_FAMILIES.length];
            var gen = Math.floor(i / FX_EFFECT_FAMILIES.length) + 1;
            names.push(family + '_' + (gen < 10 ? '0' : '') + gen);
            i += 1;
        }
        return names;
    })();
    var FX_PALETTES = [
        ['#00ff88', '#00b4ff', '#ff5078'],
        ['#7cf5ff', '#3d7cff', '#c8ff6a'],
        ['#ff9a3c', '#ff5e7a', '#ffe08a'],
        ['#b388ff', '#5eead4', '#f0abfc'],
        ['#94a3b8', '#38bdf8', '#e2e8f0'],
        ['#f97316', '#22d3ee', '#fde68a'],
        ['#34d399', '#818cf8', '#fda4af'],
        ['#67e8f9', '#a78bfa', '#fb7185'],
    ];
    var SHOP_SFX = [
        '/static/shop/sounds/shop-1.wav',
        '/static/shop/sounds/shop-4.wav',
        '/static/shop/sounds/shop-10.wav',
        '/static/shop/sounds/shop-15.wav',
        '/static/shop/sounds/shop-20.wav',
        '/static/shop/sounds/shop-25.wav',
        '/static/shop/sounds/shop-26.wav',
        '/static/shop/sounds/shop-27.wav',
        '/static/shop/sounds/shop-32.wav',
        '/static/shop/sounds/shop-33.wav',
        '/static/shop/sounds/shop-34.wav',
        '/static/shop/sounds/shop-35.wav',
        '/static/shop/sounds/shop-36.wav',
    ];

    function $(id) {
        return document.getElementById(id);
    }

    function getUserId() {
        try {
            if (window.MnUserId && typeof window.MnUserId.read === 'function') {
                return window.MnUserId.read() || '';
            }
            return localStorage.getItem('game_user_id')
                || localStorage.getItem('user_id')
                || '';
        } catch (_) {
            return '';
        }
    }

    function getTrialId() {
        try {
            var existing = localStorage.getItem(TRIAL_KEY);
            if (existing) return existing;
            var id = 'ft_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
            localStorage.setItem(TRIAL_KEY, id);
            return id;
        } catch (_) {
            return 'ft_guest';
        }
    }

    function formatRemaining(sec) {
        sec = Math.max(0, Number(sec) || 0);
        if (sec >= 3600) {
            var h = Math.floor(sec / 3600);
            var m = Math.floor((sec % 3600) / 60);
            return h + 'h ' + m + 'm';
        }
        if (sec >= 60) return Math.floor(sec / 60) + 'm';
        return sec + 's';
    }

    function renderBilling() {
        var banner = $('fp-film-pay-banner');
        var hint = $('fp-film-pay-hint');
        var pay = $('fp-film-pay');
        var mn2Label = $('fp-film-pay-mn2-label');
        var ppLabel = $('fp-film-pay-paypal-label');
        if (!billing) return;

        var pricing = billing.pricing || {};
        var mn2 = Number(pricing.price_mn2 || 0.5);
        var coins = Number(pricing.price_coins || Math.round(mn2 * 100));
        var usd = Number(pricing.price_usd || 1.99);
        var options = $('fp-film-pay-options');
        var freeProgram = !!(billing.always_free || billing.free_program);
        if (banner) {
            if (freeProgram) {
                banner.textContent = 'Free to use';
            } else if (billing.free_active) {
                banner.textContent = 'Free for the first 24 hours — '
                    + formatRemaining(billing.free_remaining_sec)
                    + ' left. After that: MN2 coins or PayPal.';
            } else if ((billing.credits || 0) > 0) {
                banner.textContent = 'Free window ended — '
                    + billing.credits
                    + ' play credit(s) left. Top up with MN2 coins or PayPal anytime.';
            } else {
                banner.textContent = 'Free window ended — choose MN2 coins or PayPal to play.';
            }
        }
        if (hint) {
            hint.textContent = billing.message
                || (freeProgram
                    ? 'Free film monitor — write a scene and press Play Movie. SND turns neural sound on.'
                    : 'Both options unlock 1 film play after the free window.');
        }
        if (pay) {
            pay.classList.toggle('fp-film-pay-free', freeProgram);
            pay.classList.toggle('is-locked', !freeProgram && !billing.can_play && !billing.free_active);
        }
        if (options) {
            if (freeProgram) {
                options.hidden = true;
                options.classList.add('is-hidden');
            } else {
                options.hidden = false;
                options.classList.remove('is-hidden');
                if (mn2Label) mn2Label.textContent = 'Pay ' + mn2 + ' MN2 (' + coins + ' coins)';
                if (ppLabel) ppLabel.textContent = 'Pay $' + usd.toFixed(2) + ' with PayPal';
            }
        }
    }

    async function refreshBilling() {
        try {
            var qs = new URLSearchParams();
            var uid = getUserId();
            var tid = getTrialId();
            if (uid) qs.set('user_id', uid);
            if (tid) qs.set('trial_id', tid);
            var r = await fetch('/api/film-canvas/billing?' + qs.toString());
            billing = await r.json();
            renderBilling();
        } catch (_) {
            if (!billing) {
                billing = {
                    free_active: true,
                    can_play: true,
                    free_remaining_sec: 24 * 3600,
                    pricing: { price_mn2: 0.5, price_coins: 50, price_usd: 1.99 },
                    message: 'Free for the first 24 hours — then MN2 coins or PayPal.',
                };
                renderBilling();
            }
        }
    }

    async function payWithMn2() {
        var uid = getUserId();
        if (!uid) {
            setStatus('Log in (Profile) to pay with MN2 coins.');
            window.location.href = '/profile';
            return;
        }
        setStatus('Charging MN2 coins…');
        try {
            var r = await fetch('/api/film-canvas/billing/pay-mn2', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: uid, trial_id: getTrialId() }),
            });
            var d = await r.json();
            if (!d || !d.success) {
                setStatus((d && d.error) || 'MN2 payment failed');
                if (d && d.code === 'ACCOUNT_REQUIRED') {
                    window.location.href = '/profile';
                }
                return;
            }
            billing = d.status || billing;
            renderBilling();
            setStatus(d.message || 'MN2 payment OK — play credit added.');
            await refreshBilling();
        } catch (err) {
            setStatus('MN2 pay error: ' + err);
        }
    }

    async function payWithPaypal() {
        var uid = getUserId();
        if (!uid) {
            setStatus('Log in (Profile) to pay with PayPal.');
            window.location.href = '/profile';
            return;
        }
        setStatus('Opening PayPal…');
        try {
            var r = await fetch('/api/film-canvas/billing/paypal-order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: uid, trial_id: getTrialId() }),
            });
            var d = await r.json();
            if (d && d.success && d.approve_url) {
                window.location.href = d.approve_url;
                return;
            }
            setStatus((d && d.error) || 'Could not start PayPal checkout');
            if (d && d.code === 'ACCOUNT_REQUIRED') {
                window.location.href = '/profile';
            }
        } catch (err) {
            setStatus('PayPal error: ' + err);
        }
    }

    async function handlePaypalReturn() {
        try {
            var params = new URLSearchParams(window.location.search);
            var flag = params.get('film_paypal');
            if (!flag) return;
            if (flag === 'cancel') {
                setStatus('PayPal checkout cancelled.');
                window.history.replaceState({}, '', window.location.pathname);
                return;
            }
            if (flag !== 'success') return;
            var token = params.get('token');
            var uid = params.get('user_id') || getUserId();
            if (!token) {
                setStatus('PayPal return missing order token.');
                return;
            }
            setStatus('Confirming PayPal payment…');
            var r = await fetch('/api/paypal/capture', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    order_id: token,
                    user_id: uid,
                    item_id: 'film-monitor-play',
                    item_name: 'Film monitor play credit',
                }),
            });
            var d = await r.json().catch(function () { return {}; });
            window.history.replaceState({}, '', window.location.pathname);
            if (d && (d.success || d.already_captured || d.item_granted)) {
                setStatus('PayPal unlocked 1 film play credit.');
                await refreshBilling();
            } else {
                setStatus((d && d.error) || 'PayPal capture failed');
            }
        } catch (err) {
            setStatus('PayPal return error: ' + err);
        }
    }

    function setStatus(text) {
        var el = $('fp-film-status');
        if (el) el.textContent = text || '';
    }

    function setReady(text, ok) {
        var el = $('fp-film-ready');
        if (!el) return;
        el.textContent = text || '';
        el.classList.toggle('is-ready', !!ok);
        el.classList.toggle('is-wait', !ok);
    }

    function setBusy(busy) {
        var play = $('fp-film-play');
        var go = $('fp-film-go');
        if (play) play.disabled = !!busy;
        if (go) go.disabled = !!busy;
        var monitor = $('fp-film-monitor');
        if (monitor) monitor.classList.toggle('is-busy', !!busy);
    }

    function setOverlay(html, show) {
        var overlay = $('fp-film-overlay');
        if (!overlay) return;
        if (html != null) overlay.innerHTML = html;
        overlay.style.display = show === false ? 'none' : '';
    }

    function soundLive() {
        if (document.body.classList.contains('mn-sound-active')) return true;
        var power = $('themeSoundToggle');
        return !!(power && power.getAttribute('aria-pressed') === 'true');
    }

    function hexToRgba(hex, alpha) {
        var h = String(hex || '#00ff88').replace('#', '');
        if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
        var r = parseInt(h.slice(0, 2), 16) || 0;
        var g = parseInt(h.slice(2, 4), 16) || 0;
        var b = parseInt(h.slice(4, 6), 16) || 0;
        return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
    }

    function pickLocalFxPack() {
        var salt = Math.floor(Math.random() * 1e9);
        var start = salt % FX_EFFECTS.length;
        var rotated = FX_EFFECTS.slice(start).concat(FX_EFFECTS.slice(0, start));
        return {
            background: FX_BACKGROUNDS[salt % FX_BACKGROUNDS.length],
            sound: FX_SOUNDS[(salt >> 3) % FX_SOUNDS.length],
            effects: rotated.slice(0, LIVE_FX_COUNT),
            live_count: LIVE_FX_COUNT,
            palette: FX_PALETTES[(salt >> 5) % FX_PALETTES.length].slice(),
            intensity: 0.45 + (salt % 18) / 100,
            sfx_bank: 'shop',
            voice_profile: [
                'performer_nova', 'performer_luna', 'performer_ember', 'performer_storm',
                'performer_velvet', 'performer_jade', 'performer_rio', 'performer_mist',
            ][salt % 8],
        };
    }

    function ensureShopSfx() {
        if (shopSfx.length) return;
        SHOP_SFX.forEach(function (src) {
            try {
                var audio = new Audio(src);
                audio.preload = 'auto';
                audio.volume = 0.28;
                shopSfx.push(audio);
            } catch (_) {}
        });
    }

    function playShopSfx() {
        ensureShopSfx();
        if (!shopSfx.length) return;
        var clip = shopSfx[shopSfxIndex % shopSfx.length];
        shopSfxIndex += 1;
        try {
            clip.currentTime = 0;
            clip.volume = 0.22 + Math.random() * 0.18;
            var p = clip.play();
            if (p && typeof p.catch === 'function') p.catch(function () {});
        } catch (_) {}
    }

    function ensureFilmVoice(profileId) {
        var voice = window.MNCamgirlsStreamVoice;
        if (!voice) return null;
        if (!voiceReady) {
            try {
                voice.init({
                    performersApi: '/api/camgirls/performers',
                });
                voice.setEnabled(true);
                voiceReady = true;
            } catch (_) {
                return null;
            }
        }
        if (profileId && typeof voice.setLeadSpeaker === 'function') {
            voice.setLeadSpeaker(profileId);
        }
        return voice;
    }

    function speakFilmLines(lines, profileId) {
        var voice = ensureFilmVoice(profileId);
        var textLines = Array.isArray(lines) ? lines.filter(Boolean) : [];
        if (!textLines.length) return;
        if (voice && typeof voice.speak === 'function') {
            textLines.forEach(function (line, idx) {
                try {
                    voice.speak(String(line).slice(0, 220), {
                        force: idx === 0,
                        queue: idx > 0,
                        rotate: idx > 0,
                    });
                } catch (_) {}
            });
            return;
        }
        // Fallback: browser speech with camgirl-like pitch profile.
        if (!window.speechSynthesis) return;
        try {
            window.speechSynthesis.cancel();
            textLines.forEach(function (line, idx) {
                var u = new SpeechSynthesisUtterance(String(line).slice(0, 220));
                u.rate = 0.95 + (idx % 3) * 0.04;
                u.pitch = 1.05 + (idx % 4) * 0.04;
                u.volume = 0.85;
                window.speechSynthesis.speak(u);
            });
        } catch (_) {}
    }

    function applyFxPack(pack, opts) {
        activeFx = pack && typeof pack === 'object' ? pack : pickLocalFxPack();
        if (!Array.isArray(activeFx.effects) || activeFx.effects.length < LIVE_FX_COUNT) {
            var local = pickLocalFxPack();
            var merged = (activeFx.effects || []).slice();
            local.effects.forEach(function (name) {
                if (merged.indexOf(name) === -1) merged.push(name);
            });
            activeFx.effects = merged.slice(0, LIVE_FX_COUNT);
        }
        activeFx.live_count = activeFx.effects.length;
        if (!Array.isArray(activeFx.palette) || activeFx.palette.length < 2) {
            activeFx.palette = FX_PALETTES[0].slice();
        }
        // Cap intensity so ambient FX never overpower the scene picture.
        var rawIntensity = Number(activeFx.intensity);
        if (!isFinite(rawIntensity)) rawIntensity = 0.5;
        activeFx.intensity = Math.max(0.35, Math.min(0.65, rawIntensity));
        var monitor = $('fp-film-monitor');
        if (monitor) {
            monitor.setAttribute('data-fx-bg', activeFx.background || 'aurora');
            monitor.setAttribute('data-fx-live', String(activeFx.live_count || LIVE_FX_COUNT));
            monitor.classList.add('is-fx-hot');
            if (opts && opts.playing) monitor.classList.add('is-playing');
            else if (!(opts && opts.keepPlaying)) monitor.classList.remove('is-playing');
            monitor.style.setProperty('--fx-a', activeFx.palette[0] || '#00ff88');
            monitor.style.setProperty('--fx-b', activeFx.palette[1] || '#00b4ff');
            monitor.style.setProperty('--fx-c', activeFx.palette[2] || '#ff5078');
        }
        var force = !!(opts && opts.forceSound);
        var snd = activeFx.sound;
        if (snd) {
            try {
                window.dispatchEvent(new CustomEvent('mn-film-fx-sound', {
                    detail: { sound: snd, forceStart: force || soundLive() },
                }));
            } catch (_) {}
            if (window.MnFrontpageSound && typeof window.MnFrontpageSound.applyFilmSound === 'function') {
                window.MnFrontpageSound.applyFilmSound(snd, force || soundLive());
            }
        }
        return activeFx;
    }

    function fxFamily(name) {
        var raw = String(name || '');
        var cut = raw.indexOf('_');
        return cut > 0 ? raw.slice(0, cut) : raw;
    }

    function fxHas(name) {
        if (!activeFx || !Array.isArray(activeFx.effects)) return false;
        if (activeFx.effects.indexOf(name) !== -1) return true;
        // Catalog uses family_01 style ids; match by family for drawing.
        var family = fxFamily(name);
        for (var i = 0; i < activeFx.effects.length; i++) {
            if (fxFamily(activeFx.effects[i]) === family) return true;
        }
        return false;
    }

    function drawFxOverlays(ctx, w, h, t, intensity, videoMode) {
        // Prompt/movie picture stays dominant. Overlays are accents only —
        // especially restrained while a finished clip is on screen.
        var pack = activeFx || pickLocalFxPack();
        var a = (pack.palette && pack.palette[0]) || '#00ff88';
        var b = (pack.palette && pack.palette[1]) || '#00b4ff';
        var c = (pack.palette && pack.palette[2]) || '#ff5078';
        var base = Math.max(0.35, Math.min(1.0, intensity || pack.intensity || 0.55));
        var dens = videoMode ? base * 0.28 : base * 0.72;
        var hot = soundLive();
        var mult = (!videoMode && hot) ? 1.15 : 1;

        if (fxHas('scan') || !activeFx) {
            var scanY = ((t * (70 * dens * mult + 40)) % (h + 50)) - 25;
            ctx.fillStyle = hexToRgba(a, (videoMode ? 0.035 : 0.07) * dens * mult);
            ctx.fillRect(0, scanY, w, videoMode ? 8 : (10 + 10 * dens));
            if (!videoMode) {
                var scanY2 = ((t * (50 * dens) + h * 0.4) % (h + 40)) - 20;
                ctx.fillStyle = hexToRgba(b, 0.04 * dens);
                ctx.fillRect(0, scanY2, w, 6);
            }
        }

        if (!videoMode && (fxHas('sparks') || fxHas('orbit'))) {
            var n = Math.floor(16 * dens * mult);
            for (var i = 0; i < n; i++) {
                var px = (Math.sin(t * 1.6 + i * 1.17) * 0.5 + 0.5) * w;
                var py = (Math.cos(t * 1.1 + i * 0.83) * 0.5 + 0.5) * h;
                ctx.fillStyle = hexToRgba(i % 2 ? a : b, 0.1 + (i % 5) * 0.025);
                ctx.beginPath();
                ctx.arc(px, py, 1.1 + (i % 3) * 0.6, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        if (!videoMode && fxHas('rain')) {
            ctx.strokeStyle = hexToRgba(b, 0.1 * dens);
            ctx.lineWidth = 1;
            var drops = Math.floor(22 * dens * mult);
            for (var d = 0; d < drops; d++) {
                var rx = ((d * 97 + t * 120) % (w + 40)) - 20;
                var ry = ((d * 53 + t * (180 + d % 40)) % (h + 60)) - 30;
                ctx.beginPath();
                ctx.moveTo(rx, ry);
                ctx.lineTo(rx + 1.5, ry + 8 + (d % 6));
                ctx.stroke();
            }
        }

        if (!videoMode && fxHas('embers')) {
            var em = Math.floor(14 * dens * mult);
            for (var e = 0; e < em; e++) {
                var ex = ((e * 61 + Math.sin(t + e) * 24) % w);
                var ey = h - ((t * (24 + e % 16) + e * 37) % (h + 40));
                ctx.fillStyle = hexToRgba(c, 0.1 + (e % 4) * 0.03);
                ctx.beginPath();
                ctx.arc(ex, ey, 1.2 + (e % 2), 0, Math.PI * 2);
                ctx.fill();
            }
        }

        if (!videoMode && fxHas('streaks')) {
            ctx.strokeStyle = hexToRgba(a, 0.07 * dens);
            ctx.lineWidth = 1;
            for (var s = 0; s < Math.floor(6 * dens * mult); s++) {
                var sy = ((s * 73 + t * 70) % h);
                ctx.beginPath();
                ctx.moveTo(0, sy);
                ctx.lineTo(w * (0.22 + (s % 4) * 0.08), sy + Math.sin(t + s) * 5);
                ctx.stroke();
            }
        }

        if (!videoMode && (fxHas('hex') || fxHas('grid'))) {
            ctx.strokeStyle = hexToRgba(a, 0.055 * dens);
            ctx.lineWidth = 1;
            var step = 28;
            for (var x = 0; x < w; x += step) {
                ctx.beginPath();
                ctx.moveTo(x + (t * 12) % step, 0);
                ctx.lineTo(x + (t * 12) % step, h);
                ctx.stroke();
            }
            for (var y = 0; y < h; y += step) {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(w, y);
                ctx.stroke();
            }
        }

        if (!videoMode && (fxHas('glitch') || fxHas('static'))) {
            for (var g = 0; g < Math.floor(4 * dens * mult); g++) {
                var gh = 1 + (g % 3);
                var gy = ((Math.sin(t * 5 + g) * 0.5 + 0.5) * h) | 0;
                ctx.fillStyle = hexToRgba(g % 2 ? c : a, 0.05 + (g % 3) * 0.02);
                ctx.fillRect(((t * 140 + g * 40) % w) - 12, gy, 18 + g * 5, gh);
            }
        }

        if (fxHas('chromatic') && videoMode) {
            ctx.globalCompositeOperation = 'screen';
            ctx.fillStyle = hexToRgba(c, 0.012 * dens);
            ctx.fillRect(1, 0, w, h);
            ctx.fillStyle = hexToRgba(b, 0.01 * dens);
            ctx.fillRect(-1, 0, w, h);
            ctx.globalCompositeOperation = 'source-over';
        }

        if (fxHas('bloom') || fxHas('flare')) {
            var gx = w * (0.4 + 0.15 * Math.sin(t * 0.45));
            var gy = h * (0.42 + 0.1 * Math.cos(t * 0.35));
            var grd = ctx.createRadialGradient(gx, gy, 10, gx, gy, w * (videoMode ? 0.22 : 0.32) * dens);
            grd.addColorStop(0, hexToRgba(a, (videoMode ? 0.04 : 0.1) * dens * mult));
            grd.addColorStop(0.55, hexToRgba(b, (videoMode ? 0.015 : 0.04) * dens));
            grd.addColorStop(1, 'rgba(0,0,0,0)');
            ctx.fillStyle = grd;
            ctx.fillRect(0, 0, w, h);
        }

        if (!videoMode && (fxHas('ripple') || fxHas('pulse_ring'))) {
            ctx.strokeStyle = hexToRgba(b, 0.08 * dens);
            ctx.lineWidth = 1;
            var rings = Math.floor(3 * dens * mult);
            for (var r = 0; r < rings; r++) {
                var rad = ((t * 28 + r * 32) % (Math.min(w, h) * 0.45));
                ctx.beginPath();
                ctx.arc(w * 0.5, h * 0.48, rad, 0, Math.PI * 2);
                ctx.stroke();
            }
        }

        if (!videoMode && fxHas('shards')) {
            ctx.fillStyle = hexToRgba(c, 0.06 * dens);
            for (var sh = 0; sh < Math.floor(7 * dens); sh++) {
                var sx = (Math.sin(t * 1.1 + sh) * 0.5 + 0.5) * w;
                var sy = (Math.cos(t * 0.8 + sh * 1.2) * 0.5 + 0.5) * h;
                ctx.beginPath();
                ctx.moveTo(sx, sy);
                ctx.lineTo(sx + 6 + (sh % 4), sy + 1);
                ctx.lineTo(sx + 2, sy + 7 + (sh % 3));
                ctx.closePath();
                ctx.fill();
            }
        }

        if (!videoMode && fxHas('noise')) {
            for (var n2 = 0; n2 < Math.floor(28 * dens * mult); n2++) {
                ctx.fillStyle = hexToRgba(n2 % 2 ? a : '#ffffff', 0.025);
                ctx.fillRect(Math.random() * w, Math.random() * h, 1.2, 1.2);
            }
        }

        // Soft edge vignette so the scene center (prompt picture) stays clearest.
        if (videoMode) {
            var vig = ctx.createRadialGradient(w * 0.5, h * 0.5, w * 0.28, w * 0.5, h * 0.5, w * 0.72);
            vig.addColorStop(0, 'rgba(0,0,0,0)');
            vig.addColorStop(1, 'rgba(0,0,0,0.18)');
            ctx.fillStyle = vig;
            ctx.fillRect(0, 0, w, h);
        }
    }

    function drawIdle(canvas, ctx, now) {
        var w = canvas.width;
        var h = canvas.height;
        var t = (now - t0) / 1000;
        var hot = soundLive();
        var pack = activeFx || { palette: ['#00ff88', '#00b4ff', '#ff5078'], intensity: 0.75 };
        var a = pack.palette[0] || '#00ff88';
        var bCol = pack.palette[1] || '#00b4ff';

        ctx.fillStyle = '#020805';
        ctx.fillRect(0, 0, w, h);

        var g = ctx.createRadialGradient(w * 0.5, h * 0.45, 20, w * 0.5, h * 0.5, w * 0.62);
        g.addColorStop(0, hexToRgba(a, hot ? 0.3 : 0.18));
        g.addColorStop(0.45, hexToRgba(bCol, hot ? 0.16 : 0.07));
        g.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, w, h);

        drawFxOverlays(ctx, w, h, t, (pack.intensity || 0.55) * (hot ? 1.05 : 0.85), false);

        ctx.fillStyle = hexToRgba(a, 0.7);
        ctx.font = '600 22px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';
        ctx.textAlign = 'center';
        var label = hot ? 'FILM CANVAS · SOUND LIVE' : 'FILM CANVAS · STANDBY';
        if (activeFx && activeFx.background) {
            label = 'FILM · ' + String(activeFx.background).toUpperCase()
                + (activeFx.sound ? (' · ' + String(activeFx.sound).toUpperCase()) : '');
        }
        ctx.fillText(label, w / 2, h / 2 - 8);
        ctx.font = '400 14px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';
        ctx.fillStyle = hexToRgba(bCol, 0.5);
        var fxCount = activeFx && activeFx.effects ? activeFx.effects.length : 0;
        ctx.fillText(
            fxCount
                ? (fxCount + ' effects live · story + voice on play')
                : 'type a scene · press Play Movie',
            w / 2,
            h / 2 + 18
        );
    }

    function drawVideoFrame(canvas, ctx, video) {
        if (!video || video.readyState < 2) return;
        var cw = canvas.width;
        var ch = canvas.height;
        var vw = video.videoWidth || cw;
        var vh = video.videoHeight || ch;
        var scale = Math.max(cw / vw, ch / vh);
        var dw = vw * scale;
        var dh = vh * scale;
        var dx = (cw - dw) / 2;
        var dy = (ch - dh) / 2;
        ctx.drawImage(video, dx, dy, dw, dh);
        var t = performance.now() / 1000;
        var intensity = (activeFx && activeFx.intensity) || 0.45;
        // Keep overlays soft so the prompt-driven picture reads first.
        drawFxOverlays(ctx, cw, ch, t, Math.min(0.55, intensity), true);
    }

    function loop() {
        var canvas = $('fp-film-canvas');
        if (!canvas) return;
        var ctx = canvas.getContext('2d');
        if (!ctx) return;
        var video = $('fp-film-video');
        if (!idle && video && !video.paused && video.readyState >= 2) {
            drawVideoFrame(canvas, ctx, video);
        } else if (idle) {
            drawIdle(canvas, ctx, performance.now());
        }
        animFrame = requestAnimationFrame(loop);
    }

    function fitCanvas() {
        var canvas = $('fp-film-canvas');
        var screen = canvas && canvas.parentElement;
        if (!canvas || !screen) return;
        var rect = screen.getBoundingClientRect();
        var w = Math.max(320, Math.floor(rect.width));
        var h = Math.max(180, Math.floor(w * 9 / 16));
        if (canvas.width !== w || canvas.height !== h) {
            canvas.width = w;
            canvas.height = h;
        }
    }

    async function refreshReady() {
        try {
            var r = await fetch('/api/system/overview?compact=1');
            var d = await r.json();
            var rows = d.video_providers || [];
            var fal = rows.find(function (p) { return p.id === 'fal_krea'; });
            var drama = rows.find(function (p) { return p.id === 'dramacanva'; });
            var auto = rows.find(function (p) { return p.id === 'film_canvas_auto'; });
            var bits = [];
            bits.push(drama && drama.available ? 'DramaCanvas ready' : 'DramaCanvas offline');
            bits.push(fal && fal.available ? 'fal ready' : 'fal offline');
            if (auto && auto.available) {
                bits.push('auto ' + (auto.selected_renderer || '—') + '/' + (auto.selected_planner || '—'));
            }
            var ok = (fal && fal.available) || (drama && drama.available);
            setReady(bits.join(' · '), ok);

            var xp = $('fp-film-node-xp');
            var level = (((d.statistics || {}).level) || null);
            if (xp && level) {
                xp.textContent = 'Lv' + level;
                xp.title = 'Level ' + level + ' · XP & trophies';
            }
        } catch (err) {
            setReady('Canvas status unavailable', false);
        }
    }

    function syncSoundNode() {
        var snd = $('fp-film-node-snd');
        var kicker = $('fp-neural-kicker');
        var monitor = $('fp-film-monitor');
        var live = soundLive();
        if (snd) {
            snd.classList.toggle('is-live', live);
            snd.setAttribute('aria-pressed', live ? 'true' : 'false');
            snd.title = live ? 'Neural sound online — click to stop' : 'Neural sound offline — click to start';
        }
        if (monitor) monitor.classList.toggle('is-sound-live', live);
        if (kicker) {
            kicker.textContent = live ? 'Neural sound online' : 'Neural sound offline';
        }
    }

    function bindLegacyNodes() {
        var ai = $('fp-film-node-ai');
        var snd = $('fp-film-node-snd');
        if (ai) {
            ai.addEventListener('click', function () {
                var prompt = $('fp-film-prompt');
                if (prompt) prompt.focus();
                playMovie();
            });
        }
        if (snd) {
            snd.addEventListener('click', function () {
                var power = $('themeSoundToggle') || $('themeSoundFloatToggle');
                if (power) power.click();
                setTimeout(syncSoundNode, 80);
            });
        }
        ['themeSoundToggle', 'themeSoundFloatToggle'].forEach(function (id) {
            var el = $(id);
            if (el) el.addEventListener('click', function () { setTimeout(syncSoundNode, 80); });
        });
        syncSoundNode();
        setInterval(syncSoundNode, 1500);
    }

    function readDurationSec() {
        var el = $('fp-film-duration');
        var raw = el ? Number(el.value) : DEFAULT_DURATION;
        if (!isFinite(raw)) raw = DEFAULT_DURATION;
        return Math.max(MIN_DURATION, Math.min(MAX_DURATION, Math.round(raw)));
    }

    function syncDurationLabel() {
        var label = $('fp-film-duration-value');
        if (label) label.textContent = readDurationSec() + 's';
    }

    function setFacePreview(dataUrl, name) {
        faceDataUrl = dataUrl || null;
        var chip = $('fp-film-face-chip');
        var img = $('fp-film-face-preview');
        var label = $('fp-film-face-label');
        var addBtn = $('fp-film-face-add');
        if (img) img.src = dataUrl || '';
        if (label) label.textContent = name ? String(name).slice(0, 18) : 'Face added';
        if (chip) {
            chip.hidden = !dataUrl;
            chip.classList.toggle('is-hidden', !dataUrl);
        }
        if (addBtn) addBtn.classList.toggle('is-active', !!dataUrl);
    }

    function clearFace() {
        var input = $('fp-film-face-input');
        if (input) input.value = '';
        setFacePreview(null);
    }

    function setDownloadLink(url, xvidUrl) {
        var link = $('fp-film-download');
        var xvid = $('fp-film-download-xvid');
        function hide(el) {
            if (!el) return;
            el.removeAttribute('href');
            el.hidden = true;
            el.classList.add('is-hidden');
        }
        function show(el, href, filename) {
            if (!el || !href) {
                hide(el);
                return;
            }
            el.href = href;
            el.setAttribute('download', filename);
            el.hidden = false;
            el.classList.remove('is-hidden');
        }
        if (!url) {
            hide(link);
            hide(xvid);
            return;
        }
        var href = String(url);
        if (!/[?&]download=/.test(href)) {
            href = href.indexOf('?') >= 0 ? (href + '&download=1') : (href + '?download=1');
        }
        show(link, href, 'masternoder-movie.mp4');
        var xhref = xvidUrl ? String(xvidUrl) : (href + (href.indexOf('?') >= 0 ? '&' : '?') + 'format=xvid');
        if (xvidUrl || url) show(xvid, xhref, 'masternoder-movie.avi');
    }

    function compressFaceDataUrl(dataUrl, maxEdge, quality) {
        return new Promise(function (resolve, reject) {
            var img = new Image();
            img.onload = function () {
                try {
                    var w = img.naturalWidth || img.width || 1;
                    var h = img.naturalHeight || img.height || 1;
                    var edge = Math.max(w, h);
                    var scale = edge > maxEdge ? (maxEdge / edge) : 1;
                    var cw = Math.max(1, Math.round(w * scale));
                    var ch = Math.max(1, Math.round(h * scale));
                    var canvas = document.createElement('canvas');
                    canvas.width = cw;
                    canvas.height = ch;
                    var ctx = canvas.getContext('2d');
                    if (!ctx) {
                        resolve(dataUrl);
                        return;
                    }
                    ctx.drawImage(img, 0, 0, cw, ch);
                    var out = canvas.toDataURL('image/jpeg', quality);
                    // Keep shrinking until payload fits under nginx's common 1MB body limit.
                    var q = quality;
                    while (out.length > 700000 && q > 0.45) {
                        q -= 0.1;
                        out = canvas.toDataURL('image/jpeg', q);
                    }
                    if (out.length > 900000 && scale > 0.4) {
                        canvas.width = Math.max(1, Math.round(cw * 0.75));
                        canvas.height = Math.max(1, Math.round(ch * 0.75));
                        ctx = canvas.getContext('2d');
                        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                        out = canvas.toDataURL('image/jpeg', 0.65);
                    }
                    resolve(out);
                } catch (err) {
                    reject(err);
                }
            };
            img.onerror = function () { reject(new Error('Could not decode face image')); };
            img.src = dataUrl;
        });
    }

    function readFaceFile(file) {
        return new Promise(function (resolve, reject) {
            if (!file) {
                resolve(null);
                return;
            }
            if (!String(file.type || '').startsWith('image/')) {
                reject(new Error('Choose an image file for the face'));
                return;
            }
            if (file.size > 8 * 1024 * 1024) {
                reject(new Error('Face image must be under 8 MB'));
                return;
            }
            var reader = new FileReader();
            reader.onload = function () {
                compressFaceDataUrl(String(reader.result || ''), 768, 0.72)
                    .then(resolve)
                    .catch(reject);
            };
            reader.onerror = function () { reject(new Error('Could not read face image')); };
            reader.readAsDataURL(file);
        });
    }

    async function readJsonResponse(response) {
        var text = await response.text();
        var trimmed = (text || '').trim();
        if (!trimmed) {
            throw new Error('Empty response from server (' + response.status + ')');
        }
        if (trimmed.charAt(0) === '<') {
            if (response.status === 413) {
                throw new Error('Face image is too large for the server — try a smaller photo');
            }
            throw new Error(
                'Server returned a page instead of JSON (' + response.status + '). '
                + 'Hard-refresh and try again without a huge face photo.'
            );
        }
        try {
            return JSON.parse(trimmed);
        } catch (err) {
            throw new Error('Invalid JSON from server (' + response.status + ')');
        }
    }

    function bindFaceAndDuration() {
        var addBtn = $('fp-film-face-add');
        var input = $('fp-film-face-input');
        var clearBtn = $('fp-film-face-clear');
        var duration = $('fp-film-duration');
        if (addBtn && input) {
            addBtn.addEventListener('click', function () { input.click(); });
            input.addEventListener('change', function () {
                var file = input.files && input.files[0];
                if (!file) return;
                readFaceFile(file).then(function (dataUrl) {
                    setFacePreview(dataUrl, file.name);
                    setStatus('Face added to prompt');
                }).catch(function (err) {
                    clearFace();
                    setStatus(String(err.message || err));
                });
            });
        }
        if (clearBtn) clearBtn.addEventListener('click', clearFace);
        if (duration) {
            duration.addEventListener('input', syncDurationLabel);
            duration.addEventListener('change', syncDurationLabel);
            syncDurationLabel();
        }
    }

    async function playMovie() {
        var promptEl = $('fp-film-prompt');
        var video = $('fp-film-video');
        var durationSec = readDurationSec();
        var prompt = ((promptEl && promptEl.value) || '').trim()
            || (promptEl && promptEl.placeholder)
            || 'Cinematic control-room monitor film';
        if (faceDataUrl) {
            prompt = prompt.replace(/\s*\[face reference attached\]\s*/ig, ' ').trim();
            prompt = (prompt + ' [face reference attached]').trim();
        }

        if (pollTimer) {
            clearTimeout(pollTimer);
            pollTimer = null;
        }
        setBusy(true);
        idle = true;
        setDownloadLink(null);
        // Fresh background + sound + overlay pack on every play.
        applyFxPack(pickLocalFxPack(), { forceSound: soundLive() });
        playShopSfx();
        ensureFilmVoice(activeFx && activeFx.voice_profile);
        speakFilmLines([
            'Starting a new story for ' + prompt.slice(0, 90),
        ], activeFx && activeFx.voice_profile);
        var monitorStart = $('fp-film-monitor');
        if (monitorStart) monitorStart.classList.remove('is-playing');
        var canvasStart = $('fp-film-canvas');
        if (canvasStart) canvasStart.style.opacity = '1';
        if (video) {
            try { video.pause(); } catch (_) {}
            video.removeAttribute('src');
            video.removeAttribute('controls');
            video.load();
            video.style.opacity = '0';
            video.style.zIndex = '';
        }
        setOverlay(
            '<p class="fp-film-idle">Starting ' + durationSec + 's story movie…</p>',
            true
        );
        setStatus(
            'Starting ' + durationSec + 's movie'
            + (faceDataUrl ? ' with face reference' : '')
            + (activeFx && activeFx.live_count ? (' · ' + activeFx.live_count + ' fx live') : '')
            + (activeFx && activeFx.background ? (' · fx:' + activeFx.background) : '')
            + (activeFx && activeFx.sound ? (' · snd:' + activeFx.sound) : '')
            + '…'
        );

        try {
            if (
                billing
                && !billing.always_free
                && !billing.free_program
                && !billing.can_play
                && !billing.free_active
            ) {
                setStatus('Trial ended — pay with MN2 coins or PayPal first.');
                setOverlay('<p class="fp-film-idle">Payment required</p>', true);
                setBusy(false);
                var payBox = $('fp-film-pay');
                if (payBox) payBox.classList.add('is-locked');
                return;
            }
            var payload = {
                prompt: prompt,
                duration_sec: durationSec,
                user_id: getUserId(),
                trial_id: getTrialId(),
            };
            if (faceDataUrl) payload.face_image = faceDataUrl;
            var start = await fetch('/api/film-canvas/interactive-movie', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            var job = await readJsonResponse(start);
            if (start.status === 402 || (job && job.code === 'PAYMENT_REQUIRED')) {
                billing = job;
                renderBilling();
                setStatus((job && job.message) || 'Pay with MN2 coins or PayPal to continue.');
                setOverlay('<p class="fp-film-idle">Payment required</p>', true);
                setBusy(false);
                return;
            }
            if (!job || !job.job_id) {
                setStatus((job && job.error) || 'Could not start movie job');
                setOverlay('<p class="fp-film-idle">Start failed</p>', true);
                setBusy(false);
                return;
            }
            refreshBilling();
            setStatus('Job ' + job.job_id + ' — ' + (job.message || 'queued'));

            var poll = async function () {
                try {
                    var r = await fetch('/api/film-canvas/interactive-movie/' + job.job_id);
                    var d = await readJsonResponse(r);
                    if (!d || d.success === false) {
                        setStatus((d && d.error) || 'Job missing');
                        setBusy(false);
                        return;
                    }
                    var prog = d.progress != null ? d.progress + '% · ' : '';
                    setStatus(
                        prog + (d.message || d.status || '…')
                        + (d.planner ? ' · plan:' + d.planner : '')
                        + (d.renderer ? ' · render:' + d.renderer : '')
                    );
                    setOverlay(
                        '<p class="fp-film-idle">' + (d.message || d.status || 'Rendering…') + '</p>',
                        true
                    );

                    if (d.status === 'completed' && d.video_url && video) {
                        idle = false;
                        setOverlay('', false);
                        if (d.fx_pack) {
                            applyFxPack(d.fx_pack, { playing: true, forceSound: true });
                        } else {
                            applyFxPack(activeFx || pickLocalFxPack(), { playing: true, forceSound: true });
                        }
                        playShopSfx();
                        var voiceId = (d.fx_pack && d.fx_pack.voice_profile)
                            || (activeFx && activeFx.voice_profile);
                        var narrate = [];
                        if (d.story) narrate.push(String(d.story).slice(0, 280));
                        if (Array.isArray(d.narration) && d.narration.length) {
                            d.narration.slice(0, 8).forEach(function (line) {
                                narrate.push(String(line).slice(0, 180));
                            });
                        }
                        speakFilmLines(narrate, voiceId);
                        // Prefer the video element so the prompt picture stays sharp;
                        // canvas keeps only soft accents underneath when opacity allows.
                        video.style.opacity = '1';
                        video.style.zIndex = '2';
                        var canvasEl = $('fp-film-canvas');
                        if (canvasEl) canvasEl.style.opacity = '0.22';
                        video.setAttribute('controls', 'controls');
                        video.src = d.video_url + '?t=' + Date.now();
                        video.onloadeddata = function () {
                            video.play().catch(function () {});
                            playShopSfx();
                        };
                        video.ontimeupdate = function () {
                            // Occasional shop/cam-style one-shots while the strip plays.
                            if (!video._mnLastSfx) video._mnLastSfx = 0;
                            if (video.currentTime - video._mnLastSfx > 2.4) {
                                video._mnLastSfx = video.currentTime;
                                playShopSfx();
                            }
                        };
                        setDownloadLink(d.download_url || d.video_url, d.xvid_url);
                        var liveN = (d.fx_pack && d.fx_pack.live_count)
                            || (d.fx_pack && d.fx_pack.effects && d.fx_pack.effects.length)
                            || LIVE_FX_COUNT;
                        setStatus(
                            'Movie ready — ' + liveN + ' effects live'
                            + (d.duration_sec ? (' · ' + d.duration_sec + 's') : '')
                            + (d.beats ? (' · ' + d.beats + ' scenes') : '')
                            + (d.mode === 'gif_storyboard' || d.mode === 'acting_storyboard'
                                ? ' · gif story panels'
                                : '')
                            + (d.pipeline_style ? (' · ' + d.pipeline_style) : '')
                            + (d.fx_pack && d.fx_pack.background ? (' · fx:' + d.fx_pack.background) : '')
                            + (d.fx_pack && d.fx_pack.sound ? (' · snd:' + d.fx_pack.sound) : '')
                            + (d.story ? ' · story on' : '')
                            + (d.pipeline_run_id ? (' · pipe:' + String(d.pipeline_run_id).slice(-6)) : '')
                            + (d.planner ? ' · plan:' + d.planner : '')
                            + (d.renderer ? ' · render:' + d.renderer : '')
                        );
                        setBusy(false);
                        return;
                    }
                    if (d.status === 'failed' || d.status === 'error') {
                        setStatus('Failed: ' + (d.error || d.message || 'unknown'));
                        setOverlay('<p class="fp-film-idle">Render failed</p>', true);
                        idle = true;
                        setBusy(false);
                        return;
                    }
                    pollTimer = setTimeout(poll, 2000);
                } catch (err) {
                    setStatus('Poll error: ' + err);
                    setBusy(false);
                }
            };
            pollTimer = setTimeout(poll, 1200);
        } catch (err) {
            setStatus('Start error: ' + err);
            setOverlay('<p class="fp-film-idle">Start error</p>', true);
            setBusy(false);
        }
    }

    function bind() {
        var play = $('fp-film-play');
        var go = $('fp-film-go');
        var prompt = $('fp-film-prompt');
        var canvas = $('fp-film-canvas');
        var mn2Btn = $('fp-film-pay-mn2');
        var paypalBtn = $('fp-film-pay-paypal');
        if (!canvas) return;

        fitCanvas();
        window.addEventListener('resize', fitCanvas);
        if (play) play.addEventListener('click', playMovie);
        if (go) go.addEventListener('click', playMovie);
        if (mn2Btn) mn2Btn.addEventListener('click', payWithMn2);
        if (paypalBtn) paypalBtn.addEventListener('click', payWithPaypal);
        if (prompt) {
            prompt.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    playMovie();
                }
            });
        }
        if (canvas) {
            canvas.addEventListener('click', function () {
                var video = $('fp-film-video');
                if (video && video.getAttribute('src') && video.readyState >= 2) {
                    if (video.paused) video.play().catch(function () {});
                    else video.pause();
                } else {
                    playMovie();
                }
            });
        }
        bindFaceAndDuration();
        bindLegacyNodes();
        applyFxPack(pickLocalFxPack());
        refreshReady();
        refreshBilling();
        handlePaypalReturn();
        if (billingTimer) clearInterval(billingTimer);
        billingTimer = setInterval(function () {
            if (billing && billing.free_active && billing.free_remaining_sec > 0) {
                billing.free_remaining_sec = Math.max(0, billing.free_remaining_sec - 30);
                if (billing.free_remaining_sec <= 0) {
                    billing.free_active = false;
                    billing.can_play = (billing.credits || 0) > 0;
                }
                renderBilling();
            }
        }, 30000);
        loop();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bind);
    } else {
        bind();
    }
})();
