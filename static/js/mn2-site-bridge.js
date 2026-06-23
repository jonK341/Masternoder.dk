/**
 * Shared MN2 helpers for site pages (index, generator, aggregator, agents).
 */
(function (global) {
    'use strict';

    var BASE = global.location ? global.location.origin : '';

    function uid() {
        return global.localStorage.getItem('game_user_id')
            || global.localStorage.getItem('user_id')
            || 'default_user';
    }

    function fetchJson(url) {
        return fetch(url).then(function (r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
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
