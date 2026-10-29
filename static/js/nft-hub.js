/* NFT wallet v2 hub — catalog, resale, holdings, avatar equip, agent wallets */
(function () {
  'use strict';

  var root = document.getElementById('nft-hub-root');
  if (!root) return;

  function uid() {
    try { return localStorage.getItem('game_user_id') || ''; }
    catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'nft-hub.js', context: 'catch' }); } return ''; }
  }

  function q(id) { return document.getElementById(id); }

  function msg(text) {
    var el = q('nft-hub-msg');
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
    }).then(function (r) {
      return r.json().then(function (data) {
        data._status = r.status;
        return data;
      });
    });
  }

  function get(path) {
    var sep = path.indexOf('?') === -1 ? '?' : '&';
    return fetch(path + sep + 'user_id=' + encodeURIComponent(uid()), { credentials: 'same-origin' })
      .then(function (r) { return r.json(); });
  }

  function setText(id, text) {
    var el = q(id);
    if (el) el.textContent = text;
  }

  function renderCatalog(cat, deals) {
    var grid = q('nft-catalog-grid');
    if (!grid) return;
    var skus = (cat && cat.skus) || [];
    if (!skus.length) {
      grid.innerHTML = '<p class="nft-muted">No editions configured.</p>';
      return;
    }
    var fee = (cat && cat.secondary_fee_percent) || (deals && deals.secondary_fee_percent) || 5;
    setText('nft-settlement-note', (cat && cat.settlement) || 'Primary: PayPal or coins. Resale: coin book.');
    setText('nft-fee-note', fee + '% house fee on resale · min list ' + ((cat && cat.min_list_coins) || 20) + ' coins');

    grid.innerHTML = skus.map(function (sku) {
      var soldOut = sku.remaining != null && sku.remaining <= 0;
      var img = sku.avatar_url
        ? '<img src="' + sku.avatar_url + '" alt="" width="72" height="72">'
        : '<div style="width:72px;height:72px;border-radius:10px;background:rgba(255,255,255,0.06);display:flex;align-items:center;justify-content:center;font-size:2rem;">' + (sku.emblem_icon || '💎') + '</div>';
      return (
        '<article class="nft-sku-card">' +
        img +
        '<div class="nft-sku-title">' + (sku.emblem_icon || '') + ' ' + (sku.name || sku.sku) + '</div>' +
        '<div class="nft-sku-meta">' + (sku.rarity || '') + ' · ' + (sku.series || '') + ' · ' +
        (soldOut ? 'Sold out' : (sku.remaining + ' left')) + ' / ' + sku.supply + '</div>' +
        '<p class="nft-sku-desc">' + (sku.description || '') + '</p>' +
        '<div class="nft-sku-meta">$' + Number(sku.price_usd || 0).toFixed(2) + ' · ' + (sku.price_coins || 0) + ' coins</div>' +
        '<div class="nft-sku-actions">' +
        '<button type="button" class="nft-btn nft-btn--paypal" data-nft-paypal="' + sku.sku + '" ' + (soldOut ? 'disabled' : '') + '>PayPal</button>' +
        '<button type="button" class="nft-btn nft-btn--coins" data-nft-coins="' + sku.sku + '" ' + (soldOut ? 'disabled' : '') + '>Coins</button>' +
        '</div></article>'
      );
    }).join('');

    grid.querySelectorAll('[data-nft-paypal]').forEach(function (btn) {
      btn.addEventListener('click', function () { buyPaypal(btn.getAttribute('data-nft-paypal')); });
    });
    grid.querySelectorAll('[data-nft-coins]').forEach(function (btn) {
      btn.addEventListener('click', function () { buyCoins(btn.getAttribute('data-nft-coins')); });
    });
  }

  function renderBook(deals) {
    var el = q('nft-resale-book');
    if (!el) return;
    var rows = (deals && deals.open_listings) || [];
    var user = uid();
    if (!rows.length) {
      el.innerHTML = '<p class="nft-muted">No open asks yet. Mint a primary edition, then list it from your wallet.</p>';
      return;
    }
    el.innerHTML = rows.map(function (row) {
      var mine = user && row.seller_id === user;
      var actions = mine
        ? '<button type="button" class="nft-btn nft-btn--ghost" data-nft-cancel="' + row.listing_id + '">Cancel</button>'
        : '<button type="button" class="nft-btn nft-btn--paypal" data-nft-buy="' + row.listing_id + '">Buy</button>';
      return (
        '<div class="nft-book-row">' +
        '<div class="nft-book-main"><strong>' + (row.name || row.sku) + ' #' + (row.serial || '?') + '</strong>' +
        '<div class="nft-muted">' + (row.price_coins || 0) + ' coins · fee ' + (row.fee_coins || 0) +
        ' · seller ' + (row.seller_id || '') + '</div></div>' + actions + '</div>'
      );
    }).join('');

    el.querySelectorAll('[data-nft-buy]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        post('/api/nft/buy', { listing_id: btn.getAttribute('data-nft-buy') }).then(function (out) {
          msg(out && out.success ? 'Bought ' + (out.edition && out.edition.edition_id) : ((out && out.error) || 'Buy failed'));
          load();
        });
      });
    });
    el.querySelectorAll('[data-nft-cancel]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        post('/api/nft/cancel', { listing_id: btn.getAttribute('data-nft-cancel') }).then(function (out) {
          msg(out && out.success ? 'Listing cancelled' : ((out && out.error) || 'Cancel failed'));
          load();
        });
      });
    });
  }

  function renderWallet(wallet, holdings) {
    var el = q('nft-wallet-editions');
    if (!el) return;
    var equipped = (wallet && wallet.equipped_avatar_edition_id) || (holdings && holdings.equipped_avatar_edition_id) || '';
    var rows = (wallet && wallet.editions) || (holdings && holdings.editions) || [];
    if (!uid()) {
      el.innerHTML = '<p class="nft-muted">Set a profile id in <a href="/profile" style="color:#c08cff;">Profile</a> to hold editions.</p>';
      return;
    }
    if (!rows.length) {
      el.innerHTML = '<p class="nft-muted">No editions yet — pick a primary drop above.</p>';
      return;
    }
    el.innerHTML = rows.map(function (row) {
      var listed = row.status === 'listed';
      var isEquipped = row.edition_id === equipped;
      var equipBtn = row.avatar_url && !listed
        ? '<button type="button" class="nft-btn nft-btn--ghost' + (isEquipped ? ' nft-equipped' : '') + '" data-nft-equip="' + row.edition_id + '">' +
          (isEquipped ? 'Equipped' : 'Equip avatar') + '</button>'
        : '';
      var listUi = listed
        ? '<span class="nft-muted">On resale book</span>'
        : '<input class="nft-input-coins" data-nft-price="' + row.edition_id + '" type="number" min="20" placeholder="coins">' +
          '<button type="button" class="nft-btn nft-btn--coins" data-nft-list="' + row.edition_id + '">List</button>';
      var thumb = row.avatar_url
        ? '<img src="' + row.avatar_url + '" alt="" width="40" height="40" style="border-radius:8px;">'
        : '<span>' + (row.emblem_icon || '💎') + '</span>';
      return (
        '<div class="nft-wallet-row">' + thumb +
        '<div class="nft-book-main"><strong>' + row.edition_id + '</strong>' +
        '<div class="nft-muted">' + (row.name || row.sku) + ' #' + (row.serial || '') + ' · ' + (row.status || 'held') + '</div></div>' +
        listUi + equipBtn + '</div>'
      );
    }).join('');

    el.querySelectorAll('[data-nft-list]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-nft-list');
        var input = el.querySelector('[data-nft-price="' + id + '"]');
        post('/api/nft/list', {
          edition_id: id,
          price_coins: parseInt(input && input.value, 10)
        }).then(function (out) {
          msg(out && out.success ? 'Listed ' + id : ((out && out.error) || 'List failed'));
          load();
        });
      });
    });
    el.querySelectorAll('[data-nft-equip]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        post('/api/nft/equip-avatar', { edition_id: btn.getAttribute('data-nft-equip') }).then(function (out) {
          msg(out && out.success ? 'Avatar equipped on profile' : ((out && out.error) || 'Equip failed'));
          load();
        });
      });
    });
  }

  function renderAgents(data) {
    var el = q('nft-agent-wallets');
    if (!el) return;
    var wallets = (data && data.wallets) || [];
    if (!wallets.length) {
      el.innerHTML = '<p class="nft-muted">No trader agent NFT wallets yet.</p>';
      return;
    }
    el.innerHTML = '<div class="nft-agent-grid">' + wallets.map(function (w) {
      var count = w.edition_count || (w.nft_editions && w.nft_editions.length) || 0;
      var preview = (w.nft_editions || []).slice(0, 2).map(function (ed) {
        return ed.edition_id;
      }).join(', ');
      return (
        '<article class="nft-agent-card">' +
        '<strong>' + (w.agent_id || 'agent') + '</strong>' +
        '<div class="nft-muted">v' + (w.wallet_schema_version || 2) + ' · ' + count + ' edition(s)</div>' +
        (preview ? '<div class="nft-muted">' + preview + '</div>' : '') +
        '<a href="/agents" class="nft-muted" style="color:#7df9ff;">Open agents</a>' +
        '</article>'
      );
    }).join('') + '</div>';
  }

  function renderGlance(cat, deals, wallet) {
    var schema = (cat && cat.wallet_schema_version) || 2;
    setText('nft-glance-schema', 'v' + schema);
    var schemaPill = q('nft-glance-schema-pill');
    if (schemaPill) schemaPill.textContent = 'Wallet v' + schema;
    setText('nft-glance-minted', String((deals && deals.minted) || 0));
    setText('nft-glance-asks', String((deals && deals.open_count) || ((deals && deals.open_listings) || []).length));
    setText('nft-glance-primary', '$' + Number((deals && deals.primary_volume_usd) || 0).toFixed(2));
    setText('nft-glance-resale', String((deals && deals.resale_volume_coins) || 0));
    setText('nft-glance-held', String((wallet && wallet.edition_count) || ((wallet && wallet.editions) || []).length));
    setText('nft-glance-fee', String((deals && deals.house_fee_coins) || 0));
    var pill = q('nft-hero-user-pill');
    if (pill) pill.textContent = uid() || 'Guest collector';
    setText('nft-hero-status', 'Wallet schema v' + schema + ' · same shop coins as Exchange');
  }

  function buyCoins(sku) {
    post('/api/nft/buy-coins', { sku: sku }).then(function (out) {
      msg(out && out.success ? 'Minted ' + (out.edition && out.edition.edition_id) : ((out && out.error) || 'Mint failed'));
      load();
    });
  }

  function buyPaypal(sku) {
    if (!uid()) {
      msg('Create an account in Profile before paying with PayPal');
      return;
    }
    post('/api/nft/buy-paypal', { sku: sku, return_to: 'nft' }).then(function (out) {
      if (out && out.success && out.approve_url) {
        window.location.href = out.approve_url;
        return;
      }
      msg((out && out.error) || 'PayPal checkout failed');
    });
  }

  var TAB_LABELS = {
    primary: 'Primary',
    resale: 'Resale',
    wallet: 'Wallet',
    agents: 'Agents'
  };

  function applyNftTab(tab, opts) {
    opts = opts || {};
    var key = TAB_LABELS[tab] ? tab : 'primary';
    document.querySelectorAll('[data-nft-panel]').forEach(function (panel) {
      var on = panel.getAttribute('data-nft-panel') === key;
      panel.classList.toggle('active', on);
      if (on) panel.removeAttribute('hidden');
      else panel.setAttribute('hidden', '');
    });
    document.querySelectorAll('#nft-hub-nav [data-nft-tab]').forEach(function (btn) {
      var on = btn.getAttribute('data-nft-tab') === key;
      btn.classList.toggle('is-active', on);
      btn.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    setText('nft-tab-status', TAB_LABELS[key] || key);
    var note = q('nft-route-note');
    if (note) {
      note.textContent =
        'Viewing: ' + (TAB_LABELS[key] || key) +
        '. Switch tabs above — inactive sections stay hidden.';
    }
    if (opts.updateUrl !== false) {
      try {
        var url = new URL(window.location.href);
        if (key === 'primary') url.searchParams.delete('tab');
        else url.searchParams.set('tab', key);
        var hash = key === 'primary' ? '' : '#nft-' + key;
        window.history.replaceState({}, document.title, url.pathname + url.search + hash);
      } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'nft-hub.js', context: 'catch' }); } /* ignore */ }
    }
  }

  function resolveInitialTab() {
    var params = new URLSearchParams(window.location.search);
    var tab = params.get('tab');
    var hash = (window.location.hash || '').replace(/^#/, '').toLowerCase();
    if (!tab && hash.indexOf('nft-') === 0) tab = hash.replace(/^nft-/, '');
    if (!tab && (hash === 'nft-primary' || hash === 'nft-resale' || hash === 'nft-wallet' || hash === 'nft-agents')) {
      tab = hash.replace(/^nft-/, '');
    }
    if (tab === 'catalog' || tab === 'drops') tab = 'primary';
    if (tab === 'book' || tab === 'asks') tab = 'resale';
    if (tab === 'holdings' || tab === 'editions') tab = 'wallet';
    return TAB_LABELS[tab] ? tab : 'primary';
  }

  function wireNftTabs() {
    var nav = q('nft-hub-nav');
    if (nav && !nav._bound) {
      nav._bound = true;
      nav.addEventListener('click', function (ev) {
        var btn = ev.target.closest('[data-nft-tab]');
        if (!btn) return;
        applyNftTab(btn.getAttribute('data-nft-tab'));
      });
    }
    document.querySelectorAll('[data-nft-go]').forEach(function (el) {
      if (el._bound) return;
      el._bound = true;
      el.addEventListener('click', function () {
        applyNftTab(el.getAttribute('data-nft-go'));
      });
    });
  }

  function captureReturn() {
    if (!window.NftPayPalReturn) return;
    window.NftPayPalReturn.handle({
      onMessage: msg,
      focusHash: '#nft-wallet',
      onReload: load,
      onSuccess: function (data) {
        if (data && data.edition && data.edition.edition_id) {
          applyNftTab('wallet', { updateUrl: true });
        }
      }
    });
  }

  function load() {
    setText('nft-hero-status', 'Refreshing NFT hub…');
    Promise.all([
      get('/api/nft/catalog'),
      get('/api/nft/deals'),
      get('/api/nft/wallet'),
      fetch('/api/agents/nft-wallets', { credentials: 'same-origin' }).then(function (r) { return r.json(); }).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'nft-hub.js', context: 'catch' }); } return {}; })
    ]).then(function (parts) {
      var cat = parts[0];
      var deals = parts[1];
      var wallet = parts[2];
      var agents = parts[3];
      renderGlance(cat, deals, wallet);
      renderCatalog(cat, deals);
      renderBook(deals);
      renderWallet(wallet, null);
      renderAgents(agents);
    }).catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'nft-hub.js', context: 'catch' }); }
      msg('Could not load NFT hub');
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    wireNftTabs();
    applyNftTab(resolveInitialTab(), { updateUrl: false });
    captureReturn();
    load();
    var refresh = q('nft-hero-refresh');
    if (refresh) refresh.addEventListener('click', load);
  });
})();
