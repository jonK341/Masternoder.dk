/**
 * MasterNoder Super Encoder — music, song & video creator with MN2 ratings.
 */
(function () {
    'use strict';

    var BASE = window.location.origin;
    var userId = localStorage.getItem('game_user_id') || 'default_user';
    var config = {};
    var encoderModes = [];
    var selectedModeId = 'full_mv';
    var selectedStars = 0;
    var ratingTrackId = null;
    var currentPlayingId = null;
    var currentMediaEl = null;

    function $(id) { return document.getElementById(id); }

    function toast(msg) {
        var el = $('cr-toast');
        if (!el) return;
        el.textContent = msg;
        el.classList.add('show');
        setTimeout(function () { el.classList.remove('show'); }, 3200);
    }

    function api(path, opts) {
        opts = opts || {};
        var url = BASE + path + (path.indexOf('?') >= 0 ? '&' : '?') + 'user_id=' + encodeURIComponent(userId);
        return fetch(url, opts).then(function (r) { return r.json(); });
    }

    function getSelectedMode() {
        for (var i = 0; i < encoderModes.length; i++) {
            if (encoderModes[i].id === selectedModeId) return encoderModes[i];
        }
        return encoderModes[0] || { id: 'full_mv', layers: { lyrics: true, audio: true, video: true, sync: true } };
    }

    function pipelineLabel(layers) {
        if (!layers) return 'Processing';
        var parts = [];
        if (layers.lyrics) parts.push('Lyrics');
        if (layers.audio) parts.push('Audio');
        if (layers.video) parts.push('Video');
        if (layers.sync) parts.push('Sync');
        return parts.length ? parts.join(' → ') : 'Processing';
    }

    function updateModeUi() {
        var mode = getSelectedMode();
        var desc = $('cr-mode-desc');
        if (desc) desc.textContent = mode.description || 'Pick a mode — each runs a different creation pipeline.';
        var pipeline = $('cr-encode-pipeline');
        if (pipeline) pipeline.textContent = pipelineLabel(mode.layers);
        var priceEl = $('cr-encode-price');
        if (priceEl) {
            var base = (config.encode && config.encode.one_click_mn2) || 0.15;
            var price = mode.price_mn2 != null ? mode.price_mn2 : base;
            priceEl.textContent = price + ' MN2';
        }
        if (mode.default_genre) {
            var genreEl = $('cr-genre');
            if (genreEl) genreEl.value = mode.default_genre;
        }
        if (mode.default_mood) {
            var moodEl = $('cr-mood');
            if (moodEl) moodEl.value = mode.default_mood;
        }
        document.querySelectorAll('.cr-mode-card').forEach(function (card) {
            card.classList.toggle('active', card.getAttribute('data-mode') === selectedModeId);
        });
    }

    function renderModeGrid(modes, defaultMode) {
        var grid = $('cr-mode-grid');
        var countEl = $('cr-mode-count');
        if (!grid) return;
        encoderModes = modes || [];
        if (countEl) countEl.textContent = '(' + encoderModes.length + ' modes)';
        if (!encoderModes.length) {
            grid.innerHTML = '<p class="cr-mode-loading">No encoder modes configured.</p>';
            return;
        }
        selectedModeId = defaultMode || encoderModes[0].id;
        grid.innerHTML = encoderModes.map(function (m) {
            return '<button type="button" class="cr-mode-card" data-mode="' + escapeAttr(m.id) + '" role="option" aria-selected="false">' +
                '<span class="cr-mode-icon">' + (m.icon || '🎵') + '</span>' +
                '<span class="cr-mode-name">' + escapeHtml(m.label || m.id) + '</span>' +
                '</button>';
        }).join('');
        grid.querySelectorAll('.cr-mode-card').forEach(function (btn) {
            btn.addEventListener('click', function () {
                selectedModeId = btn.getAttribute('data-mode');
                updateModeUi();
            });
        });
        updateModeUi();
    }

    function escapeAttr(s) {
        return String(s).replace(/"/g, '&quot;');
    }

    function loadConfig() {
        return api('/api/creator/config').then(function (data) {
            if (!data.success) return;
            config = data.config || {};
            var modesPayload = data.encoder_modes || {};
            renderModeGrid(modesPayload.modes || [], modesPayload.default_mode || config.default_encoder_mode);
            var storage = data.storage || {};
            var pill = $('cr-storage-pill');
            if (pill) {
                pill.innerHTML = 'Storage: <strong>' + (storage.stored_videos || 0) + '</strong> / ' +
                    (storage.max_videos || 125) + ' videos · <strong>' +
                    (storage.slots_remaining || 125) + '</strong> slots left';
            }
            var aiEl = $('cr-ai-status');
            if (aiEl && data.ai) {
                var lines = [];
                if (data.ai.music_hook && data.ai.music_hook.preferred) {
                    lines.push('music: ' + data.ai.music_hook.preferred);
                }
                if (data.ai.ai_routing) {
                    Object.keys(data.ai.ai_routing).forEach(function (k) {
                        var r = data.ai.ai_routing[k];
                        var sel = r.selected ? r.selected.provider : 'fallback';
                        lines.push(k + ': ' + sel);
                    });
                }
                aiEl.textContent = 'AI routing: ' + lines.join(' · ');
            }
        }).catch(function () { /* optional */ });
    }

    function trackHasPlayback(t) {
        if (!t) return false;
        var st = (t.status || '').toLowerCase();
        if (st.indexOf('failed') >= 0 || st === 'queued' || st === 'encoding') return false;
        return !!(t.audio_url || t.video_url || t.sync_url || (t.layers && (t.layers.audio || t.layers.video)));
    }

    function trackMediaUrl(t, preferVideo) {
        if (!t) return null;
        if (preferVideo) {
            if (t.sync_url) return BASE + t.sync_url;
            if (t.video_url) return BASE + t.video_url;
        }
        if (t.audio_url) return BASE + t.audio_url;
        if (t.sync_url) return BASE + t.sync_url;
        if (t.video_url) return BASE + t.video_url;
        return null;
    }

    function trackIsVideo(t) {
        if (!t) return false;
        if (t.sync_url || t.video_url) return true;
        if (t.layers && t.layers.video) return true;
        var mode = (t.encoder_mode || '').toLowerCase();
        return mode.indexOf('mv') >= 0 || mode.indexOf('video') >= 0;
    }

    function stopPlayback() {
        if (currentMediaEl) {
            try { currentMediaEl.pause(); } catch (e) { /* ignore */ }
            currentMediaEl = null;
        }
        currentPlayingId = null;
        document.querySelectorAll('.cr-track.playing').forEach(function (el) {
            el.classList.remove('playing');
        });
        document.querySelectorAll('.cr-play-btn.playing').forEach(function (btn) {
            btn.classList.remove('playing');
            btn.setAttribute('aria-label', 'Play');
        });
    }

    function togglePlayback(trackId, tracks) {
        var t = null;
        for (var i = 0; i < tracks.length; i++) {
            if (tracks[i].id === trackId) { t = tracks[i]; break; }
        }
        if (!t || !trackHasPlayback(t)) {
            toast('No audio/video ready yet');
            return;
        }
        var article = document.querySelector('.cr-track[data-id="' + trackId + '"]');
        var playerWrap = article ? article.querySelector('.cr-track-player') : null;
        if (!playerWrap) return;

        if (currentPlayingId === trackId && currentMediaEl && !currentMediaEl.paused) {
            stopPlayback();
            playerWrap.hidden = true;
            return;
        }

        stopPlayback();
        currentPlayingId = trackId;
        if (article) article.classList.add('playing');
        var playBtn = article ? article.querySelector('.cr-play-btn') : null;
        if (playBtn) {
            playBtn.classList.add('playing');
            playBtn.setAttribute('aria-label', 'Pause');
        }

        var preferVideo = trackIsVideo(t);
        var url = trackMediaUrl(t, preferVideo);
        if (!url) {
            toast('Playback URL not available');
            stopPlayback();
            return;
        }

        playerWrap.hidden = false;
        var isVideo = preferVideo && (t.sync_url || t.video_url);
        playerWrap.innerHTML = isVideo
            ? '<video class="cr-media" controls playsinline preload="metadata" src="' + escapeAttr(url) + '"></video>'
            : '<audio class="cr-media" controls preload="metadata" src="' + escapeAttr(url) + '"></audio>';

        currentMediaEl = playerWrap.querySelector('.cr-media');
        if (currentMediaEl) {
            currentMediaEl.addEventListener('ended', stopPlayback);
            currentMediaEl.addEventListener('pause', function () {
                if (currentMediaEl && currentMediaEl.paused && currentPlayingId === trackId) {
                    if (playBtn) {
                        playBtn.classList.remove('playing');
                        playBtn.setAttribute('aria-label', 'Play');
                    }
                }
            });
            var playPromise = currentMediaEl.play();
            if (playPromise && playPromise.catch) {
                playPromise.catch(function () { /* autoplay blocked — user can press play */ });
            }
        }
    }

    function renderTracks(tracks, targetId) {
        var list = $(targetId || 'cr-tracks-list');
        if (!list) return;
        if (!tracks || !tracks.length) {
            list.innerHTML = '<p style="color:var(--cr-muted);font-size:0.85rem;">No tracks yet — pick a mode and hit Super Encode.</p>';
            return;
        }
        list.innerHTML = tracks.map(function (t) {
            var statusCls = (t.status || '').indexOf('completed') >= 0 ? 'completed' :
                (t.status || '').indexOf('failed') >= 0 ? 'failed' : '';
            var modeTag = t.encoder_mode_label
                ? (t.encoder_mode_icon || '') + ' ' + escapeHtml(t.encoder_mode_label)
                : '';
            var stars = '';
            for (var i = 1; i <= 5; i++) {
                stars += '<button type="button" class="cr-star" data-track="' + t.id + '" data-score="' + i + '" aria-label="' + i + ' stars">' +
                    (i <= Math.round(t.avg_rating || 0) ? '★' : '☆') + '</button>';
            }
            var canPlay = trackHasPlayback(t);
            var playIcon = trackIsVideo(t) ? '▶' : '▶';
            var playBtn = canPlay
                ? '<button type="button" class="cr-play-btn" data-track="' + t.id + '" aria-label="Play">' + playIcon + '</button>'
                : '';
            return '<article class="cr-track' + (canPlay ? ' has-playback' : '') + '" data-id="' + t.id + '">' +
                '<div class="cr-track-art">' + playBtn + (t.encoder_mode_icon || '🎵') + '</div>' +
                '<div class="cr-track-body">' +
                '<div class="cr-track-info">' +
                '<h3>' + escapeHtml(t.title || 'Untitled') + '</h3>' +
                '<p>' + escapeHtml(t.genre || '') + ' · ' + escapeHtml(t.mood || '') +
                (modeTag ? ' · ' + modeTag : '') +
                (t.avg_rating ? ' · ★ ' + t.avg_rating : '') + '</p>' +
                '<div class="cr-rating-row">' + stars + '</div>' +
                '</div>' +
                '<div class="cr-track-player" hidden></div>' +
                '</div>' +
                '<span class="cr-track-status ' + statusCls + '">' + escapeHtml(t.status || 'queued') + '</span>' +
                '</article>';
        }).join('');

        list.querySelectorAll('.cr-star').forEach(function (btn) {
            btn.addEventListener('click', function () {
                rateTrack(btn.getAttribute('data-track'), parseInt(btn.getAttribute('data-score'), 10));
            });
        });
        list.querySelectorAll('.cr-play-btn').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                togglePlayback(btn.getAttribute('data-track'), tracks);
            });
        });
    }

    function escapeHtml(s) {
        var d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    function loadTracks() {
        return api('/api/creator/tracks?limit=125').then(function (data) {
            if (data.success) renderTracks(data.tracks);
        }).catch(function () { /* optional */ });
    }

    function superEncode() {
        if (!userId || userId === 'default_user') {
            toast('Create your profile first to encode tracks');
            window.location.href = '/profile';
            return;
        }
        var title = ($('cr-title') || {}).value || '';
        if (!title.trim()) {
            toast('Enter a song title');
            return;
        }
        var btn = $('cr-super-encode-btn');
        if (btn) btn.disabled = true;
        var mode = getSelectedMode();
        var genre = ($('cr-genre') || {}).value || mode.default_genre || 'electronic';
        var mood = ($('cr-mood') || {}).value || mode.default_mood || 'energetic';
        var duration = mode.default_duration != null ? mode.default_duration : 60;
        fetch(BASE + '/api/creator/encode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                title: title.trim(),
                genre: genre,
                mood: mood,
                duration: duration,
                mode: selectedModeId,
                pay_with_mn2: true
            })
        }).then(function (r) { return r.json(); }).then(function (data) {
            if (btn) btn.disabled = false;
            if (data.success) {
                toast((data.mode_label || 'Encode') + ' started: ' + data.track_id);
                loadTracks();
                loadConfig();
            } else {
                toast(data.error || 'Encode failed');
            }
        }).catch(function () {
            if (btn) btn.disabled = false;
            toast('Network error');
        });
    }

    function rateTrack(trackId, score) {
        fetch(BASE + '/api/creator/rate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                track_id: trackId,
                score: score,
                pay_with_mn2: true
            })
        }).then(function (r) { return r.json(); }).then(function (data) {
            if (data.success) {
                toast('Rated ★' + score + ' — ' + (data.cost_mn2 || 0) + ' MN2');
                loadTracks();
            } else {
                toast(data.error || 'Rating failed');
            }
        }).catch(function () { toast('Rating error'); });
    }

    function loadMobileConfig() {
        api('/api/creator/mobile/config').then(function (data) {
            if (!data.success) return;
            var apk = $('cr-dl-apk');
            if (apk && data.download_apk_url) {
                apk.href = data.download_apk_url;
                if (data.download_apk_filename) apk.setAttribute('download', data.download_apk_filename);
            }
        }).catch(function () { /* optional */ });
    }

    function initNav() {
        document.querySelectorAll('.cr-nav-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                document.querySelectorAll('.cr-nav-btn').forEach(function (b) { b.classList.remove('active'); });
                btn.classList.add('active');
                var tab = btn.getAttribute('data-tab');
                var encode = $('cr-tab-encode');
                var tracks = $('cr-tab-tracks');
                var feed = $('cr-tab-feed');
                if (encode) encode.hidden = tab !== 'encode';
                if (tracks) tracks.hidden = tab !== 'tracks';
                if (feed) feed.hidden = tab !== 'feed';
                if (tab === 'feed') loadFeed();
            });
        });
    }

    function loadFeed() {
        api('/api/creator/feed').then(function (data) {
            var el = $('cr-feed-list');
            if (!el || !data.success) return;
            var items = data.featured || [];
            if (!items.length) {
                el.innerHTML = '<p style="color:var(--cr-muted);">No featured tracks yet — rate content to populate the feed.</p>';
                return;
            }
            renderTracks(items, 'cr-feed-list');
        }).catch(function () { /* optional */ });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var encodeBtn = $('cr-super-encode-btn');
        if (encodeBtn) encodeBtn.addEventListener('click', superEncode);
        var pwaBtn = $('cr-dl-pwa');
        if (pwaBtn) {
            pwaBtn.addEventListener('click', function () {
                if (window.__creatorInstallPwa) window.__creatorInstallPwa();
                else toast('Use browser menu → Add to Home Screen');
            });
        }
        initNav();
        loadConfig();
        loadTracks();
        loadMobileConfig();
        setInterval(loadTracks, 15000);
    });
})();
