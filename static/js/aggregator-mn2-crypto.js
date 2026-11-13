/**
 * MN2 crypto tiles for the aggregator monitor hub.
 */
(function () {
    'use strict';

    function uid() {
        try {
            return localStorage.getItem('game_user_id')
                || localStorage.getItem('user_id')
                || (window.MnUserId ? window.MnUserId.read() : '');
        } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'aggregator-mn2-crypto.js', context: 'catch' }); }
            return (window.MnUserId ? window.MnUserId.read() : '');
        }
    }

    function setText(id, text) {
        var el = document.getElementById(id);
        if (el) el.textContent = text;
    }

    function fmtDaemonVer(v) {
        if (v == null || v === '') return '—';
        var n = Number(v);
        if (!isNaN(n) && n >= 1000000) {
            var maj = Math.floor(n / 1000000);
            var min = Math.floor((n % 1000000) / 10000);
            var rev = Math.floor((n % 10000) / 100);
            var build = n % 100;
            return maj + '.' + min + '.' + rev + '.' + build;
        }
        return String(v);
    }

    function applyDaemonStats(ov) {
        if (!ov) return;
        var dm = ov.daemon || {};
        var h = ov.block_height != null ? ov.block_height : dm.block_height;
        if (h != null) {
            setText('agg-crypto-height', String(h));
            setText('agg-d-block', String(h));
        }
        if (dm.connections != null) {
            setText('agg-crypto-peers', String(dm.connections));
            setText('agg-d-peers', String(dm.connections));
        }
        if (dm.mempool_tx != null) {
            setText('agg-d-mempool', String(dm.mempool_tx));
        }
        if (dm.version != null) {
            setText('agg-d-ver', fmtDaemonVer(dm.version));
        }
        var stake = dm.staking_status || (ov.staking_health && ov.staking_health.staking_status_detail);
        if (typeof stake === 'object' && stake) {
            stake = stake.status || stake.staking_status;
        }
        if (stake) {
            var st = String(stake);
            setText('agg-crypto-stake', st.length > 18 ? st.slice(0, 16) + '…' : st);
            setText('agg-d-stake', st);
        } else if (ov.staking_health && ov.staking_health.status) {
            setText('agg-crypto-stake', String(ov.staking_health.status));
            setText('agg-d-stake', String(ov.staking_health.status));
        }
        if (dm.masternode_sync_pct != null) {
            setText('agg-d-mnsync', Number(dm.masternode_sync_pct).toFixed(1) + '%');
        }
        if (dm.header_lag != null) {
            setText('agg-d-lag', String(dm.header_lag));
        }
        if (dm.relay_fee != null) {
            setText('agg-d-relay', Number(dm.relay_fee).toFixed(6));
        }
        setText('agg-daemon-updated', 'Updated ' + new Date().toLocaleTimeString());
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
            }).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'aggregator-mn2-crypto.js', context: 'catch' }); }
                setText('agg-crypto-balance', '—');
            }),
            bridge.loadPrice().then(function (price) {
                if (price && price.mn2_usd_price != null) {
                    setText('agg-crypto-price', '$' + Number(price.mn2_usd_price).toFixed(4));
                }
            }).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'aggregator-mn2-crypto.js', context: 'catch' }); }}),
            bridge.loadStakingMonitor().then(function (mon) {
                if (!mon || !mon.success) return;
                var agg = mon.aggregates || {};
                var pool = agg.total_staked != null ? agg.total_staked : (mon.pool_balance || mon.total_staked);
                if (pool != null) setText('agg-crypto-pool', bridge.fmtMn2(pool, 2) + ' MN2');
            }).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'aggregator-mn2-crypto.js', context: 'catch' }); }
                setText('agg-crypto-pool', '—');
            }),
            bridge.loadStatsSummary().then(function (stats) {
                if (stats && stats.stats && stats.stats.total_users != null) {
                    setText('agg-crypto-users', String(stats.stats.total_users));
                } else if (stats && stats.success && stats.total_users != null) {
                    setText('agg-crypto-users', String(stats.total_users));
                }
            }).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'aggregator-mn2-crypto.js', context: 'catch' }); }
                setText('agg-crypto-users', '—');
            }),
            bridge.loadNetworkOverview().then(function (ov) {
                if (!ov) return;
                applyDaemonStats(ov);
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
            }).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'aggregator-mn2-crypto.js', context: 'catch' }); }
                setText('agg-crypto-market', '—');
                setText('agg-daemon-updated', 'Daemon stats unavailable');
            }),
            fetch('/api/aggregators/mn2/stats?user_id=' + encodeURIComponent(uid()))
                .then(function (r) { return r.json(); })
                .then(function (stats) {
                    if (!stats || !stats.success) return;
                    var earned = stats.earned_today_mn2;
                    if (earned != null) {
                        setText('agg-crypto-earned', bridge.fmtMn2(earned, 4) + ' MN2');
                    }
                }).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'aggregator-mn2-crypto.js', context: 'catch' }); }
                    setText('agg-crypto-earned', '—');
                }),
        ];

        Promise.all(tasks).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'aggregator-mn2-crypto.js', context: 'catch' }); }});
    }

    window.AggregatorMn2Hud = { refresh: loadAggCryptoHud };

    document.addEventListener('DOMContentLoaded', function () {
        loadAggCryptoHud();
        setInterval(loadAggCryptoHud, 120000);
    });
})();
