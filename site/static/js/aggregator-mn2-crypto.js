/**
 * MN2 crypto tiles for the aggregator monitor hub.
 */
(function () {
    'use strict';

    function uid() {
        try {
            return localStorage.getItem('game_user_id')
                || localStorage.getItem('user_id')
                || 'default_user';
        } catch (e) {
            return 'default_user';
        }
    }

    function setText(id, text) {
        var el = document.getElementById(id);
        if (el) el.textContent = text;
    }

    function loadAggCryptoHud() {
        var bridge = window.Mn2SiteBridge;
        if (!bridge) return;

        var tasks = [
            bridge.loadBalance().then(function (bal) {
                if (!bal || !bal.success) return;
                setText('agg-crypto-balance', bridge.fmtMn2(bal.mn2_balance, 4));
                if (bal.mn2_usd_price != null) {
                    setText('agg-crypto-price', '$' + Number(bal.mn2_usd_price).toFixed(4));
                }
            }).catch(function () {
                setText('agg-crypto-balance', '—');
            }),
            bridge.loadPrice().then(function (price) {
                if (price && price.mn2_usd_price != null) {
                    setText('agg-crypto-price', '$' + Number(price.mn2_usd_price).toFixed(4));
                }
            }).catch(function () {}),
            bridge.loadStakingMonitor().then(function (mon) {
                if (!mon || !mon.success) return;
                var agg = mon.aggregates || {};
                var pool = agg.total_staked != null ? agg.total_staked : (mon.pool_balance || mon.total_staked);
                if (pool != null) setText('agg-crypto-pool', bridge.fmtMn2(pool, 2) + ' MN2');
            }).catch(function () {
                setText('agg-crypto-pool', '—');
            }),
            bridge.loadStatsSummary().then(function (stats) {
                if (stats && stats.stats && stats.stats.total_users != null) {
                    setText('agg-crypto-users', String(stats.stats.total_users));
                } else if (stats && stats.success && stats.total_users != null) {
                    setText('agg-crypto-users', String(stats.total_users));
                }
            }).catch(function () {
                setText('agg-crypto-users', '—');
            }),
            bridge.loadNetworkOverview().then(function (ov) {
                if (!ov) return;
                var p2p = ov.p2p || {};
                var onramp = ov.onramp || {};
                var usd = (parseFloat(p2p.p2p_volume_usd_24h) || 0) + (parseFloat(onramp.onramp_volume_usd_24h) || 0);
                if (usd > 0) {
                    setText('agg-crypto-market', '$' + usd.toFixed(2) + ' / 24h');
                } else if (p2p.mn2_traded_24h != null && parseFloat(p2p.mn2_traded_24h) > 0) {
                    setText('agg-crypto-market', bridge.fmtMn2(p2p.mn2_traded_24h, 2) + ' MN2 / 24h');
                } else {
                    setText('agg-crypto-market', 'P2P · $0 / 24h');
                }
            }).catch(function () {
                setText('agg-crypto-market', '—');
            }),
            fetch('/api/aggregators/mn2/stats?user_id=' + encodeURIComponent(uid()))
                .then(function (r) { return r.json(); })
                .then(function (stats) {
                    if (!stats || !stats.success) return;
                    var earned = stats.earned_today_mn2;
                    if (earned != null) {
                        setText('agg-crypto-earned', bridge.fmtMn2(earned, 4) + ' MN2');
                    }
                }).catch(function () {
                    setText('agg-crypto-earned', '—');
                }),
        ];

        Promise.all(tasks).catch(function () {});
    }

    window.AggregatorMn2Hud = { refresh: loadAggCryptoHud };

    document.addEventListener('DOMContentLoaded', function () {
        loadAggCryptoHud();
        setInterval(loadAggCryptoHud, 120000);
    });
})();
