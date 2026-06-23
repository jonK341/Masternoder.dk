/**
 * Global MN2 activity SSE + optional sound cues for wins / ledger events.
 */
(function (global) {
    'use strict';

    var es = null;
    var lastEventKey = '';
    var enabled = global.localStorage.getItem('mn2_activity_sounds') !== '0';

    function playTone(freq, ms) {
        if (!enabled) return;
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

    function onEvents(events) {
        if (!events || !events.length) return;
        var top = events[0];
        var key = (top.kind || '') + '|' + (top.ts || '') + '|' + (top.text || '');
        if (key === lastEventKey) return;
        lastEventKey = key;
        if (top.kind === 'casino_win') playTone(880, 150);
        else if (top.kind === 'mn2_ledger') playTone(520, 100);
        var panel = global.document.getElementById('mn2-activity-toast');
        if (panel && top.text) {
            panel.textContent = top.text;
            panel.style.opacity = '1';
            setTimeout(function () { panel.style.opacity = '0'; }, 4000);
        }
    }

    function connect() {
        if (es) return;
        if (typeof EventSource === 'undefined') return;
        var sounds = enabled ? '1' : '0';
        es = new EventSource('/api/activity/stream?interval=12&sounds=' + sounds);
        es.onmessage = function (ev) {
            try {
                var data = JSON.parse(ev.data);
                if (data.type === 'activity' && data.events) onEvents(data.events);
            } catch (e) { /* ignore */ }
        };
        es.onerror = function () {
            if (es) { es.close(); es = null; }
            setTimeout(connect, 15000);
        };
    }

    function injectToast() {
        if (global.document.getElementById('mn2-activity-toast')) return;
        var el = global.document.createElement('div');
        el.id = 'mn2-activity-toast';
        el.setAttribute('aria-live', 'polite');
        el.style.cssText = 'position:fixed;bottom:72px;right:16px;max-width:280px;padding:10px 14px;border-radius:12px;background:rgba(0,30,20,0.92);border:1px solid rgba(0,255,136,0.35);color:#00ff88;font-size:0.82rem;z-index:9998;opacity:0;transition:opacity 0.3s;pointer-events:none;';
        global.document.body.appendChild(el);
    }

    global.Mn2ActivityStream = {
        connect: connect,
        setSounds: function (on) {
            enabled = !!on;
            global.localStorage.setItem('mn2_activity_sounds', on ? '1' : '0');
        },
    };

    global.document.addEventListener('DOMContentLoaded', function () {
        injectToast();
        connect();
    });
})(window);
