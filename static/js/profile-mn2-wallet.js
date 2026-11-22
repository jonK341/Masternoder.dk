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

  function fetchJson(url, opts) {
    opts = opts || {};
    var ctrl = new AbortController();
    var timer = setTimeout(function () {
      ctrl.abort();
    }, opts.timeout || TIMEOUT_MS);
    var method = opts.method || 'GET';
    var headers = Object.assign({}, opts.headers || {});
    // Only set JSON Content-Type when sending a body. A GET with
    // Content-Type: application/json triggers middleware Bad Request.
    if (opts.body != null) {
      headers['Content-Type'] = headers['Content-Type'] || 'application/json';
    }
    return fetch(url, {
      method: method,
      credentials: 'same-origin',
      headers: headers,
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
      if (depositHintEl) {
        if (addrData.mn2_coins != null) {
          depositHintEl.style.display = '';
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
      }
      if (qrEl && typeof QRCode !== 'undefined') {
        qrEl.innerHTML = '';
        try {
          new QRCode(qrEl, { text: addrData.deposit_address, width: 96, height: 96 });
        } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'profile-mn2-wallet.js', context: 'catch' }); }
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

  function fmtCoin(n, d) {
    var x = Number(n || 0);
    if (!isFinite(x)) return '—';
    if (x === 0) return '0';
    if (x > 0 && x < 0.0001) return x.toExponential(3);
    return x.toLocaleString(undefined, { maximumFractionDigits: d == null ? 6 : d });
  }

  function renderCoinGrid(el, wallet, opts) {
    if (!el) return;
    opts = opts || {};
    if (!wallet || !wallet.success) {
      el.innerHTML = '<p style="opacity:0.75;margin:0;">Exchange wallets unavailable.</p>';
      return;
    }
    var rows = wallet.wallets || [];
    if (!rows.length) {
      var assets = wallet.assets || {};
      rows = Object.keys(assets).sort().map(function (sym) {
        return { symbol: sym, name: sym, balance: assets[sym], usd_value: 0 };
      });
      if (wallet.mn2_balance != null) {
        rows.unshift({ symbol: 'MN2', name: 'MasterNoder2', balance: wallet.mn2_balance, usd_value: 0 });
      }
    }
    if (opts.nonzeroOnly) {
      rows = rows.filter(function (r) { return Number(r.balance || 0) > 0; });
    }
    if (!rows.length) {
      el.innerHTML = '<p style="opacity:0.75;margin:0;">No coin balances yet.</p>';
      return;
    }
    var limit = opts.limit || rows.length;
    var shown = rows.slice(0, limit);
    el.innerHTML = shown.map(function (r) {
      var bal = Number(r.balance || 0);
      var usd = Number(r.usd_value || 0);
      var cls = bal > 0 ? 'profile-coin-chip is-funded' : 'profile-coin-chip';
      return '<div class="' + cls + '" title="' + (r.name || r.symbol) + '">' +
        '<span class="sym">' + (r.symbol || '?') + '</span>' +
        '<strong>' + fmtCoin(bal, bal < 1 ? 6 : 4) + '</strong>' +
        (usd > 0 ? '<span class="usd">$' + fmtCoin(usd, 2) + '</span>' : '<span class="usd">$0</span>') +
        '</div>';
    }).join('') +
      (rows.length > limit
        ? '<p style="grid-column:1/-1;margin:4px 0 0;font-size:0.78rem;opacity:0.75;">+' +
          (rows.length - limit) + ' more on All coins · total ~$' + fmtCoin(wallet.total_usd, 2) + '</p>'
        : '<p style="grid-column:1/-1;margin:4px 0 0;font-size:0.78rem;opacity:0.75;">' +
          (wallet.wallet_count || rows.length) + ' wallets · ~$' + fmtCoin(wallet.total_usd, 2) + '</p>');
  }

  function renderAgentWallets(el, data) {
    if (!el) return;
    if (!data || !data.success || !(data.agents || []).length) {
      el.innerHTML = '<p style="opacity:0.75;margin:0;">No exchange agents configured.</p>';
      return;
    }
    el.innerHTML = data.agents.map(function (a) {
      var w = a.wallet || {};
      var rows = w.wallets || [];
      var funded = rows.filter(function (r) { return Number(r.balance || 0) > 0; });
      var chips = (funded.length ? funded : rows.slice(0, 8)).map(function (r) {
        return '<span class="profile-agent-bal">' + r.symbol + ' ' + fmtCoin(r.balance, 4) + '</span>';
      }).join(' ');
      return '<div class="profile-agent-wallet-card">' +
        '<div class="profile-agent-wallet-head"><strong>' + (a.name || a.id) + '</strong>' +
        '<span>' + ((a.assets || []).join(', ') || 'all coins') + '</span></div>' +
        '<div class="profile-agent-wallet-bals">' + (chips || 'All coin slots ready (0)') + '</div>' +
        '<div class="profile-agent-wallet-meta">MN2 ' + fmtCoin(w.mn2_balance, 4) +
        ' · ~$' + fmtCoin(w.total_usd, 2) + ' · ' + (w.wallet_count || 0) + ' wallets</div></div>';
    }).join('');
  }

  function fillProfileMwAssets(wallet) {
    var sel = document.getElementById('profile-mw-asset');
    if (!sel) return;
    var rows = (wallet && wallet.wallets) || [];
    if (!rows.length) return;
    var cur = sel.value;
    sel.innerHTML = rows.map(function (r) {
      return '<option value="' + r.symbol + '">' + r.symbol + '</option>';
    }).join('');
    if (cur) sel.value = cur;
  }

  function loadExchangeWallets() {
    var user = encodeURIComponent(uid());
    fetchJson(base() + '/api/exchange/wallet?user_id=' + user).then(function (res) {
      var wallet = res.data || res;
      renderCoinGrid(document.getElementById('profile-exchange-wallet-preview'), wallet, { nonzeroOnly: false, limit: 8 });
      renderCoinGrid(document.getElementById('profile-exchange-wallet-all'), wallet, { nonzeroOnly: false });
      fillProfileMwAssets(wallet);
    });
    fetchJson(base() + '/api/exchange/agents').then(function (res) {
      renderAgentWallets(document.getElementById('profile-exchange-agent-wallets'), res.data || res);
    });
    fetchJson(base() + '/api/exchange/multi-wallet/daemon').then(function (res) {
      var el = document.getElementById('profile-mw-daemon-status');
      var d = res.data || res;
      if (!el) return;
      if (!d || !d.success) {
        el.textContent = 'Multi-daemon status unavailable.';
        return;
      }
      el.textContent = 'One multi-daemon for all coins · ticks=' + (d.tick_count || 0) +
        (d.last_tick_at ? ' · last ' + String(d.last_tick_at).slice(0, 19) : '') +
        ' · script ' + (d.daemon_script || 'exchange_multi_wallet_daemon.py');
    });
    var depBtn = document.getElementById('profile-mw-deposit-btn');
    if (depBtn && !depBtn._mwWired) {
      depBtn._mwWired = true;
      depBtn.addEventListener('click', function () {
        var asset = (document.getElementById('profile-mw-asset') || {}).value || 'USDT';
        var amount = (document.getElementById('profile-mw-amount') || {}).value;
        var info = document.getElementById('profile-mw-deposit-info');
        var path = base() + '/api/exchange/deposit?asset=' + encodeURIComponent(asset) +
          '&user_id=' + encodeURIComponent(uid()) +
          (amount ? '&amount=' + encodeURIComponent(amount) : '');
        fetchJson(path).then(function (res) {
          var d = res.data || res;
          if (!info) return;
          if (!d || !d.success) {
            info.textContent = (d && (d.message || d.error)) || 'Could not load deposit address.';
            return;
          }
          info.innerHTML = '<strong>' + d.asset + '</strong> (' + (d.network || '') + ')<br><code>' +
            (d.address || '—') + '</code>' +
            (d.tag ? '<br>Memo: <code>' + d.tag + '</code>' : '') +
            '<br><span style="opacity:0.8">' + (d.message || '') + '</span>';
        });
      });
    }
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
    loadExchangeWallets();
  }

  global.ProfileMn2Wallet = { load: load, requestDepositAddress: requestDepositAddress };
})(window);
