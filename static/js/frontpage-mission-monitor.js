/**
 * Frontpage Mission Control monitor — original interactive movie stage (no canvas).
 * Same DramaCanvas → fal pipeline as /debugger Mission Control.
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
        var play = $('fp-mc-play');
        if (play) play.disabled = !!busy;
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
        } catch (_) {
            setReady('Canvas status unavailable', false);
        }
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
        var prompt = $('fp-mc-prompt');
        if (play) play.addEventListener('click', playMovie);
        if (prompt) {
            prompt.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    playMovie();
                }
            });
        }
        refreshReady();
        setInterval(refreshReady, 45000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bind);
    } else {
        bind();
    }
})();
