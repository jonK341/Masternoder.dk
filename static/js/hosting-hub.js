/**
 * Masternode Hosting Hub — toasts, live monitor, checkout, fleet (pattern: exchange-trade-desk.js)
 */
(function () {
  'use strict';

  var TAB_LABELS = {
    overview: '📊 Overview',
    rent: '🛒 Rent',
    fleet: '🏛️ Fleet',
    network: '🌐 Network',
    orders: '📋 My orders',
    faq: '❓ FAQ',
  };

  var pollTimer = null;
  var quoteTimer = null;
  var checkoutConfig = null;
  var lastService = null;
  var fleetCache = [];
  var netCache = [];
  var currentTab = 'overview';
  var payPalReturnDone = false;
  var onChainPollTimer = null;
  var FAV_KEY = 'mn_host_favorites';
  var RECENT_KEY = 'mn_host_recent_rentals';

  function q(id) { return document.getElementById(id); }

  function uid() {
    if (window.Mn2SiteBridge && window.Mn2SiteBridge.uid) return window.Mn2SiteBridge.uid();
    try {
      return localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
    } catch (e) {
      return 'default_user';
    }
  }

  function isAuthed() {
    var u = uid();
    return u && u !== 'default_user' && !String(u).startsWith('anon_');
  }

  function toast(text, type) {
    var host = q('host-toast-host');
    if (!host) {
      if (window.cexToast) window.cexToast(text, type);
      return;
    }
    var el = document.createElement('div');
    el.className = 'host-toast ' + (type === 'err' ? 'err' : type === 'warn' ? 'warn' : 'ok');
    el.setAttribute('role', 'status');
    el.textContent = text;
    host.appendChild(el);
    setTimeout(function () {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 4200);
  }

  function fmtNum(v, dp) {
    if (v === null || v === undefined) return '—';
    var n = Number(v);
    if (!isFinite(n)) return '—';
    return n.toLocaleString(undefined, { minimumFractionDigits: dp || 0, maximumFractionDigits: dp || 0 });
  }

  function fetchJson(path, opts) {
    opts = opts || {};
    return fetch(path, {
      credentials: 'same-origin',
      method: opts.method || 'GET',
      headers: opts.headers || (opts.body ? { 'Content-Type': 'application/json' } : {}),
      body: opts.body || undefined,
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok && d && !d.error) d.error = 'HTTP ' + r.status;
        return d;
      });
    });
  }

  function copyText(text) {
    if (!text) return;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(function () { toast('Copied to clipboard', 'ok'); }).catch(fallback);
    } else fallback();
    function fallback() {
      var ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand('copy');
        toast('Copied', 'ok');
      } catch (e) {
        toast('Copy failed', 'err');
      }
      document.body.removeChild(ta);
    }
  }

  function readJson(key, fallback) {
    try {
      var raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) {
      return fallback;
    }
  }

  function writeJson(key, val) {
    try { localStorage.setItem(key, JSON.stringify(val)); } catch (e) { /* ignore */ }
  }

  function getFavorites() {
    return readJson(FAV_KEY, []);
  }

  function toggleFavorite(id) {
    var favs = getFavorites();
    var i = favs.indexOf(id);
    if (i >= 0) favs.splice(i, 1);
    else favs.push(id);
    writeJson(FAV_KEY, favs.slice(0, 50));
    renderFleet(fleetCache);
    toast(i >= 0 ? 'Removed from favorites' : 'Added to favorites', 'ok');
  }

  function pushRecent(slots, method) {
    var rec = readJson(RECENT_KEY, []);
    rec.unshift({ slots: slots, method: method, ts: new Date().toISOString() });
    writeJson(RECENT_KEY, rec.slice(0, 8));
    renderRecent();
  }

  function renderRecent() {
    var el = q('host-recent-rentals');
    if (!el) return;
    var rec = readJson(RECENT_KEY, []);
    if (!rec.length) {
      el.innerHTML = '<span class="host-muted">No recent checkout attempts yet.</span>';
      return;
    }
    el.innerHTML = rec.map(function (r) {
      return '<span class="host-recent-chip">' + r.slots + ' slot(s) · ' + (r.method || '—') + '</span>';
    }).join('');
  }

  function renderSecurityBar() {
    var el = q('host-security-bar');
    if (!el) return;
    if (!isAuthed()) {
      el.innerHTML =
        '<span class="host-status-pill warn">🔒 Guest — <a href="/profile" style="color:#00d4ff">sign in</a> to rent &amp; view orders</span>' +
        '<span class="host-status-pill">Session: anonymous</span>';
      return;
    }
    el.innerHTML =
      '<span class="host-status-pill ok">🔐 Signed in · ' + uid().slice(0, 14) + '</span>' +
      '<span class="host-status-pill" id="host-wallet-pill">Wallet loading…</span>';
    fetchJson('/api/points/all?user_id=' + encodeURIComponent(uid()))
      .then(function (d) {
        var pill = q('host-wallet-pill');
        if (!pill || !d || !d.success) return;
        var pts = d.points || {};
        pill.textContent = fmtNum(pts.mn2_balance, 4) + ' MN2 · ' + fmtNum(pts.coins, 0) + ' coins';
        pill.className = 'host-status-pill ok';
      }).catch(function () {});
  }

  function setFooter(text) {
    var foot = q('host-footer-bar');
    if (foot) foot.innerHTML = text;
  }

  function pushActivity(msg) {
    var feed = q('host-activity-feed');
    if (!feed) return;
    var row = document.createElement('div');
    row.className = 'host-activity-row';
    row.innerHTML = '<time>' + new Date().toLocaleTimeString() + '</time>' + msg;
    feed.insertBefore(row, feed.firstChild);
    while (feed.children.length > 20) feed.removeChild(feed.lastChild);
  }

  function renderLiveMonitor(d) {
    if (!d || !d.success) return;
    lastService = d;
    var open = d.slots_available != null ? d.slots_available : 0;
    var max = d.max_hosted_nodes || 0;
    var used = d.hosted_count || 0;
    var pct = max ? Math.min(100, Math.round((used / max) * 100)) : 0;

    if (q('host-slots-open')) q('host-slots-open').textContent = String(open);
    if (q('host-slots-open-strip')) q('host-slots-open-strip').textContent = String(open);
    if (q('host-slots-used')) q('host-slots-used').textContent = used + ' / ' + max;
    if (q('host-meter-fill')) q('host-meter-fill').style.width = pct + '%';
    if (q('host-net-enabled')) q('host-net-enabled').textContent = fmtNum((d.network || {}).enabled, 0);
    if (q('host-platform-live')) q('host-platform-live').textContent = fmtNum(d.platform_enabled_on_chain, 0);
    if (q('host-waiting-slots')) q('host-waiting-slots').textContent = fmtNum(d.waiting_slots, 0);
    if (q('host-stale-count')) q('host-stale-count').textContent = fmtNum(d.stale_provisioning_count, 0);

    var daemon = d.daemon || {};
    if (q('host-daemon-status')) {
      q('host-daemon-status').textContent = daemon.staking_active ? 'Minting' : 'Idle';
    }
    if (q('host-daemon-sync')) {
      q('host-daemon-sync').textContent = daemon.mnsync ? 'mnsync OK' : 'sync pending';
    }
    if (q('host-daemon-version')) {
      q('host-daemon-version').textContent = daemon.version || '—';
    }

    var dot = q('host-live-dot');
    if (dot) {
      var ok = !(d.network || {}).rpc_error && daemon.mnsync !== false;
      dot.className = 'host-live-pulse' + (ok ? '' : ' off');
    }

    var staleEl = q('host-stale-warning');
    if (staleEl) {
      var rpcErr = (d.network || {}).rpc_error;
      staleEl.hidden = !rpcErr;
      if (rpcErr) staleEl.textContent = 'RPC stale: ' + rpcErr;
    }

    applySoldOut(open);
    applyPricing();
    fleetCache = d.hosts || [];
    renderFleet(fleetCache);
    setFooter(
      '<span>Last sync: ' + new Date().toLocaleTimeString() + '</span>' +
      '<span>Slots open: ' + open + '</span>' +
      '<span>Network enabled: ' + fmtNum((d.network || {}).enabled, 0) + '</span>' +
      '<span>Poll: 30s · <kbd>R</kbd> refresh</span>'
    );
  }

  function renderFleet(hosts) {
    var grid = q('host-fleet-grid');
    if (!grid) return;
    var query = ((q('host-fleet-search') || {}).value || '').toLowerCase();
    var filter = (q('host-fleet-filter') || {}).value || 'all';
    var favs = getFavorites();

    var list = (hosts || []).filter(function (h) {
      var st = String(h.on_chain_status || h.status || '').toLowerCase();
      if (filter === 'enabled' && st !== 'enabled') return false;
      if (filter === 'queued' && st !== 'queued' && st !== 'provisioning') return false;
      if (query) {
        var hay = ((h.label || '') + ' ' + (h.id || '') + ' ' + (h.broadcast_address || '') + ' ' + (h.collateral_address || '')).toLowerCase();
        if (hay.indexOf(query) < 0) return false;
      }
      return true;
    });

    if (!list.length) {
      grid.innerHTML = '<div class="host-empty"><span class="host-empty-icon">🏛️</span>No fleet nodes match filters.</div>';
      return;
    }

    grid.innerHTML = list.map(function (h) {
      var id = h.id || h.label || '';
      var addr = h.broadcast_address || h.collateral_address || '';
      var st = h.on_chain_status || h.status || 'unknown';
      var isFav = favs.indexOf(id) >= 0;
      var cls = String(st).toUpperCase() === 'ENABLED' ? 'host-node-card--enabled' : '';
      if (isFav) cls += ' host-node-card--fav';
      return '<div class="host-node-card ' + cls + '" data-host-id="' + id + '">' +
        '<div class="host-node-title">' + (h.label || id) +
        '<span><button type="button" class="host-copy-btn" data-copy-id="' + id + '" title="Copy node ID" aria-label="Copy node ID">📋</button>' +
        '<button type="button" class="host-copy-btn host-fav-btn" data-fav-id="' + id + '" title="Favorite" aria-label="Toggle favorite">' +
        (isFav ? '★' : '☆') + '</button></span></div>' +
        (addr ? '<div class="host-node-addr">' + addr +
        ' <button type="button" class="host-copy-btn" data-copy-addr="' + addr + '" aria-label="Copy address">📋</button></div>' : '') +
        '<div><span class="host-badge host-badge--' + (String(st).toLowerCase() === 'enabled' ? 'enabled' : 'queued') + '">' + st + '</span>' +
        (h.synced ? '<span class="host-badge host-badge--enabled">synced</span>' : '') +
        '</div></div>';
    }).join('');

    grid.querySelectorAll('[data-copy-id]').forEach(function (btn) {
      btn.addEventListener('click', function () { copyText(btn.getAttribute('data-copy-id')); });
    });
    grid.querySelectorAll('[data-copy-addr]').forEach(function (btn) {
      btn.addEventListener('click', function () { copyText(btn.getAttribute('data-copy-addr')); });
    });
    grid.querySelectorAll('.host-fav-btn').forEach(function (btn) {
      btn.addEventListener('click', function () { toggleFavorite(btn.getAttribute('data-fav-id')); });
    });
  }

  function renderNetwork(list) {
    netCache = list || [];
    var tbody = q('host-net-table-body');
    if (!tbody) return;
    var sort = (q('host-net-sort') || {}).value || 'rank';
    var sorted = netCache.slice();
    if (sort === 'activetime') {
      sorted.sort(function (a, b) { return Number(b.activetime || 0) - Number(a.activetime || 0); });
    } else {
      sorted.sort(function (a, b) { return Number(a.rank || 999) - Number(b.rank || 999); });
    }
    if (!sorted.length) {
      tbody.innerHTML = '<tr><td colspan="4"><div class="host-empty"><span class="host-empty-icon">🌐</span>No network masternodes loaded.</div></td></tr>';
      return;
    }
    tbody.innerHTML = sorted.map(function (m) {
      var addr = m.addr || '—';
      return '<tr><td>' + (m.rank != null ? m.rank : '—') + '</td><td class="host-node-addr">' + addr +
        ' <button type="button" class="host-copy-btn" data-copy-net="' + addr + '" aria-label="Copy">📋</button></td>' +
        '<td><span class="host-badge host-badge--enabled">' + (m.status || '—') + '</span></td>' +
        '<td>' + (m.activetime != null ? m.activetime + 's' : '—') + '</td></tr>';
    }).join('');
    tbody.querySelectorAll('[data-copy-net]').forEach(function (btn) {
      btn.addEventListener('click', function () { copyText(btn.getAttribute('data-copy-net')); });
    });
  }

  function applySoldOut(open) {
    var soldOut = open != null && Number(open) <= 0;
    var banner = q('host-sold-out');
    var card = q('host-checkout-card');
    if (banner) banner.hidden = !soldOut;
    if (card) card.classList.toggle('host-checkout-card--sold-out', soldOut);
    document.querySelectorAll('#host-checkout-actions .host-btn').forEach(function (btn) {
      btn.disabled = soldOut;
    });
    var slotsInput = q('host-checkout-slots');
    if (slotsInput) slotsInput.disabled = soldOut;
  }

  function applyPricing() {
    var sample = (checkoutConfig && checkoutConfig.pricing_sample) || {};
    var pp = checkoutConfig || {};
    var slots = parseInt((q('host-checkout-slots') || {}).value, 10) || 1;
    var usd = Number(pp.price_usd_per_slot || sample.usd_per_slot || 4.99);
    var coins = Number(sample.coins_per_slot || Math.round(usd * 100));
    var mn2v = Number(sample.mn2_per_slot || coins / 100);
    if (q('host-price-usd')) q('host-price-usd').textContent = '$' + fmtNum(usd * slots, 2);
    if (q('host-fee-breakdown')) {
      q('host-fee-breakdown').innerHTML =
        '<b>Fee breakdown</b> · ' + slots + ' slot(s)<br>' +
        'USD: <b>$' + fmtNum(usd * slots, 2) + '</b> ($' + fmtNum(usd, 2) + '/slot)<br>' +
        'Coins: <b>' + fmtNum(coins * slots, 0) + '</b> (' + fmtNum(coins, 0) + '/slot)<br>' +
        'MN2: <b>' + fmtNum(mn2v * slots, 4) + '</b> (' + fmtNum(mn2v, 4) + '/slot)<br>' +
        'Collateral lock: <b>' + fmtNum((lastService && lastService.collateral_mn2) || 5000, 0) + ' MN2</b> per node (platform)';
    }
    if (q('host-price-alt')) {
      q('host-price-alt').textContent = fmtNum(coins * slots, 0) + ' coins · ' + fmtNum(mn2v * slots, 4) + ' MN2';
    }
  }

  function applyCheckoutRails() {
    var rails = ((checkoutConfig && checkoutConfig.shop_payments) || {}).payment_rails ||
      ['paypal', 'mn2', 'credits', 'mn2_onchain'];
    var map = { paypal: 'paypal', coins: 'credits', mn2: 'mn2', onchain: 'mn2_onchain' };
    document.querySelectorAll('[data-host-pay]').forEach(function (btn) {
      var rail = btn.getAttribute('data-host-pay');
      btn.style.display = rails.indexOf(map[rail] || rail) >= 0 ? '' : 'none';
    });
  }

  function startQuoteCountdown(expiresAt) {
    if (quoteTimer) clearInterval(quoteTimer);
    var el = q('host-quote-ttl');
    if (!el || !expiresAt) { if (el) el.textContent = ''; return; }
    function tick() {
      var end = new Date(expiresAt).getTime();
      var left = Math.max(0, Math.floor((end - Date.now()) / 1000));
      if (left <= 0) {
        el.innerHTML = '<span class="host-cooldown-pill">Quote expired — request a new one</span>';
        clearInterval(quoteTimer);
        return;
      }
      el.textContent = 'Quote valid ' + Math.floor(left / 60) + 'm ' + (left % 60) + 's';
    }
    tick();
    quoteTimer = setInterval(tick, 1000);
  }

  function loadService(fresh) {
    var suffix = fresh ? '?fresh=1' : '';
    return fetchJson('/api/mn2/masternode/service' + suffix).then(function (d) {
      if (d && d.success) {
        renderLiveMonitor(d);
        pushActivity(
          'Service snapshot · ' + (d.slots_available || 0) + ' open · ' +
          (d.waiting_slots || 0) + ' waiting'
        );
      } else {
        var err = (d && d.error) || 'Hosting service unavailable';
        setFooter('<span style="color:#ffaa66">API error: ' + err + ' · press <kbd>R</kbd> to retry</span>');
        toast(err, 'warn');
      }
      return d;
    }).catch(function () {
      setFooter('<span style="color:#ffaa66">Could not reach hosting API · press <kbd>R</kbd> to retry</span>');
      toast('Hosting service unreachable', 'err');
    });
  }

  function loadNetwork() {
    return fetchJson('/api/mn2/masternodes?limit=50&fresh=1').then(function (d) {
      renderNetwork((d && d.list) || []);
      if (d && d.rpc_error) toast('Network RPC: ' + d.rpc_error, 'warn');
    });
  }

  function loadCheckoutConfig() {
    return fetchJson('/api/mn2/masternode/checkout/config').then(function (cfg) {
      if (cfg && cfg.success) {
        checkoutConfig = cfg;
        applyPricing();
        applyCheckoutRails();
        if (q('host-checkout-slots') && cfg.max_slots_per_order) {
          q('host-checkout-slots').max = String(cfg.max_slots_per_order);
        }
      }
    });
  }

  function loadMyOrders() {
    var tbody = q('host-orders-body');
    if (!tbody) return;
    if (!isAuthed()) {
      tbody.innerHTML = '<tr><td colspan="5"><div class="host-empty"><span class="host-empty-icon">🔒</span>Sign in to view your hosting orders.</div></td></tr>';
      return;
    }
    tbody.innerHTML = '<tr><td colspan="5"><span class="host-skeleton host-skeleton--row"></span></td></tr>';
    fetchJson('/api/mn2/masternode/my-orders?limit=20&user_id=' + encodeURIComponent(uid()))
      .then(function (d) {
        if (!d || !d.success) {
          tbody.innerHTML = '<tr><td colspan="5">' + ((d && d.error) || 'Could not load orders') + '</td></tr>';
          return;
        }
        var rows = d.orders || [];
        if (!rows.length) {
          tbody.innerHTML = '<tr><td colspan="5"><div class="host-empty"><span class="host-empty-icon">📋</span>No hosting orders yet — rent your first slot!</div></td></tr>';
          return;
        }
        tbody.innerHTML = rows.map(function (o) {
          var total = o.usd_total != null ? ('$' + fmtNum(o.usd_total, 2)) :
            (o.mn2_total != null ? fmtNum(o.mn2_total, 4) + ' MN2' : '—');
          return '<tr><td><button type="button" class="host-copy-btn" data-copy-order="' + (o.order_id || '') + '">📋</button> ' +
            (o.order_id || '—') + '</td><td>' + (o.status || '—') + '</td><td>' + (o.slots || 1) +
            '</td><td>' + total + '</td><td>' + (o.paid_at || o.created_at || '—') + '</td></tr>';
        }).join('');
        tbody.querySelectorAll('[data-copy-order]').forEach(function (btn) {
          btn.addEventListener('click', function () { copyText(btn.getAttribute('data-copy-order')); });
        });
      });
  }

  function loadHealth() {
    return fetchJson('/api/mn2/masternode/health').then(function (h) {
      var pill = q('host-health-pill');
      if (!pill || !h) return;
      var st = h.status || 'unknown';
      pill.textContent = 'Health: ' + st;
      pill.className = 'host-status-pill ' + (st === 'healthy' ? 'ok' : st === 'disabled' ? '' : 'warn');
    });
  }

  function confirmCheckout(method, slots) {
    var labels = { paypal: 'PayPal', coins: 'shop coins', mn2: 'MN2 wallet', onchain: 'on-chain MN2' };
    return window.confirm(
      'Confirm masternode hosting checkout?\n\n' +
      slots + ' slot(s) via ' + (labels[method] || method) + '.\n\nProvisioning starts automatically after payment.'
    );
  }

  function setCheckoutBusy(busy) {
    document.querySelectorAll('#host-checkout-actions .host-btn').forEach(function (b) {
      if (!b.closest('.host-checkout-card--sold-out')) b.disabled = !!busy;
    });
  }

  function fetchQuote(slots) {
    return fetchJson('/api/mn2/masternode/checkout/quote', {
      method: 'POST',
      body: JSON.stringify({ slots: slots, user_id: uid() }),
    });
  }

  function runCheckout(method) {
    if (!isAuthed()) {
      toast('Sign in at Profile to rent a slot', 'warn');
      return;
    }
    var openEl = q('host-slots-open');
    var open = openEl ? Number(openEl.textContent) : null;
    if (open != null && !isNaN(open) && open <= 0) {
      toast('Sold out — no slots available', 'warn');
      return;
    }
    var slots = parseInt((q('host-checkout-slots') || {}).value, 10) || 1;
    if (!confirmCheckout(method, slots)) return;
    setCheckoutBusy(true);
    var msg = q('host-checkout-msg');
    if (msg) msg.textContent = 'Creating quote…';
    fetchQuote(slots).then(function (quote) {
      if (!quote || !quote.success) {
        setCheckoutBusy(false);
        var err = (quote && quote.error) || 'Quote failed';
        if (quote && quote.code === 'auth_required') toast('Sign in required', 'warn');
        else if (quote && quote.code === 'quote_expired') toast('Quote expired — try again', 'warn');
        else toast(err, 'err');
        if (msg) msg.textContent = err;
        return null;
      }
      startQuoteCountdown(quote.expires_at);
      pushRecent(slots, method);
      if (method === 'coins') {
        if (msg) msg.textContent = 'Paying with coins…';
        return payInstant('/api/mn2/masternode/checkout/pay-coins', quote, 'Paid with coins — provisioning started.');
      }
      if (method === 'mn2') {
        if (msg) msg.textContent = 'Paying with MN2…';
        return payInstant('/api/mn2/masternode/checkout/pay-mn2', quote, 'Paid with MN2 — provisioning started.');
      }
      if (method === 'onchain') {
        return payOnchain(quote);
      }
      return payPayPal(quote);
    }).catch(function () {
      setCheckoutBusy(false);
      toast('Checkout failed', 'err');
    });
  }

  function payInstant(endpoint, quote, okMsg) {
    return fetchJson(endpoint, {
      method: 'POST',
      body: JSON.stringify({ quote_id: quote.quote_id, user_id: uid() }),
    }).then(function (pay) {
      setCheckoutBusy(false);
      var msg = q('host-checkout-msg');
      if (!pay || !pay.success) {
        toast((pay && pay.error) || 'Payment failed', 'err');
        if (msg) msg.textContent = (pay && pay.error) || 'Payment failed';
        return;
      }
      toast(pay.message || okMsg, 'ok');
      if (msg) msg.textContent = pay.message || okMsg;
      loadService(true);
      loadMyOrders();
    });
  }

  function payPayPal(quote) {
    var msg = q('host-checkout-msg');
    if (msg) msg.textContent = 'Opening PayPal…';
    var returnUrl = window.location.origin + '/hosting/?paypal=success&mn_quote=' + encodeURIComponent(quote.quote_id);
    var cancelUrl = window.location.origin + '/hosting/?paypal=cancel';
    return fetchJson('/api/mn2/masternode/checkout/order', {
      method: 'POST',
      body: JSON.stringify({
        quote_id: quote.quote_id,
        user_id: uid(),
        return_url: returnUrl,
        cancel_url: cancelUrl,
      }),
    }).then(function (order) {
      setCheckoutBusy(false);
      if (!order || !order.success) {
        toast((order && order.error) || 'PayPal order failed', 'err');
        if (msg) msg.textContent = (order && order.error) || 'PayPal order failed';
        return;
      }
      if (order.approve_url) window.location.href = order.approve_url;
    });
  }

  function payOnchain(quote) {
    var msg = q('host-checkout-msg');
    if (msg) msg.textContent = 'Creating on-chain payment…';
    return fetchJson('/api/mn2/masternode/checkout/pay-onchain', {
      method: 'POST',
      body: JSON.stringify({ quote_id: quote.quote_id, user_id: uid() }),
    }).then(function (pay) {
      setCheckoutBusy(false);
      if (!pay || !pay.success) {
        toast((pay && pay.error) || 'On-chain setup failed', 'err');
        return;
      }
      openOnchainModal(pay);
      toast('Send exact MN2 amount shown in modal', 'ok');
    });
  }

  function openOnchainModal(data) {
    var modal = q('host-onchain-modal');
    if (!modal || !data) return;
    if (q('host-onchain-address')) q('host-onchain-address').textContent = data.address || '';
    if (q('host-onchain-amount')) q('host-onchain-amount').textContent = 'Send exactly ' + fmtNum(data.amount_mn2, 8) + ' MN2';
    if (q('host-onchain-status')) q('host-onchain-status').textContent = 'Waiting for payment…';
    var qrEl = q('host-onchain-qr');
    if (qrEl) qrEl.innerHTML = '';
    if (qrEl && window.QRCode && data.address) {
      try { new window.QRCode(qrEl, { text: data.address, width: 120, height: 120 }); } catch (e) { qrEl.textContent = 'QR N/A'; }
    }
    var copyBtn = q('host-onchain-copy');
    if (copyBtn) copyBtn.onclick = function () { copyText(data.address); };
    modal.hidden = false;
    modal.setAttribute('aria-hidden', 'false');
    if (onChainPollTimer) clearInterval(onChainPollTimer);
    onChainPollTimer = setInterval(function () {
      fetchJson('/api/mn2/order-payment/status?payment_ref=' + encodeURIComponent(data.payment_ref) + '&user_id=' + encodeURIComponent(uid()))
        .then(function (s) {
          if (s.status === 'fulfilled') {
            clearInterval(onChainPollTimer);
            modal.hidden = true;
            toast('Payment confirmed — provisioning started', 'ok');
            loadService(true);
            loadMyOrders();
          } else if (s.status === 'expired' && q('host-onchain-status')) {
            q('host-onchain-status').textContent = 'Payment expired.';
            clearInterval(onChainPollTimer);
          }
        });
    }, 10000);
  }

  function handlePayPalReturn() {
    if (payPalReturnDone) return;
    var params = new URLSearchParams(window.location.search);
    if (params.get('paypal') !== 'success') return;
    var quoteId = params.get('mn_quote');
    if (!quoteId) return;
    payPalReturnDone = true;
    fetchJson('/api/mn2/masternode/checkout/capture', {
      method: 'POST',
      body: JSON.stringify({ order_id: quoteId, user_id: uid() }),
    }).then(function (d) {
      if (d && d.success) {
        toast(d.message || 'Payment confirmed', 'ok');
        loadService(true);
        loadMyOrders();
      } else toast((d && d.error) || 'Capture failed', 'err');
      try {
        var url = new URL(window.location.href);
        url.searchParams.delete('paypal');
        url.searchParams.delete('mn_quote');
        window.history.replaceState({}, document.title, url.pathname + url.search);
      } catch (e) { /* ignore */ }
    });
  }

  function applyTab(tabId) {
    currentTab = tabId;
    document.querySelectorAll('.host-tab-shell').forEach(function (el) {
      el.classList.toggle('active', el.getAttribute('data-host-tab') === tabId);
      el.hidden = el.getAttribute('data-host-tab') !== tabId;
    });
    document.querySelectorAll('.host-hub-tab').forEach(function (btn) {
      var on = btn.getAttribute('data-host-tab') === tabId;
      btn.classList.toggle('active', on);
      btn.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    var note = q('host-route-note');
    if (note) note.textContent = 'Viewing: ' + (TAB_LABELS[tabId] || tabId);
    try {
      var url = new URL(window.location.href);
      if (tabId === 'overview') url.searchParams.delete('host_tab');
      else url.searchParams.set('host_tab', tabId);
      window.history.replaceState({}, document.title, url.pathname + url.search + url.hash);
    } catch (e) { /* ignore */ }
    if (tabId === 'orders') loadMyOrders();
    if (tabId === 'network') loadNetwork();
  }

  function bindCollapsibles() {
    document.querySelectorAll('.host-collapse-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-collapse');
        var body = q(id);
        if (!body) return;
        var open = body.hidden;
        body.hidden = !open;
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        btn.textContent = open ? '▼' : '▶';
      });
    });
  }

  function bindKeyboard() {
    document.addEventListener('keydown', function (ev) {
      if (ev.target && (ev.target.tagName === 'INPUT' || ev.target.tagName === 'TEXTAREA')) return;
      if (ev.key === '/') {
        ev.preventDefault();
        var search = q('host-fleet-search');
        if (search) search.focus();
      }
      if (ev.key === 'r' || ev.key === 'R') {
        loadService(true);
        loadNetwork();
        toast('Refreshed', 'ok');
      }
      if (ev.key >= '1' && ev.key <= '5') {
        var slots = q('host-checkout-slots');
        if (slots) {
          slots.value = ev.key;
          applyPricing();
          document.querySelectorAll('.host-quick-slots button').forEach(function (b) {
            b.classList.toggle('active', b.getAttribute('data-slots') === ev.key);
          });
        }
      }
    });
  }

  function bindCheckout() {
    document.querySelectorAll('[data-host-pay]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        runCheckout(btn.getAttribute('data-host-pay') || 'paypal');
      });
    });
    var slotsInput = q('host-checkout-slots');
    if (slotsInput) {
      slotsInput.addEventListener('input', applyPricing);
    }
    document.querySelectorAll('.host-quick-slots button').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var n = btn.getAttribute('data-slots');
        if (slotsInput) slotsInput.value = n;
        document.querySelectorAll('.host-quick-slots button').forEach(function (b) {
          b.classList.toggle('active', b === btn);
        });
        applyPricing();
      });
    });
    var closeBtn = q('host-onchain-close');
    var modal = q('host-onchain-modal');
    if (closeBtn && modal) {
      closeBtn.addEventListener('click', function () {
        modal.hidden = true;
        if (onChainPollTimer) clearInterval(onChainPollTimer);
      });
    }
  }

  function bindFleetTools() {
    var search = q('host-fleet-search');
    var filter = q('host-fleet-filter');
    if (search) search.addEventListener('input', function () { renderFleet(fleetCache); });
    if (filter) filter.addEventListener('change', function () { renderFleet(fleetCache); });
    var sort = q('host-net-sort');
    if (sort) sort.addEventListener('change', function () { renderNetwork(netCache); });
  }

  function bindTabs() {
    document.querySelectorAll('.host-hub-tab').forEach(function (btn) {
      btn.addEventListener('click', function () {
        applyTab(btn.getAttribute('data-host-tab') || 'overview');
      });
    });
    var requested = new URLSearchParams(window.location.search).get('host_tab');
    if (requested && TAB_LABELS[requested]) applyTab(requested);
  }

  function bindOnboard() {
    var banner = q('host-onboard');
    var dismiss = q('host-onboard-dismiss');
    if (!banner) return;
    try {
      if (localStorage.getItem('host_onboard_dismissed') === '1') banner.hidden = true;
    } catch (e) { /* ignore */ }
    if (dismiss) {
      dismiss.addEventListener('click', function () {
        banner.hidden = true;
        try { localStorage.setItem('host_onboard_dismissed', '1'); } catch (e) { /* ignore */ }
      });
    }
  }

  function startPolling() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(function () {
      loadService(true);
      if (currentTab === 'network') loadNetwork();
    }, 30000);
  }

  function initHostingPage() {
    if (!q('host-hub-nav')) return;
    document.body.classList.add('host-hub-ready');
    bindTabs();
    bindCollapsibles();
    bindKeyboard();
    bindCheckout();
    bindFleetTools();
    bindOnboard();
    renderSecurityBar();
    renderRecent();
    handlePayPalReturn();
    loadCheckoutConfig();
    loadHealth();
    loadService(true);
    loadNetwork();
    startPolling();
  }

  /** Explorer masternode tab enhancements */
  function initExplorerUpgrades() {
    var panel = document.querySelector('.mn2-tab-panel[data-mn2-tab="masternodes"]');
    if (!panel || panel.getAttribute('data-host-upgraded') === '1') return;
    panel.setAttribute('data-host-upgraded', '1');

    var bar = document.createElement('div');
    bar.className = 'host-status-bar';
    bar.id = 'mn-explorer-security-bar';
    bar.innerHTML = '<span class="host-status-pill">Checking session…</span>';
    panel.insertBefore(bar, panel.firstChild);

    var subnav = document.createElement('div');
    subnav.className = 'mn-host-subnav';
    subnav.setAttribute('role', 'tablist');
    subnav.innerHTML =
      '<button type="button" class="active" data-mn-section="checkout">🛒 Checkout</button>' +
      '<button type="button" data-mn-section="fleet">🏛️ Fleet</button>' +
      '<button type="button" data-mn-section="network">🌐 Network</button>';
    var hero = panel.querySelector('.mn-hero');
    if (hero) hero.after(subnav);

    subnav.querySelectorAll('button').forEach(function (btn) {
      btn.addEventListener('click', function () {
        subnav.querySelectorAll('button').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        var sec = btn.getAttribute('data-mn-section');
        var checkout = q('mn-checkout-card');
        var fleetTitle = panel.querySelector('#mn-node-grid');
        var netTable = panel.querySelector('.mn-net-table');
        if (checkout) checkout.style.display = sec === 'checkout' ? '' : 'none';
        if (fleetTitle) {
          var fleetBlock = fleetTitle.previousElementSibling;
          if (fleetBlock && fleetBlock.classList.contains('ex-section-title')) {
            fleetBlock.style.display = sec === 'fleet' ? '' : 'none';
          }
          fleetTitle.style.display = sec === 'fleet' ? '' : 'none';
        }
        if (netTable) {
          var netTitle = netTable.previousElementSibling;
          if (netTitle && netTitle.classList.contains('ex-section-title')) {
            netTitle.style.display = sec === 'network' ? '' : 'none';
          }
          netTable.style.display = sec === 'network' ? '' : 'none';
        }
      });
    });

    if (!q('host-toast-host')) {
      var toastHost = document.createElement('div');
      toastHost.id = 'host-toast-host';
      toastHost.className = 'host-toast-host';
      toastHost.setAttribute('aria-live', 'polite');
      document.body.appendChild(toastHost);
    }

    if (!isAuthed()) {
      bar.innerHTML = '<span class="host-status-pill warn">🔒 Guest — sign in at <a href="/profile" style="color:#00d4ff">Profile</a> to rent</span>';
    } else {
      bar.innerHTML = '<span class="host-status-pill ok">🔐 ' + uid().slice(0, 12) + '</span>' +
        '<a href="/hosting/?host_tab=orders" class="host-status-pill" style="text-decoration:none;color:inherit">📋 Order history →</a>';
    }

    var slotsInput = q('mn-checkout-slots');
    if (slotsInput && !q('mn-quick-slots')) {
      var quick = document.createElement('div');
      quick.className = 'host-quick-slots';
      quick.id = 'mn-quick-slots';
      quick.innerHTML = [1, 2, 3, 5].map(function (n) {
        return '<button type="button" data-slots="' + n + '">' + n + '</button>';
      }).join('');
      slotsInput.parentNode.after(quick);
      quick.querySelectorAll('button').forEach(function (btn) {
        btn.addEventListener('click', function () {
          slotsInput.value = btn.getAttribute('data-slots');
          slotsInput.dispatchEvent(new Event('input'));
        });
      });
    }
  }

  window.HostingHub = {
    toast: toast,
    copyText: copyText,
    initHostingPage: initHostingPage,
    initExplorerUpgrades: initExplorerUpgrades,
    loadService: loadService,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initHostingPage();
      initExplorerUpgrades();
    });
  } else {
    initHostingPage();
    initExplorerUpgrades();
  }
})();
