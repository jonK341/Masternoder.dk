/**
 * Frontpage interactive film monitor — canvas stage + prompt + play.
 * Uses /api/film-canvas/interactive-movie (DramaCanvas plan → fal render).
 */
(function () {
    'use strict';

    var pollTimer = null;
    var animFrame = null;
    var idle = true;
    var t0 = performance.now();

    function $(id) {
        return document.getElementById(id);
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

    function drawIdle(canvas, ctx, now) {
        var w = canvas.width;
        var h = canvas.height;
        var t = (now - t0) / 1000;
        ctx.fillStyle = '#020805';
        ctx.fillRect(0, 0, w, h);

        var g = ctx.createRadialGradient(w * 0.5, h * 0.45, 20, w * 0.5, h * 0.5, w * 0.62);
        g.addColorStop(0, 'rgba(0,255,136,0.16)');
        g.addColorStop(0.55, 'rgba(0,180,255,0.06)');
        g.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, w, h);

        ctx.strokeStyle = 'rgba(0,255,136,0.08)';
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

        var scanY = ((t * 70) % (h + 40)) - 20;
        ctx.fillStyle = 'rgba(0,255,180,0.07)';
        ctx.fillRect(0, scanY, w, 18);

        ctx.fillStyle = 'rgba(180,255,220,0.55)';
        ctx.font = '600 22px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';
        ctx.textAlign = 'center';
        ctx.fillText('FILM CANVAS · STANDBY', w / 2, h / 2 - 8);
        ctx.font = '400 14px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';
        ctx.fillStyle = 'rgba(140,220,180,0.45)';
        ctx.fillText('type a prompt under the monitor', w / 2, h / 2 + 18);
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
        var live = document.body.classList.contains('mn-sound-active');
        if (!live) {
            var power = $('themeSoundToggle');
            live = !!(power && power.getAttribute('aria-pressed') === 'true');
        }
        if (snd) {
            snd.classList.toggle('is-live', live);
            snd.setAttribute('aria-pressed', live ? 'true' : 'false');
            snd.title = live ? 'Neural sound online — click to stop' : 'Neural sound offline — click to start';
        }
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

    async function playMovie() {
        var promptEl = $('fp-film-prompt');
        var video = $('fp-film-video');
        var prompt = ((promptEl && promptEl.value) || '').trim()
            || (promptEl && promptEl.placeholder)
            || 'Cinematic control-room monitor film';

        if (pollTimer) {
            clearTimeout(pollTimer);
            pollTimer = null;
        }
        setBusy(true);
        idle = true;
        if (video) {
            try { video.pause(); } catch (_) {}
            video.removeAttribute('src');
            video.load();
            video.style.opacity = '0';
        }
        setOverlay('<p class="fp-film-idle">Starting interactive movie…</p>', true);
        setStatus('Starting interactive movie…');

        try {
            var start = await fetch('/api/film-canvas/interactive-movie', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: prompt }),
            });
            var job = await start.json();
            if (!job || !job.job_id) {
                setStatus((job && job.error) || 'Could not start movie job');
                setOverlay('<p class="fp-film-idle">Start failed</p>', true);
                setBusy(false);
                return;
            }
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
                        video.src = d.video_url + '?t=' + Date.now();
                        video.onloadeddata = function () {
                            video.play().catch(function () {});
                        };
                        setStatus(
                            'Playing on canvas'
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
        if (!canvas) return;

        fitCanvas();
        window.addEventListener('resize', fitCanvas);
        if (play) play.addEventListener('click', playMovie);
        if (go) go.addEventListener('click', playMovie);
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
        bindLegacyNodes();
        refreshReady();
        loop();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bind);
    } else {
        bind();
    }
})();
