/**
 * P7 explorer widgets: mempool feed, staking calc, 30d price, pool stake chart,
 * order book mini, fork alert, chain sync.
 */
(function () {
  'use strict';

  function q(id) { return document.getElementById(id); }

  function fmtNum(n, d) {
    if (n == null || n === '' || isNaN(Number(n))) return '—';
    return Number(n).toLocaleString(undefined, {
      minimumFractionDigits: d == null ? 0 : d,
      maximumFractionDigits: d == null ? 0 : d,
    });
  }

  function shortHash(h) {
    if (!h || h.length < 16) return h || '—';
    return h.slice(0, 8) + '…' + h.slice(-8);
  }

  function areaChart(values, w, h) {
    w = w || 320;
    h = h || 72;
    var pts = (values || []).filter(function (v) { return v != null && !isNaN(Number(v)); }).map(Number);
    if (pts.length < 2) {
      return '<div class="ex-p7-empty">Not enough data yet</div>';
    }
    var pad = 4;
    var min = Math.min.apply(null, pts);
    var max = Math.max.apply(null, pts);
    var range = (max - min) || 1;
    var step = w / (pts.length - 1);
    var coords = pts.map(function (v, i) {
      return [i * step, h - pad - ((v - min) / range) * (h - pad * 2)];
    });
    var line = coords.map(function (c, i) {
      return (i === 0 ? 'M' : 'L') + c[0].toFixed(1) + ',' + c[1].toFixed(1);
    }).join(' ');
    var up = pts[pts.length - 1] >= pts[0];
    var color = up ? '#00ff88' : '#ff7a7a';
    return '<svg viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="none" class="ex-p7-svg">' +
      '<path d="' + line + '" fill="none" stroke="' + color + '" stroke-width="1.8"/></svg>';
  }

  function barCompare(pool, network) {
    pool = Number(pool) || 0;
    network = Number(network) || 0;
    if (!pool && !network) {
      return '<div class="ex-p7-empty">Stake data unavailable</div>';
    }
    var total = pool + network;
    var poolPct = total ? (pool / total) * 100 : 0;
    var netPct = total ? (network / total) * 100 : 0;
    return '<div class="ex-stake-bars">' +
      '<div class="ex-stake-row"><span>Pool</span><div class="ex-stake-track"><div class="ex-stake-fill pool" style="width:' + poolPct.toFixed(1) + '%"></div></div><span>' + fmtNum(pool, 0) + ' (' + poolPct.toFixed(1) + '%)</span></div>' +
      '<div class="ex-stake-row"><span>Network</span><div class="ex-stake-track"><div class="ex-stake-fill net" style="width:' + netPct.toFixed(1) + '%"></div></div><span>' + fmtNum(network, 0) + ' (' + netPct.toFixed(1) + '%)</span></div>' +
      '</div>';
  }

  function loadMempoolFeed() {
    fetch('/api/mn2/mempool', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var feed = q('ex-mempool-feed');
        var meta = q('ex-mempool-meta');
        if (!feed) return;
        var txids = (d && d.sample_txids) ? d.sample_txids : [];
        if (meta) meta.textContent = (d && d.size != null) ? (d.size + ' pending') : '—';
        if (!txids.length) {
          feed.innerHTML = '<li class="ex-p7-empty">Mempool empty or unavailable</li>';
          return;
        }
        feed.innerHTML = txids.map(function (txid) {
          return '<li><a href="/explorer/tx/' + encodeURIComponent(txid) + '">' + shortHash(txid) + '</a></li>';
        }).join('');
      })
      .catch(function () {
        var feed = q('ex-mempool-feed');
        if (feed) feed.innerHTML = '<li class="ex-p7-empty">Mempool unavailable</li>';
      });
  }

  function updateCalc() {
    var amount = Number((q('ex-calc-amount') && q('ex-calc-amount').value) || 0);
    var days = Number((q('ex-calc-days') && q('ex-calc-days').value) || 30);
    var uptimeEl = q('ex-calc-uptime');
    var uptime = uptimeEl ? Number(uptimeEl.value) / 100 : 0.95;
    var label = q('ex-calc-uptime-label');
    if (label && uptimeEl) label.textContent = uptimeEl.value + '%';
    if (!amount || amount <= 0) {
      var res = q('ex-calc-result');
      if (res) res.textContent = 'Enter an amount to estimate rewards';
      return;
    }
    fetch('/api/mn2/staking/calculator?amount=' + encodeURIComponent(amount) +
      '&days=' + encodeURIComponent(days) + '&uptime=' + encodeURIComponent(uptime),
      { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var el = q('ex-calc-result');
        if (!el) return;
        if (!d || d.success === false) {
          el.textContent = 'Calculator unavailable';
          return;
        }
        var reward = d.projected_reward != null ? d.projected_reward : d.reward;
        var apr = d.apr_percent != null ? d.apr_percent : d.apr;
        el.innerHTML = '<strong>~' + fmtNum(reward, 4) + ' MN2</strong> over ' + days + 'd' +
          (apr != null ? ' <span class="ex-calc-apr">(' + fmtNum(apr, 2) + '% APR est.)</span>' : '');
      })
      .catch(function () {
        var el = q('ex-calc-result');
        if (el) el.textContent = 'Calculator unavailable';
      });
  }

  function initCalc() {
    ['ex-calc-amount', 'ex-calc-days', 'ex-calc-uptime'].forEach(function (id) {
      var el = q(id);
      if (el) el.addEventListener('input', updateCalc);
    });
    updateCalc();
  }

  function loadPriceChart() {
    fetch('/api/mn2/explorer/price-history', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var chart = q('ex-price-chart');
        var meta = q('ex-price-meta');
        if (!chart) return;
        var series = (d && d.series) ? d.series : [];
        if (meta) meta.textContent = series.length ? (series.length + ' snapshots') : 'no history';
        var prices = series.map(function (p) { return p.price; });
        chart.innerHTML = areaChart(prices);
      })
      .catch(function () {
        var chart = q('ex-price-chart');
        if (chart) chart.innerHTML = '<div class="ex-p7-empty">Price history unavailable</div>';
      });
  }

  function loadStakeChart() {
    fetch('/api/mn2/network-overview', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var chart = q('ex-stake-chart');
        var meta = q('ex-stake-meta');
        if (!chart || !d) return;
        var pool = d.pool_total_staked;
        var network = d.staking_weight || d.network_hashps;
        if (meta) {
          meta.textContent = (pool != null && network != null) ? 'live' : 'partial data';
        }
        chart.innerHTML = barCompare(pool, network);
      })
      .catch(function () {
        var chart = q('ex-stake-chart');
        if (chart) chart.innerHTML = '<div class="ex-p7-empty">Stake comparison unavailable</div>';
      });
  }

  function loadOrderBook() {
    Promise.all([
      fetch('/api/market/ticker', { credentials: 'same-origin' }).then(function (r) { return r.json(); }),
      fetch('/api/market/orders?limit=5', { credentials: 'same-origin' }).then(function (r) { return r.json(); }),
    ]).then(function (parts) {
      var ticker = parts[0];
      var orders = parts[1];
      var tickEl = q('ex-ob-ticker');
      var listEl = q('ex-ob-orders');
      if (tickEl && ticker) {
        tickEl.innerHTML =
          '<span>Bid <strong>' + (ticker.best_bid != null ? fmtNum(ticker.best_bid, 2) : '—') + '</strong></span>' +
          '<span>Ask <strong>' + (ticker.best_ask != null ? fmtNum(ticker.best_ask, 2) : '—') + '</strong></span>' +
          '<span>Last <strong>' + (ticker.last_price_coins_per_mn2 != null ? fmtNum(ticker.last_price_coins_per_mn2, 2) : '—') + '</strong></span>';
      }
      if (!listEl) return;
      var rows = (orders && orders.orders) ? orders.orders.slice(0, 5) : [];
      if (!rows.length) {
        listEl.innerHTML = '<li class="ex-p7-empty">No open orders</li>';
        return;
      }
      listEl.innerHTML = rows.map(function (o) {
        var side = (o.side || o.type || '').toUpperCase();
        return '<li><span class="ex-ob-side ' + side.toLowerCase() + '">' + side + '</span> ' +
          fmtNum(o.amount_mn2 || o.amount, 2) + ' @ ' + fmtNum(o.price_coins_per_mn2 || o.price, 2) + '</li>';
      }).join('');
    }).catch(function () {
      var tickEl = q('ex-ob-ticker');
      if (tickEl) tickEl.textContent = 'Market unavailable';
    });
  }

  function loadChainSync() {
    fetch('/api/mn2/explorer/chain-sync', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var el = q('ex-sync-stats');
        if (!el || !d) return;
        var vp = d.verification_progress;
        var vpPct = vp != null ? (Number(vp) * 100).toFixed(2) + '%' : '—';
        el.innerHTML =
          '<div class="ex-sync-row"><span>Blocks</span><strong>' + fmtNum(d.blocks, 0) + '</strong></div>' +
          '<div class="ex-sync-row"><span>Headers</span><strong>' + fmtNum(d.headers, 0) + '</strong></div>' +
          '<div class="ex-sync-row"><span>Behind</span><strong>' + fmtNum(d.headers_behind, 0) + '</strong></div>' +
          '<div class="ex-sync-row"><span>Verified</span><strong>' + vpPct + '</strong></div>' +
          '<div class="ex-sync-row"><span>Synced</span><strong>' + (d.synced === true ? 'Yes' : (d.synced === false ? 'No' : '—')) + '</strong></div>';
      })
      .catch(function () {
        var el = q('ex-sync-stats');
        if (el) el.textContent = 'Sync status unavailable';
      });
  }

  function loadForkAlert() {
    fetch('/api/mn2/explorer/fork-status', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var el = q('ex-fork-alert');
        if (!el) return;
        if (d && d.fork_risk) {
          el.hidden = false;
          el.textContent = d.message || 'Possible fork detected — headers ahead of blocks.';
        } else {
          el.hidden = true;
          el.textContent = '';
        }
      })
      .catch(function () {});
  }

  function init() {
    var panel = document.querySelector('.mn2-tab-panel[data-mn2-tab="explorer"]');
    if (!panel || !q('ex-p7-grid')) return;
    loadMempoolFeed();
    initCalc();
    loadPriceChart();
    loadStakeChart();
    loadOrderBook();
    loadChainSync();
    loadForkAlert();
    setInterval(loadMempoolFeed, 20000);
    setInterval(loadForkAlert, 60000);
    setInterval(loadOrderBook, 45000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
