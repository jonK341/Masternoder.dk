/**
 * Shared MN2 helpers for site pages (index, generator, aggregator, agents).
 */
(function (global) {
    'use strict';

    var BASE = global.location ? global.location.origin : '';

    function uid() {
        if (global.MnUserId && typeof global.MnUserId.read === 'function') return global.MnUserId.read();
        var raw = global.localStorage.getItem('game_user_id')
            || global.localStorage.getItem('user_id')
            || '';
        if (!raw || raw === '[object Promise]') return '';
        var lowered = String(raw).toLowerCase();
        if (lowered === 'default_user' || lowered === 'undefined' || lowered === 'null') return '';
        return String(raw).trim();
    }

    function fetchJson(url) {
        return fetch(url).then(function (r) {
            if (!r.ok) {
                return { success: false, unavailable: true, status: r.status };
            }
            return r.json();
        }).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'mn2-site-bridge.js', context: 'catch' }); }
            return { success: false, unavailable: true, status: 0 };
        });
    }

    function fmtMn2(n, digits) {
        var d = digits === undefined ? 4 : digits;
        var v = parseFloat(n);
        if (!isFinite(v)) return '0';
        return v.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: d });
    }

    /** Prefer ledger field; never treat casino/coins `balance` as MN2. */
    function pickLedgerBalance(d) {
        if (!d || typeof d !== 'object') return 0;
        if (d.mn2_balance != null && d.mn2_balance !== '') return Number(d.mn2_balance) || 0;
        if (d.liquid_mn2 != null && d.liquid_mn2 !== '') return Number(d.liquid_mn2) || 0;
        if (d.available != null && d.available !== '') return Number(d.available) || 0;
        // Last resort only when response is clearly an MN2-only payload (no coins currency).
        if (d.balance != null && d.currency !== 'coins' && d.active_currency !== 'coins') {
            return Number(d.balance) || 0;
        }
        return 0;
    }

    function pickUsdPrice(d) {
        if (!d || typeof d !== 'object') return null;
        var p = d.mn2_usd_price != null ? d.mn2_usd_price
            : (d.price_usd != null ? d.price_usd : d.usd);
        if (p == null || p === '') return null;
        var n = Number(p);
        return isFinite(n) ? n : null;
    }

    global.Mn2SiteBridge = {
        BASE: BASE,
        uid: uid,
        fmtMn2: fmtMn2,
        pickLedgerBalance: pickLedgerBalance,
        pickUsdPrice: pickUsdPrice,
        loadBalance: function () {
            return fetchJson(BASE + '/api/mn2/balance?user_id=' + encodeURIComponent(uid()));
        },
        loadPrice: function () {
            return fetchJson(BASE + '/api/mn2/price');
        },
        loadNetworkOverview: function () {
            return fetchJson(BASE + '/api/mn2/network-overview');
        },
        loadStakingMonitor: function () {
            return fetchJson(BASE + '/api/mn2/staking/monitor');
        },
        loadAgentStakingCapabilities: function () {
            return fetchJson(BASE + '/api/agent/staking/capabilities');
        },
        loadStatsSummary: function () {
            return fetchJson(BASE + '/api/stats/summary');
        },
    };
})(window);

;(function () {
  if (typeof window === 'undefined' || !window.ErrorManager || typeof window.ErrorManager.logJSError !== 'function') return;
  var source = 'mn2-site-bridge.js';
  window.addEventListener('error', function (event) {
    var file = (event && event.filename) || '';
    if (file.indexOf(source) === -1) return;
    window.ErrorManager.logJSError(event.error || new Error(event.message || 'script error'), { source: source, context: 'window_error' });
  });
})();
