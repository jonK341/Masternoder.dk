/* Profile card: numbered NFT editions + link to /market resale book. */
(function () {
  'use strict';

  var root = document.getElementById('profile-nft-holdings');
  if (!root) return;

  function uid() {
    try { return localStorage.getItem('game_user_id') || ''; }
    catch (e) { return ''; }
  }

  function load() {
    var user = uid();
    if (!user) {
      root.textContent = 'Sign in with a profile id to hold editions.';
      return;
    }
    fetch('/api/nft/holdings?user_id=' + encodeURIComponent(user), { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        var rows = (res && res.editions) || [];
        if (!rows.length) {
          root.innerHTML = 'No editions yet. <a href="/market" style="color:#c08cff;">Buy on the market</a> (PayPal from $2.99).';
          return;
        }
        root.innerHTML = rows.map(function (row) {
          return '<div style="padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.06);">' +
            '<strong>' + row.edition_id + '</strong> · ' + (row.status || 'held') +
            (row.status === 'listed' ? '' : ' · <a href="/market" style="color:#c08cff;">List for resale</a>') +
            '</div>';
        }).join('');
      })
      .catch(function () {
        root.textContent = 'Could not load NFT holdings.';
      });
  }

  document.addEventListener('DOMContentLoaded', load);
  window.addEventListener('storage', function (ev) {
    if (ev.key === 'game_user_id') load();
  });
})();
