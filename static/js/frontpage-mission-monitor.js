/**
 * Frontpage Mission Control #2 — pre-canvas status board.
 * Health ring + video/LLM providers from /api/system/overview.
 * Interactive movie lives on /debugger#mission-control (OPS).
 */
(function () {
    'use strict';

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

    function providerRows(list, nameKey, metaKey) {
        if (!list || !list.length) {
            return '<div class="fp-mc-row muted">No providers reported</div>';
        }
        return list.map(function (p) {
            var ok = !!p.available;
            var name = esc(p[nameKey] || p.name || p.id || 'provider');
            var meta = esc(p[metaKey] || p.model || p.type || '');
            return '<div class="fp-mc-row">'
                + '<span><span class="fp-mc-dot ' + (ok ? 'on' : 'off') + '"></span>' + name + '</span>'
                + (meta ? '<span class="fp-mc-meta">' + meta + '</span>' : '')
                + '</div>';
        }).join('');
    }

    async function loadOverview(fullScan) {
        var stage = $('fp-mc-stage');
        if (!stage) return;
        setReady('Refreshing…', false);
        setStatus(fullScan ? 'Full scan…' : 'Loading Mission Control…');
        try {
            var url = '/api/system/overview' + (fullScan ? '' : '?compact=1');
            var r = await fetch(url);
            var d = await r.json();
            var h = d.health || {};
            var score = Number(h.score || 0);
            var circle = $('fp-mc-ring-circle');
            var scoreEl = $('fp-mc-health-score');
            var labelEl = $('fp-mc-health-label');
            var detailEl = $('fp-mc-health-detail');
            if (circle) {
                var circ = 2 * Math.PI * 38;
                circle.style.strokeDashoffset = String(circ - (circ * score / 100));
                circle.style.stroke = h.color || '#4caf50';
            }
            if (scoreEl) scoreEl.textContent = String(score || '—');
            if (labelEl) {
                labelEl.textContent = h.label || '—';
                labelEl.style.color = h.color || '#eafff4';
            }
            if (detailEl) {
                detailEl.innerHTML =
                    (h.llm_providers_ready || 0) + ' LLM ready · '
                    + (h.video_providers_ready || 0) + ' video ready · '
                    + 'TTS ' + (h.tts_ready ? 'active' : 'offline') + ' · '
                    + 'Audio ' + (h.audio_enhancement_ready ? 'on' : 'off');
            }

            var videos = d.video_providers || [];
            var vidAvail = videos.filter(function (p) { return p.available; }).length;
            var videoBadge = $('fp-mc-video-badge');
            var videoRows = $('fp-mc-video-rows');
            if (videoBadge) videoBadge.textContent = vidAvail + ' active';
            if (videoRows) videoRows.innerHTML = providerRows(videos, 'name', 'type');

            var llm = d.llm || {};
            var llmProviders = llm.providers || [];
            var llmBadge = $('fp-mc-llm-badge');
            var llmRows = $('fp-mc-llm-rows');
            if (llmBadge) {
                llmBadge.textContent = (llm.available || 0) + '/' + (llm.total || llmProviders.length || 0);
            }
            if (llmRows) llmRows.innerHTML = providerRows(llmProviders, 'name', 'model');

            var fal = videos.find(function (p) { return p.id === 'fal_krea'; });
            var drama = videos.find(function (p) { return p.id === 'dramacanva'; });
            var bits = [];
            bits.push(drama && drama.available ? 'DramaCanvas ready' : 'DramaCanvas offline');
            bits.push(fal && fal.available ? 'fal ready' : 'fal offline');
            var ok = !!(fal && fal.available) || !!(drama && drama.available) || vidAvail > 0;
            setReady(bits.join(' · '), ok);
            setStatus('Mission Control status loaded');
        } catch (err) {
            setReady('Status unavailable', false);
            setStatus('Load error: ' + err);
        }
    }

    function bind() {
        if (!$('fp-mc-stage')) return;
        var refresh = $('fp-mc-refresh');
        if (refresh) {
            refresh.addEventListener('click', function () { loadOverview(false); });
            refresh.addEventListener('dblclick', function () { loadOverview(true); });
        }
        loadOverview(false);
        setInterval(function () { loadOverview(false); }, 45000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bind);
    } else {
        bind();
    }
})();
