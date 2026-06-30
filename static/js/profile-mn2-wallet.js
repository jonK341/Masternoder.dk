/**
 * Profile MN2 wallet — lazy tab loading, wallet-hub aggregator, deposit/withdraw.
 */
(function (global) {
  'use strict';

  var TIMEOUT_MS = 12000;
  var tabsLoaded = {};

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

  function renderNetworkStatus(hub) {
    var strip = document.getElementById('profile-mn2-network-status');
    if (!strip || !hub) return;
    var net = hub.network || {};
    var peers = net.connections != null ? net.connections : net.peer_catalog_count;
    var height = net.block_height != null ? net.block_height : '—';
    var health = net.peer_health || {};
    var sp = hub.spork_gates || {};
    var maint = sp.maintenance_mode ? 'Maintenance ON' : 'Network live';
    var exGate = sp.exchange_live && sp.exchange_live.allowed === false ? ' · Exchange gated' : '';
    strip.innerHTML =
      '<span class="mn2-net-pill">Height <strong>' + height + '</strong></span>' +
      '<span class="mn2-net-pill">Peers <strong>' + (peers != null ? peers : '—') + '</strong></span>' +
      '<span class="mn2-net-pill">' + maint + exGate + '</span>' +
      (health.message ? '<span class="mn2-net-pill mn2-net-pill--' + (health.status || 'unknown') + '">' + health.message + '</span>' : '') +
      ' <a href="/api/mn2/network-peers" style="color:#00d4ff;font-size:0.78rem;">Bootstrap peers</a>';
  }

  function renderDeposit(addrData) {
    var addrEl = document.getElementById('profile-mn2-deposit-address');
    var qrEl = document.getElementById('profile-mn2-qr');
    var explorerLink = document.getElementById('profile-mn2-explorer-link');
    var depositErrEl = document.getElementById('profile-mn2-deposit-error');
    var depositHintEl = document.getElementById('profile-mn2-deposit-hint');
    var depositRetryBtn = document.getElementById('profile-mn2-deposit-retry');
    var requestAddrBtn = document.getElementById('profile-mn2-request-addr');
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
      if (qrEl && typeof QRCode !== 'undefined') {
        qrEl.innerHTML = '';
        try {
          new QRCode(qrEl, { text: addrData.deposit_address, width: 96, height: 96 });
        } catch (e) {
          qrEl.innerHTML = '';
        }
      }
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
          var src = t.source ? '[' + t.source + '] ' : '';
          var type = t.type || '—';
          var amt = t.amount != null ? Number(t.amount).toFixed(4) : '—';
          var txLink = t.explorer_tx_url
            ? '<a href="' + t.explorer_tx_url + '" target="_blank" rel="noopener" style="color:#00d4ff;">Explorer tx</a>'
            : '';
          var addrLink = t.explorer_address_url
            ? ' <a href="' + t.explorer_address_url + '" target="_blank" rel="noopener" style="color:#88ccff;">Explorer address</a>'
            : '';
          var date = t.created_at ? new Date(t.created_at).toLocaleString() : '';
          return '<li>' + src + type + ': ' + amt + ' MN2 ' + txLink + addrLink + (date ? ' (' + date + ')' : '') + '</li>';
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

  function loadTabData(tab) {
    if (tabsLoaded[tab]) return;
    var user = uid();
    var q = encodeURIComponent(user);
    if (tab === 'deposit') {
      tabsLoaded.deposit = true;
      fetchJson(base() + '/api/mn2/deposit-address?user_id=' + q, { timeout: 18000 }).then(function (res) {
        renderDeposit(res.data);
      });
    } else if (tab === 'transactions') {
      tabsLoaded.transactions = true;
      fetchJson(base() + '/api/mn2/recent-transactions?limit=25').then(function (res) {
        renderTransactions(res.data);
      });
      if (typeof global.profileMn2LoadStatement === 'function') {
        global.profileMn2LoadStatement();
      }
    } else if (tab === 'overview') {
      tabsLoaded.overview = true;
      fetchJson(base() + '/api/mn2/wallet-activity?user_id=' + q + '&days=5', { timeout: 15000 }).then(function (res) {
        renderActivity(res.data);
      });
    } else if (tab === 'desktop') {
      loadWalletDownloads();
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
              tabsLoaded.transactions = false;
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
      loadTabData(tab);
    });
  }

  var downloadsLoaded = false;
  function loadWalletDownloads() {
    if (downloadsLoaded) return;
    var grid = document.getElementById('profile-wallet-downloads');
    if (!grid) return;
    fetchJson(base() + '/api/mn2/releases', { timeout: 15000 }).then(function (res) {
      downloadsLoaded = true;
      var d = res.data || {};
      if (!d.success || !(d.downloads && d.downloads.length)) {
        grid.innerHTML = '<p style="opacity:0.8;margin:0;">Downloads unavailable. <a href="/wallets" style="color:#00d4ff;">Try wallets page</a></p>';
        return;
      }
      grid.innerHTML = d.downloads
        .map(function (item, i) {
          return (
            '<article class="mn2-wallet-dl-card' +
            (i === 0 ? ' mn2-wallet-dl-card--featured' : '') +
            '">' +
            '<div class="mn2-wallet-dl-head"><span class="mn2-wallet-dl-icon">' +
            (item.icon || '💠') +
            '</span><div><h3 class="mn2-wallet-dl-title">' +
            item.name +
            '</h3><p class="mn2-wallet-dl-platform">' +
            item.platform +
            (item.release_tag ? ' · ' + item.release_tag : '') +
            '</p></div></div>' +
            '<p class="mn2-wallet-dl-desc">' +
            (item.description || '') +
            '</p>' +
            '<div class="mn2-wallet-dl-actions"><a class="mn2-wallet-dl-btn" href="' +
            item.url +
            '" download><i class="fas fa-download"></i> ' +
            item.filename +
            '</a></div>' +
            (item.sha256
              ? '<div class="mn2-wallet-dl-checksum">SHA256 ' + item.sha256.slice(0, 16) + '…</div>'
              : '') +
            '</article>'
          );
        })
        .join('');
    }).catch(function () {
      grid.innerHTML = '<p style="opacity:0.8;margin:0;">Could not load downloads.</p>';
    });
  }

  function load() {
    var balanceEl = document.getElementById('profile-mn2-balance');
    var chartEl = document.getElementById('profile-mn2-5d-chart');
    if (balanceEl && balanceEl.textContent === '--') balanceEl.textContent = '…';
    if (chartEl && chartEl.textContent.indexOf('Loading') >= 0) {
      chartEl.innerHTML = '<span style="opacity:0.6;font-size:0.85rem;">Loading activity…</span>';
    }

    wireControls();
    wireFiatToggle();
    initWalletSubTabs();

    fetchJson(base() + '/api/mn2/wallet-hub?user_id=' + encodeURIComponent(uid()), { timeout: 15000 }).then(function (res) {
      var hub = res.data || {};
      if (hub.success) {
        var bal = hub.balance || {};
        if (hub.mn2_usd_price != null) bal.mn2_usd_price = hub.mn2_usd_price;
        renderBalance(bal);
        renderNetworkStatus(hub);
        var txPrev = hub.recent_transactions_preview;
        if (txPrev && txPrev.length && !tabsLoaded.transactions) {
          var txList = document.getElementById('profile-mn2-transactions');
          if (txList && txList.textContent.indexOf('Loading') >= 0) {
            renderTransactions({ success: true, transactions: txPrev });
          }
        }
      } else {
        fetchJson(base() + '/api/mn2/balance?user_id=' + encodeURIComponent(uid())).then(function (r2) {
          renderBalance(r2.data);
        });
      }
    });

    loadTabData('overview');
  }

  global.ProfileMn2Wallet = { load: load, requestDepositAddress: requestDepositAddress, loadTabData: loadTabData };
})(window);
