/**
 * Profile MN2 wallet — independent section loading, deposit request, wallet sub-tabs.
 */
(function (global) {
  'use strict';

  var TIMEOUT_MS = 12000;

  function uid() {
    return (
      (global.profileManager && global.profileManager.userId) ||
      localStorage.getItem('game_user_id') ||
      localStorage.getItem('user_id') ||
      'default_user'
    );
  }

  function base() {
    return global.location.origin;
  }

  function fetchJson(url, opts) {
    opts = opts || {};
    var ctrl = new AbortController();
    var timer = setTimeout(function () {
      ctrl.abort();
    }, opts.timeout || TIMEOUT_MS);
    return fetch(url, {
      method: opts.method || 'GET',
      credentials: 'same-origin',
      headers: Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {}),
      body: opts.body ? JSON.stringify(opts.body) : undefined,
      signal: ctrl.signal,
    })
      .then(function (r) {
        return r.json().then(function (j) {
          return { ok: r.ok, data: j };
        });
      })
      .catch(function (e) {
        return { ok: false, data: { success: false, error: e.name === 'AbortError' ? 'Request timed out' : 'Network error' } };
      })
      .finally(function () {
        clearTimeout(timer);
      });
  }

  function hasDepositAddress(addrEl) {
    var t = (addrEl && addrEl.textContent) ? addrEl.textContent.trim() : '';
    return t && t !== '--' && t !== '—' && t !== '…' && t !== 'Loading…';
  }

  function wireFiatToggle() {
    var tg = document.getElementById('mn2-fiat-toggle');
    if (!tg || tg._mn2Wired) return;
    tg._mn2Wired = true;
    tg.checked = localStorage.getItem('mn2_fiat_display') === '1';
    tg.addEventListener('change', function () {
      localStorage.setItem('mn2_fiat_display', tg.checked ? '1' : '0');
      fetchJson(base() + '/api/mn2/balance?user_id=' + encodeURIComponent(uid())).then(function (res) {
        renderBalance(res.data);
      });
    });
  }

  function renderBalance(balData) {
    var balanceEl = document.getElementById('profile-mn2-balance');
    var fiatEl = document.getElementById('profile-mn2-balance-fiat');
    if (!balData || !balData.success) {
      if (balanceEl) balanceEl.textContent = '—';
      var showcaseErr = document.getElementById('profile-mn2-showcase-balance');
      if (showcaseErr) showcaseErr.textContent = (balData && balData.error) ? balData.error : '—';
      return;
    }
    var balNum = Number(balData.mn2_balance) || 0;
    if (balanceEl) balanceEl.textContent = balNum.toFixed(8);
    var showcase = document.getElementById('profile-mn2-showcase-balance');
    if (showcase) showcase.textContent = balNum.toFixed(4) + ' MN2';
    if (fiatEl && localStorage.getItem('mn2_fiat_display') === '1') {
      var usd = balData.mn2_usd_price;
      if (usd != null) {
        fiatEl.textContent = '(≈ $' + (balNum * Number(usd)).toFixed(4) + ')';
      } else {
        fetchJson(base() + '/api/mn2/price', { timeout: 8000 }).then(function (res) {
          var p = res.data || {};
          if (p.mn2_usd_price != null) {
            fiatEl.textContent = '(≈ $' + (balNum * Number(p.mn2_usd_price)).toFixed(4) + ')';
          }
        });
      }
    } else if (fiatEl) {
      fiatEl.textContent = '';
    }
    var revAddr = (balData.shop_revenue_address || '').trim();
    var revBlock = document.getElementById('profile-mn2-revenue-block');
    var revAddrEl = document.getElementById('profile-mn2-revenue-address');
    var revExplorer = document.getElementById('profile-mn2-revenue-explorer');
    if (revAddr && revBlock) {
      revBlock.style.display = 'block';
      if (revAddrEl) revAddrEl.textContent = revAddr;
      if (revExplorer && balData.shop_revenue_explorer_url) {
        revExplorer.href = balData.shop_revenue_explorer_url;
        revExplorer.style.display = '';
      }
    } else if (revBlock) revBlock.style.display = 'none';
    var verificationMsg = document.getElementById('profile-mn2-withdraw-verification-msg');
    var profileWithdrawBtn = document.getElementById('profile-mn2-withdraw-btn');
    if (balData.withdrawal_verified === false) {
      if (verificationMsg) verificationMsg.style.display = 'block';
      if (profileWithdrawBtn) {
        profileWithdrawBtn.disabled = true;
        profileWithdrawBtn.title = 'Verification required';
      }
    } else {
      if (verificationMsg) verificationMsg.style.display = 'none';
      if (profileWithdrawBtn) {
        profileWithdrawBtn.disabled = false;
        profileWithdrawBtn.title = '';
      }
    }
  }

  function renderDeposit(addrData) {
    var addrEl = document.getElementById('profile-mn2-deposit-address');
    var qrEl = document.getElementById('profile-mn2-qr');
    var explorerLink = document.getElementById('profile-mn2-explorer-link');
    var depositErrEl = document.getElementById('profile-mn2-deposit-error');
    var depositHintEl = document.getElementById('profile-mn2-deposit-hint');
    var depositRetryBtn = document.getElementById('profile-mn2-deposit-retry');
    var requestAddrBtn = document.getElementById('profile-mn2-request-addr');

    function drawQr(text) {
      if (!qrEl || !text) return;
      if (typeof QRCode === 'undefined') {
        setTimeout(function () { drawQr(text); }, 200);
        return;
      }
      qrEl.innerHTML = '';
      try {
        new QRCode(qrEl, { text: text, width: 96, height: 96 });
      } catch (e) {
        qrEl.innerHTML = '';
      }
    }

    if (addrData && addrData.success && addrData.deposit_address) {
      if (addrEl) addrEl.textContent = addrData.deposit_address;
      if (depositErrEl) {
        depositErrEl.style.display = 'none';
        depositErrEl.textContent = '';
      }
      if (depositHintEl) depositHintEl.style.display = 'none';
      if (depositRetryBtn) depositRetryBtn.style.display = 'none';
      if (requestAddrBtn) requestAddrBtn.style.display = 'inline-block';
      if (explorerLink && addrData.explorer_address_url) {
        explorerLink.href = addrData.explorer_address_url;
        explorerLink.style.display = '';
      }
      drawQr(addrData.deposit_address);
    } else {
      if (addrEl) addrEl.textContent = '—';
      var errMsg =
        (addrData && addrData.error) ||
        'Deposit address unavailable. Wallet RPC may be offline — use Request address when ready.';
      if (depositErrEl) {
        depositErrEl.textContent = errMsg;
        depositErrEl.style.display = 'block';
      }
      if (depositHintEl) depositHintEl.style.display = 'block';
      if (depositRetryBtn) depositRetryBtn.style.display = 'inline-block';
      if (requestAddrBtn) requestAddrBtn.style.display = 'inline-block';
    }
  }

  function renderTransactions(txData) {
    var txList = document.getElementById('profile-mn2-transactions');
    if (!txList) return;
    var txs = txData && txData.success && txData.transactions ? txData.transactions : [];
    if (!txs.length) {
      txList.innerHTML = '<p style="margin:0;">No transactions yet.</p>';
      return;
    }
    txList.innerHTML =
      '<ul style="margin:0;padding-left:1.2rem;">' +
      txs
        .map(function (t) {
          var type = t.type || '—';
          var amt = t.amount != null ? Number(t.amount).toFixed(4) : '—';
          var txLink = t.explorer_tx_url
            ? '<a href="' + t.explorer_tx_url + '" target="_blank" rel="noopener" style="color:#00d4ff;">Explorer tx</a>'
            : '';
          var addrLink = t.explorer_address_url
            ? ' <a href="' + t.explorer_address_url + '" target="_blank" rel="noopener" style="color:#88ccff;">Explorer address</a>'
            : '';
          var date = t.created_at ? new Date(t.created_at).toLocaleString() : '';
          return '<li>' + type + ': ' + amt + ' MN2 ' + txLink + addrLink + (date ? ' (' + date + ')' : '') + '</li>';
        })
        .join('') +
      '</ul>';
  }

  function renderActivity(actData) {
    var chartEl = document.getElementById('profile-mn2-5d-chart');
    if (!chartEl) return;
    if (actData && actData.success && actData.buckets && actData.buckets.length) {
      var buckets = actData.buckets;
      var maxV = 1e-10;
      buckets.forEach(function (b) {
        maxV = Math.max(maxV, b.deposits_mn2 || 0, b.out_mn2 || 0);
      });
      chartEl.innerHTML = buckets
        .map(function (b) {
          var hIn = Math.max(2, Math.round(((b.deposits_mn2 || 0) / maxV) * 34));
          var hOut = Math.max(2, Math.round(((b.out_mn2 || 0) / maxV) * 34));
          var day = b.date && b.date.length >= 10 ? b.date.slice(5) : b.date || '';
          var netStr = ((b.net_mn2 || 0) >= 0 ? '+' : '') + (Number(b.net_mn2) || 0).toFixed(3);
          return (
            '<div class="mn2-5d-col"><div class="mn2-5d-barstack"><div class="mn2-5d-bar-in" style="height:' +
            hIn +
            'px"></div><div class="mn2-5d-bar-out" style="height:' +
            hOut +
            'px"></div></div><div class="mn2-5d-label">' +
            day +
            '</div><div class="mn2-5d-net">' +
            netStr +
            '</div></div>'
          );
        })
        .join('');
    } else {
      chartEl.innerHTML =
        '<span style="opacity:0.75;font-size:0.85rem;">No ledger activity in the last 5 UTC days.</span>';
    }
  }

  function requestDepositAddress(forceNew) {
    var user = uid();
    var addrEl = document.getElementById('profile-mn2-deposit-address');
    var requestBtn = document.getElementById('profile-mn2-request-addr');
    var depositErrEl = document.getElementById('profile-mn2-deposit-error');
    if (addrEl) addrEl.textContent = '…';
    if (requestBtn) {
      requestBtn.disabled = true;
      requestBtn.textContent = 'Requesting…';
    }
    if (depositErrEl) {
      depositErrEl.style.display = 'none';
      depositErrEl.textContent = '';
    }
    var hasAddr = forceNew || hasDepositAddress(addrEl);
    var promise;
    if (hasAddr && forceNew !== false) {
      promise = fetchJson(base() + '/api/mn2/wallet/refresh', {
        method: 'POST',
        body: { user_id: user },
        timeout: 20000,
      }).then(function (res) {
        if (res.data && res.data.success) return { data: res.data };
        return fetchJson(base() + '/api/mn2/deposit-address?user_id=' + encodeURIComponent(user), { timeout: 20000 });
      });
    } else {
      promise = fetchJson(base() + '/api/mn2/deposit-address?user_id=' + encodeURIComponent(user), { timeout: 20000 });
    }
    return promise
      .then(function (res) {
        renderDeposit(res.data || {});
        if (!(res.data && res.data.success) && depositErrEl) {
          depositErrEl.textContent = (res.data && res.data.error) || 'Could not get deposit address.';
          depositErrEl.style.display = 'block';
        }
      })
      .finally(function () {
        if (requestBtn) {
          requestBtn.disabled = false;
          requestBtn.innerHTML = '<i class="fas fa-plus-circle"></i> Request address';
        }
      });
  }

  function wireControls() {
    var copyBtn = document.getElementById('profile-mn2-copy');
    var addrEl = document.getElementById('profile-mn2-deposit-address');
    var depositRetryBtn = document.getElementById('profile-mn2-deposit-retry');
    var requestAddrBtn = document.getElementById('profile-mn2-request-addr');
    var withdrawBtn = document.getElementById('profile-mn2-withdraw-btn');

    if (depositRetryBtn && !depositRetryBtn._mn2Wired) {
      depositRetryBtn._mn2Wired = true;
      depositRetryBtn.addEventListener('click', function () {
        load();
      });
    }
    if (requestAddrBtn && !requestAddrBtn._mn2Wired) {
      requestAddrBtn._mn2Wired = true;
      requestAddrBtn.addEventListener('click', function () {
        var addrEl2 = document.getElementById('profile-mn2-deposit-address');
        requestDepositAddress(hasDepositAddress(addrEl2));
      });
    }
    if (copyBtn && !copyBtn._mn2Wired) {
      copyBtn._mn2Wired = true;
      copyBtn.addEventListener('click', function () {
        var addr = addrEl && addrEl.textContent ? addrEl.textContent.trim() : '';
        if (!addr || addr === '--' || addr === '—') return;
        navigator.clipboard.writeText(addr).then(function () {
          if (typeof toast !== 'undefined') toast.success('Address copied');
        });
      });
    }
    var copyRevBtn = document.getElementById('profile-mn2-copy-revenue');
    var revAddrEl = document.getElementById('profile-mn2-revenue-address');
    if (copyRevBtn && !copyRevBtn._mn2Wired) {
      copyRevBtn._mn2Wired = true;
      copyRevBtn.addEventListener('click', function () {
        var addr = revAddrEl && revAddrEl.textContent ? revAddrEl.textContent.trim() : '';
        if (!addr) return;
        navigator.clipboard.writeText(addr).then(function () {
          if (typeof toast !== 'undefined') toast.success('Revenue address copied');
        });
      });
    }
    if (withdrawBtn && !withdrawBtn._mn2Wired) {
      withdrawBtn._mn2Wired = true;
      withdrawBtn.addEventListener('click', function () {
        var address = (document.getElementById('profile-mn2-withdraw-address') || {}).value.trim();
        var amount = parseFloat((document.getElementById('profile-mn2-withdraw-amount') || {}).value);
        if (!address) {
          if (typeof toast !== 'undefined') toast.error('Enter MN2 address');
          return;
        }
        if (!(amount > 0)) {
          if (typeof toast !== 'undefined') toast.error('Enter amount');
          return;
        }
        withdrawBtn.disabled = true;
        var origHtml = withdrawBtn.innerHTML;
        withdrawBtn.textContent = 'Sending…';
        fetchJson(base() + '/api/mn2/withdraw', {
          method: 'POST',
          body: { user_id: uid(), address: address, amount: amount },
          timeout: 20000,
        })
          .then(function (res) {
            var data = res.data || {};
            if (data.success) {
              if (typeof toast !== 'undefined') toast.success('Withdrawal sent');
              document.getElementById('profile-mn2-withdraw-address').value = '';
              document.getElementById('profile-mn2-withdraw-amount').value = '';
              load();
            } else if (typeof toast !== 'undefined') toast.error(data.error || 'Withdrawal failed');
          })
          .finally(function () {
            withdrawBtn.disabled = false;
            withdrawBtn.innerHTML = origHtml;
          });
      });
    }
  }

  function initWalletSubTabs() {
    var nav = document.getElementById('profile-wallet-subnav');
    if (!nav || nav._wired) return;
    nav._wired = true;
    var panels = document.querySelectorAll('[data-wallet-panel]');
    nav.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-wallet-tab]');
      if (!btn) return;
      var tab = btn.getAttribute('data-wallet-tab');
      nav.querySelectorAll('[data-wallet-tab]').forEach(function (b) {
        b.classList.toggle('active', b === btn);
        b.setAttribute('aria-selected', b === btn ? 'true' : 'false');
      });
      panels.forEach(function (p) {
        p.style.display = p.getAttribute('data-wallet-panel') === tab ? 'block' : 'none';
      });
    });
  }

  function load() {
    var user = uid();
    var q = encodeURIComponent(user);
    var chartEl = document.getElementById('profile-mn2-5d-chart');
    var balanceEl = document.getElementById('profile-mn2-balance');
    var txList = document.getElementById('profile-mn2-transactions');
    if (balanceEl && balanceEl.textContent === '--') balanceEl.textContent = '…';
    if (chartEl && chartEl.textContent.indexOf('Loading') >= 0) {
      chartEl.innerHTML = '<span style="opacity:0.6;font-size:0.85rem;">Loading activity…</span>';
    }
    if (txList && txList.textContent.indexOf('Loading') >= 0) {
      txList.innerHTML = '<p style="margin:0;opacity:0.7;">Loading…</p>';
    }

    wireControls();
    wireFiatToggle();
    initWalletSubTabs();

    fetchJson(base() + '/api/mn2/balance?user_id=' + q).then(function (res) {
      renderBalance(res.data);
    });
    fetchJson(base() + '/api/mn2/deposit-address?user_id=' + q, { timeout: 18000 }).then(function (res) {
      renderDeposit(res.data);
    });
    fetchJson(base() + '/api/mn2/transactions?user_id=' + q + '&limit=20').then(function (res) {
      renderTransactions(res.data);
    });
    fetchJson(base() + '/api/mn2/wallet-activity?user_id=' + q + '&days=5').then(function (res) {
      renderActivity(res.data);
    });
  }

  global.ProfileMn2Wallet = { load: load, requestDepositAddress: requestDepositAddress };
})(window);
