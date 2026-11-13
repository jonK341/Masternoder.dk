/**
 * Frontpage Mission Control monitor — original video stage (no canvas)
 * plus Film Canvas control chips: AI / SND / XP / v2.0 / on-screen play.
 */
(function () {
    'use strict';

    var pollTimer = null;

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
            var key = 'fp_film_trial_id';
            var existing = localStorage.getItem(key);
            if (existing) return existing;
            var id = 'ft_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
            localStorage.setItem(key, id);
            return id;
        } catch (_) {
            return 'ft_guest';
        }
    }

    function setStatus(text) {
        var el = $('fp-mc-status');
        if (el) el.textContent = text || '';
    }

    function setReady(text, ok) {
        var el = $('fp-mc-ready');
        if (!el) return;
        el.textContent = text || '';
        el.classList.toggle('is-ready', !!ok);
        el.classList.toggle('is-wait', !ok);
    }

    function setBusy(busy) {
        ['fp-mc-play', 'fp-mc-play-overlay', 'fp-mc-node-ai'].forEach(function (id) {
            var el = $(id);
            if (el && 'disabled' in el) el.disabled = !!busy;
        });
        var monitor = $('fp-mc-monitor');
        if (monitor) monitor.classList.toggle('is-busy', !!busy);
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

            var xp = $('fp-mc-node-xp');
            var level = (((d.statistics || {}).level) || null);
            if (xp && level) {
                xp.textContent = 'Lv' + level;
                xp.title = 'Level ' + level + ' · XP & trophies';
            }
        } catch (_) {
            setReady('Canvas status unavailable', false);
        }
    }

    function syncSoundNode() {
        var snd = $('fp-mc-node-snd');
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

    function bindControlNodes() {
        var ai = $('fp-mc-node-ai');
        var snd = $('fp-mc-node-snd');
        if (ai) {
            ai.addEventListener('click', function () {
                var prompt = $('fp-mc-prompt');
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
        var promptEl = $('fp-mc-prompt');
        var video = $('fp-mc-video');
        var placeholder = $('fp-mc-placeholder');
        var prompt = ((promptEl && promptEl.value) || '').trim()
            || (promptEl && promptEl.placeholder)
            || 'Cinematic control-room monitor film';

        if (pollTimer) {
            clearTimeout(pollTimer);
            pollTimer = null;
        }
        setBusy(true);
        setStatus('Starting interactive movie…');
        if (placeholder) placeholder.style.display = 'block';
        if (video) {
            video.style.display = 'none';
            video.removeAttribute('src');
            try { video.load(); } catch (_) {}
        }

        try {
            var start = await fetch('/api/film-canvas/interactive-movie', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt: prompt,
                    user_id: getUserId(),
                    trial_id: getTrialId(),
                }),
            });
            var job = await start.json();
            if (start.status === 402 || (job && job.code === 'PAYMENT_REQUIRED')) {
                setStatus((job && job.message) || 'Pay with MN2 coins or PayPal under the monitors.');
                var payBox = $('fp-film-pay');
                if (payBox) {
                    payBox.classList.add('is-locked');
                    payBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
                setBusy(false);
                return;
            }
            if (!job || !job.job_id) {
                setStatus((job && job.error) || 'Could not start movie job');
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

                    if (d.status === 'completed' && d.video_url && video) {
                        if (placeholder) placeholder.style.display = 'none';
                        video.style.display = 'block';
                        video.src = d.video_url + '?t=' + Date.now();
                        video.onloadeddata = function () {
                            video.play().catch(function () {});
                        };
                        setStatus(
                            'Playing interactive movie'
                            + (d.planner ? ' · plan:' + d.planner : '')
                            + (d.renderer ? ' · render:' + d.renderer : '')
                        );
                        setBusy(false);
                        return;
                    }
                    if (d.status === 'failed' || d.status === 'error') {
                        setStatus('Failed: ' + (d.error || d.message || 'unknown'));
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
            setBusy(false);
        }
    }

    function bind() {
        var stage = $('fp-mc-stage');
        if (!stage) return;
        var play = $('fp-mc-play');
        var overlay = $('fp-mc-play-overlay');
        var prompt = $('fp-mc-prompt');
        var frame = stage.querySelector('.fp-mc-frame');
        if (play) play.addEventListener('click', playMovie);
        if (overlay) overlay.addEventListener('click', playMovie);
        if (prompt) {
            prompt.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    playMovie();
                }
            });
        }
        if (frame) {
            frame.addEventListener('click', function (e) {
                if (e.target && (e.target.id === 'fp-mc-play-overlay' || e.target.closest('#fp-mc-play-overlay'))) {
                    return;
                }
                var video = $('fp-mc-video');
                if (video && video.getAttribute('src') && video.readyState >= 2) {
                    if (video.paused) video.play().catch(function () {});
                    else video.pause();
                } else {
                    playMovie();
                }
            });
        }
        bindControlNodes();
        refreshReady();
        setInterval(refreshReady, 45000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bind);
    } else {
        bind();
    }
})();
