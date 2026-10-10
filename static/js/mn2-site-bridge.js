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

    global.Mn2SiteBridge = {
        BASE: BASE,
        uid: uid,
        fmtMn2: fmtMn2,
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
