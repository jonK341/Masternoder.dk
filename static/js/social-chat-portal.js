/**
 * Social Chat Portal — cross-network monitor embed for /chat/, casino, game, social.
 */
(function (global) {
    'use strict';

    var _pollers = {};

    function uid() {
        return global.localStorage.getItem('game_user_id')
            || global.localStorage.getItem('user_id')
            || 'default_user';
    }

    function esc(s) {
        return String(s || '').replace(/[&<>"']/g, function (c) {
            return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c];
        });
    }

    function fxClass(fx) {
        if (!fx || fx === 'none') return '';
        return 'scp-fx-' + String(fx).replace(/^scp-fx-/, '').replace(/_/g, '-');
    }

    function renderMessages(feedEl, messages, fxMap) {
        if (!feedEl) return;
        if (!messages || !messages.length) {
            feedEl.innerHTML = '<p style="opacity:0.65;margin:0;">No messages yet — cross-post to all networks!</p>';
            return;
        }
        var nearBottom = feedEl.scrollHeight - feedEl.scrollTop - feedEl.clientHeight < 48;
        feedEl.innerHTML = messages.map(function (m) {
            var ts = m.created_at ? new Date(m.created_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }) : '';
            var nets = (m.networks || ['site']).map(function (n) { return esc(n); }).join(' · ');
            var fx = fxClass(m.fx);
            var fxDef = (fxMap && m.fx && fxMap[m.fx]) ? fxMap[m.fx].class : '';
            return '<div class="scp-msg ' + esc(fxDef || fx) + '">' +
                '<div><strong>' + esc(m.display_name || m.user_id) + '</strong>' +
                '<span class="scp-msg-meta"> ' + esc(ts) + '</span>' +
                '<span class="scp-msg-nets">→ ' + nets + '</span></div>' +
                '<div>' + esc(m.message) + '</div></div>';
        }).join('');
        if (nearBottom) feedEl.scrollTop = feedEl.scrollHeight;
    }

    function loadFeed(feedEl, opts) {
        opts = opts || {};
        var base = global.location.origin || '';
        var q = '/api/social/chat/unified?limit=' + (opts.limit || 40);
        if (opts.network) q += '&network=' + encodeURIComponent(opts.network);
        return fetch(base + q).then(function (r) { return r.json(); }).then(function (d) {
            if (d && d.success) renderMessages(feedEl, d.messages, opts.fxMap);
            return d;
        });
    }

    function sendMessage(opts) {
        var base = global.location.origin || '';
        var body = {
            user_id: opts.userId || uid(),
            message: opts.message,
            cross_post: true,
            fx: opts.fx || 'none',
            source_site: opts.sourceSite || 'portal',
        };
        if (opts.networks) body.networks = opts.networks;
        return fetch(base + '/api/social/chat/cross-send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        }).then(function (r) { return r.json(); });
    }

    function stopPoll(key) {
        if (_pollers[key]) {
            clearInterval(_pollers[key]);
            delete _pollers[key];
        }
    }

    function startPoll(key, fn, ms) {
        stopPoll(key);
        _pollers[key] = setInterval(fn, ms || 12000);
    }

    function mount(container, options) {
        options = options || {};
        if (!container) return null;
        var mode = options.mode || 'compact';
        var sourceSite = options.site || 'embed';
        var userId = options.userId || uid();
        var pollKey = container.id || ('scp_' + Math.random().toString(36).slice(2));
        var activeNet = '';

        container.innerHTML = '';
        container.classList.add('scp-root', mode === 'full' ? 'scp-full' : 'scp-compact');

        var header = document.createElement('div');
        header.className = 'scp-header';
        header.innerHTML = '<h2>💬 Social Chat Monitor</h2>' +
            (mode !== 'full' ? '<a href="/chat/">Open full hub ↗</a>' : '');
        container.appendChild(header);

        var netBar = document.createElement('div');
        netBar.className = 'scp-net-bar';
        container.appendChild(netBar);

        if (mode === 'full') {
            var monitor = document.createElement('div');
            monitor.className = 'scp-monitor-grid';
            monitor.id = pollKey + '_mon';
            container.appendChild(monitor);
        }

        var feed = document.createElement('div');
        feed.className = 'scp-feed';
        feed.id = pollKey + '_feed';
        container.appendChild(feed);

        var compose = document.createElement('div');
        compose.className = 'scp-compose';
        compose.innerHTML =
            '<input type="text" class="scp-input" placeholder="Cross-post to all networks…" maxlength="1000" />' +
            '<select class="scp-fx" aria-label="Message effect"><option value="none">FX: Plain</option></select>' +
            '<label class="scp-cross-label"><input type="checkbox" class="scp-cross" checked /> All networks</label>' +
            '<button type="button" class="scp-send">Send</button>';
        container.appendChild(compose);

        var input = compose.querySelector('.scp-input');
        var fxSel = compose.querySelector('.scp-fx');
        var crossCb = compose.querySelector('.scp-cross');
        var sendBtn = compose.querySelector('.scp-send');
        var hubCfg = { networks: [], fx_effects: [], default_cross_networks: ['site'] };

        function refresh() {
            return loadFeed(feed, { limit: options.limit || 50, network: activeNet || null, fxMap: hubCfg.fxMap }).then(function () {
                if (mode === 'full' && monitor) {
                    fetch((global.location.origin || '') + '/api/social/chat/hub/monitor')
                        .then(function (r) { return r.json(); })
                        .then(function (d) {
                            if (!d || !d.success) return;
                            var t = d.totals || {};
                            monitor.innerHTML =
                                '<div class="scp-monitor-stat"><strong>' + (t.messages || 0) + '</strong>msgs</div>' +
                                Object.keys(t.by_network || {}).slice(0, 6).map(function (k) {
                                    return '<div class="scp-monitor-stat"><strong>' + t.by_network[k] + '</strong>' + esc(k) + '</div>';
                                }).join('');
                        });
                }
            });
        }

        fetch((global.location.origin || '') + '/api/social/chat/hub').then(function (r) { return r.json(); }).then(function (cfg) {
            if (!cfg || !cfg.success) return;
            hubCfg = cfg;
            hubCfg.fxMap = {};
            (cfg.fx_effects || []).forEach(function (f) { hubCfg.fxMap[f.id] = f; });
            netBar.innerHTML = '<button type="button" class="scp-net-chip active" data-net="">All</button>' +
                (cfg.networks || []).map(function (n) {
                    return '<button type="button" class="scp-net-chip" data-net="' + esc(n.id) + '">' +
                        esc(n.icon || '') + ' ' + esc(n.label) + '</button>';
                }).join('');
            netBar.querySelectorAll('.scp-net-chip').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    netBar.querySelectorAll('.scp-net-chip').forEach(function (b) { b.classList.remove('active'); });
                    btn.classList.add('active');
                    activeNet = btn.getAttribute('data-net') || '';
                    refresh();
                });
            });
            (cfg.fx_effects || []).forEach(function (f) {
                if (f.id === 'none') return;
                var opt = document.createElement('option');
                opt.value = f.id;
                opt.textContent = 'FX: ' + f.label;
                fxSel.appendChild(opt);
            });
        }).finally(refresh);

        function doSend() {
            var text = (input.value || '').trim();
            if (!text) return;
            sendBtn.disabled = true;
            sendMessage({
                userId: userId,
                message: text,
                fx: fxSel.value,
                sourceSite: sourceSite,
                networks: crossCb.checked ? null : [activeNet || 'site'],
            }).then(function (d) {
                sendBtn.disabled = false;
                if (d && d.success) {
                    input.value = '';
                    refresh();
                }
            }).catch(function () { sendBtn.disabled = false; });
        }

        sendBtn.addEventListener('click', doSend);
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); doSend(); }
        });

        if (options.poll !== false) startPoll(pollKey, refresh, options.intervalMs || 12000);

        return {
            refresh: refresh,
            destroy: function () { stopPoll(pollKey); },
        };
    }

    global.SocialChatPortal = {
        mount: mount,
        loadFeed: loadFeed,
        sendMessage: sendMessage,
        stopAll: function () { Object.keys(_pollers).forEach(stopPoll); },
    };
})(typeof window !== 'undefined' ? window : this);
