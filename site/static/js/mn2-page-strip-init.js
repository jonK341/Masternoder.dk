/**
 * Auto-init standard MN2 page strips (balance + USD rate + optional extra fetch nodes).
 * Mark strip: class="mn2-page-strip" data-mn2-auto data-balance-id="..." data-rate-id="..."
 * Extra metric: <strong id="x" data-mn2-extra="/api/..." data-mn2-extra-key="config.rake.tournaments" data-mn2-extra-format="text"></strong>
 */
(function (global) {
    'use strict';

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
        fetch(url).then(function (r) { return r.json(); }).then(function (d) {
            var val = pick(d, key);
            if (val == null) return;
            if (format === 'mn2') {
                node.textContent = fmt(val) + ' MN2';
            } else if (format === 'percent') {
                node.textContent = String(val) + '%';
            } else {
                node.textContent = String(val);
            }
        }).catch(function () { /* ignore */ });
    }

    function initStrip(strip) {
        var bridge = global.Mn2SiteBridge;
        if (!bridge) return;
        var balanceId = strip.getAttribute('data-balance-id');
        var rateId = strip.getAttribute('data-rate-id');

        bridge.loadBalance().then(function (d) {
            var bal = (d && (d.balance != null ? d.balance : d.mn2_balance)) || 0;
            if (balanceId) {
                var el = global.document.getElementById(balanceId);
                if (el) el.textContent = fmt(bal) + ' MN2';
            }
        }).catch(function () {
            if (balanceId) {
                var el = global.document.getElementById(balanceId);
                if (el) el.textContent = '—';
            }
        });

        bridge.loadPrice().then(function (d) {
            var p = d && (d.price_usd != null ? d.price_usd : d.usd);
            if (rateId) {
                var el = global.document.getElementById(rateId);
                if (el) el.textContent = p != null ? ('$' + Number(p).toFixed(4) + ' / MN2') : '—';
            }
        }).catch(function () {
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
