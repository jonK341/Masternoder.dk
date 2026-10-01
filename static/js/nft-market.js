/* NFT edition catalog and resale book for /market. */
(function () {
  'use strict';

  var root = document.getElementById('nft-market-panel');
  if (!root) return;

  function uid() {
    try { return localStorage.getItem('game_user_id') || ''; }
    catch (e) { return ''; }
  }
  function q(id) { return document.getElementById(id); }
  function msg(text) {
    var el = q('nft-market-msg');
    if (el) el.textContent = text || '';
  }
  function post(path, body) {
    body = body || {};
    body.user_id = uid();
    return fetch(path, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }).then(function (r) { return r.json().then(function (data) { data._status = r.status; return data; }); });
  }
  function get(path) {
    var sep = path.indexOf('?') === -1 ? '?' : '&';
    return fetch(path + sep + 'user_id=' + encodeURIComponent(uid()), { credentials: 'same-origin' })
      .then(function (r) { return r.json(); });
  }

  function load() {
    get('/api/nft/deals').then(render).catch(function () { msg('Could not load NFT market'); });
    get('/api/nft/holdings').then(renderHoldings).catch(function () {});
  }

  function render(res) {
    var catalogEl = q('nft-catalog');
    var bookEl = q('nft-listings');
    var dealsEl = q('nft-deals');
    if (dealsEl) {
      var open = (res && res.open_count) || 0;
      var minted = (res && res.minted) || 0;
      var usd = (res && res.primary_volume_usd) || 0;
      dealsEl.textContent = minted + ' minted · ' + open + ' asks · $' + Number(usd).toFixed(2) + ' primary volume';
    }
    if (bookEl) {
      var rows = (res && res.open_listings) || [];
      if (!rows.length) {
        bookEl.textContent = 'No resale asks yet. Buy a primary edition, then list it.';
      } else {
        bookEl.innerHTML = rows.map(function (row) {
          return '<div style="display:flex;gap:8px;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.06);">' +
            '<span style="flex:1;">' + (row.name || row.sku) + ' #' + row.serial +
            ' · ' + row.price_coins + ' coins <span style="opacity:0.6;">fee ' + row.fee_coins + '</span></span>' +
            '<button type="button" data-nft-buy="' + row.listing_id + '" style="padding:5px 10px;border-radius:6px;border:none;background:#0070ba;color:#fff;cursor:pointer;">Buy</button>' +
            '</div>';
        }).join('');
        bookEl.querySelectorAll('[data-nft-buy]').forEach(function (btn) {
          btn.addEventListener('click', function () {
            post('/api/nft/buy', { listing_id: btn.getAttribute('data-nft-buy') }).then(function (out) {
              msg(out && out.success ? 'Bought ' + (out.edition && out.edition.edition_id) : ((out && out.error) || 'Buy failed'));
              load();
            });
          });
        });
      }
    }
    if (!catalogEl) return;
    get('/api/nft/catalog').then(function (cat) {
      var skus = (cat && cat.skus) || [];
      if (!skus.length) { catalogEl.textContent = 'No editions configured.'; return; }
      catalogEl.innerHTML = skus.map(function (sku) {
        var sold = sku.remaining <= 0 ? 'Sold out' : (sku.remaining + ' left');
        return '<div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06);">' +
          '<strong>' + sku.name + '</strong> <span style="opacity:0.7;">' + sku.rarity + ' · ' + sold + ' / ' + sku.supply + '</span>' +
          '<div style="font-size:0.82rem;opacity:0.8;margin:4px 0;">' + (sku.description || '') + '</div>' +
          '<div style="display:flex;gap:8px;flex-wrap:wrap;">' +
          '<button type="button" data-nft-paypal="' + sku.sku + '" ' + (sku.remaining ? '' : 'disabled ') +
          'style="padding:6px 10px;border-radius:6px;border:none;background:#0070ba;color:#fff;cursor:pointer;">PayPal $' + Number(sku.price_usd).toFixed(2) + '</button>' +
          '<button type="button" data-nft-coins="' + sku.sku + '" ' + (sku.remaining ? '' : 'disabled ') +
          'style="padding:6px 10px;border-radius:6px;border:1px solid #c08cff;background:transparent;color:#c08cff;cursor:pointer;">Coins ' + sku.price_coins + '</button>' +
          '</div></div>';
      }).join('');
      catalogEl.querySelectorAll('[data-nft-paypal]').forEach(function (btn) {
        btn.addEventListener('click', function () { buyPaypal(btn.getAttribute('data-nft-paypal')); });
      });
      catalogEl.querySelectorAll('[data-nft-coins]').forEach(function (btn) {
        btn.addEventListener('click', function () { buyCoins(btn.getAttribute('data-nft-coins')); });
      });
    });
  }

  function renderHoldings(res) {
    var el = q('nft-holdings');
    if (!el) return;
    var rows = (res && res.editions) || [];
    if (!rows.length) { el.textContent = 'You do not hold an edition yet.'; return; }
    el.innerHTML = rows.map(function (row) {
      var listed = row.status === 'listed';
      return '<div style="display:flex;gap:8px;align-items:center;padding:4px 0;">' +
        '<span style="flex:1;">' + row.edition_id + ' · ' + row.status + '</span>' +
        (listed ? '' : '<input data-nft-price="' + row.edition_id + '" type="number" min="20" placeholder="coins" style="width:80px;padding:4px;border-radius:6px;border:1px solid rgba(255,255,255,0.2);background:rgba(0,0,0,0.3);color:#fff;">' +
          '<button type="button" data-nft-list="' + row.edition_id + '" style="padding:5px 10px;border-radius:6px;border:1px solid #c08cff;background:rgba(170,0,255,0.18);color:#c08cff;cursor:pointer;">List</button>') +
        '</div>';
    }).join('');
    el.querySelectorAll('[data-nft-list]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-nft-list');
        var input = el.querySelector('[data-nft-price="' + id + '"]');
        post('/api/nft/list', { edition_id: id, price_coins: parseInt(input && input.value, 10) }).then(function (out) {
          msg(out && out.success ? 'Listed ' + id : ((out && out.error) || 'List failed'));
          load();
        });
      });
    });
  }

  function buyCoins(sku) {
    post('/api/nft/buy-coins', { sku: sku }).then(function (out) {
      msg(out && out.success ? 'Minted ' + (out.edition && out.edition.edition_id) : ((out && out.error) || 'Mint failed'));
      load();
    });
  }

  function buyPaypal(sku) {
    if (!uid()) { msg('Create an account in Profile before paying with PayPal'); return; }
    post('/api/nft/buy-paypal', { sku: sku }).then(function (out) {
      if (out && out.success && out.approve_url) {
        window.location.href = out.approve_url;
        return;
      }
      msg((out && out.error) || 'PayPal checkout failed');
    });
  }

  function captureReturn() {
    var params = new URLSearchParams(window.location.search);
    if (params.get('paypal') === 'cancel') {
      msg('PayPal checkout cancelled');
      window.history.replaceState({}, '', window.location.pathname);
      return;
    }
    var token = params.get('token');
    if (params.get('paypal') !== 'success' || !token) return;
    fetch('/api/paypal/capture', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        order_id: token,
        item_id: params.get('item_id') || '',
        user_id: params.get('user_id') || uid()
      })
    }).then(function (r) { return r.json(); }).then(function (data) {
      if (data && data.success && data.edition) msg('Minted ' + data.edition.edition_id);
      else if (data && data.success) msg('Payment captured');
      else msg((data && (data.details || data.error)) || 'Capture failed');
      window.history.replaceState({}, '', window.location.pathname);
      load();
    }).catch(function () { msg('Capture failed'); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    captureReturn();
    load();
  });
  var listBtn = q('nft-refresh');
  if (listBtn) listBtn.addEventListener('click', load);
})();
