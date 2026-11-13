/**
 * Frontpage Mission Control #2 — full board as a movie.
 * Status (health/video/LLM/TTS/audio) + interactive movie + sticky SND/FX.
 */
(function () {
    'use strict';

    var pollTimer = null;

    function $(id) {
        return document.getElementById(id);
    }

    function esc(text) {
        return String(text == null ? '' : text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
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

    function setReady(text, ok) {
        var el = $('fp-mc-ready');
        if (!el) return;
        el.textContent = text || '';
        el.classList.toggle('is-ready', !!ok);
        el.classList.toggle('is-wait', !ok);
    }

    function setStatus(text) {
        var el = $('fp-mc-status');
        if (el) el.textContent = text || '';
    }

    function setBusy(busy) {
        ['fp-mc-play', 'fp-mc-play-overlay', 'fp-mc-node-ai'].forEach(function (id) {
            var el = $(id);
            if (el && 'disabled' in el) el.disabled = !!busy;
        });
        var monitor = $('fp-mc-monitor');
        if (monitor) monitor.classList.toggle('is-busy', !!busy);
    }

    function providerRows(list, nameKey, metaKey) {
        if (!list || !list.length) {
            return '<div class="fp-mc-row muted">None</div>';
        }
        return list.map(function (p) {
            var ok = !!(p.available || p.configured);
            var name = esc(p[nameKey] || p.name || p.id || 'item');
            var meta = esc(p[metaKey] || p.model || p.type || '');
            return '<div class="fp-mc-row">'
                + '<span><span class="fp-mc-dot ' + (ok ? 'on' : 'off') + '"></span>' + name + '</span>'
                + (meta ? '<span class="fp-mc-meta">' + meta + '</span>' : '')
                + '</div>';
        }).join('');
    }

    function syncSoundNode() {
        var snd = $('fp-mc-node-snd');
        var monitor = $('fp-mc-monitor');
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
        if (monitor) monitor.classList.toggle('is-sound-live', live);
        if (kicker) {
            kicker.textContent = live ? 'Neural sound online' : 'Neural sound offline';
        }
    }

    function bindSoundSticky() {
        var snd = $('fp-mc-node-snd');
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
        setInterval(syncSoundNode, 1200);
    }

    async function loadOverview() {
        if (!$('fp-mc-stage')) return;
        try {
            var r = await fetch('/api/system/overview?compact=1');
            var d = await r.json();
            var h = d.health || {};
            var score = Number(h.score || 0);
            var circle = $('fp-mc-ring-circle');
            if (circle) {
                var circ = 2 * Math.PI * 38;
                circle.style.strokeDashoffset = String(circ - (circ * score / 100));
                circle.style.stroke = h.color || '#4caf50';
            }
            var scoreEl = $('fp-mc-health-score');
            var labelEl = $('fp-mc-health-label');
            var detailEl = $('fp-mc-health-detail');
            if (scoreEl) scoreEl.textContent = String(score || '—');
            if (labelEl) {
                labelEl.textContent = h.label || 'Mission Control';
                labelEl.style.color = h.color || '#eafff4';
            }
            if (detailEl) {
                detailEl.innerHTML =
                    (h.llm_providers_ready || 0) + ' LLM · '
                    + (h.video_providers_ready || 0) + ' video · '
                    + 'TTS ' + (h.tts_ready ? 'on' : 'off') + ' · '
                    + 'Audio ' + (h.audio_enhancement_ready ? 'on' : 'off');
            }

            var videos = d.video_providers || [];
            var vidAvail = videos.filter(function (p) { return p.available; }).length;
            if ($('fp-mc-video-badge')) $('fp-mc-video-badge').textContent = vidAvail + ' active';
            if ($('fp-mc-video-rows')) $('fp-mc-video-rows').innerHTML = providerRows(videos, 'name', 'type');

            var llm = d.llm || {};
            var llmProviders = llm.providers || [];
            if ($('fp-mc-llm-badge')) {
                $('fp-mc-llm-badge').textContent = (llm.available || 0) + '/' + (llm.total || llmProviders.length || 0);
            }
            if ($('fp-mc-llm-rows')) $('fp-mc-llm-rows').innerHTML = providerRows(llmProviders, 'name', 'model');

            var tts = d.tts || {};
            var ttsRows = [
                { name: 'Piper', available: !!(tts.piper && tts.piper.available), type: 'free local' },
                { name: 'ElevenLabs', available: !!(tts.elevenlabs && tts.elevenlabs.configured), type: 'voices' },
                { name: 'gTTS', available: !!(tts.gtts && tts.gtts.available), type: 'free' },
                { name: 'pyttsx3', available: !!(tts.pyttsx3 && tts.pyttsx3.available), type: 'offline' },
            ];
            if ($('fp-mc-tts-badge')) $('fp-mc-tts-badge').textContent = tts.active_provider || 'none';
            if ($('fp-mc-tts-rows')) $('fp-mc-tts-rows').innerHTML = providerRows(ttsRows, 'name', 'type');

            var audio = d.audio_enhancement || d.audio || {};
            var audioRows = [
                { name: 'DeepFilterNet', available: !!(audio.deepfilternet || audio.noise_reduction), type: 'denoise' },
                { name: 'FFmpeg loudnorm', available: !!(audio.loudnorm || audio.ffmpeg), type: 'level' },
                { name: 'Enhancement', available: !!(h.audio_enhancement_ready || audio.enabled || audio.ready), type: 'pipeline' },
            ];
            if ($('fp-mc-audio-badge')) {
                $('fp-mc-audio-badge').textContent = (h.audio_enhancement_ready || audio.ready) ? 'on' : 'off';
            }
            if ($('fp-mc-audio-rows')) $('fp-mc-audio-rows').innerHTML = providerRows(audioRows, 'name', 'type');

            var fal = videos.find(function (p) { return p.id === 'fal_krea'; });
            var drama = videos.find(function (p) { return p.id === 'dramacanva'; });
            var bits = [];
            bits.push(drama && drama.available ? 'DramaCanvas ready' : 'DramaCanvas offline');
            bits.push(fal && fal.available ? 'fal ready' : 'fal offline');
            setReady(bits.join(' · '), !!(fal && fal.available) || !!(drama && drama.available) || vidAvail > 0);

            var xp = $('fp-mc-node-xp');
            var level = (((d.statistics || {}).level) || null);
            if (xp && level) {
                xp.textContent = 'Lv' + level;
                xp.title = 'Level ' + level + ' · XP & trophies';
            }
        } catch (err) {
            setReady('Board offline', false);
            setStatus('Status error: ' + err);
        }
    }

    async function playMovie() {
        var promptEl = $('fp-mc-prompt');
        var video = $('fp-mc-video');
        var placeholder = $('fp-mc-placeholder');
        var prompt = ((promptEl && promptEl.value) || '').trim()
            || (promptEl && promptEl.placeholder)
            || 'Mission Control cinematic board film';

        if (pollTimer) {
            clearTimeout(pollTimer);
            pollTimer = null;
        }
        setBusy(true);
        setStatus('Starting Mission Control movie…');
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
                    setStatus(prog + (d.message || d.status || '…'));
                    if (d.status === 'completed' && d.video_url && video) {
                        if (placeholder) placeholder.style.display = 'none';
                        video.style.display = 'block';
                        video.src = d.video_url + '?t=' + Date.now();
                        video.onloadeddata = function () {
                            video.play().catch(function () {});
                        };
                        setStatus('Playing Mission Control movie'
                            + (d.planner ? ' · plan:' + d.planner : '')
                            + (d.renderer ? ' · render:' + d.renderer : ''));
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
        if (!$('fp-mc-stage')) return;
        var play = $('fp-mc-play');
        var overlay = $('fp-mc-play-overlay');
        var ai = $('fp-mc-node-ai');
        var prompt = $('fp-mc-prompt');
        var refresh = $('fp-mc-refresh');
        if (play) play.addEventListener('click', playMovie);
        if (overlay) overlay.addEventListener('click', function (e) {
            e.stopPropagation();
            playMovie();
        });
        if (ai) ai.addEventListener('click', function () {
            if (prompt) prompt.focus();
            playMovie();
        });
        if (prompt) {
            prompt.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    playMovie();
                }
            });
        }
        if (refresh) refresh.addEventListener('click', loadOverview);
        bindSoundSticky();
        loadOverview();
        setInterval(loadOverview, 45000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bind);
    } else {
        bind();
    }
})();
