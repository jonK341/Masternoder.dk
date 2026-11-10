/**
 * Auto-init standard MN2 page strips (balance + USD rate + optional extra fetch nodes).
 * Mark strip: class="mn2-page-strip" data-mn2-auto data-balance-id="..." data-rate-id="..."
 * Extra metric: <strong id="x" data-mn2-extra="/api/..." data-mn2-extra-key="config.rake.tournaments" data-mn2-extra-format="text"></strong>
 * Balance uses /api/mn2/balance/fast; refreshes every 90s when a balance is present.
 */
(function (global) {
    'use strict';

    var REFRESH_MS = 90000;
    var _timers = [];

    function fmt(n) {
        var bridge = global.Mn2SiteBridge;
        return bridge ? bridge.fmtMn2(n) : String(n);
    }

    function pick(obj, path) {
        if (!path) return obj;
        return String(path).split('.').reduce(function (o, k) {
            return o && o[k] !== undefined ? o[k] : undefined;
        }, obj);
    }

    function initExtra(node) {
        var url = node.getAttribute('data-mn2-extra');
        if (!url) return;
        var key = node.getAttribute('data-mn2-extra-key') || 'value';
        var format = node.getAttribute('data-mn2-extra-format') || 'text';
        fetch(url, { credentials: 'same-origin' }).then(function (r) { return r.json(); }).then(function (d) {
            var val = pick(d, key);
            if (val == null) return;
            if (format === 'mn2') {
                node.textContent = fmt(val) + ' MN2';
            } else if (format === 'percent') {
                node.textContent = String(val) + '%';
            } else {
                node.textContent = String(val);
            }
        }).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'mn2-page-strip-init.js', context: 'catch' }); } /* ignore */ });
    }

    function paintStripBalance(strip, d) {
        var balanceId = strip.getAttribute('data-balance-id');
        if (!balanceId) return;
        var el = global.document.getElementById(balanceId);
        if (!el) return;
        if (!d || d.unavailable || (d.mn2_balance == null && d.balance == null)) {
            el.textContent = '—';
            return;
        }
        var bal = d.mn2_balance != null ? d.mn2_balance : d.balance;
        el.textContent = fmt(bal) + ' MN2';
    }

    function initStrip(strip) {
        var bridge = global.Mn2SiteBridge;
        if (!bridge) return;
        var rateId = strip.getAttribute('data-rate-id');

        bridge.loadFastBalance().then(function (d) {
            paintStripBalance(strip, d);
            if (d && d.mn2_balance != null) {
                var t = setInterval(function () {
                    bridge.loadFastBalance().then(function (again) {
                        paintStripBalance(strip, again);
                    }).catch(function () { /* ignore */ });
                }, REFRESH_MS);
                _timers.push(t);
            }
        }).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'mn2-page-strip-init.js', context: 'catch' }); }
            paintStripBalance(strip, null);
        });

        bridge.loadPrice().then(function (d) {
            var p = d && (d.mn2_usd_price != null ? d.mn2_usd_price : (d.price_usd != null ? d.price_usd : d.usd));
            if (rateId) {
                var el = global.document.getElementById(rateId);
                if (el) el.textContent = p != null ? ('$' + Number(p).toFixed(4) + ' / MN2') : '—';
            }
        }).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'mn2-page-strip-init.js', context: 'catch' }); }
            if (rateId) {
                var el = global.document.getElementById(rateId);
                if (el) el.textContent = '—';
            }
        });

        strip.querySelectorAll('[data-mn2-extra]').forEach(initExtra);
    }

    function init() {
        global.document.querySelectorAll('.mn2-page-strip[data-mn2-auto]').forEach(initStrip);
    }

    global.Mn2PageStripInit = { init: init, initStrip: initStrip };
    global.document.addEventListener('DOMContentLoaded', init);
})(window);

;(function () {
  if (typeof window === 'undefined' || !window.ErrorManager || typeof window.ErrorManager.logJSError !== 'function') return;
  var source = 'mn2-page-strip-init.js';
  window.addEventListener('error', function (event) {
    var file = (event && event.filename) || '';
    if (file.indexOf(source) === -1) return;
    window.ErrorManager.logJSError(event.error || new Error(event.message || 'script error'), { source: source, context: 'window_error' });
  });
})();
