/* MN2 explorer overview - polls /api/mn2/network-overview and renders network + pool + market tiles.
   Source priority is decided server-side (self-hosted explorer -> RPC -> Chainz); each field's
   origin is shown via the `source` map. Tiles show "—" when a stat is unavailable. */
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

  function fmtCompact(n) {
    if (n == null || isNaN(Number(n))) return '—';
    var v = Number(n);
    if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(2) + 'B';
    if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(2) + 'M';
    if (Math.abs(v) >= 1e3) return (v / 1e3).toFixed(2) + 'K';
    return fmtNum(v, 0);
  }

  function setSrc(id, source, key) {
    var s = (source && source[key]) ? source[key] : '';
    q(id).textContent = s ? ('src: ' + s) : '';
  }

  var explorerBase = 'https://chainz.cryptoid.info/mn2/';

  function renderHealth(sh) {
    var el = q('ex-health');
    if (!el) return;
    if (!sh || !sh.status) { el.style.display = 'none'; return; }
    var st = sh.status;
    var cls = 'warn', msg;
    if (st === 'active') { cls = 'ok'; msg = '🟢 Daemon staking active — pool is minting blocks.'; }
    else if (st === 'inactive') { cls = 'warn'; msg = '🟠 Daemon staking inactive' + (sh.staking_status_detail && sh.staking_status_detail.mnsync === false ? ' (masternode sync in progress).' : ' — not minting, realized yield is 0.'); }
    else if (st === 'unreachable') { cls = 'bad'; msg = '🔴 Daemon unreachable — stats may be stale.'; }
    else { el.style.display = 'none'; return; }
    el.className = 'ex-health ' + cls;
    el.textContent = msg;
    el.style.display = 'block';
  }

  function explorerLink(term) {
    var base = (explorerBase || 'https://chainz.cryptoid.info/mn2/').replace(/\/+$/, '');
    var isChainz = /chainz\.cryptoid/.test(base);
    var isTx = /^[0-9a-fA-F]{64}$/.test(term);
    if (isChainz) return base + (isTx ? '/tx.dws?txid=' : '/address.dws?addr=') + encodeURIComponent(term);
    return base + (isTx ? '/tx/' : '/address/') + encodeURIComponent(term);
  }

  function sparkline(elId, values) {
    var el = q(elId);
    if (!el) return;
    var pts = (values || []).filter(function (v) { return v != null && !isNaN(Number(v)); }).map(Number);
    if (pts.length < 2) { el.innerHTML = ''; return; }
    var w = 120, h = 26, min = Math.min.apply(null, pts), max = Math.max.apply(null, pts);
    var range = (max - min) || 1;
    var step = w / (pts.length - 1);
    var d = pts.map(function (v, i) {
      var x = (i * step).toFixed(1);
      var y = (h - 2 - ((v - min) / range) * (h - 4)).toFixed(1);
      return (i === 0 ? 'M' : 'L') + x + ',' + y;
    }).join(' ');
    var up = pts[pts.length - 1] >= pts[0];
    var color = up ? '#00ff88' : '#ff7a7a';
    el.innerHTML = '<svg viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="none">' +
      '<path d="' + d + '" fill="none" stroke="' + color + '" stroke-width="1.5"/></svg>';
  }

  function loadSparklines() {
    fetch('/api/mn2/network-history?hours=24&limit=300', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d || !d.success || !d.history) return;
        var hist = d.history;
        sparkline('sp-price', hist.map(function (r) { return r.mn2_usd_price; }));
        sparkline('sp-diff', hist.map(function (r) { return r.difficulty; }));
        sparkline('sp-weight', hist.map(function (r) { return r.network_hashps != null ? r.network_hashps : r.staking_weight; }));
        sparkline('sp-pool', hist.map(function (r) { return r.pool_total_staked; }));
        sparkline('sp-conn', hist.map(function (r) { return r.connections; }));
        sparkline('sp-mempool', hist.map(function (r) { return r.mempool_tx; }));
      })
      .catch(function () {});
  }

  function render(d) {
    if (!d || !d.success) return;
    var src = d.source || {};

    q('t-price').textContent = d.mn2_usd_price != null ? ('$' + fmtNum(d.mn2_usd_price, 4)) : '—';
    setSrc('s-price', src, 'mn2_usd_price');

    q('t-height').textContent = fmtNum(d.block_height, 0);
    setSrc('s-height', src, 'block_height');

    q('t-diff').textContent = fmtNum(d.difficulty, 2);
    setSrc('s-diff', src, 'difficulty');

    q('t-mn').textContent = fmtNum(d.masternode_count, 0);
    setSrc('s-mn', src, 'masternode_count');

    var weight = d.network_hashps != null ? d.network_hashps : d.staking_weight;
    q('t-weight').textContent = weight != null ? (fmtCompact(weight) + ' H/s') : '—';

    var pool = Number(d.pool_total_staked || 0);
    q('t-pool').textContent = fmtNum(pool, 2) + ' MN2';
    q('t-poolapr').textContent = d.pool_apr_percent != null ? (fmtNum(d.pool_apr_percent, 2) + '%') : '—';

    var price = Number(d.mn2_usd_price || 0);
    q('t-poolusd').textContent = (price > 0) ? ('$' + fmtNum(pool * price, 2)) : '—';

    var supply = d.circulating_supply;
    q('t-supply').textContent = supply != null ? (fmtCompact(supply) + ' MN2') : '—';
    setSrc('s-supply', src, 'circulating_supply');
    q('t-poolshare').textContent = (supply && Number(supply) > 0) ? ((pool / Number(supply)) * 100).toFixed(4) + '%' : '—';

    var on = d.onramp || {};
    var p2p = d.p2p || {};
    var hasMarket = (d.onramp && Object.keys(on).length) || (d.p2p && Object.keys(p2p).length);
    if (hasMarket) {
      q('market-title').style.display = '';
      q('ex-market').style.display = '';
      q('t-onvol').textContent = on.onramp_volume_usd_24h != null ? ('$' + fmtNum(on.onramp_volume_usd_24h, 2)) : '—';
      q('t-onmn2').textContent = on.mn2_sold_24h != null ? (fmtNum(on.mn2_sold_24h, 4) + ' MN2') : '—';
      q('t-p2pvol').textContent = p2p.p2p_volume_usd_24h != null ? ('$' + fmtNum(p2p.p2p_volume_usd_24h, 2)) : '—';
      q('t-p2plist').textContent = p2p.open_listings != null ? fmtNum(p2p.open_listings, 0) : '—';
    }

    if (d.explorer_base_url) {
      explorerBase = d.explorer_base_url;
      q('ex-open').href = d.explorer_base_url;
    }

    renderHealth(d.staking_health);
    renderDaemon(d.daemon);

    q('ex-updated').textContent = 'Updated ' + new Date().toLocaleTimeString();
  }

  function fmtBytes(n) {
    if (n == null || isNaN(Number(n))) return '—';
    var v = Number(n);
    if (v >= 1e9) return (v / 1e9).toFixed(2) + ' GB';
    if (v >= 1e6) return (v / 1e6).toFixed(2) + ' MB';
    if (v >= 1e3) return (v / 1e3).toFixed(2) + ' KB';
    return fmtNum(v, 0) + ' B';
  }

  function renderDaemon(dm) {
    dm = dm || {};
    var state = q('daemon-state');
    if (state) state.textContent = dm.reachable ? '— online' : '— unreachable';
    q('t-conn').textContent = dm.connections != null ? fmtNum(dm.connections, 0) : '—';
    q('t-mempool').textContent = dm.mempool_tx != null ? (fmtNum(dm.mempool_tx, 0) + (dm.mempool_bytes != null ? ' · ' + fmtBytes(dm.mempool_bytes) : '')) : '—';
    q('t-ver').textContent = dm.version != null ? String(dm.version) : '—';
    q('t-subver').textContent = dm.subversion ? String(dm.subversion).replace(/[\/]/g, '') : (dm.protocol_version != null ? 'proto ' + dm.protocol_version : '');
    if (dm.verification_progress != null) {
      q('t-sync').textContent = (Number(dm.verification_progress) * 100).toFixed(2) + '%';
    } else { q('t-sync').textContent = dm.reachable ? '100%' : '—'; }
    q('t-chain').textContent = dm.chain ? ('chain: ' + dm.chain) : '';
    q('t-disk').textContent = dm.size_on_disk != null ? fmtBytes(dm.size_on_disk) : '—';
    q('t-supply2').textContent = dm.money_supply != null ? (fmtCompact(dm.money_supply) + ' MN2') : '—';
  }

  function refresh() {
    fetch('/api/mn2/network-overview', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(render)
      .catch(function () { q('ex-updated').textContent = 'Stats temporarily unavailable.'; });
  }

  function ageStr(unixTs) {
    if (!unixTs) return '—';
    var s = Math.max(0, Math.floor(Date.now() / 1000 - Number(unixTs)));
    if (s < 60) return s + 's';
    if (s < 3600) return Math.floor(s / 60) + 'm';
    if (s < 86400) return Math.floor(s / 3600) + 'h';
    return Math.floor(s / 86400) + 'd';
  }

  function durStr(seconds) {
    var s = Number(seconds || 0);
    if (s <= 0) return '—';
    if (s < 3600) return Math.floor(s / 60) + 'm';
    if (s < 86400) return Math.floor(s / 3600) + 'h';
    return Math.floor(s / 86400) + 'd';
  }

  function blockLink(height, hash) {
    var base = (explorerBase || 'https://chainz.cryptoid.info/mn2/').replace(/\/+$/, '');
    var isChainz = /chainz\.cryptoid/.test(base);
    if (isChainz) return base + '/block.dws?id=' + encodeURIComponent(hash || height);
    return base + '/block/' + encodeURIComponent(hash || height);
  }

  function loadBlocks() {
    fetch('/api/mn2/recent-blocks?limit=12', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var body = q('ex-blocks');
        if (!body) return;
        var rows = (d && d.success && d.blocks) ? d.blocks : [];
        if (!rows.length) { body.innerHTML = '<tr><td colspan="4">No block data (daemon unreachable).</td></tr>'; return; }
        body.innerHTML = rows.map(function (b) {
          return '<tr>' +
            '<td><a class="ex-open" href="' + blockLink(b.height, b.hash) + '" target="_blank" rel="noopener">' + (b.height != null ? b.height : '—') + '</a></td>' +
            '<td>' + ageStr(b.time) + '</td>' +
            '<td>' + (b.tx_count != null ? b.tx_count : '—') + '</td>' +
            '<td>' + (b.size != null ? fmtNum(b.size, 0) + ' B' : '—') + '</td>' +
            '</tr>';
        }).join('');
      })
      .catch(function () {});
  }

  function loadMasternodes() {
    fetch('/api/mn2/masternodes?limit=50', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var body = q('ex-mn');
        if (!body) return;
        if (!d || !d.success) { return; }
        var sum = q('mn-summary');
        if (sum) sum.textContent = '— ' + (d.enabled || 0) + ' enabled / ' + (d.total || 0) + ' total';
        var list = d.list || [];
        if (!list.length) { body.innerHTML = '<tr><td colspan="4">No masternode data.</td></tr>'; return; }
        body.innerHTML = list.map(function (m) {
          var on = String(m.status || '').toUpperCase() === 'ENABLED';
          var pill = '<span class="pill ' + (on ? 'on' : 'off') + '">' + (m.status || '—') + '</span>';
          var addr = m.addr ? '<a class="ex-open" href="' + explorerLink(m.addr) + '" target="_blank" rel="noopener">' + m.addr + '</a>' : '—';
          return '<tr>' +
            '<td>' + (m.rank != null ? m.rank : '—') + '</td>' +
            '<td>' + addr + '</td>' +
            '<td>' + pill + '</td>' +
            '<td>' + durStr(m.activetime) + '</td>' +
            '</tr>';
        }).join('');
      })
      .catch(function () {});
  }

  // ---- 5-day Network Monitor: multi-metric area charts from network-history ----

  var MON_METRICS = [
    { key: 'block_height', label: 'Block Height', fmt: function (v) { return fmtNum(v, 0); } },
    { key: 'mn2_usd_price', label: 'MN2 Price', fmt: function (v) { return '$' + fmtNum(v, 4); } },
    { key: 'difficulty', label: 'Difficulty', fmt: function (v) { return fmtNum(v, 2); } },
    { key: 'network_hashps', alt: 'staking_weight', label: 'Network Weight', fmt: function (v) { return fmtCompact(v) + ' H/s'; } },
    { key: 'masternode_count', label: 'Masternodes', fmt: function (v) { return fmtNum(v, 0); } },
    { key: 'connections', label: 'Peers', fmt: function (v) { return fmtNum(v, 0); } },
    { key: 'mempool_tx', label: 'Mempool', fmt: function (v) { return fmtNum(v, 0) + ' tx'; } },
    { key: 'pool_total_staked', label: 'Pool Staked', fmt: function (v) { return fmtCompact(v) + ' MN2'; } }
  ];

  function areaChart(values) {
    var pts = (values || []).filter(function (v) { return v != null && !isNaN(Number(v)); }).map(Number);
    if (pts.length < 2) return '<svg viewBox="0 0 260 64" preserveAspectRatio="none"></svg>';
    var w = 260, h = 64, pad = 4;
    var min = Math.min.apply(null, pts), max = Math.max.apply(null, pts);
    var range = (max - min) || 1;
    var step = w / (pts.length - 1);
    var coords = pts.map(function (v, i) {
      var x = (i * step);
      var y = (h - pad - ((v - min) / range) * (h - pad * 2));
      return [x, y];
    });
    var line = coords.map(function (c, i) { return (i === 0 ? 'M' : 'L') + c[0].toFixed(1) + ',' + c[1].toFixed(1); }).join(' ');
    var area = line + ' L' + w + ',' + h + ' L0,' + h + ' Z';
    var up = pts[pts.length - 1] >= pts[0];
    var color = up ? '#00ff88' : '#ff7a7a';
    var gid = 'g' + Math.random().toString(36).slice(2, 8);
    return '<svg viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="none">' +
      '<defs><linearGradient id="' + gid + '" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0%" stop-color="' + color + '" stop-opacity="0.35"/>' +
      '<stop offset="100%" stop-color="' + color + '" stop-opacity="0"/></linearGradient></defs>' +
      '<path d="' + area + '" fill="url(#' + gid + ')" stroke="none"/>' +
      '<path d="' + line + '" fill="none" stroke="' + color + '" stroke-width="1.6"/></svg>';
  }

  function deltaBadge(pts) {
    if (!pts || pts.length < 2) return '<span class="mon-delta flat">—</span>';
    var first = pts[0], last = pts[pts.length - 1];
    if (first === 0 || first == null) {
      var cls0 = last > 0 ? 'up' : 'flat';
      return '<span class="mon-delta ' + cls0 + '">' + (last > 0 ? '+new' : '—') + '</span>';
    }
    var pct = ((last - first) / Math.abs(first)) * 100;
    var cls = Math.abs(pct) < 0.005 ? 'flat' : (pct > 0 ? 'up' : 'down');
    var sign = pct > 0 ? '+' : '';
    return '<span class="mon-delta ' + cls + '">' + sign + pct.toFixed(2) + '%</span>';
  }

  function renderMonitor(hist) {
    var grid = q('mon-grid');
    if (!grid) return;
    if (!hist || !hist.length) {
      grid.innerHTML = '<div class="mon-empty">No 5-day history yet — snapshots accrue every ~10 min as the explorer is polled.</div>';
      return;
    }
    var meta = q('mon-meta');
    if (meta) meta.textContent = '— ' + hist.length + ' snapshots';
    var html = MON_METRICS.map(function (m) {
      var series = hist.map(function (r) {
        var v = r[m.key];
        if ((v == null || isNaN(Number(v))) && m.alt) v = r[m.alt];
        return v;
      });
      var pts = series.filter(function (v) { return v != null && !isNaN(Number(v)); }).map(Number);
      if (!pts.length) {
        return '<div class="mon-card"><div class="mon-head"><span class="mon-name">' + m.label + '</span>' + deltaBadge(pts) + '</div>' +
          '<div class="mon-last">—</div><div class="mon-chart">' + areaChart(series) + '</div>' +
          '<div class="mon-foot"><span>no data</span><span></span></div></div>';
      }
      var last = pts[pts.length - 1];
      var min = Math.min.apply(null, pts), max = Math.max.apply(null, pts);
      return '<div class="mon-card">' +
        '<div class="mon-head"><span class="mon-name">' + m.label + '</span>' + deltaBadge(pts) + '</div>' +
        '<div class="mon-last">' + m.fmt(last) + '</div>' +
        '<div class="mon-chart">' + areaChart(series) + '</div>' +
        '<div class="mon-foot"><span>' + m.fmt(min) + ' … ' + m.fmt(max) + '</span><span>' + pts.length + ' pts</span></div>' +
        '</div>';
    }).join('');
    grid.innerHTML = html;
  }

  function loadMonitor() {
    // 5 days = 120h. Snapshots are throttled ~10 min, so cap is generous.
    fetch('/api/mn2/network-history?hours=120&limit=900', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) { renderMonitor((d && d.success && d.history) ? d.history : []); })
      .catch(function () {});
    fetch('/api/mn2/network-alerts?limit=5', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var el = q('mon-alerts');
        if (!el) return;
        var alerts = (d && d.success && d.alerts) ? d.alerts : [];
        if (!alerts.length) { el.innerHTML = ''; return; }
        el.innerHTML = alerts.map(function (a) {
          var bad = a.type === 'staking_stopped';
          var when = a.ts ? new Date(a.ts).toLocaleString() : '';
          return '<div class="mon-alert' + (bad ? ' bad' : '') + '">⚠️ ' + (a.message || a.type) + (when ? ' <span style="opacity:0.6">(' + when + ')</span>' : '') + '</div>';
        }).join('');
      })
      .catch(function () {});
  }

  function initSearch() {
    var form = q('ex-search');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var v = (q('ex-q').value || '').trim();
      if (!v) return;
      window.open(explorerLink(v), '_blank', 'noopener');
    });
  }

  initSearch();
  refresh();
  loadSparklines();
  loadBlocks();
  loadMasternodes();
  loadMonitor();
  setInterval(refresh, 30000);
  setInterval(loadSparklines, 300000);
  setInterval(loadBlocks, 30000);
  setInterval(loadMasternodes, 60000);
  setInterval(loadMonitor, 120000);
})();
