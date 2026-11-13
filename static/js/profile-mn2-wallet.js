/**
 * Profile MN2 wallet — independent section loading, deposit request, wallet sub-tabs.
 */
(function (global) {
  'use strict';

  var TIMEOUT_MS = 12000;

  function uid() {
    var fromProfile = global.profileManager && global.profileManager.userId;
    if (global.MnUserId && global.MnUserId.isUsable(fromProfile)) return String(fromProfile).trim();
    if (global.MnUserId && typeof global.MnUserId.read === 'function') return global.MnUserId.read();
    return '';
  }

  function base() {
    return global.location.origin;
  }

  function readSecurityToken() {
    try {
      var casino = localStorage.getItem('casino_security_token') || '';
      if (casino) return casino;
    } catch (e) { /* ignore */ }
    try {
      var sess = sessionStorage.getItem('mn2_security_token') || sessionStorage.getItem('security_verification_token') || '';
      if (sess) return sess;
    } catch (e2) { /* ignore */ }
    var input = document.getElementById('profile-mn2-withdraw-security-token')
      || document.getElementById('profile-security-verify-token');
    return (input && input.value) ? String(input.value).trim() : '';
  }

  function readTotpCode() {
    var input = document.getElementById('profile-mn2-withdraw-totp')
      || document.getElementById('mn2-withdraw-totp');
    return (input && input.value) ? String(input.value).trim() : '';
  }

  function ensureSessionBound(user) {
    if (!user) return Promise.resolve();
    return fetchJson(base() + '/api/user/bind-session', {
      method: 'POST',
      body: { user_id: user },
      timeout: 8000,
    }).catch(function () {
      return { ok: false, data: {} };
    });
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
      .catch(function (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'profile-mn2-wallet.js', context: 'catch' }); }
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
    if (global.Mn2Wallet) {
      global.Mn2Wallet.renderOnchain(document.getElementById('profile-mn2-onchain'), balData);
    }
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

  function badge(label, kind) {
    var colors = {
      ok: 'background:rgba(0,255,136,0.18);color:#00ff88;border:1px solid rgba(0,255,136,0.35)',
      warn: 'background:rgba(255,170,0,0.16);color:#ffaa00;border:1px solid rgba(255,170,0,0.35)',
      bad: 'background:rgba(255,80,80,0.16);color:#ff8888;border:1px solid rgba(255,80,80,0.35)',
      info: 'background:rgba(0,212,255,0.14);color:#00d4ff;border:1px solid rgba(0,212,255,0.35)',
    };
    return '<span style="padding:3px 8px;border-radius:999px;' + (colors[kind] || colors.info) + ';">' + label + '</span>';
  }

  function renderStatusBadges(frameData) {
    var el = document.getElementById('profile-mn2-status-badges');
    if (!el || !frameData) return;
    var parts = [];
    var mode = frameData.wallet_mode || 'ledger';
    parts.push(badge('mode ' + mode, 'info'));
    if (frameData.ledger_only) {
      parts.push(badge('ledger receive', 'warn'));
    } else {
      parts.push(badge('chain deposit', 'ok'));
    }
    var rpc = frameData.rpc_status || 'unknown';
    parts.push(badge('RPC ' + rpc, rpc === 'up' ? 'ok' : rpc === 'unconfigured' ? 'warn' : 'bad'));
    if (frameData.fee_payer_configured === false && mode === 'onchain') {
      parts.push(badge('fee payer missing', 'bad'));
    } else if (frameData.fee_payer_configured) {
      parts.push(badge('fee payer ready', 'ok'));
    }
    if (frameData.last_scan && frameData.last_scan.end) {
      parts.push(badge('scan ok', frameData.last_scan.error ? 'bad' : 'ok'));
    }
    el.innerHTML = parts.join('');
  }

  function renderPendingDeposits(frameData) {
    var el = document.getElementById('profile-mn2-pending-deposits');
    if (!el) return;
    var rows = (frameData && frameData.pending_deposits) || [];
    if (!rows.length) {
      el.innerHTML = frameData && frameData.ledger_only
        ? '<span style="opacity:0.75;">No on-chain pending deposits while using a ledger receive id.</span>'
        : '<span style="opacity:0.75;">No pending deposits awaiting confirmations.</span>';
      return;
    }
    el.innerHTML =
      '<strong style="color:#00d4ff;">Pending deposits</strong><ul style="margin:6px 0 0;padding-left:1.1rem;">' +
      rows
        .map(function (r) {
          return (
            '<li>' +
            (Number(r.amount_mn2) || 0).toFixed(4) +
            ' MN2 · ' +
            (r.progress || r.confirmations + '/' + r.required_confirmations) +
            ' conf' +
            (r.txid ? ' · ' + String(r.txid).slice(0, 10) + '…' : '') +
            '</li>'
          );
        })
        .join('') +
      '</ul>';
  }

  var _upgradePollTimer = null;
  function maybeStartUpgradePoll(frameData) {
    if (_upgradePollTimer) {
      clearInterval(_upgradePollTimer);
      _upgradePollTimer = null;
    }
    if (!(frameData && frameData.ledger_only)) return;
    var ticks = 0;
    _upgradePollTimer = setInterval(function () {
      ticks += 1;
      if (ticks > 20) {
        clearInterval(_upgradePollTimer);
        _upgradePollTimer = null;
        return;
      }
      fetchJson(base() + '/api/mn2/wallet-frame?user_id=' + encodeURIComponent(uid()), { timeout: 12000 }).then(function (res) {
        var data = res.data || {};
        if (data.success && !data.ledger_only && data.deposit_address) {
          clearInterval(_upgradePollTimer);
          _upgradePollTimer = null;
          renderDeposit(data);
          renderStatusBadges(data);
          renderPendingDeposits(data);
          if (typeof toast !== 'undefined') toast.success('Chain deposit address ready');
        }
      });
    }, 45000);
  }

  function renderDeposit(addrData) {
    var addrEl = document.getElementById('profile-mn2-deposit-address');
    var qrEl = document.getElementById('profile-mn2-qr');
    var explorerLink = document.getElementById('profile-mn2-explorer-link');
    var depositErrEl = document.getElementById('profile-mn2-deposit-error');
    var depositHintEl = document.getElementById('profile-mn2-deposit-hint');
    var depositRetryBtn = document.getElementById('profile-mn2-deposit-retry');
    var requestAddrBtn = document.getElementById('profile-mn2-request-addr');
    renderStatusBadges(addrData || {});
    renderPendingDeposits(addrData || {});
    maybeStartUpgradePoll(addrData || {});
    if (addrData && addrData.success && addrData.deposit_address) {
      if (addrEl) addrEl.textContent = addrData.deposit_address;
      if (depositErrEl) {
        depositErrEl.style.display = 'none';
        depositErrEl.textContent = '';
      }
      if (depositHintEl) {
        depositHintEl.style.display = '';
        if (addrData.ledger_only || addrData.address_warning) {
          depositHintEl.textContent = addrData.address_warning
            || 'In-app ledger wallet — balance and peer transfers work; do not send on-chain MN2 here.';
        } else if (addrData.mn2_coins != null) {
          depositHintEl.textContent = 'One wallet · ' + addrData.mn2_coins + ' MN2 coins';
        } else {
          depositHintEl.style.display = 'none';
        }
      }
      if (depositRetryBtn) depositRetryBtn.style.display = 'none';
      if (requestAddrBtn) requestAddrBtn.style.display = 'inline-block';
      if (explorerLink && addrData.explorer_address_url) {
        explorerLink.href = addrData.explorer_address_url;
        explorerLink.style.display = '';
      } else if (explorerLink) {
        explorerLink.style.display = 'none';
      }
      if (qrEl && typeof QRCode !== 'undefined' && !addrData.ledger_only) {
        qrEl.innerHTML = '';
        try {
          new QRCode(qrEl, { text: addrData.deposit_address, width: 96, height: 96 });
        } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'profile-mn2-wallet.js', context: 'catch' }); }
          qrEl.innerHTML = '';
        }
      } else if (qrEl && addrData.ledger_only) {
        qrEl.innerHTML = '';
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
        return fetchJson(base() + '/api/mn2/wallet-frame?user_id=' + encodeURIComponent(user), { timeout: 20000 });
      });
    } else {
      promise = fetchJson(base() + '/api/mn2/wallet-frame?user_id=' + encodeURIComponent(user), { timeout: 20000 });
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
        var body = {
          user_id: uid(),
          address: address,
          amount: amount,
        };
        var token = readSecurityToken();
        if (token) body.verification_token = token;
        var totp = readTotpCode();
        if (totp) body.totp_code = totp;
        ensureSessionBound(uid()).then(function () {
          return fetchJson(base() + '/api/mn2/withdraw', {
            method: 'POST',
            body: body,
            timeout: 20000,
          });
        })
          .then(function (res) {
            var data = res.data || {};
            if (data.success) {
              if (typeof toast !== 'undefined') toast.success('Withdrawal sent');
              document.getElementById('profile-mn2-withdraw-address').value = '';
              document.getElementById('profile-mn2-withdraw-amount').value = '';
              load();
              return;
            }
            var code = data.code || '';
            var err = data.error || 'Withdrawal failed';
            if (code === 'password_verification_required') {
              err = 'Verify your password in Profile → Security, then withdraw again.';
            } else if (code === 'whitelist_required') {
              err = 'Add this address to your withdrawal whitelist first (security panel below).';
              fetchJson(base() + '/api/mn2/withdraw/whitelist', {
                method: 'POST',
                body: { action: 'add', address: address, user_id: uid() },
              }).then(function (wl) {
                if (wl.data && wl.data.success && typeof toast !== 'undefined') {
                  toast.success('Address added to whitelist. Retry after cooldown if prompted.');
                }
              });
            } else if (code === 'rpc_unconfigured' || code === 'rpc_error') {
              err = (data.error || err) + ' Tip: send to another user with Transfer (ledger mode).';
            }
            if (typeof toast !== 'undefined') toast.error(err);
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

  function renderNftWallet(data) {
    var root = document.getElementById('profile-mn2-nft-wallet');
    var emblemEl = document.getElementById('profile-mn2-nft-emblems');
    var strip = document.getElementById('profile-nft-emblems-strip');
    if (!data || !data.success) {
      if (root) root.textContent = 'NFT wallet unavailable.';
      return;
    }
    var editions = data.editions || [];
    if (root) {
      if (!editions.length) {
        root.innerHTML = 'No editions yet. <a href="/market" style="color:#c08cff;">Buy on market</a>.';
      } else {
        root.innerHTML = editions.map(function (e) {
          return '<div style="padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.06);">' +
            '<strong>' + e.edition_id + '</strong> · ' + (e.emblem_icon || '💎') +
            ' <button type="button" class="btn-primary" style="padding:4px 8px;margin-left:8px;" data-equip-nft="' + e.edition_id + '">Use avatar</button></div>';
        }).join('');
        root.querySelectorAll('[data-equip-nft]').forEach(function (btn) {
          btn.addEventListener('click', function () {
            var eid = btn.getAttribute('data-equip-nft');
            fetchJson(base() + '/api/nft/equip-avatar', {
              method: 'POST',
              body: { user_id: uid(), edition_id: eid },
            }).then(function (res) {
              if (res.data && res.data.success) {
                if (typeof toast !== 'undefined') toast.success('Avatar updated from ' + eid);
                if (res.data.avatar_url && global.profileManager && global.backendConnector) {
                  var newPrefs = Object.assign({}, global.profileManager.currentPreferences || {}, {
                    avatar_url: res.data.avatar_url,
                  });
                  global.backendConnector.updateUserProfile({ preferences: newPrefs }).then(function () {
                    global.profileManager.loadProfile();
                  });
                } else if (global.profileManager) {
                  global.profileManager.initAvatarTab();
                }
              }
            });
          });
        });
      }
    }
    fetchJson(base() + '/api/nft/emblems?user_id=' + encodeURIComponent(uid())).then(function (res) {
      var emblems = (res.data && res.data.emblems) || [];
      var html = emblems.length
        ? 'Emblems: ' + emblems.map(function (e) { return (e.icon || '💎') + ' ' + e.name; }).join(' · ')
        : '';
      if (emblemEl) emblemEl.textContent = html;
      if (strip) strip.innerHTML = html ? ('💎 NFT emblems — ' + html) : '';
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

    ensureSessionBound(user).then(function () {
      fetchJson(base() + '/api/mn2/balance?user_id=' + q).then(function (res) {
        renderBalance(res.data);
      });
      fetchJson(base() + '/api/mn2/wallet-frame?user_id=' + q, { timeout: 18000 }).then(function (res) {
        renderDeposit(res.data);
      });
      fetchJson(base() + '/api/mn2/transactions?user_id=' + q + '&limit=20').then(function (res) {
        renderTransactions(res.data);
      });
      fetchJson(base() + '/api/mn2/wallet-activity?user_id=' + q + '&days=5').then(function (res) {
        renderActivity(res.data);
      });
      fetchJson(base() + '/api/nft/wallet?user_id=' + q).then(function (res) {
        renderNftWallet(res.data);
      });
    });
  }

  global.ProfileMn2Wallet = { load: load, requestDepositAddress: requestDepositAddress };
})(window);
