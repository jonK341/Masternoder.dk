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

  function showError(msg) {
    var loading = q('ex-detail-loading');
    var body = q('ex-detail-body');
    if (loading) loading.textContent = msg;
    if (body) body.style.display = 'none';
  }

  function showBody(html, externalHtml) {
    var loading = q('ex-detail-loading');
    var body = q('ex-detail-body');
    var ext = q('ex-detail-external');
    if (loading) loading.style.display = 'none';
    if (body) {
      body.style.display = 'block';
      body.innerHTML = html;
      bindCopyButtons(body);
    }
    if (ext) ext.innerHTML = externalHtml || '';
  }

  function renderVouts(vouts) {
    if (!vouts || !vouts.length) return '';
    var rows = vouts.map(function (v) {
      var addrs = v.addresses;
      if (!addrs && v.scriptPubKey && v.scriptPubKey.address) addrs = [v.scriptPubKey.address];
      var addrHtml = '—';
      if (Array.isArray(addrs) && addrs.length) {
        addrHtml = addrs.map(function (a) {
          return '<a href="/explorer/address/' + encodeURIComponent(a) + '">' + a + '</a>';
        }).join('<br>');
      }
      return '<tr><td>' + (v.n != null ? v.n : '—') + '</td><td>' + fmtNum(v.value, 8) + '</td><td>' + addrHtml + '</td></tr>';
    }).join('');
    return '<h2 class="ex-detail-subhead">Outputs</h2><table class="ex-detail-table"><thead><tr><th>n</th><th>Value (MN2)</th><th>Address</th></tr></thead><tbody>' + rows + '</tbody></table>';
  }

  function renderTx(txid, data) {
    var tx = (data && data.transaction) || {};
    var html = '<dl class="ex-detail-dl">' +
      row('TxID', '<span class="ex-mono">' + txid + '</span> ' + copyBtn(txid, 'txid')) +
      row('Confirmations', tx.confirmations != null ? fmtNum(tx.confirmations, 0) : '—') +
      row('Time', fmtTime(tx.time)) +
      row('Block', tx.blockhash ? '<a href="/explorer/block/' + encodeURIComponent(tx.blockhash) + '">' + shortHash(tx.blockhash) + '</a> ' + copyBtn(tx.blockhash, 'block hash') : '—') +
      row('Outputs', tx.vout_count != null ? fmtNum(tx.vout_count, 0) : '—') +
      row('Source', tx.source || '—') +
      '</dl>' + renderVouts(tx.vout);
    var ext = tx.explorer_tx_url
      ? '<a href="' + tx.explorer_tx_url + '" target="_blank" rel="noopener">View on full block explorer ↗</a>'
      : '';
    showBody(html, ext);
  }

  function renderAddress(address, data) {
    var addr = (data && data.address) || {};
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
      '</dl>' + txHtml;
    var ext = addr.explorer_address_url
      ? '<a href="' + addr.explorer_address_url + '" target="_blank" rel="noopener">View on full block explorer ↗</a>'
      : '';
    showBody(html, ext);
  }

  function renderBlock(ref, data) {
    var blk = (data && data.block) || {};
    var txids = blk.txids || [];
    var txHtml = '';
    if (txids.length) {
      txHtml = '<h2 class="ex-detail-subhead">Transactions</h2><ul class="ex-detail-txlist">' +
        txids.map(function (id) {
          return '<li><a href="/explorer/tx/' + encodeURIComponent(id) + '">' + shortHash(id) + '</a></li>';
        }).join('') + '</ul>';
    }
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
      row('Confirmations', blk.confirmations != null ? fmtNum(blk.confirmations, 0) : '—') +
      row('Transactions', blk.tx_count != null ? fmtNum(blk.tx_count, 0) : '—') +
      row('Size', blk.size != null ? fmtNum(blk.size, 0) + ' B' : '—') +
      row('Difficulty', blk.difficulty != null ? fmtNum(blk.difficulty, 4) : '—') +
      row('Previous', prevHtml) +
      row('Source', blk.source || '—') +
      '</dl>' + txHtml;
    var ext = blk.explorer_block_url
      ? '<a href="' + blk.explorer_block_url + '" target="_blank" rel="noopener">View on full block explorer ↗</a>'
      : '';
    showBody(html, ext);
  }

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
