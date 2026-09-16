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
        loadExchangeWallet: function (userId) {
            var u = userId || uid();
            return fetchJson(BASE + '/api/exchange/wallet?user_id=' + encodeURIComponent(u));
        },
        loadMn2PoolStatus: function () {
            return fetchJson(BASE + '/api/exchange/mn2-pool/status');
        },
        loadSwoopAssets: function () {
            return fetchJson(BASE + '/api/exchange/swoop/assets');
        },
        loadWalletHub: function (userId) {
            var u = userId || uid();
            return fetchJson(BASE + '/api/exchange/wallet-hub?user_id=' + encodeURIComponent(u))
                .then(function (hub) {
                    if (!hub || !hub.success) {
                        return global.Mn2SiteBridge.loadExchangeWallet(u).then(function (wallet) {
                            return { success: !!(wallet && wallet.success), wallet: wallet, pool: null, swoop: null };
                        });
                    }
                    return {
                        success: true,
                        hub: hub,
                        wallet: {
                            success: true,
                            mn2_balance: hub.balances && hub.balances.MN2,
                            assets: { USDT: hub.balances && hub.balances.USDT, USDC: hub.balances && hub.balances.USDC },
                        },
                        pool: hub.pool,
                        swoop: { success: true, assets: hub.swoop_assets, pool_swap_reserve_bps: hub.pool_swap_reserve_bps, swap_back_hint: hub.swap_back_hint },
                    };
                });
        },
        swoopQuote: function (fromAsset, toAsset, amount, userId) {
            var u = userId || uid();
            return fetch(BASE + '/api/exchange/swoop/quote', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: u,
                    from_asset: fromAsset,
                    to_asset: toAsset,
                    amount: amount,
                }),
            }).then(function (r) { return r.json(); });
        },
        swoopExecute: function (fromAsset, toAsset, amount, quoteId, userId) {
            var u = userId || uid();
            return fetch(BASE + '/api/exchange/swoop', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: u,
                    from_asset: fromAsset,
                    to_asset: toAsset,
                    amount: amount,
                    quote_id: quoteId || '',
                }),
            }).then(function (r) { return r.json(); });
        },
    };
})(window);
