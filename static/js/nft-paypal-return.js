/**
 * Shared PayPal return + capture for NFT primary sales (hub, market, shop).
 */
(function (global) {
  'use strict';

  function uid() {
    try { return global.localStorage.getItem('game_user_id') || ''; }
    catch (e) { return ''; }
  }

  function isNftSku(itemId) {
    var id = String(itemId || '');
    return id.indexOf('nft-') === 0 || id.indexOf('nft_') === 0;
  }

  /**
   * @param {object} opts
   * @param {function(string):void} [opts.onMessage]
   * @param {function(object):void} [opts.onSuccess]
   * @param {function():void} [opts.onReload]
   * @param {string} [opts.focusHash] e.g. '#nft-wallet'
   * @param {string} [opts.redirectAfterMint] full URL to open after NFT mint
   * @param {boolean} [opts.replaceStatePath]
   */
  function handlePayPalReturn(opts) {
    opts = opts || {};
    var params = new URLSearchParams(global.location.search);
    if (params.get('paypal') === 'cancel') {
      if (opts.onMessage) opts.onMessage('PayPal checkout cancelled');
      if (opts.replaceStatePath !== false) {
        global.history.replaceState({}, '', global.location.pathname);
      }
      return Promise.resolve({ cancelled: true });
    }
    var token = params.get('token');
    if (params.get('paypal') !== 'success' || !token) {
      return Promise.resolve({ skipped: true });
    }
    var itemId = params.get('item_id') || '';
    return fetch('/api/paypal/capture', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        order_id: token,
        item_id: itemId,
        user_id: params.get('user_id') || uid()
      })
    }).then(function (r) { return r.json(); }).then(function (data) {
      var minted = data && data.success && data.edition && data.edition.edition_id;
      if (minted) {
        if (opts.onMessage) {
          opts.onMessage('Minted ' + data.edition.edition_id + ' — check your NFT wallet.');
        }
        if (opts.onSuccess) opts.onSuccess(data);
        if (opts.redirectAfterMint && isNftSku(itemId)) {
          global.location.href = opts.redirectAfterMint;
          return data;
        }
        if (opts.focusHash && isNftSku(itemId)) {
          global.history.replaceState({}, '', global.location.pathname + opts.focusHash);
          var target = global.document.querySelector(opts.focusHash);
          if (target && target.scrollIntoView) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        } else if (opts.replaceStatePath !== false) {
          global.history.replaceState({}, '', global.location.pathname);
        }
      } else if (data && data.success) {
        if (opts.onMessage) opts.onMessage('Payment captured');
        if (opts.onSuccess) opts.onSuccess(data);
        if (opts.replaceStatePath !== false) {
          global.history.replaceState({}, '', global.location.pathname);
        }
      } else {
        if (opts.onMessage) {
          opts.onMessage((data && (data.details || data.error)) || 'Capture failed');
        }
        if (opts.replaceStatePath !== false) {
          global.history.replaceState({}, '', global.location.pathname);
        }
      }
      if (opts.onReload) opts.onReload();
      return data;
    }).catch(function () {
      if (opts.onMessage) opts.onMessage('Capture failed');
      return { success: false };
    });
  }

  global.NftPayPalReturn = {
    handle: handlePayPalReturn,
    isNftSku: isNftSku
  };
})(typeof window !== 'undefined' ? window : this);
