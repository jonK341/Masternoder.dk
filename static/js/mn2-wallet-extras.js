/**
 * MN2 wallet extras — trusted address book, internal gifts, statement export UI.
 */
(function (global) {
  'use strict';

  function uid() {
    return (
      (global.profileManager && global.profileManager.userId) ||
      global.localStorage.getItem('game_user_id') ||
      global.localStorage.getItem('user_id') ||
      'default_user'
    );
  }

  function post(path, body) {
    return fetch(path, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    }).then(function (r) { return r.json(); });
  }

  function loadAddrBook() {
    var el = global.document.getElementById('mn2-addrbook-list');
    if (!el) return;
    fetch('/api/mn2/address-book?user_id=' + encodeURIComponent(uid()), { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var rows = (d && d.addresses) || [];
        if (!rows.length) {
          el.innerHTML = '<p style="margin:0;opacity:0.7;">No saved addresses.</p>';
          return;
        }
        el.innerHTML = rows.map(function (a) {
          return '<div style="margin:4px 0;"><code style="font-size:0.75rem;">' + (a.address || '') + '</code> ' +
            (a.label ? '<span style="opacity:0.8;">' + a.label + '</span> ' : '') +
            '<span style="opacity:0.6;">' + (a.cleared ? '✓ cleared' : 'pending clearance') + '</span></div>';
        }).join('');
      })
      .catch(function () { el.textContent = 'Could not load trusted addresses.'; });
  }

  function loadStatement() {
    var rowsEl = global.document.getElementById('mn2-statement-rows');
    var summaryEl = global.document.getElementById('mn2-statement-summary');
    var yearEl = global.document.getElementById('mn2-statement-year');
    if (!rowsEl) return;
    var year = yearEl ? yearEl.value : '';
    var url = '/api/mn2/statement' + (year ? '?year=' + encodeURIComponent(year) : '');
    fetch(url, { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d || !d.success) {
          rowsEl.textContent = (d && d.error) || 'Could not load statement.';
          return;
        }
        var rows = d.rows || [];
        if (summaryEl && d.summary) {
          summaryEl.textContent = rows.length + ' events · balance ' + (d.current_balance_mn2 != null ? Number(d.current_balance_mn2).toFixed(4) : '—') + ' MN2';
        }
        if (!rows.length) {
          rowsEl.textContent = 'No ledger events yet.';
          return;
        }
        rowsEl.innerHTML = rows.slice(0, 80).map(function (r) {
          return '<div style="margin:3px 0;font-size:0.78rem;"><span style="opacity:0.65;">' + (r.created_at || '').slice(0, 19) +
            '</span> <strong>' + (r.type || '') + '</strong> ' + Number(r.delta_mn2 || 0).toFixed(4) + ' MN2</div>';
        }).join('');
      })
      .catch(function () { rowsEl.textContent = 'Could not load statement.'; });
  }

  function init() {
    var addBtn = global.document.getElementById('mn2-addrbook-add');
    if (addBtn && !addBtn._mn2Wired) {
      addBtn._mn2Wired = true;
      addBtn.addEventListener('click', function () {
        var addr = ((global.document.getElementById('mn2-addrbook-address') || {}).value || '').trim();
        var label = ((global.document.getElementById('mn2-addrbook-label') || {}).value || '').trim();
        var pwdEl = global.document.getElementById('mn2-addrbook-password');
        var token = pwdEl ? pwdEl.value : '';
        if (!addr) {
          if (typeof global.toast !== 'undefined') global.toast.error('Enter an MN2 address');
          return;
        }
        post('/api/mn2/address-book', { address: addr, label: label, password: token || undefined, user_id: uid() })
          .then(function (d) {
            if (d.success) {
              if (typeof global.toast !== 'undefined') global.toast.success('Trusted address saved');
              if (pwdEl) pwdEl.value = '';
              loadAddrBook();
            } else if (typeof global.toast !== 'undefined') {
              global.toast.error(d.error || 'Failed — profile password may be required.');
            }
          });
      });
    }

    var giftBtn = global.document.getElementById('mn2-gift-send');
    if (giftBtn && !giftBtn._mn2Wired) {
      giftBtn._mn2Wired = true;
      giftBtn.addEventListener('click', function () {
        var to = ((global.document.getElementById('mn2-gift-to') || {}).value || '').trim();
        var amt = parseFloat((global.document.getElementById('mn2-gift-amount') || {}).value || '0');
        var msg = global.document.getElementById('mn2-gift-msg');
        post('/api/mn2/transfer', { to: to, amount: amt, user_id: uid() }).then(function (d) {
          if (msg) {
            msg.textContent = d.success
              ? ('Sent ' + d.amount_mn2 + ' MN2 to ' + (d.to_user || to))
              : (d.error || 'Failed');
            msg.style.color = d.success ? '#00ff88' : '#ffaa44';
          }
          if (d.success && global.ProfileMn2Wallet) global.ProfileMn2Wallet.load();
        });
      });
    }

    var yearEl = global.document.getElementById('mn2-statement-year');
    if (yearEl && !yearEl._mn2Wired) {
      yearEl._mn2Wired = true;
      var y = new Date().getUTCFullYear();
      for (var i = 0; i < 6; i++) {
        var opt = global.document.createElement('option');
        opt.value = String(y - i);
        opt.textContent = String(y - i);
        yearEl.appendChild(opt);
      }
      yearEl.addEventListener('change', loadStatement);
    }

    loadAddrBook();
    loadStatement();
  }

  if (global.document.readyState === 'loading') {
    global.document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
