(function () {
  'use strict';

  var CONF_TARGET = 6;
  var EMBED = false;
  var ADDR_RE = /^[13mnMNJ][a-km-zA-HJ-NP-Z1-9]{25,62}$/;

  function q(id) { return document.getElementById(id); }

  function params() {
    try { return new URLSearchParams(window.location.search); } catch (e) { return new URLSearchParams(); }
  }

  function initEmbed() {
    EMBED = params().get('embed') === '1';
    if (EMBED) document.body.classList.add('ex-embed');
    var back = document.querySelector('.ex-detail-back');
    if (back && EMBED) back.style.display = 'none';
  }

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

  function fmtTime(unixTs) {
    if (!unixTs) return '—';
    try {
      return new Date(Number(unixTs) * 1000).toLocaleString();
    } catch (e) {
      return '—';
    }
  }

  function copyBtn(text, label) {
    var safe = String(text || '').replace(/"/g, '&quot;');
    return '<button type="button" class="ex-copy-btn" data-copy="' + safe + '" title="Copy ' + (label || 'value') + '">Copy</button>';
  }

  function bindCopyButtons(root) {
    if (!root) return;
    root.querySelectorAll('.ex-copy-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var val = btn.getAttribute('data-copy') || '';
        if (!val) return;
        function done(ok) {
          btn.textContent = ok ? 'Copied' : 'Copy failed';
          setTimeout(function () { btn.textContent = 'Copy'; }, 1500);
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(val).then(function () { done(true); }).catch(function () { done(false); });
        } else {
          try {
            var ta = document.createElement('textarea');
            ta.value = val;
            document.body.appendChild(ta);
            ta.select();
            done(document.execCommand('copy'));
            document.body.removeChild(ta);
          } catch (e) {
            done(false);
          }
        }
      });
    });
  }

  function row(label, valueHtml) {
    return '<div class="ex-detail-row"><dt>' + label + '</dt><dd>' + valueHtml + '</dd></div>';
  }

  function setBreadcrumb(items) {
    var el = q('ex-breadcrumb');
    if (!el) return;
    if (!items || !items.length) { el.innerHTML = ''; return; }
    el.innerHTML = items.map(function (it, i) {
      var inner = it.href
        ? '<a href="' + it.href + '">' + it.label + '</a>'
        : '<span aria-current="page">' + it.label + '</span>';
      return '<span class="ex-crumb">' + inner + '</span>' +
        (i < items.length - 1 ? '<span class="ex-crumb-sep" aria-hidden="true">›</span>' : '');
    }).join('');
  }

  function setMobileDeepLink(path) {
    if (!path) return;
    var href = 'masternoder://' + String(path).replace(/^\//, '');
    var link = document.querySelector('link[rel="alternate"][data-mn2-deep]');
    if (!link) {
      link = document.createElement('link');
      link.rel = 'alternate';
      link.setAttribute('data-mn2-deep', '1');
      document.head.appendChild(link);
    }
    link.href = href;
  }

  function discordEmbedLink(ref) {
    return '/api/mn2/explorer/discord-embed?block=' + encodeURIComponent(ref);
  }
    opts = opts || {};
    if (opts.title) document.title = opts.title;
    function upsert(attr, key, val) {
      if (!val) return;
      var sel = 'meta[' + attr + '="' + key + '"]';
      var m = document.querySelector(sel);
      if (!m) {
        m = document.createElement('meta');
        m.setAttribute(attr, key);
        document.head.appendChild(m);
      }
      m.setAttribute('content', val);
    }
    upsert('property', 'og:title', opts.title);
    upsert('property', 'og:description', opts.description);
    upsert('property', 'og:url', opts.url || window.location.href);
    upsert('property', 'og:type', opts.type || 'website');
    upsert('name', 'description', opts.description);
    if (opts.jsonLd) {
      var ld = q('ex-jsonld');
      if (!ld) {
        ld = document.createElement('script');
        ld.type = 'application/ld+json';
        ld.id = 'ex-jsonld';
        document.head.appendChild(ld);
      }
      ld.textContent = JSON.stringify(opts.jsonLd);
    }
  }

  function renderConfirmBar(conf) {
    if (conf == null || isNaN(Number(conf))) return '—';
    var n = Number(conf);
    var pct = Math.min(100, Math.round((n / CONF_TARGET) * 100));
    var label = n >= CONF_TARGET ? 'Confirmed (' + fmtNum(n, 0) + ')' : fmtNum(n, 0) + ' / ' + CONF_TARGET;
    return '<div class="ex-confirm-bar" role="progressbar" aria-valuenow="' + n + '" aria-valuemin="0" aria-valuemax="' + CONF_TARGET + '">' +
      '<div class="ex-confirm-fill' + (n >= CONF_TARGET ? ' done' : '') + '" style="width:' + pct + '%"></div>' +
      '<span class="ex-confirm-label">' + label + '</span></div>';
  }

  function addrLinks(addrs) {
    if (!Array.isArray(addrs) || !addrs.length) return '—';
    return addrs.map(function (a) {
      return '<a href="/explorer/address/' + encodeURIComponent(a) + '">' + a + '</a>';
    }).join('<br>');
  }

  function renderVins(vins) {
    if (!vins || !vins.length) return '';
    var rows = vins.map(function (v) {
      if (v.coinbase) {
        return '<tr><td>' + (v.n != null ? v.n : '—') + '</td><td colspan="2"><em>Coinbase</em></td><td>—</td></tr>';
      }
      var prev = '—';
      if (v.prev_txid) {
        prev = '<a href="/explorer/tx/' + encodeURIComponent(v.prev_txid) + '">' + shortHash(v.prev_txid) + '</a>';
        if (v.prev_vout != null) prev += ' :' + v.prev_vout;
      }
      return '<tr><td>' + (v.n != null ? v.n : '—') + '</td><td>' + prev + '</td><td>' +
        fmtNum(v.value, 8) + '</td><td>' + addrLinks(v.addresses) + '</td></tr>';
    }).join('');
    return '<h2 class="ex-detail-subhead">Inputs</h2><table class="ex-detail-table"><thead><tr><th>n</th><th>Previous output</th><th>Value (MN2)</th><th>Address</th></tr></thead><tbody>' + rows + '</tbody></table>';
  }

  function renderVouts(vouts) {
    if (!vouts || !vouts.length) return '';
    var rows = vouts.map(function (v) {
      var addrs = v.addresses;
      if (!addrs && v.scriptPubKey && v.scriptPubKey.address) addrs = [v.scriptPubKey.address];
      return '<tr><td>' + (v.n != null ? v.n : '—') + '</td><td>' + fmtNum(v.value, 8) + '</td><td>' + addrLinks(addrs) + '</td></tr>';
    }).join('');
    return '<h2 class="ex-detail-subhead">Outputs</h2><table class="ex-detail-table"><thead><tr><th>n</th><th>Value (MN2)</th><th>Address</th></tr></thead><tbody>' + rows + '</tbody></table>';
  }

  function renderBlockTxTable(txids) {
    if (!txids || !txids.length) return '';
    var rows = txids.map(function (id, i) {
      return '<tr><td>' + (i + 1) + '</td><td class="ex-mono"><a href="/explorer/tx/' + encodeURIComponent(id) + '">' + shortHash(id) + '</a></td></tr>';
    }).join('');
    return '<h2 class="ex-detail-subhead">Transactions (' + txids.length + ')</h2>' +
      '<table class="ex-detail-table"><thead><tr><th>#</th><th>TxID</th></tr></thead><tbody>' + rows + '</tbody></table>';
  }

  function renderAddressQr(address) {
    var wrap = q('ex-qr-wrap');
    if (!wrap || EMBED || !ADDR_RE.test(address)) return;
    wrap.innerHTML = '<h2 class="ex-detail-subhead">QR code</h2><div id="ex-addr-qr" class="ex-addr-qr" aria-label="Address QR code"></div>';
    var target = q('ex-addr-qr');
    if (target && typeof QRCode !== 'undefined') {
      new QRCode(target, { text: address, width: 160, height: 160 });
    } else if (target) {
      target.textContent = 'QR library unavailable';
    }
  }

  function bindRawToggle(data) {
    var btn = q('ex-raw-toggle');
    var pre = q('ex-raw-json');
    if (!btn || !pre) return;
    btn.hidden = false;
    pre.textContent = JSON.stringify(data, null, 2);
    if (btn._bound) return;
    btn._bound = true;
    btn.addEventListener('click', function () {
      var show = pre.hidden;
      pre.hidden = !show;
      btn.textContent = show ? 'Hide raw JSON' : 'Show raw JSON';
      btn.setAttribute('aria-expanded', show ? 'true' : 'false');
    });
  }

  function showError(msg) {
    var loading = q('ex-detail-loading');
    var body = q('ex-detail-body');
    if (loading) loading.textContent = msg;
    if (body) body.style.display = 'none';
  }

  function showBody(html, externalHtml, rawData) {
    var loading = q('ex-detail-loading');
    var body = q('ex-detail-body');
    var ext = q('ex-detail-external');
    if (loading) loading.style.display = 'none';
    if (body) {
      body.style.display = 'block';
      body.innerHTML = html;
      bindCopyButtons(body);
    }
    if (ext) {
      ext.innerHTML = EMBED ? '' : (externalHtml || '');
    }
    if (rawData) bindRawToggle(rawData);
  }

  function renderTx(txid, data) {
    var tx = (data && data.transaction) || {};
    var crumbs = [
      { label: 'Crypto Hub', href: '/explorer/' },
      { label: 'Tx ' + shortHash(txid) },
    ];
    if (tx.blockhash) {
      crumbs.splice(1, 0, { label: 'Block ' + shortHash(tx.blockhash), href: '/explorer/block/' + encodeURIComponent(tx.blockhash) });
    }
    setBreadcrumb(crumbs);
    setSeoMeta({
      title: 'MN2 Tx ' + shortHash(txid) + ' — Explorer',
      description: 'Transaction ' + txid + ' on MasterNoder2.',
      type: 'article',
      jsonLd: {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: crumbs.map(function (c, i) {
          return { '@type': 'ListItem', position: i + 1, name: c.label, item: c.href ? (window.location.origin + c.href) : window.location.href };
        }),
      },
    });
    var feeHtml = tx.fee != null ? fmtNum(tx.fee, 8) + ' MN2' : '—';
    var html = '<dl class="ex-detail-dl">' +
      row('TxID', '<span class="ex-mono">' + txid + '</span> ' + copyBtn(txid, 'txid')) +
      row('Confirmations', renderConfirmBar(tx.confirmations)) +
      row('Fee', feeHtml) +
      row('Time', fmtTime(tx.time)) +
      row('Block', tx.blockhash ? '<a href="/explorer/block/' + encodeURIComponent(tx.blockhash) + '">' + shortHash(tx.blockhash) + '</a> ' + copyBtn(tx.blockhash, 'block hash') : '—') +
      row('Inputs', tx.vin_count != null ? fmtNum(tx.vin_count, 0) : (tx.vin && tx.vin.length ? fmtNum(tx.vin.length, 0) : '—')) +
      row('Outputs', tx.vout_count != null ? fmtNum(tx.vout_count, 0) : '—') +
      row('Source', tx.source || '—') +
      '</dl>' + renderVins(tx.vin) + renderVouts(tx.vout);
    var ext = tx.explorer_tx_url
      ? '<a href="' + tx.explorer_tx_url + '" target="_blank" rel="noopener">View on full block explorer ↗</a>'
      : '';
    setMobileDeepLink('/explorer/tx/' + txid);
    showBody(html, ext, data);
  }

  function renderAddress(address, data) {
    var addr = (data && data.address) || {};
    setBreadcrumb([
      { label: 'Crypto Hub', href: '/explorer/' },
      { label: 'Address ' + shortHash(address) },
    ]);
    setSeoMeta({
      title: 'MN2 Address ' + shortHash(address) + ' — Explorer',
      description: 'Address ' + address + ' balance and transactions on MasterNoder2.',
      jsonLd: {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Crypto Hub', item: window.location.origin + '/explorer/' },
          { '@type': 'ListItem', position: 2, name: address, item: window.location.href },
        ],
      },
    });
    var txs = addr.transactions;
    var txHtml = '';
    if (Array.isArray(txs) && txs.length) {
      txHtml = '<h2 class="ex-detail-subhead">Recent transactions</h2><ul class="ex-detail-txlist">' +
        txs.slice(0, 10).map(function (t) {
          var id = (typeof t === 'string') ? t : (t.txid || t.hash || '');
          if (!id) return '';
          return '<li><a href="/explorer/tx/' + encodeURIComponent(id) + '">' + shortHash(id) + '</a></li>';
        }).join('') + '</ul>';
    }
    var html = '<dl class="ex-detail-dl">' +
      row('Address', '<span class="ex-mono">' + address + '</span> ' + copyBtn(address, 'address')) +
      row('Balance', addr.balance != null ? fmtNum(addr.balance, 8) + ' MN2' : '—') +
      row('Received', addr.received != null ? fmtNum(addr.received, 8) + ' MN2' : '—') +
      row('Sent', addr.sent != null ? fmtNum(addr.sent, 8) + ' MN2' : '—') +
      row('Tx count', addr.tx_count != null ? fmtNum(addr.tx_count, 0) : '—') +
      row('Source', addr.source || '—') +
      '</dl><div id="ex-qr-wrap"></div>' + txHtml;
    var ext = addr.explorer_address_url
      ? '<a href="' + addr.explorer_address_url + '" target="_blank" rel="noopener">View on full block explorer ↗</a>'
      : '';
    setMobileDeepLink('/explorer/address/' + encodeURIComponent(address));
    showBody(html, ext, data);
    renderAddressQr(address);
  }

  function renderBlock(ref, data) {
    var blk = (data && data.block) || {};
    var txids = blk.txids || [];
    var height = blk.height;
    setBreadcrumb([
      { label: 'Crypto Hub', href: '/explorer/' },
      { label: height != null ? 'Block #' + height : 'Block ' + shortHash(blk.hash || ref) },
    ]);
    setSeoMeta({
      title: (height != null ? 'MN2 Block #' + height : 'MN2 Block') + ' — Explorer',
      description: 'Block ' + (blk.hash || ref) + ' on MasterNoder2.',
      jsonLd: {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Crypto Hub', item: window.location.origin + '/explorer/' },
          { '@type': 'ListItem', position: 2, name: 'Block', item: window.location.href },
        ],
      },
    });
    var prev = blk.previousblockhash;
    var prevHtml = '—';
    if (prev) {
      prevHtml = '<a href="' + (blk.previous_block_path || ('/explorer/block/' + encodeURIComponent(prev))) + '">' +
        shortHash(prev) + '</a>';
      if (blk.explorer_previous_block_url) {
        prevHtml += ' <a href="' + blk.explorer_previous_block_url + '" target="_blank" rel="noopener" style="margin-left:8px;font-size:0.82rem">ext ↗</a>';
      }
    }
    var html = '<dl class="ex-detail-dl">' +
      row('Height', blk.height != null ? '<a href="/explorer/block/' + blk.height + '">' + fmtNum(blk.height, 0) + '</a>' : '—') +
      row('Hash', '<span class="ex-mono">' + (blk.hash || ref) + '</span> ' + copyBtn(blk.hash || ref, 'hash')) +
      row('Time', fmtTime(blk.time)) +
      row('Confirmations', renderConfirmBar(blk.confirmations)) +
      row('Transactions', blk.tx_count != null ? fmtNum(blk.tx_count, 0) : '—') +
      row('Size', blk.size != null ? fmtNum(blk.size, 0) + ' B' : '—') +
      row('Difficulty', blk.difficulty != null ? fmtNum(blk.difficulty, 4) : '—') +
      row('Block reward', blk.block_reward != null ? fmtNum(blk.block_reward, 8) + ' MN2' : '—') +
      row('Previous', prevHtml) +
      row('Source', blk.source || '—') +
      '</dl>' + renderBlockTxTable(txids);
    var ext = blk.explorer_block_url
      ? '<a href="' + blk.explorer_block_url + '" target="_blank" rel="noopener">View on full block explorer ↗</a>'
      : '';
    ext += (ext ? ' · ' : '') +
      '<a href="' + discordEmbedLink(blk.height != null ? blk.height : (blk.hash || ref)) + '" target="_blank" rel="noopener">Discord embed JSON ↗</a>';
    setMobileDeepLink('/explorer/block/' + (height != null ? height : (blk.hash || ref)));
    showBody(html, ext, data);
  }

  initEmbed();

  var path = window.location.pathname || '';
  var txMatch = path.match(/\/explorer\/tx\/([0-9a-fA-F]{64})\/?$/);
  var addrMatch = path.match(/\/explorer\/address\/([^/]+)\/?$/);
  var blockMatch = path.match(/\/explorer\/block\/([^/]+)\/?$/);

  if (txMatch) {
    var txid = txMatch[1];
    fetch('/api/mn2/explorer/tx/' + encodeURIComponent(txid), { credentials: 'same-origin' })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (res) {
        if (!res.ok || !res.d || !res.d.success) {
          showError('Transaction not found or unavailable.');
          return;
        }
        renderTx(txid, res.d);
      })
      .catch(function () { showError('Failed to load transaction.'); });
  } else if (addrMatch) {
    var address = decodeURIComponent(addrMatch[1]);
    fetch('/api/mn2/explorer/address/' + encodeURIComponent(address), { credentials: 'same-origin' })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (res) {
        if (!res.ok || !res.d || !res.d.success) {
          showError('Address not found or invalid.');
          return;
        }
        var addr = (res.d && res.d.address) || {};
        var txs = addr.transactions;
        if (Array.isArray(txs) && txs.length) {
          renderAddress(address, res.d);
          return;
        }
        fetch('/api/mn2/explorer/address/' + encodeURIComponent(address) + '/txs?limit=25', { credentials: 'same-origin' })
          .then(function (r2) { return r2.json(); })
          .then(function (txRes) {
            if (txRes && txRes.success && txRes.transactions) {
              addr.transactions = txRes.transactions.map(function (t) { return t.txid || t; });
              res.d.address = addr;
            }
            renderAddress(address, res.d);
          })
          .catch(function () { renderAddress(address, res.d); });
      })
      .catch(function () { showError('Failed to load address.'); });
  } else if (blockMatch) {
    var ref = decodeURIComponent(blockMatch[1]);
    fetch('/api/mn2/explorer/block/' + encodeURIComponent(ref), { credentials: 'same-origin' })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (res) {
        if (!res.ok || !res.d || !res.d.success) {
          showError('Block not found or unavailable.');
          return;
        }
        renderBlock(ref, res.d);
      })
      .catch(function () { showError('Failed to load block.'); });
  } else {
    showError('Invalid explorer detail URL.');
  }
})();
