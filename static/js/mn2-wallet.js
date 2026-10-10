/**
 * Shared MN2 wallet display for Profile and Shop.
 * Both pages read the same /api/mn2/balance payload (ledger + on-chain reconcile).
 */
(function (global) {
  'use strict';

  function fmt(value) {
    var n = Number(value);
    if (!isFinite(n)) return '—';
    return n.toFixed(8);
  }

  function renderOnchain(el, data) {
    if (!el) return;
    var chain = data && data.onchain;
    var reconcile = data && data.reconcile;
    if (!chain) {
      el.textContent = '';
      return;
    }
    if (chain.available === false) {
      el.textContent = chain.error
        ? 'On-chain balance unavailable (' + chain.error + '). Ledger balance is shown above.'
        : 'On-chain balance unavailable. Ledger balance is shown above.';
      return;
    }
    var line =
      'On-chain confirmed ' +
      fmt(chain.confirmed_mn2) +
      ' MN2 · unconfirmed ' +
      fmt(chain.unconfirmed_mn2) +
      ' MN2';
    if (reconcile && typeof reconcile.delta_mn2 === 'number') {
      line += ' · ledger delta ' + fmt(reconcile.delta_mn2) + ' MN2';
    }
    if (data.wallet_mode) {
      line += ' · shop wallet_mode ' + data.wallet_mode;
    }
    el.textContent = line;
  }

  global.Mn2Wallet = {
    renderOnchain: renderOnchain,
  };
})(window);
