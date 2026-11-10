/**
 * Star Map 25 monitor dock: 25-point grid, profit daemon Jon, and the live stream.
 * Mount every [data-starmap-monitor] on the front page and on /starmap25/.
 */
(function () {
    'use strict';

    var BASE = window.location.origin || '';
    var DEFAULT_VIDEO = '-iSYSBSn_8E';

    function esc(text) {
        return String(text == null ? '' : text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function embedUrl(videoId) {
        var id = videoId || DEFAULT_VIDEO;
        return 'https://www.youtube.com/embed/' + encodeURIComponent(id) + '?rel=0';
    }

    function paintGrid(root, points, investigated, invaded) {
        var grid = root.querySelector('[data-monitor-grid]');
        var line = root.querySelector('[data-monitor-line]');
        if (!grid) return;
        var done = {};
        var secured = {};
        (investigated || []).forEach(function (id) { done[id] = true; });
        (invaded || []).forEach(function (id) { secured[id] = true; });
        if (!points || !points.length) {
            grid.innerHTML = '';
            if (line) line.textContent = 'Star Map 25 has no systems to show.';
            return;
        }
        grid.innerHTML = points.map(function (point, index) {
            var id = point.id || ('point_' + (index + 1));
            var cls = 'sm25-cell';
            if (done[id]) cls += ' done';
            if (secured[id]) cls += ' secured';
            var n = point.index != null ? point.index : (index + 1);
            var name = point.name || id;
            return '<div class="' + cls + '" title="' + esc(name) + '">' + esc(n) + '</div>';
        }).join('');
        if (line) {
            line.textContent = points.length + ' systems on the monitor'
                + (investigated && investigated.length ? ' · ' + investigated.length + ' investigated' : '')
                + '.';
        }
    }

    function paintDaemon(root, data) {
        var card = root.querySelector('[data-daemon-jon]');
        if (!card) return;
        var levelEl = card.querySelector('[data-daemon-level]');
        var visionEl = card.querySelector('[data-daemon-vision]');
        var moveEl = card.querySelector('[data-daemon-move]');
        var level = data && data.level ? data.level : 0;
        var progress = (data && data.progress) || {};
        if (levelEl) {
            levelEl.textContent = data && data.defined
                ? 'Level ' + level + ' · following the board'
                : 'Level ' + level + ' · ' + (progress.filled || 0) + '/' + (progress.required || 20) + ' assignments set';
        }
        if (visionEl) {
            visionEl.innerHTML = '<strong>Vision.</strong> ' + esc((data && data.vision) || 'Not set yet.');
        }
        if (moveEl) {
            moveEl.innerHTML = '<strong>Next profit move.</strong> ' + esc((data && data.next_profit_move) || 'Not set yet.');
        }
    }

    function paintStream(root, youtube) {
        var frame = root.querySelector('[data-live-stream]');
        var note = root.querySelector('[data-live-note]');
        var info = youtube || {};
        var videoId = info.video_id || DEFAULT_VIDEO;
        if (frame) {
            var next = embedUrl(videoId);
            if (frame.getAttribute('src') !== next) frame.setAttribute('src', next);
        }
        if (!note) return;
        if (!info.checked_at && !info.title) {
            note.textContent = 'Live stream is on this monitor.';
            return;
        }
        var live = info.live ? 'Live now' : 'Not live';
        var title = info.title ? ' · ' + esc(info.title) : '';
        var detail = info.note ? ' ' + esc(info.note) : '';
        var href = info.watch_url
            ? ' <a href="' + esc(info.watch_url) + '" target="_blank" rel="noopener">Watch</a>'
            : '';
        note.innerHTML = live + title + '.' + detail + href;
    }

    function loadMonitor(root) {
        fetch(BASE + '/api/star-map/25')
            .then(function (res) { return res.json(); })
            .then(function (mapData) {
                var points = (mapData && mapData.star_map_25 && mapData.star_map_25.points) || [];
                return fetch(BASE + '/api/star-map/25/status').then(function (res) { return res.json(); }).then(function (status) {
                    paintGrid(root, points, status.investigated_ids, status.invaded_ids);
                }).catch(function () {
                    paintGrid(root, points, [], []);
                });
            })
            .catch(function () { paintGrid(root, [], [], []); });

        fetch(BASE + '/api/profit-daemon/level')
            .then(function (res) { return res.json(); })
            .then(function (data) {
                paintDaemon(root, data);
                paintStream(root, data.youtube);
            })
            .catch(function () {
                paintDaemon(root, null);
            });

        fetch(BASE + '/api/profit-daemon/level/youtube-check', { method: 'POST' })
            .then(function (res) { return res.json(); })
            .then(function (youtube) { paintStream(root, youtube); })
            .catch(function () {
                paintStream(root, { checked_at: 'local', live: false, video_id: DEFAULT_VIDEO, note: 'Live stream is on this monitor.' });
            });
    }

    function boot() {
        var mounts = document.querySelectorAll('[data-starmap-monitor]');
        Array.prototype.forEach.call(mounts, loadMonitor);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
