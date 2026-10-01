/* NFT catalog + resale book on /exchange marketplace tab. */
(function () {
  'use strict';

  var catalogEl = document.getElementById('cex-nft-catalog');
  var listingsEl = document.getElementById('cex-nft-listings');
  if (!catalogEl && !listingsEl) return;

  function cardSku(row) {
    var img = row.avatar_url
      ? '<img src="' + row.avatar_url + '" alt="" width="48" height="48" style="border-radius:8px;margin-bottom:6px;">'
      : '';
    return (
      '<article class="cex-market-card">' +
      img +
      '<div class="cex-market-title">' + (row.emblem_icon || '💎') + ' ' + (row.name || row.sku) + '</div>' +
      '<div class="cex-muted">' + (row.rarity || '') + ' · ' + (row.remaining != null ? row.remaining : '?') + ' left</div>' +
      '<div>$' + (row.price_usd || 0) + ' · ' + (row.price_coins || 0) + ' coins</div>' +
      '<a class="cex-btn cex-btn--ghost" href="/market">Buy on market</a>' +
      '</article>'
    );
  }

  function cardListing(row) {
    return (
      '<article class="cex-market-card">' +
      '<div class="cex-market-title">' + (row.edition_id || row.listing_id) + '</div>' +
      '<div class="cex-muted">Seller: ' + (row.seller_id || '') + '</div>' +
      '<div>' + (row.price_coins || 0) + ' coins</div>' +
      '<a class="cex-btn cex-btn--ghost" href="/market">Trade on market</a>' +
      '</article>'
    );
  }

  fetch('/api/exchange/nft/market', { credentials: 'same-origin' })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (!data || !data.success) {
        if (catalogEl) catalogEl.textContent = 'NFT market unavailable.';
        return;
      }
      var skus = data.catalog || [];
      if (catalogEl) {
        catalogEl.innerHTML = skus.length
          ? skus.map(cardSku).join('')
          : '<p class="cex-muted">No NFT SKUs configured.</p>';
      }
      var open = (data.deals && data.deals.open_listings) || [];
      if (listingsEl) {
        listingsEl.innerHTML = open.length
          ? open.map(cardListing).join('')
          : '<p class="cex-muted">No open resale listings yet.</p>';
      }
    })
    .catch(function () {
      if (catalogEl) catalogEl.textContent = 'Could not load NFT exchange data.';
    });
})();
