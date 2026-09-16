/**
 * MN2 wallet extras — statement export, trusted address book, internal gifts.
 * Used by /wallets and profile wallet card.
 */
(function (global) {
  'use strict';

  var LABELS = {
    deposit: 'Deposit', withdrawal: 'Withdrawal', staking_reward: 'Staking reward',
    stake: 'Stake', unstake: 'Unstake', shop_payment: 'Shop payment',
    onramp_purchase: 'PayPal buy', onramp_clawback: 'Chargeback', p2p_buy: 'P2P buy',
    p2p_sell_escrow: 'P2P escrow', p2p_escrow_return: 'P2P escrow return',
    gift_sent: 'Gift sent', gift_received: 'Gift received',
  };

  function fmt(n) {
    return Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 8 });
  }

  function refreshWallet() {
    if (global.ProfileMn2Wallet && global.ProfileMn2Wallet.load) {
      global.ProfileMn2Wallet.load();
    } else if (global.profileManager && global.profileManager.loadProfileMn2Wallet) {
      global.profileManager.loadProfileMn2Wallet();
    }
  }

  function loadStatement() {
    var rowsEl = document.getElementById('mn2-statement-rows');
    if (!rowsEl) return;
    var yearEl = document.getElementById('mn2-statement-year');
    var csvEl = document.getElementById('mn2-statement-csv');
    var sumEl = document.getElementById('mn2-statement-summary');
    var y = yearEl ? yearEl.value : '';
    if (csvEl) csvEl.href = '/api/mn2/statement?format=csv' + (y ? '&year=' + y : '');
    rowsEl.innerHTML = 'Loading…';
    fetch('/api/mn2/statement' + (y ? '?year=' + y : ''), { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d || !d.success) {
          rowsEl.innerHTML = (d && d.code === 'auth_required') ? 'Sign in to view your statement.' : 'Could not load statement.';
          return;
        }
        if (yearEl && yearEl.options.length <= 1) {
          var ys = Object.keys((d.summary && d.summary.by_year) || {}).sort().reverse();
          ys.forEach(function (yr) {
            var o = document.createElement('option');
            o.value = yr;
            o.textContent = yr;
            yearEl.appendChild(o);
          });
        }
        if (sumEl) {
          sumEl.textContent = 'Current balance ' + fmt(d.current_balance_mn2) + ' MN2 · ' + ((d.summary && d.summary.events) || 0) + ' events';
        }
        var rows = d.rows || [];
        if (!rows.length) {
          rowsEl.innerHTML = '<p style="margin:0;">No transactions yet.</p>';
          return;
        }
        rowsEl.innerHTML =
          '<table style="width:100%; border-collapse:collapse;"><thead><tr style="opacity:0.7;">' +
          '<th style="text-align:left; padding:2px 8px;">Date</th><th style="text-align:left; padding:2px 8px;">Type</th>' +
          '<th style="text-align:right; padding:2px 8px;">Change</th><th style="text-align:right; padding:2px 8px;">Balance</th></tr></thead><tbody>' +
          rows.map(function (r) {
            var pos = (r.delta_mn2 || 0) >= 0;
            var d2 = (r.created_at || '').slice(0, 16).replace('T', ' ');
            var dc = (r.delta_mn2 === 0) ? 'opacity:0.6;' : (pos ? 'color:#00ff88;' : 'color:#ffaa44;');
            var sign = (r.delta_mn2 > 0 ? '+' : '');
            return '<tr><td style="padding:2px 8px;">' + d2 + '</td><td style="padding:2px 8px;">' + (LABELS[r.type] || r.type) +
              '</td><td style="padding:2px 8px; text-align:right; ' + dc + '">' + (r.delta_mn2 === 0 ? '—' : sign + fmt(r.delta_mn2)) +
              '</td><td style="padding:2px 8px; text-align:right;">' + fmt(r.running_balance_mn2) + '</td></tr>';
          }).join('') + '</tbody></table>';
      })
      .catch(function () { rowsEl.innerHTML = 'Could not load statement.'; });
  }

  function loadAddrBook() {
    var el = document.getElementById('mn2-addrbook-list');
    if (!el) return;
    fetch('/api/mn2/address-book', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var rows = (d && d.addresses) || [];
        if (!rows.length) {
          el.innerHTML = '<p style="margin:0;opacity:0.7;">No saved addresses.</p>';
          return;
        }
        el.innerHTML = rows.map(function (a) {
          return '<div style="margin:4px 0;">' + (a.label || a.address).slice(0, 40) +
            ' <span style="opacity:0.6;">' + (a.cleared ? '✓ cleared' : 'pending clearance') + '</span></div>';
        }).join('');
      })
      .catch(function () { el.textContent = 'Could not load.'; });
  }

  function wireExtras() {
    var yearEl = document.getElementById('mn2-statement-year');
    if (yearEl && !yearEl._mn2Wired) {
      yearEl._mn2Wired = true;
      yearEl.addEventListener('change', loadStatement);
    }
    var addBtn = document.getElementById('mn2-addrbook-add');
    if (addBtn && !addBtn._mn2Wired) {
      addBtn._mn2Wired = true;
      addBtn.addEventListener('click', function () {
        var addr = (document.getElementById('mn2-addrbook-address') || {}).value || '';
        var label = (document.getElementById('mn2-addrbook-label') || {}).value || '';
        var pwdEl = document.getElementById('mn2-addrbook-password');
        var token = pwdEl ? pwdEl.value : '';
        fetch('/api/mn2/address-book', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ address: addr, label: label, verification_token: token || undefined, password: token || undefined }),
        })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (typeof toast !== 'undefined') {
              d.success ? toast.success('Trusted address saved.') : toast.error(d.error || 'Failed');
            } else {
              alert(d.success ? 'Trusted address saved.' : (d.error || 'Failed'));
            }
            if (d.success && pwdEl) pwdEl.value = '';
            loadAddrBook();
          });
      });
    }
    var giftBtn = document.getElementById('mn2-gift-send');
    if (giftBtn && !giftBtn._mn2Wired) {
      giftBtn._mn2Wired = true;
      giftBtn.addEventListener('click', function () {
        var to = (document.getElementById('mn2-gift-to') || {}).value || '';
        var amt = (document.getElementById('mn2-gift-amount') || {}).value || 0;
        var msg = document.getElementById('mn2-gift-msg');
        fetch('/api/mn2/transfer', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ to: to, amount: amt }),
        })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (msg) {
              msg.textContent = d.success ? ('Sent ' + d.amount_mn2 + ' MN2 to ' + d.to_user) : (d.error || 'Failed');
              msg.style.color = d.success ? '#00ff88' : '#ffaa44';
            }
            if (d.success) refreshWallet();
          });
      });
    }
    var copyRev = document.getElementById('profile-mn2-copy-revenue');
    if (copyRev && !copyRev._mn2Wired) {
      copyRev._mn2Wired = true;
      copyRev.addEventListener('click', function () {
        var el = document.getElementById('profile-mn2-revenue-address');
        var t = el && el.textContent ? el.textContent.trim() : '';
        if (t) navigator.clipboard.writeText(t);
      });
    }
  }

  function init() {
    wireExtras();
    loadStatement();
    loadAddrBook();
  }

  global.Mn2WalletExtras = { init: init, loadStatement: loadStatement, loadAddrBook: loadAddrBook };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window);
