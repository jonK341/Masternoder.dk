/**
 * Profile MN2 wallet — independent section loading, deposit request, wallet sub-tabs.
 */
(function (global) {
  'use strict';

  var TIMEOUT_MS = 12000;
  var POLL_MS = 3000;
  var QR_RENDER_PX = 256;
  var QR_DISPLAY_PX = 192;
  var _pollTimer = null;
  var _sse = null;
  var _lastBalance = null;
  var _lastStakeStatus = null;
  var _lastDepositAddress = null;
  var _withdrawSecurity = null;

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
    var method = (opts.method || 'GET').toUpperCase();
    var headers = Object.assign({}, opts.headers || {});
    var body = opts.body ? JSON.stringify(opts.body) : undefined;
    // Flask rejects GET requests that send Content-Type: application/json (400 Bad Request).
    if (body && !headers['Content-Type'] && !headers['content-type']) {
      headers['Content-Type'] = 'application/json';
    }
    var ctrl = new AbortController();
    var timer = setTimeout(function () {
      ctrl.abort();
    }, opts.timeout || TIMEOUT_MS);
    return fetch(url, {
      method: method,
      credentials: 'same-origin',
      headers: headers,
      body: body,
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

  var _MN2_ADDR_RE = /^[MJ][1-9A-HJ-NP-Za-km-z]{24,55}$/;

  function looksLikeMn2Address(addr) {
    return _MN2_ADDR_RE.test((addr || '').replace(/\s+/g, '').trim());
  }

  function humanizeWalletError(msg) {
    var t = (msg || '').toString();
    if (/invalid.*address|rejected|format validation/i.test(t)) {
      return 'Could not create address — wallet node rejected the format. Ensure MN2 RPC is online, then retry.';
    }
    if (/unreachable|connection|refused|timeout|401|403|rpc/i.test(t)) {
      return 'Wallet node unavailable. Start the MN2 daemon and check RPC settings, then try again.';
    }
    return t || 'Could not create wallet address.';
  }

  function renderWithdrawSecurityHint(sec) {
    var el = document.getElementById('profile-mn2-withdraw-whitelist-hint');
    if (!el || !sec) return;
    el.style.display = sec.withdrawal_requires_whitelist ? 'block' : 'none';
    renderWithdrawWhitelistQuick(sec);
  }

  function renderWithdrawWhitelistQuick(sec) {
    if (sec) _withdrawSecurity = sec;
    var quick = document.getElementById('profile-mn2-withdraw-whitelist-quick');
    if (!quick) return;
    var required = _withdrawSecurity && _withdrawSecurity.withdrawal_requires_whitelist;
    quick.style.display = required ? 'block' : 'none';
  }

  function renderWithdrawBalanceHint(balData) {
    var el = document.getElementById('profile-mn2-withdraw-balance-hint');
    if (!el) return;
    if (!balData || !balData.success) {
      el.textContent = 'Withdrawable balance: loading…';
      return;
    }
    var liquid = balData.liquid_mn2 != null ? Number(balData.liquid_mn2) : Number(balData.mn2_balance) || 0;
    var held = balData.held_mn2 != null ? Number(balData.held_mn2) : 0;
    var withdrawable =
      balData.withdrawable_mn2 != null ? Number(balData.withdrawable_mn2) : Math.max(0, liquid - held);
    var text = 'Withdrawable: ' + withdrawable.toFixed(8) + ' MN2';
    if (held > 0) text += ' (' + held.toFixed(4) + ' on clearance hold)';
    el.textContent = text;
  }

  function loadWithdrawSecurityHint() {
    return fetchJson(base() + '/api/mn2/withdraw/security', { timeout: 8000 }).then(function (res) {
      if (res.data && res.data.success !== false) {
        _withdrawSecurity = res.data;
        renderWithdrawSecurityHint(res.data);
      }
    });
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

  function ensureBalanceBreakdownEl() {
    var el = document.getElementById('profile-mn2-balance-breakdown');
    if (el) return el;
    var chart = document.getElementById('profile-mn2-5d-chart');
    if (!chart || !chart.parentNode) return null;
    el = document.createElement('div');
    el.id = 'profile-mn2-balance-breakdown';
    el.style.cssText =
      'display:flex;flex-wrap:wrap;gap:8px;margin:10px 0;font-size:0.78rem;';
    chart.parentNode.insertBefore(el, chart);
    return el;
  }

  function renderBalanceBreakdown(balData, stakeData) {
    var el = ensureBalanceBreakdownEl();
    if (!el || !balData || !balData.success) {
      if (el) el.innerHTML = '';
      return;
    }
    var liquid = balData.liquid_mn2 != null ? Number(balData.liquid_mn2) : Number(balData.mn2_balance) || 0;
    var held = balData.held_mn2 != null ? Number(balData.held_mn2) : 0;
    var withdrawable =
      balData.withdrawable_mn2 != null ? Number(balData.withdrawable_mn2) : Math.max(0, liquid - held);
    var staked = stakeData && stakeData.success ? Number(stakeData.staked || 0) : null;
    function chip(label, value, color) {
      return (
        '<div class="mn2-monitor-chip" style="min-width:110px;"><span>' +
        label +
        '</span><strong style="color:' +
        (color || '#00ff88') +
        ';">' +
        value.toFixed(4) +
        '</strong></div>'
      );
    }
    var html = chip('Liquid', liquid, '#00d4ff');
    if (staked != null) html += chip('Staked', staked, '#7ee8ff');
    if (held > 0) html += chip('On hold', held, '#ffaa44');
    html += chip('Withdrawable', withdrawable, '#00ff88');
    el.innerHTML = html;
  }

  function renderBalance(balData, stakeData) {
    var balanceEl = document.getElementById('profile-mn2-balance');
    var fiatEl = document.getElementById('profile-mn2-balance-fiat');
    if (!balData || !balData.success) {
      if (balanceEl) balanceEl.textContent = '—';
      var showcaseErr = document.getElementById('profile-mn2-showcase-balance');
      if (showcaseErr) showcaseErr.textContent = '—';
      renderBalanceBreakdown(null, null);
      return;
    }
    renderBalanceBreakdown(balData, stakeData);
    var balNum = Number(balData.mn2_balance) || 0;
    if (balanceEl) balanceEl.textContent = balNum.toFixed(8);
    var showcase = document.getElementById('profile-mn2-showcase-balance');
    if (showcase) showcase.textContent = balNum.toFixed(4) + ' MN2';
    if (_lastBalance !== null && balNum > _lastBalance) {
      flashInstantCredit(balNum - _lastBalance);
    }
    _lastBalance = balNum;
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
    renderWithdrawBalanceHint(balData);
    if (balData.deposit_address) _lastDepositAddress = balData.deposit_address;
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
      _lastDepositAddress = addrData.deposit_address;
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
          new QRCode(qrEl, {
            text: addrData.deposit_address,
            width: QR_RENDER_PX,
            height: QR_RENDER_PX,
            colorDark: '#000000',
            colorLight: '#ffffff',
            correctLevel: QRCode.CorrectLevel ? QRCode.CorrectLevel.H : undefined,
          });
          var canvas = qrEl.querySelector('canvas');
          var img = qrEl.querySelector('img');
          if (canvas) {
            canvas.style.width = QR_DISPLAY_PX + 'px';
            canvas.style.height = QR_DISPLAY_PX + 'px';
            canvas.style.imageRendering = 'pixelated';
          }
          if (img) {
            img.style.width = QR_DISPLAY_PX + 'px';
            img.style.height = QR_DISPLAY_PX + 'px';
            img.style.imageRendering = 'pixelated';
          }
        } catch (e) {
          qrEl.innerHTML = '';
        }
      }
    } else {
      if (addrEl) addrEl.textContent = '—';
      var errMsg = humanizeWalletError(
        (addrData && addrData.error) ||
          'Deposit address unavailable. Wallet RPC may be offline — use Request address when ready.'
      );
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
          var instantBadge = (t.metadata && t.metadata.chain_paid) || t.txid
            ? ' <span style="color:#00ff88;font-size:0.72rem;">⛓ on-chain</span>'
            : ' <span style="color:#88ffcc;font-size:0.72rem;">⚡ instant</span>';
          var txLink = t.explorer_tx_url
            ? '<a href="' + t.explorer_tx_url + '" target="_blank" rel="noopener" style="color:#00d4ff;">Explorer tx</a>'
            : '';
          var addrLink = t.explorer_address_url
            ? ' <a href="' + t.explorer_address_url + '" target="_blank" rel="noopener" style="color:#88ccff;">Explorer address</a>'
            : '';
          var date = t.created_at ? new Date(t.created_at).toLocaleString() : '';
          return '<li>' + type + ': ' + amt + ' MN2' + instantBadge + ' ' + txLink + addrLink + (date ? ' (' + date + ')' : '') + '</li>';
        })
        .join('') +
      '</ul>';
  }

  function renderUserWalletMap(data) {
    var summary = document.getElementById('profile-mn2-user-wallet-map-summary');
    var body = document.getElementById('profile-mn2-user-wallet-map-body');
    if (!body) return;
    if (!data || !data.success) {
      if (summary) summary.textContent = 'Could not load user wallet map.';
      body.innerHTML = '<tr><td colspan="5" style="padding:8px;opacity:0.7;">Unavailable</td></tr>';
      return;
    }
    var rows = data.users || [];
    if (summary) {
      summary.textContent =
        data.total +
        ' users total · ' +
        (data.wallet_ready_count || 0) +
        ' with wallet on this page · ' +
        (data.clone_copy_count || 0) +
        ' clone/copy rows';
    }
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="5" style="padding:8px;opacity:0.7;">No users found</td></tr>';
      return;
    }
    body.innerHTML = rows
      .map(function (r) {
        var clone =
          r.is_clone_copy
            ? '<span style="color:#ffaa44;" title="' +
              (r.clone_reasons || []).join(', ') +
              '">copy ×' +
              (r.clone_siblings || 2) +
              '</span>'
            : '—';
        var addr = r.deposit_address || (r.wallet_ready ? '…' : 'pending');
        var addrCell =
          r.explorer_address_url && r.deposit_address
            ? '<a href="' +
              r.explorer_address_url +
              '" target="_blank" rel="noopener" style="color:#00d4ff;word-break:break-all;">' +
              addr +
              '</a>'
            : '<code style="word-break:break-all;">' + addr + '</code>';
        var walletBadge = r.wallet_ready
          ? '<span style="color:#00ff88;">✓ ' + (r.wallet_type || 'core') + '</span>'
          : '<span style="color:#ffaa44;">missing</span>';
        return (
          '<tr style="border-top:1px solid rgba(255,255,255,0.06);">' +
          '<td style="padding:5px 8px;max-width:120px;word-break:break-all;">' +
          (r.user_id || '—') +
          '</td>' +
          '<td style="padding:5px 8px;">' +
          walletBadge +
          '</td>' +
          '<td style="padding:5px 8px;max-width:180px;">' +
          addrCell +
          '</td>' +
          '<td style="padding:5px 8px;">' +
          (Number(r.mn2_balance || 0).toFixed(4)) +
          '</td>' +
          '<td style="padding:5px 8px;">' +
          clone +
          '</td>' +
          '</tr>'
        );
      })
      .join('');
  }

  function renderAgentWallets(data) {
    var el = document.getElementById('profile-mn2-agent-wallets');
    if (!el) return;
    var rows = (data && data.success && data.agents) ? data.agents : [];
    if (!rows.length) {
      el.innerHTML = '<span style="opacity:0.75;font-size:0.82rem;">No agent wallets provisioned yet.</span>';
      return;
    }
    var unique = data.unique_addresses != null ? data.unique_addresses : rows.length;
    el.innerHTML =
      '<div style="font-size:0.74rem;opacity:0.78;margin-bottom:6px;">' +
      rows.length +
      ' agents · ' +
      unique +
      ' unique addresses</div>' +
      rows
        .map(function (a) {
          var addr = a.address || (a.address_pending ? 'pending (RPC)' : '—');
          var bal = Number(a.mn2_balance || 0).toFixed(4);
          var explorer = a.explorer_address_url
            ? ' <a href="' + a.explorer_address_url + '" target="_blank" rel="noopener" style="color:#00d4ff;font-size:0.72rem;">explorer</a>'
            : '';
          return (
            '<div class="mn2-wallet-row"><span style="color:#7ee8ff;font-weight:600;min-width:120px;">' +
            (a.agent_id || 'agent') +
            '</span><code style="flex:1;word-break:break-all;font-size:0.7rem;">' +
            addr +
            '</code><span style="color:#00ff88;font-size:0.72rem;">' +
            bal +
            ' MN2</span>' +
            explorer +
            '</div>'
          );
        })
        .join('');
  }

  function renderWalletsList(data) {
    var listEl = document.getElementById('profile-mn2-wallets-list');
    if (!listEl) return;
    var rows = (data && data.success && data.addresses) ? data.addresses : [];
    if (!rows.length) {
      listEl.innerHTML = '<p style="margin:0;opacity:0.75;">No wallets yet.</p>';
      return;
    }
    listEl.innerHTML = rows
      .map(function (w) {
        var addr = w.address || '—';
        var lbl = w.label || 'wallet';
        var active = w.active ? ' active' : '';
        var explorer = w.explorer_address_url
          ? ' <a href="' + w.explorer_address_url + '" target="_blank" rel="noopener" style="color:#00d4ff;font-size:0.72rem;">explorer</a>'
          : '';
        return (
          '<div class="mn2-wallet-row' +
          active +
          '"><span style="color:#00ff88;font-weight:600;">' +
          lbl +
          '</span><code style="flex:1;word-break:break-all;font-size:0.72rem;">' +
          addr +
          '</code>' +
          explorer +
          '</div>'
        );
      })
      .join('');
  }

  function flashInstantCredit(delta) {
    var showcase = document.getElementById('profile-mn2-showcase');
    if (!showcase) return;
    showcase.classList.add('mn2-instant-flash');
    var toast = document.getElementById('profile-mn2-instant-toast');
    if (toast) {
      toast.textContent = '+' + (Number(delta) || 0).toFixed(6) + ' MN2 credited instantly';
      toast.style.opacity = '1';
      setTimeout(function () { toast.style.opacity = '0'; }, 3200);
    }
    setTimeout(function () { showcase.classList.remove('mn2-instant-flash'); }, 900);
  }

  function renderDaemonMonitor(monData) {
    var el = document.getElementById('profile-mn2-daemon-monitor');
    if (!el) return;
    if (!monData || !monData.success) {
      el.innerHTML = '<span style="opacity:0.7;font-size:0.82rem;">Status unavailable.</span>';
      return;
    }
    var daemon = monData.daemon || {};
    var settlement = monData.last_settlement || {};
    var chainOn = monData.chain_payouts_enabled ? 'on' : 'off';
    var daemonOk = daemon.healthy;
    el.innerHTML =
      '<div class="mn2-monitor-chip"><span>Daemon</span><strong style="color:' +
      (daemonOk ? '#00ff88' : '#ffaa44') +
      ';">' +
      (daemonOk ? 'online' : 'offline') +
      '</strong><span style="opacity:0.7;">' +
      (daemon.block_height != null ? 'block ' + daemon.block_height : 'RPC probe') +
      '</span></div>' +
      '<div class="mn2-monitor-chip"><span>Chain payouts</span><strong style="color:#00d4ff;">' +
      chainOn +
      '</strong><span style="opacity:0.7;">' +
      (monData.chain_tx_count || 0) +
      ' on-chain tx</span></div>' +
      '<div class="mn2-monitor-chip"><span>Agent cron</span><strong style="color:#88ccff;">' +
      (settlement.ran_at ? 'active' : 'pending') +
      '</strong><span style="opacity:0.7;">' +
      (settlement.systems_count != null ? settlement.systems_count + ' systems' : 'awaiting run') +
      '</span></div>';
  }

  function renderSystemMonitor(monData) {
    var el = document.getElementById('profile-mn2-system-monitor');
    if (!el) return;
    renderDaemonMonitor(monData);
    if (!monData || !monData.success) {
      el.innerHTML = '<span style="opacity:0.7;font-size:0.82rem;">Monitor unavailable.</span>';
      return;
    }
    var systems = monData.by_system || {};
    var keys = Object.keys(systems);
    var chips = keys
      .map(function (k) {
        var s = systems[k] || {};
        var total = Number(s.total_mn2 || 0).toFixed(4);
        return (
          '<div class="mn2-monitor-chip"><span>' +
          k +
          '</span><strong>+' +
          total +
          '</strong><span style="opacity:0.7;">' +
          (s.count || 0) +
          ' tx</span></div>'
        );
      })
      .join('');
    el.innerHTML = chips || '<span style="opacity:0.7;font-size:0.82rem;">No reward activity yet — agents will credit instantly when systems run.</span>';
    var instantMsg = document.getElementById('profile-mn2-deposit-instant-msg');
    if (instantMsg) {
      var conf = monData.instant_deposit_confirmations != null
        ? monData.instant_deposit_confirmations
        : (monData.confirmations_required != null ? monData.confirmations_required : 0);
      var rewardsNote = monData.instant_rewards ? 'Rewards &amp; bonuses credit instantly' : 'Rewards may batch';
      instantMsg.innerHTML =
        rewardsNote +
        '. Deposits: ' +
        (monData.instant_deposits
          ? 'instant (' + conf + ' conf).'
          : 'after ' + conf + ' confirmations.');
    }
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
    var hasAddr = hasDepositAddress(addrEl);
    var promise;
    if (forceNew === true || (hasAddr && forceNew !== false && forceNew !== undefined)) {
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
          depositErrEl.textContent = humanizeWalletError(
            (res.data && res.data.error) || 'Could not get deposit address.'
          );
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
    var createWalletBtn = document.getElementById('profile-mn2-create-wallet');
    if (createWalletBtn && !createWalletBtn._mn2Wired) {
      createWalletBtn._mn2Wired = true;
      createWalletBtn.addEventListener('click', function () {
        var labelEl = document.getElementById('profile-mn2-new-wallet-label');
        var label = (labelEl && labelEl.value ? labelEl.value.trim() : '') || 'wallet';
        createWalletBtn.disabled = true;
        fetchJson(base() + '/api/mn2/wallet/create', {
          method: 'POST',
          body: { user_id: uid(), label: label },
          timeout: 20000,
        })
          .then(function (res) {
            var data = res.data || {};
            if (data.success) {
              if (typeof toast !== 'undefined') toast.success('New wallet created');
              if (labelEl) labelEl.value = '';
              showWalletTab('deposit');
              load();
            } else if (typeof toast !== 'undefined') {
              toast.error(humanizeWalletError(data.error || 'Could not create wallet'));
            }
            var depositErrEl = document.getElementById('profile-mn2-deposit-error');
            if (depositErrEl) {
              depositErrEl.textContent = humanizeWalletError(data.error || 'Could not create wallet');
              depositErrEl.style.display = 'block';
            }
          })
          .finally(function () {
            createWalletBtn.disabled = false;
          });
      });
    }
    var useDepositBtn = document.getElementById('profile-mn2-withdraw-use-deposit');
    if (useDepositBtn && !useDepositBtn._mn2Wired) {
      useDepositBtn._mn2Wired = true;
      useDepositBtn.addEventListener('click', function () {
        var addrInput = document.getElementById('profile-mn2-withdraw-address');
        var dep = _lastDepositAddress;
        if (!dep) {
          var depEl = document.getElementById('profile-mn2-deposit-address');
          dep = depEl && hasDepositAddress(depEl) ? depEl.textContent.trim() : '';
        }
        if (!dep) {
          if (typeof toast !== 'undefined') toast.error('No deposit address loaded — open Deposit tab first');
          return;
        }
        if (addrInput) addrInput.value = dep;
        var inlineMsg = document.getElementById('profile-mn2-withdraw-inline-msg');
        if (inlineMsg) {
          inlineMsg.textContent = 'Filled with your deposit address (self-transfer test).';
          inlineMsg.style.display = 'block';
          inlineMsg.style.color = '#88ccff';
        }
      });
    }
    var whitelistQuickBtn = document.getElementById('profile-mn2-withdraw-whitelist-add');
    if (whitelistQuickBtn && !whitelistQuickBtn._mn2Wired) {
      whitelistQuickBtn._mn2Wired = true;
      whitelistQuickBtn.addEventListener('click', function () {
        var addrInput = document.getElementById('profile-mn2-withdraw-address');
        var address = addrInput ? addrInput.value.replace(/\s+/g, '').trim() : '';
        var inlineMsg = document.getElementById('profile-mn2-withdraw-inline-msg');
        if (!address) {
          if (typeof toast !== 'undefined') toast.error('Enter a payout address first');
          return;
        }
        if (!looksLikeMn2Address(address)) {
          var fmtErr = 'Invalid MN2 address — use the full address (J… or M…, no spaces).';
          if (inlineMsg) {
            inlineMsg.textContent = fmtErr;
            inlineMsg.style.display = 'block';
            inlineMsg.style.color = '#ffaa44';
          }
          return;
        }
        whitelistQuickBtn.disabled = true;
        fetchJson(base() + '/api/mn2/withdraw/whitelist', {
          method: 'POST',
          body: { action: 'add', address: address },
          timeout: 15000,
        })
          .then(function (res) {
            var data = res.data || {};
            if (data.success) {
              if (typeof toast !== 'undefined') toast.success('Address added to whitelist');
              if (inlineMsg) {
                inlineMsg.textContent = 'Address whitelisted — you can withdraw to it now.';
                inlineMsg.style.display = 'block';
                inlineMsg.style.color = '#00ff88';
              }
              if (global.Mn2WithdrawalSecurity && global.Mn2WithdrawalSecurity.refresh) {
                global.Mn2WithdrawalSecurity.refresh();
              }
            } else {
              var err = data.error || 'Could not add to whitelist';
              if (inlineMsg) {
                inlineMsg.textContent = err;
                inlineMsg.style.display = 'block';
                inlineMsg.style.color = '#ffaa44';
              }
              if (typeof toast !== 'undefined') toast.error(err);
            }
          })
          .finally(function () {
            whitelistQuickBtn.disabled = false;
          });
      });
    }
    if (withdrawBtn && !withdrawBtn._mn2Wired) {
      withdrawBtn._mn2Wired = true;
      withdrawBtn.addEventListener('click', function () {
        var address = (document.getElementById('profile-mn2-withdraw-address') || {}).value
          .replace(/\s+/g, '')
          .trim();
        var amount = parseFloat((document.getElementById('profile-mn2-withdraw-amount') || {}).value);
        var inlineMsg = document.getElementById('profile-mn2-withdraw-inline-msg');
        if (inlineMsg) {
          inlineMsg.style.display = 'none';
          inlineMsg.textContent = '';
        }
        if (!address) {
          if (typeof toast !== 'undefined') toast.error('Enter MN2 address');
          return;
        }
        if (!looksLikeMn2Address(address)) {
          var fmtErr = 'Invalid MN2 address — use the full address from Deposit (J… or M…, no spaces).';
          if (inlineMsg) {
            inlineMsg.textContent = fmtErr;
            inlineMsg.style.display = 'block';
          }
          if (typeof toast !== 'undefined') toast.error(fmtErr);
          return;
        }
        if (!(amount > 0)) {
          if (typeof toast !== 'undefined') toast.error('Enter amount');
          return;
        }
        var totpEl = document.getElementById('profile-mn2-withdraw-totp');
        var totp = totpEl ? totpEl.value.trim() : '';
        withdrawBtn.disabled = true;
        var origHtml = withdrawBtn.innerHTML;
        withdrawBtn.textContent = 'Sending…';
        var body = { user_id: uid(), address: address, amount: amount };
        if (totp) body.totp_code = totp;
        fetchJson(base() + '/api/mn2/withdraw', {
          method: 'POST',
          body: body,
          timeout: 20000,
        })
          .then(function (res) {
            var data = res.data || {};
            if (data.success) {
              if (typeof toast !== 'undefined') toast.success('Withdrawal sent');
              document.getElementById('profile-mn2-withdraw-address').value = '';
              document.getElementById('profile-mn2-withdraw-amount').value = '';
              if (totpEl) totpEl.value = '';
              load();
            } else {
              var err = data.error || 'Withdrawal failed';
              if (data.code === 'whitelist_required') {
                err += ' Add it under Withdraw 2FA → whitelist, or use the Trusted tab.';
              } else if (data.code === 'invalid_address' || /invalid.*address/i.test(err)) {
                err = 'Invalid MN2 address — copy the full address from Deposit (starts with J or M, no spaces).';
              }
              if (inlineMsg) {
                inlineMsg.textContent = err;
                inlineMsg.style.display = 'block';
              }
              if (typeof toast !== 'undefined') toast.error(err);
            }
          })
          .finally(function () {
            withdrawBtn.disabled = false;
            withdrawBtn.innerHTML = origHtml;
          });
      });
    }
  }

  function showWalletTab(tab) {
    var nav = document.getElementById('profile-wallet-subnav');
    var panels = document.querySelectorAll('[data-wallet-panel]');
    var active = tab || 'overview';
    if (nav) {
      nav.querySelectorAll('[data-wallet-tab]').forEach(function (b) {
        var on = b.getAttribute('data-wallet-tab') === active;
        b.classList.toggle('active', on);
        b.setAttribute('aria-selected', on ? 'true' : 'false');
      });
    }
    panels.forEach(function (p) {
      var on = p.getAttribute('data-wallet-panel') === active;
      p.style.display = on ? 'block' : 'none';
    });
    try {
      var path = location.pathname || '';
      if (path.indexOf('/wallets') >= 0) {
        if (active === 'overview') history.replaceState(null, '', location.pathname);
        else history.replaceState(null, '', location.pathname + '#' + active);
      } else if (path.indexOf('/profile') >= 0) {
        var url = new URL(location.href);
        url.searchParams.set('tab', 'wallet');
        url.hash = active === 'overview' ? 'mn2-wallet' : active;
        history.replaceState(null, '', url.pathname + url.search + url.hash);
      }
    } catch (e) { /* ignore */ }
    if (global.Mn2WalletHubPanels && global.Mn2WalletHubPanels.onTabShown) {
      global.Mn2WalletHubPanels.onTabShown(active);
    }
    if (active === 'security' && global.Mn2WithdrawalSecurity && global.Mn2WithdrawalSecurity.refresh) {
      global.Mn2WithdrawalSecurity.refresh();
    }
    if (active === 'withdraw') {
      loadWithdrawSecurityHint();
      fetchJson(base() + '/api/mn2/balance?user_id=' + encodeURIComponent(uid()), { timeout: 8000 }).then(function (res) {
        renderWithdrawBalanceHint(res.data);
        if (res.data && res.data.deposit_address) _lastDepositAddress = res.data.deposit_address;
      });
    }
  }

  function initWalletSubTabs() {
    var nav = document.getElementById('profile-wallet-subnav');
    if (!nav || nav._wired) return;
    nav._wired = true;
    showWalletTab('overview');
    nav.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-wallet-tab]');
      if (!btn) return;
      var tab = btn.getAttribute('data-wallet-tab');
      showWalletTab(tab);
    });
    var card = document.getElementById('profile-mn2-wallet-card');
    if (card && !card._secLinksWired) {
      card._secLinksWired = true;
      card.addEventListener('click', function (e) {
        var a = e.target.closest('a[href="#security"]');
        if (!a) return;
        e.preventDefault();
        showWalletTab('security');
      });
    }
  }

  function refreshInstant() {
    var user = uid();
    var q = encodeURIComponent(user);
    fetchJson(base() + '/api/mn2/staking/status').then(function (res) {
      _lastStakeStatus = res.data || null;
    });
    fetchJson(base() + '/api/mn2/balance?user_id=' + q).then(function (res) {
      renderBalance(res.data, _lastStakeStatus);
    });
    fetchJson(base() + '/api/mn2/transactions?user_id=' + q + '&limit=20').then(function (res) {
      renderTransactions(res.data);
    });
    fetchJson(base() + '/api/mn2/profile-monitor?user_id=' + q + '&days=5').then(function (res) {
      renderSystemMonitor(res.data);
    });
    fetchJson(base() + '/api/mn2/wallet-activity?user_id=' + q + '&days=5').then(function (res) {
      renderActivity(res.data);
    });
  }

  function connectInstantStream() {
    if (_sse || typeof EventSource === 'undefined') return;
    var user = uid();
    _sse = new EventSource(base() + '/api/activity/stream?interval=3&sounds=0');
    _sse.onmessage = function (ev) {
      try {
        var data = JSON.parse(ev.data);
        if (data.type !== 'activity' || !data.events || !data.events.length) return;
        var mine = data.events.some(function (e) {
          var uidMatch = (e.user_id || e.payload && e.payload.user_id || '') === user;
          var kind = (e.kind || e.type || '').toLowerCase();
          return uidMatch && (
            kind.indexOf('mn2') >= 0 ||
            kind.indexOf('reward') >= 0 ||
            kind === 'game_mn2_reward' ||
            kind === 'mn2_ledger' ||
            kind === 'deposit'
          );
        });
        if (mine) refreshInstant();
      } catch (e) { /* ignore */ }
    };
    _sse.onerror = function () {
      if (_sse) { _sse.close(); _sse = null; }
      setTimeout(connectInstantStream, 12000);
    };
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

    fetchJson(base() + '/api/mn2/balance?user_id=' + q, { timeout: 18000 }).then(function (res) {
      var bal = res.data || {};
      renderBalance(bal, _lastStakeStatus);
      if (bal.wallet_ready && bal.deposit_address) {
        renderDeposit({
          success: true,
          deposit_address: bal.deposit_address,
          explorer_address_url: bal.explorer_address_url,
        });
      } else if (!bal.wallet_ready) {
        fetchJson(base() + '/api/mn2/deposit-address?user_id=' + q, { timeout: 18000 }).then(function (addrRes) {
          renderDeposit(addrRes.data);
        });
      }
    });
    fetchJson(base() + '/api/mn2/transactions?user_id=' + q + '&limit=20').then(function (res) {
      renderTransactions(res.data);
    });
    fetchJson(base() + '/api/mn2/wallet-activity?user_id=' + q + '&days=5').then(function (res) {
      renderActivity(res.data);
    });
    fetchJson(base() + '/api/mn2/wallet/addresses?user_id=' + q).then(function (res) {
      renderWalletsList(res.data);
    });
    fetchJson(base() + '/api/mn2/profile-monitor?user_id=' + q + '&days=5').then(function (res) {
      renderSystemMonitor(res.data);
    });
    fetchJson(base() + '/api/mn2/user-wallet-map?limit=200&provision=1', { timeout: 60000 }).then(function (res) {
      renderUserWalletMap(res.data || {});
    });
    fetchJson(base() + '/api/mn2/agent-wallets?provision=0', { timeout: 18000 }).then(function (res) {
      if (!(res.data && res.data.success) || !(res.data.agents && res.data.agents.length)) {
        return fetchJson(base() + '/api/mn2/agent-wallets?provision=1', { timeout: 20000 }).then(function (res2) {
          renderAgentWallets(res2.data || {});
        });
      }
      renderAgentWallets(res.data);
    });
    fetchJson(base() + '/api/mn2/staking/status', { timeout: 12000 }).then(function (res) {
      _lastStakeStatus = res.data || null;
      fetchJson(base() + '/api/mn2/balance?user_id=' + q, { timeout: 8000 }).then(function (balRes) {
        renderBalance(balRes.data, _lastStakeStatus);
      });
    });

    connectInstantStream();
    loadWithdrawSecurityHint();

    if (_pollTimer) clearInterval(_pollTimer);
    _pollTimer = setInterval(refreshInstant, POLL_MS);
  }

  global.ProfileMn2Wallet = { load: load, requestDepositAddress: requestDepositAddress, showWalletTab: showWalletTab };

  function isWalletHubPage() {
    var path = (global.location.pathname || '').replace(/\/+$/, '');
    return path === '/wallets' || path.endsWith('/wallets');
  }

  document.addEventListener('DOMContentLoaded', function () {
    if (isWalletHubPage()) return; // /wallets bootstraps load + tab from hash in page script
    // /profile loads wallet JS when applyFocusedProfileRoute('wallet') runs (tab=wallet or #mn2-wallet).
  });
})(window);
