/*
 * MN2 P2P marketplace (Model B) controller. Shows only when the market is enabled.
 * Sell: escrow + list. Buy: create order -> redirect to PayPal -> capture on return.
 */
(function () {
  'use strict';

  var panel = document.getElementById('mn2-p2p-panel');
  if (!panel) return;

  function uid() {
    try { return localStorage.getItem('game_user_id') || 'default_user'; }
    catch (e) { return 'default_user'; }
  }
  function q(id) { return document.getElementById(id); }
  function fmt(n, d) { return Number(n || 0).toFixed(d == null ? 4 : d); }

  function post(path, body) {
    body = body || {};
    body.user_id = uid();
    return fetch(path, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
    }).then(function (r) { return r.json(); });
  }
  function get(path) {
    var sep = path.indexOf('?') === -1 ? '?' : '&';
    return fetch(path + sep + 'user_id=' + encodeURIComponent(uid()), { credentials: 'same-origin' })
      .then(function (r) { return r.json(); });
  }
  function msg(t) { var el = q('mn2-p2p-msg'); if (el) el.textContent = t || ''; }

  function loadConfig() {
    get('/api/mn2/p2p/config').then(function (cfg) {
      if (cfg && cfg.success && cfg.enabled) { panel.style.display = 'block'; loadListings(); }
    }).catch(function () {});
  }

  function loadListings() {
    get('/api/mn2/p2p/listings?limit=50').then(function (res) {
      var el = q('mn2-p2p-listings');
      if (!el) return;
      var rows = (res && res.listings) || [];
      if (!rows.length) { el.textContent = 'No open listings.'; return; }
      el.innerHTML = rows.map(function (l) {
        return '<div style="display:flex; gap:8px; align-items:center; padding:4px 0; border-bottom:1px solid rgba(255,255,255,0.06);">' +
          '<span style="flex:1;">' + fmt(l.mn2_available, 4) + ' MN2 @ $' + fmt(l.price_usd_per_mn2, 4) + '/MN2 <span style="opacity:0.6;">(' + l.seller + ')</span></span>' +
          '<input type="number" min="0" placeholder="qty" data-buy="' + l.listing_id + '" style="width:70px; padding:4px; border-radius:6px; border:1px solid rgba(255,255,255,0.2); background:rgba(0,0,0,0.3); color:#fff;">' +
          '<button type="button" data-buybtn="' + l.listing_id + '" style="padding:5px 10px; border-radius:6px; border:none; background:#0070ba; color:#fff; cursor:pointer;">Buy</button>' +
          '</div>';
      }).join('');
      el.querySelectorAll('[data-buybtn]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var id = btn.getAttribute('data-buybtn');
          var input = el.querySelector('[data-buy="' + id + '"]');
          buy(id, parseFloat(input && input.value));
        });
      });
    }).catch(function () {});
  }

  function listForSale() {
    var amt = parseFloat(q('mn2-p2p-sell-amount').value);
    var price = parseFloat(q('mn2-p2p-sell-price').value);
    if (!amt || !price) { msg('Enter amount and price'); return; }
    post('/api/mn2/p2p/listings', { mn2_amount: amt, price_usd_per_mn2: price }).then(function (res) {
      if (res && res.success) { msg('Listed ' + amt + ' MN2'); loadListings(); if (window.MN2Staking) window.MN2Staking.refresh(); }
      else { msg((res && res.error) || 'Could not list'); }
    });
  }

  function buy(listingId, mn2) {
    if (!mn2 || mn2 <= 0) { msg('Enter a quantity to buy'); return; }
    var base = window.location.origin + window.location.pathname;
    post('/api/mn2/p2p/buy', {
      listing_id: listingId, mn2_amount: mn2,
      return_url: base + '?p2p_capture=PENDING',
      cancel_url: base + '?p2p_cancel=1'
    }).then(function (res) {
      if (res && res.success && res.approve_url) {
        // order id isn't known at return_url build time; stash it and read on return
        try { sessionStorage.setItem('mn2_p2p_order', res.order_id); } catch (e) {}
        window.location.href = res.approve_url;
      } else { msg((res && res.error) || 'Could not start checkout'); }
    });
  }

  function handleReturn() {
    var params = new URLSearchParams(window.location.search);
    if (!params.has('p2p_capture')) return;
    var orderId = params.get('p2p_capture');
    if (orderId === 'PENDING' || !orderId) {
      try { orderId = sessionStorage.getItem('mn2_p2p_order'); } catch (e) {}
    }
    if (!orderId) return;
    msg('Confirming payment…');
    post('/api/mn2/p2p/capture', { order_id: orderId }).then(function (res) {
      if (res && res.success) {
        msg('Bought ' + fmt(res.mn2_amount, 6) + ' MN2 (held until ' + (res.buyer_hold_until || 'clearance') + ').');
        loadListings();
        if (window.MN2Staking) window.MN2Staking.refresh();
      } else { msg((res && res.error) || 'Could not confirm payment.'); }
      try { sessionStorage.removeItem('mn2_p2p_order'); window.history.replaceState({}, '', window.location.pathname); } catch (e) {}
    });
  }

  function init() {
    loadConfig();
    handleReturn();
    var listBtn = q('mn2-p2p-list-btn');
    if (listBtn) listBtn.addEventListener('click', listForSale);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
