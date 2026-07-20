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

  var path = window.location.pathname || '';
  var txMatch = path.match(/\/explorer\/tx\/([0-9a-fA-F]{64})\/?$/);
  var addrMatch = path.match(/\/explorer\/address\/([^/]+)\/?$/);

  function showError(msg) {
    var loading = q('ex-detail-loading');
    var body = q('ex-detail-body');
    if (loading) loading.textContent = msg;
    if (body) body.style.display = 'none';
  }

  function renderTx(txid, data) {
    var tx = (data && data.transaction) || {};
    var html = '<dl>' +
      '<dt>TxID</dt><dd style="word-break:break-all">' + txid + '</dd>' +
      '<dt>Confirmations</dt><dd>' + (tx.confirmations != null ? tx.confirmations : '—') + '</dd>' +
      '<dt>Outputs</dt><dd>' + (tx.vout_count != null ? tx.vout_count : '—') + '</dd>' +
      '<dt>Source</dt><dd>' + (tx.source || '—') + '</dd>' +
      '</dl>';
    q('ex-detail-loading').style.display = 'none';
    q('ex-detail-body').style.display = 'block';
    q('ex-detail-body').innerHTML = html;
    if (tx.explorer_tx_url) {
      q('ex-detail-external').innerHTML = '<a href="' + tx.explorer_tx_url + '" target="_blank" rel="noopener">View on full block explorer ↗</a>';
    }
  }

  function renderAddress(address, data) {
    var addr = (data && data.address) || {};
    var html = '<dl>' +
      '<dt>Address</dt><dd style="word-break:break-all">' + address + '</dd>' +
      '<dt>Balance</dt><dd>' + (addr.balance != null ? fmtNum(addr.balance, 8) + ' MN2' : '—') + '</dd>' +
      '<dt>Received</dt><dd>' + (addr.received != null ? fmtNum(addr.received, 8) : '—') + '</dd>' +
      '<dt>Sent</dt><dd>' + (addr.sent != null ? fmtNum(addr.sent, 8) : '—') + '</dd>' +
      '<dt>Source</dt><dd>' + (addr.source || '—') + '</dd>' +
      '</dl>';
    q('ex-detail-loading').style.display = 'none';
    q('ex-detail-body').style.display = 'block';
    q('ex-detail-body').innerHTML = html;
    if (addr.explorer_address_url) {
      q('ex-detail-external').innerHTML = '<a href="' + addr.explorer_address_url + '" target="_blank" rel="noopener">View on full block explorer ↗</a>';
    }
  }

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
        renderAddress(address, res.d);
      })
      .catch(function () { showError('Failed to load address.'); });
  } else {
    showError('Invalid explorer detail URL.');
  }
})();
