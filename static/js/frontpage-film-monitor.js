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
    var TRIAL_KEY = 'fp_film_trial_id';
    var MIN_DURATION = 2;
    var MAX_DURATION = 120;
    var DEFAULT_DURATION = 8;

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

    function drawIdle(canvas, ctx, now) {
        var w = canvas.width;
        var h = canvas.height;
        var t = (now - t0) / 1000;
        var hot = soundLive();
        ctx.fillStyle = '#020805';
        ctx.fillRect(0, 0, w, h);

        var g = ctx.createRadialGradient(w * 0.5, h * 0.45, 20, w * 0.5, h * 0.5, w * 0.62);
        g.addColorStop(0, hot ? 'rgba(0,255,136,0.28)' : 'rgba(0,255,136,0.16)');
        g.addColorStop(0.45, hot ? 'rgba(0,180,255,0.14)' : 'rgba(0,180,255,0.06)');
        g.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, w, h);

        ctx.strokeStyle = hot ? 'rgba(0,255,136,0.16)' : 'rgba(0,255,136,0.08)';
        ctx.lineWidth = 1;
        var step = hot ? 22 : 28;
        var drift = hot ? 22 : 12;
        for (var x = 0; x < w; x += step) {
            ctx.beginPath();
            ctx.moveTo(x + (t * drift) % step, 0);
            ctx.lineTo(x + (t * drift) % step, h);
            ctx.stroke();
        }
        for (var y = 0; y < h; y += step) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(w, y);
            ctx.stroke();
        }

        var scanSpeed = hot ? 120 : 70;
        var scanY = ((t * scanSpeed) % (h + 40)) - 20;
        ctx.fillStyle = hot ? 'rgba(0,255,180,0.14)' : 'rgba(0,255,180,0.07)';
        ctx.fillRect(0, scanY, w, hot ? 26 : 18);

        if (hot) {
            for (var i = 0; i < 18; i++) {
                var px = (Math.sin(t * 1.7 + i * 1.3) * 0.5 + 0.5) * w;
                var py = (Math.cos(t * 1.1 + i * 0.9) * 0.5 + 0.5) * h;
                ctx.fillStyle = 'rgba(0,255,200,' + (0.18 + (i % 5) * 0.04) + ')';
                ctx.beginPath();
                ctx.arc(px, py, 1.5 + (i % 3), 0, Math.PI * 2);
                ctx.fill();
            }
        }

        ctx.fillStyle = 'rgba(180,255,220,0.55)';
        ctx.font = '600 22px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';
        ctx.textAlign = 'center';
        ctx.fillText(hot ? 'FILM CANVAS · SOUND LIVE' : 'FILM CANVAS · STANDBY', w / 2, h / 2 - 8);
        ctx.font = '400 14px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';
        ctx.fillStyle = 'rgba(140,220,180,0.45)';
        ctx.fillText('type a scene · press Play Movie', w / 2, h / 2 + 18);
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
        ctx.fillStyle = 'rgba(0,255,136,0.05)';
        var scan = ((performance.now() / 1000) * 90) % (ch + 30);
        ctx.fillRect(0, scan - 15, cw, 12);
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

    function setDownloadLink(url) {
        var link = $('fp-film-download');
        if (!link) return;
        if (!url) {
            link.removeAttribute('href');
            link.hidden = true;
            link.classList.add('is-hidden');
            return;
        }
        var href = String(url);
        if (!/[?&]download=/.test(href)) {
            href = href.indexOf('?') >= 0 ? (href + '&download=1') : (href + '?download=1');
        }
        link.href = href;
        link.setAttribute('download', 'masternoder-movie.mp4');
        link.hidden = false;
        link.classList.remove('is-hidden');
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
            if (file.size > 4 * 1024 * 1024) {
                reject(new Error('Face image must be under 4 MB'));
                return;
            }
            var reader = new FileReader();
            reader.onload = function () { resolve(String(reader.result || '')); };
            reader.onerror = function () { reject(new Error('Could not read face image')); };
            reader.readAsDataURL(file);
        });
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
        if (video) {
            try { video.pause(); } catch (_) {}
            video.removeAttribute('src');
            video.removeAttribute('controls');
            video.load();
            video.style.opacity = '0';
        }
        setOverlay(
            '<p class="fp-film-idle">Starting ' + durationSec + 's interactive movie…</p>',
            true
        );
        setStatus(
            'Starting ' + durationSec + 's movie'
            + (faceDataUrl ? ' with face reference' : '')
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
            var job = await start.json();
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
                    var d = await r.json();
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
                        video.style.opacity = '1';
                        video.setAttribute('controls', 'controls');
                        video.src = d.video_url + '?t=' + Date.now();
                        video.onloadeddata = function () {
                            video.play().catch(function () {});
                        };
                        setDownloadLink(d.download_url || d.video_url);
                        setStatus(
                            'Movie ready — play or download'
                            + (d.duration_sec ? (' · ' + d.duration_sec + 's') : '')
                            + (d.beats ? (' · ' + d.beats + ' scenes') : '')
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
