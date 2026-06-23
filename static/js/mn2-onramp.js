/*
 * MN2 PayPal on-ramp (Model A) controller.
 * Quote -> create PayPal order -> redirect to approve -> capture on return.
 */
(function () {
  'use strict';

  var panel = document.getElementById('mn2-onramp-panel');
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

  var currentQuoteId = null;

  function loadConfig() {
    get('/api/mn2/onramp/config').then(function (cfg) {
      if (cfg && cfg.success && cfg.enabled) panel.style.display = 'block';
    }).catch(function () {});
  }

  function refreshHeld() {
    get('/api/mn2/onramp/status').then(function (res) {
      var el = q('mn2-onramp-held');
      if (el && res && res.held_mn2 > 0) {
        el.textContent = fmt(res.held_mn2, 4) + ' MN2 in clearance hold (not yet withdrawable).';
      } else if (el) { el.textContent = ''; }
    }).catch(function () {});
  }

  function getQuote() {
    var usd = q('mn2-onramp-usd').value || 0;
    q('mn2-onramp-quote-result').textContent = 'Getting quote…';
    get('/api/mn2/onramp/quote?usd=' + usd).then(function (res) {
      if (!res || !res.success) {
        currentQuoteId = null;
        q('mn2-onramp-pay-btn').disabled = true;
        q('mn2-onramp-quote-result').textContent = (res && res.error) || 'Could not get a quote.';
        return;
      }
      currentQuoteId = res.quote_id;
      q('mn2-onramp-pay-btn').disabled = false;
      q('mn2-onramp-quote-result').textContent =
        '≈ ' + fmt(res.mn2_amount, 6) + ' MN2 for $' + fmt(res.usd_amount, 2) +
        ' (rate ' + fmt(res.rate_mn2_per_usd, 6) + ' MN2/$, ' + res.spread_percent + '% spread). ' +
        'Held ' + res.hold_hours + 'h before withdrawal. Quote expires soon.';
    }).catch(function () {
      q('mn2-onramp-quote-result').textContent = 'Could not get a quote.';
    });
  }

  function pay() {
    if (!currentQuoteId) return;
    var base = window.location.origin + window.location.pathname;
    post('/api/mn2/onramp/order', {
      quote_id: currentQuoteId,
      return_url: base + '?onramp_capture=' + encodeURIComponent(currentQuoteId),
      cancel_url: base + '?onramp_cancel=1'
    }).then(function (res) {
      if (res && res.success && res.approve_url) {
        window.location.href = res.approve_url;
      } else {
        q('mn2-onramp-quote-result').textContent = (res && res.error) || 'Could not start PayPal checkout.';
      }
    });
  }

  // Capture on return from PayPal
  function handleReturn() {
    var params = new URLSearchParams(window.location.search);
    var orderId = params.get('onramp_capture');
    if (!orderId) return;
    q('mn2-onramp-quote-result').textContent = 'Confirming payment…';
    post('/api/mn2/onramp/capture', { order_id: orderId }).then(function (res) {
      if (res && res.success) {
        q('mn2-onramp-quote-result').textContent =
          'Purchased ' + fmt(res.mn2_amount, 6) + ' MN2 (held until ' + (res.hold_until || 'clearance') + ').';
        refreshHeld();
        if (window.MN2Staking && window.MN2Staking.refresh) window.MN2Staking.refresh();
      } else {
        q('mn2-onramp-quote-result').textContent = (res && res.error) || 'Could not confirm payment. If you were charged, it will be credited shortly.';
      }
      // clean the URL
      try { window.history.replaceState({}, '', window.location.pathname); } catch (e) {}
    });
  }

  function init() {
    loadConfig();
    refreshHeld();
    handleReturn();
    q('mn2-onramp-quote-btn').addEventListener('click', getQuote);
    q('mn2-onramp-pay-btn').addEventListener('click', pay);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
