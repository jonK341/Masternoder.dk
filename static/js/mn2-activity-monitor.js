/**
 * MN2 activity monitor panel — SSE live feed + status tiles (customers, Discord, news).
 */
(function (global) {
    'use strict';

    var es = null;
    var pollTimer = null;
    var lastSig = '';
    var soundsOn = global.localStorage.getItem('mn2_activity_sounds') !== '0';

    function esc(s) {
        var d = global.document.createElement('div');
        d.textContent = s == null ? '' : String(s);
        return d.innerHTML;
    }

    function hubClass(status) {
        if (status === 'healthy' || status === 'ok' || status === 'active') return 'ok';
        if (status === 'unknown' || status === 'unconfigured' || status === 'disabled') return 'warn';
        return 'bad';
    }

    function playTone(freq, ms) {
        if (!soundsOn) return;
        try {
            var Ctx = global.AudioContext || global.webkitAudioContext;
            if (!Ctx) return;
            var ctx = new Ctx();
            var osc = ctx.createOscillator();
            var gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.frequency.value = freq;
            gain.gain.value = 0.04;
            osc.start();
            setTimeout(function () { osc.stop(); ctx.close(); }, ms || 120);
        } catch (e) { /* ignore */ }
    }

    function onLiveEvents(events) {
        if (!events || !events.length) return;
        var top = events[0];
        var sig = JSON.stringify(top);
        if (sig === lastSig) return;
        lastSig = sig;
        var kind = top.kind || top.type || '';
        if (kind === 'casino_win') playTone(880, 150);
        else if (kind === 'mn2_ledger') playTone(520, 100);
        else if (kind === 'customer_new') playTone(660, 180);
        else if (kind === 'customer_active') playTone(440, 90);
        renderFeed(events.slice(0, 12));
    }

    function tileHtml(label, value, sub, status) {
        return '<div class="am-tile ' + hubClass(status) + '">' +
            '<div class="am-tile-label">' + esc(label) + '</div>' +
            '<div class="am-tile-value">' + esc(value) + '</div>' +
            (sub ? '<div class="am-tile-sub">' + esc(sub) + '</div>' : '') +
            '</div>';
    }

    function renderStatus(data) {
        var root = global.document.getElementById('mn2-activity-monitor');
        if (!root || !data || !data.success) return;
        var tiles = data.tiles || {};
        var cust = tiles.customers || {};
        var disc = tiles.discord || {};
        var news = tiles.news || {};
        var tilesEl = root.querySelector('.am-tiles');
        if (tilesEl) {
            var discSub = disc.configured
                ? (disc.failures_recent || 0) + ' fail / ' + (disc.total_recent || 0) + ' recent'
                : 'webhook not set';
            var last = disc.last_post || {};
            if (last.ts) discSub += ' · last ' + String(last.ts).slice(0, 19).replace('T', ' ');
            tilesEl.innerHTML = [
                tileHtml('Customers', cust.total || 0, (cust.active_today || 0) + ' active today · ' + (cust.with_mn2 || 0) + ' with MN2', 'ok'),
                tileHtml('Discord feed', disc.status || '—', discSub, disc.status || 'unknown'),
                tileHtml('Platform news', news.count || 0, (news.channels || []).slice(0, 4).join(', ') || 'no channels', 'ok'),
            ].join('');
        }
        var newsEl = root.querySelector('.am-news');
        if (newsEl && data.news && data.news.length) {
            newsEl.innerHTML = data.news.slice(0, 5).map(function (n) {
                var ch = n.channel || n.category || 'general';
                return '<div class="am-news-item"><span class="am-news-ch">' + esc(ch) + '</span> ' +
                    esc(n.title || n.headline || 'News') + '</div>';
            }).join('');
        }
        var updated = root.querySelector('.am-updated');
        if (updated) updated.textContent = 'Updated ' + new Date().toLocaleTimeString();
    }

    function renderFeed(events) {
        var root = global.document.getElementById('mn2-activity-monitor');
        if (!root) return;
        var feed = root.querySelector('.am-feed');
        if (!feed) return;
        if (!events || !events.length) {
            feed.innerHTML = '<div class="am-feed-empty">No live events yet.</div>';
            return;
        }
        feed.innerHTML = events.map(function (ev) {
            var kind = ev.kind || ev.type || 'event';
            var payload = ev.payload || {};
            var avatar = payload.avatar_url || '/static/img/agents/default.svg';
            var user = ev.user_id ? '<img class="am-avatar" src="' + esc(avatar) + '" alt="" loading="lazy">' : '';
            return '<div class="am-feed-row kind-' + esc(kind) + '">' +
                user +
                '<div class="am-feed-body">' +
                '<span class="am-kind">' + esc(kind.replace(/_/g, ' ')) + '</span> ' +
                esc(ev.text || kind) +
                '<span class="am-ts">' + esc(String(ev.ts || '').slice(0, 19).replace('T', ' ')) + '</span>' +
                '</div></div>';
        }).join('');
    }

    function fetchStatus() {
        return fetch('/api/activity/monitor?news_limit=6&event_limit=15', { credentials: 'same-origin' })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                renderStatus(data);
                if (data.recent_events) onLiveEvents(data.recent_events);
            })
            .catch(function () {});
    }

    function connectSse() {
        if (es || typeof EventSource === 'undefined') return;
        es = new EventSource('/api/activity/stream?interval=12&sounds=' + (soundsOn ? '1' : '0'));
        es.onmessage = function (ev) {
            try {
                var data = JSON.parse(ev.data);
                if (data.type === 'activity' && data.events) onLiveEvents(data.events);
            } catch (e) { /* ignore */ }
        };
        es.onerror = function () {
            if (es) { es.close(); es = null; }
            setTimeout(connectSse, 15000);
        };
    }

    function mount(root) {
        if (!root || root.dataset.mounted === '1') return;
        root.dataset.mounted = '1';
        root.innerHTML =
            '<div class="am-head"><h3>Live activity monitor</h3>' +
            '<label class="am-sound-toggle"><input type="checkbox" class="am-sounds-cb"' + (soundsOn ? ' checked' : '') + '> Sounds</label></div>' +
            '<div class="am-tiles"></div>' +
            '<div class="am-section"><h4>Platform news</h4><div class="am-news"></div></div>' +
            '<div class="am-section"><h4>Live feed</h4><div class="am-feed"></div></div>' +
            '<div class="am-updated"></div>';
        var cb = root.querySelector('.am-sounds-cb');
        if (cb) {
            cb.addEventListener('change', function () {
                soundsOn = !!cb.checked;
                global.localStorage.setItem('mn2_activity_sounds', soundsOn ? '1' : '0');
            });
        }
        fetchStatus();
        connectSse();
        pollTimer = setInterval(fetchStatus, 30000);
    }

    function init() {
        var root = global.document.getElementById('mn2-activity-monitor');
        if (root) mount(root);
    }

    global.Mn2ActivityMonitor = { mount: mount, refresh: fetchStatus };

    if (global.document.readyState === 'loading') {
        global.document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})(window);
