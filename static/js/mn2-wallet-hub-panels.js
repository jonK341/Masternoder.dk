/**
 * Super-wallet hub panels: hold banner, proof-of-reserves, AMM swap, scan deposits, settings.
 */
(function (global) {
  'use strict';

  var uid = function () {
    try { return global.localStorage.getItem('game_user_id') || 'default_user'; }
    catch (e) { return 'default_user'; }
  };

  function q(id) { return global.document.getElementById(id); }

  function fmt(n, d) {
    var x = Number(n || 0);
    if (!isFinite(x)) return '—';
    return x.toLocaleString(undefined, { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 });
  }

  function mn2(v) {
    return v === null || v === undefined ? '—' : fmt(v, 4) + ' MN2';
  }

  function get(path) {
    var sep = path.indexOf('?') === -1 ? '?' : '&';
    return fetch(path + sep + 'user_id=' + encodeURIComponent(uid()), { credentials: 'same-origin' })
      .then(function (r) { return r.json(); });
  }

  function post(path, body) {
    body = body || {};
    body.user_id = uid();
    return fetch(path, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(function (r) { return r.json(); });
  }

  var porLoaded = false;
  var swapQuoteId = null;

  function loadHoldBanner() {
    var el = q('wh-hold-banner');
    if (!el) return;
    Promise.all([
      get('/api/mn2/onramp/status').catch(function () { return {}; }),
      get('/api/mn2/p2p/status').catch(function () { return {}; }),
    ]).then(function (res) {
      var onramp = res[0] || {};
      var p2p = res[1] || {};
      var held = Number(onramp.held_mn2 || 0) + Number(p2p.held_mn2 || 0);
      if (held <= 0) {
        el.className = 'wh-hold-banner ok';
        el.textContent = 'No MN2 in clearance hold — full liquid balance is withdrawable (subject to 2FA/whitelist).';
        return;
      }
      el.className = 'wh-hold-banner';
      var parts = [];
      if (onramp.held_mn2 > 0) parts.push(fmt(onramp.held_mn2, 4) + ' MN2 from PayPal on-ramp');
      if (p2p.held_mn2 > 0) parts.push(fmt(p2p.held_mn2, 4) + ' MN2 from P2P purchases');
      el.textContent = 'Clearance hold: ' + parts.join(' · ') + '. Held MN2 can be staked or spent but not withdrawn until the window passes.';
    });
  }

  function renderCompactPoR(d) {
    var banner = q('wh-por-banner-text');
    var icon = q('wh-por-banner-icon');
    if (!banner) return;
    var por = (d && d.proof_of_reserves) || d;
    if (!por || por.success === false) {
      banner.textContent = 'Could not load reserve data.';
      return;
    }
    var cov = por.coverage_ratio;
    var onchainOk = por.assets && por.assets.onchain && por.assets.onchain.status === 'ok';
    if (icon) {
      if (!onchainOk) icon.textContent = '⏳';
      else if (por.fully_backed) icon.textContent = '✅';
      else icon.textContent = '⚠️';
    }
    if (!onchainOk) {
      banner.textContent = 'Daemon balance temporarily unavailable — liabilities shown when node responds.';
    } else if (por.fully_backed) {
      banner.textContent = 'Fully backed — custodial reserves cover all user MN2.';
    } else if (cov !== null && cov >= 1.0) {
      banner.textContent = 'Reserves cover liabilities; reconciliation flagged for review.';
    } else {
      banner.textContent = 'Coverage below 1.0 — review reserve snapshot.';
    }
    if (q('wh-t-coverage')) q('wh-t-coverage').textContent = cov === null ? '—' : (cov * 100).toFixed(2) + '%';
    if (q('wh-t-assets')) q('wh-t-assets').textContent = mn2(por.assets ? por.assets.total_mn2 : null);
    if (q('wh-t-liab')) q('wh-t-liab').textContent = mn2(por.liabilities ? por.liabilities.total_mn2 : null);
    if (q('wh-t-surplus')) q('wh-t-surplus').textContent = mn2(por.surplus_mn2);
  }

  function loadProofOfReserves() {
    if (porLoaded) return;
    porLoaded = true;
    fetch('/api/mn2/staking/reserves-overview', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(renderCompactPoR)
      .catch(function () {
        var banner = q('wh-por-banner-text');
        if (banner) banner.textContent = 'Could not load reserve data.';
      });
  }

  function loadSwapQuote() {
    var side = (q('wh-swap-side') || {}).value || 'sell';
    var amt = parseFloat((q('wh-swap-amount') || {}).value || '0');
    var msg = q('wh-swap-msg');
    if (!(amt > 0)) {
      if (msg) msg.textContent = 'Enter an amount.';
      return;
    }
    if (msg) msg.textContent = 'Getting quote…';
    post('/api/mn2/swap/quote', { side: side, mn2_amount: amt }).then(function (res) {
      if (!res || !res.success) {
        swapQuoteId = null;
        if (msg) msg.textContent = (res && res.error) || 'Quote failed.';
        return;
      }
      swapQuoteId = res.quote_id;
      if (msg) {
        msg.textContent = (side === 'sell' ? 'Receive ' : 'Pay ') + fmt(res.counter_amount, 4) +
          ' coins for ' + fmt(res.mn2_amount, 4) + ' MN2 (fee ' + fmt(res.fee_mn2, 4) + '). Click Execute to confirm.';
      }
    }).catch(function () {
      if (msg) msg.textContent = 'Quote failed.';
    });
  }

  function executeSwap() {
    var side = (q('wh-swap-side') || {}).value || 'sell';
    var amt = parseFloat((q('wh-swap-amount') || {}).value || '0');
    var msg = q('wh-swap-msg');
    if (!swapQuoteId) {
      if (msg) msg.textContent = 'Get a quote first.';
      return;
    }
    if (msg) msg.textContent = 'Executing…';
    post('/api/mn2/swap/execute', { quote_id: swapQuoteId, side: side, mn2_amount: amt }).then(function (res) {
      swapQuoteId = null;
      if (!res || !res.success) {
        if (msg) msg.textContent = (res && res.error) || 'Swap failed.';
        return;
      }
      if (msg) msg.textContent = 'Swap complete — ' + fmt(res.mn2_amount, 4) + ' MN2.';
      if (global.ProfileMn2Wallet && global.ProfileMn2Wallet.load) global.ProfileMn2Wallet.load();
      if (global.MN2InternalMarket && global.MN2InternalMarket.refresh) global.MN2InternalMarket.refresh();
    }).catch(function () {
      if (msg) msg.textContent = 'Swap failed.';
    });
  }

  function scanDeposits() {
    var msg = q('wh-scan-msg');
    if (msg) msg.textContent = 'Scanning chain for deposits…';
    post('/api/mn2/scan-deposits', {}).then(function (res) {
      if (!res || !res.success) {
        if (msg) msg.textContent = (res && res.error) || 'Scan failed (ops token may be required).';
        return;
      }
      var credits = res.credits_applied != null ? res.credits_applied : 0;
      if (msg) msg.textContent = 'Scan complete — ' + credits + ' credit(s) applied.';
      if (global.ProfileMn2Wallet && global.ProfileMn2Wallet.load) global.ProfileMn2Wallet.load();
    }).catch(function () {
      if (msg) msg.textContent = 'Scan request failed.';
    });
  }

  function initSettings() {
    var soundToggle = q('wh-activity-sounds');
    if (soundToggle) {
      soundToggle.checked = global.localStorage.getItem('mn2_activity_sounds') !== '0';
      soundToggle.addEventListener('change', function () {
        if (global.Mn2ActivityStream && global.Mn2ActivityStream.setSounds) {
          global.Mn2ActivityStream.setSounds(soundToggle.checked);
        } else {
          global.localStorage.setItem('mn2_activity_sounds', soundToggle.checked ? '1' : '0');
        }
      });
    }
    var scanBtn = q('wh-scan-deposits-btn');
    if (scanBtn) scanBtn.addEventListener('click', scanDeposits);
    var swapQuoteBtn = q('wh-swap-quote-btn');
    if (swapQuoteBtn) swapQuoteBtn.addEventListener('click', loadSwapQuote);
    var swapExecBtn = q('wh-swap-execute-btn');
    if (swapExecBtn) swapExecBtn.addEventListener('click', executeSwap);
  }

  function onTabShown(tab) {
    if (tab === 'overview') {
      loadHoldBanner();
      loadProofOfReserves();
    }
    if (tab === 'trade') {
      if (global.MN2InternalMarket && global.MN2InternalMarket.refresh) global.MN2InternalMarket.refresh();
    }
    if (tab === 'hosting' && global.Mn2WalletHosting && global.Mn2WalletHosting.refresh) {
      global.Mn2WalletHosting.refresh();
    }
  }

  function init() {
    initSettings();
    loadHoldBanner();
    var params = new global.URLSearchParams(global.location.search);
    if (params.get('paypal') === 'success' && params.get('mn_quote')) {
      if (global.ProfileMn2Wallet && global.ProfileMn2Wallet.showWalletTab) {
        global.ProfileMn2Wallet.showWalletTab('hosting');
      }
    }
    if (params.get('wallet_tab')) {
      var t = params.get('wallet_tab');
      if (global.ProfileMn2Wallet && global.ProfileMn2Wallet.showWalletTab) {
        global.ProfileMn2Wallet.showWalletTab(t);
      }
    }
  }

  global.Mn2WalletHubPanels = { onTabShown: onTabShown, refreshHold: loadHoldBanner };

  if (global.document.readyState === 'loading') {
    global.document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
