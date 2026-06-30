/* MN2 Crypto Hub — tab nav + leaderboard / teams / reserves / market loaders */
(function () {
  'use strict';

  var TAB_LABELS = {
    explorer: 'Explorer overview',
    staking: 'Staking monitor',
    leaderboard: 'Staking leaderboard',
    teams: 'Staking teams',
    reserves: 'Proof of reserves',
    masternodes: 'Masternode hosting',
    market: 'P2P market'
  };

  var porLoaded = false;
  var marketChecked = false;
  var mnLoaded = false;
  var mnPayPalReturnDone = false;
  var mnCheckoutConfig = null;
  var mnOnChainPollTimer = null;

  function uid() {
    if (window.Mn2SiteBridge && window.Mn2SiteBridge.uid) return window.Mn2SiteBridge.uid();
    try {
      return window.localStorage.getItem('game_user_id')
        || window.localStorage.getItem('user_id')
        || 'default_user';
    } catch (e) {
      return 'default_user';
    }
  }

  function q(id) { return document.getElementById(id); }

  function fmtNum(v, dp) {
    if (v === null || v === undefined) return '--';
    var n = Number(v);
    if (!isFinite(n)) return '--';
    return n.toLocaleString(undefined, { minimumFractionDigits: dp || 0, maximumFractionDigits: dp || 0 });
  }

  function mn2(v) { return v === null || v === undefined ? '--' : fmtNum(v, 4) + ' MN2'; }

  function applyMn2Tab(tabId) {
    var nav = q('mn2-hub-nav');
    var panels = document.querySelectorAll('.mn2-tab-panel[data-mn2-tab]');
    panels.forEach(function (el) {
      el.hidden = el.getAttribute('data-mn2-tab') !== tabId;
    });
    if (nav) {
      nav.querySelectorAll('.mn2-hub-tab').forEach(function (btn) {
        var on = btn.getAttribute('data-mn2-tab') === tabId;
        btn.classList.toggle('active', on);
        btn.setAttribute('aria-selected', on ? 'true' : 'false');
      });
    }
    var note = q('mn2-route-note');
    if (note) {
      note.textContent = 'Viewing: ' + (TAB_LABELS[tabId] || tabId) + '. Switch tabs above to browse the MN2 crypto hub.';
    }
    try {
      var url = new URL(window.location.href);
      if (tabId === 'explorer') url.searchParams.delete('tab');
      else url.searchParams.set('tab', tabId);
      window.history.replaceState({}, document.title, url.pathname + url.search + url.hash);
    } catch (e) { /* ignore */ }

    if (tabId === 'leaderboard') loadLeaderboard();
    if (tabId === 'teams') loadTeams();
    if (tabId === 'reserves' && !porLoaded) { porLoaded = true; loadProofOfReserves(); }
    if (tabId === 'masternodes' && !mnLoaded) { mnLoaded = true; loadMasternodeHosting(); }
    if (tabId === 'market' && !marketChecked) { marketChecked = true; checkMarketEnabled(); }
  }

  function initTabs() {
    var nav = q('mn2-hub-nav');
    if (!nav) return;
    nav.addEventListener('click', function (ev) {
      var btn = ev.target.closest('[data-mn2-tab]');
      if (!btn || !nav.contains(btn)) return;
      applyMn2Tab(btn.getAttribute('data-mn2-tab'));
    });
    var requested = new URLSearchParams(window.location.search).get('tab');
    var valid = Object.prototype.hasOwnProperty.call(TAB_LABELS, requested);
    applyMn2Tab(valid ? requested : 'explorer');
    handleMasternodePayPalReturn();
  }

  function loadLeaderboard() {
    var body = q('lb-body');
    if (!body || body.getAttribute('data-loaded') === '1') return;
    fetch('/api/mn2/staking/leaderboard?limit=50', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        body.setAttribute('data-loaded', '1');
        var priv = q('lb-privacy');
        if (priv && d.privacy) priv.textContent = d.privacy;
        var rows = (d && d.leaderboard) || [];
        if (!rows.length) { body.innerHTML = '<tr><td colspan="6">No opt-in stakers yet.</td></tr>'; return; }
        var showAmt = rows.some(function (r) { return r.staked != null; });
        if (showAmt) {
          q('col-staked').style.display = '';
          q('col-earned').style.display = '';
        }
        body.innerHTML = rows.map(function (r, i) {
          return '<tr><td class="rank">' + (i + 1) + '</td><td>' + (r.display_id || '—') +
            '</td><td class="tier">' + (r.longevity_label || r.longevity_tier || '—') +
            '</td><td>' + (r.longevity_days != null ? r.longevity_days : '—') +
            (showAmt ? '</td><td>' + (r.staked != null ? Number(r.staked).toFixed(4) : '—') +
              '</td><td>' + (r.total_earned != null ? Number(r.total_earned).toFixed(4) : '—') : '') + '</td></tr>';
        }).join('');
      })
      .catch(function () { body.innerHTML = '<tr><td colspan="6">Could not load.</td></tr>'; });
  }

  function loadTeams() {
    var tb = q('st-teams-body');
    if (!tb || tb.getAttribute('data-loaded') === '1') return;
    fetch('/api/mn2/staking/teams/leaderboard?limit=50', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        tb.setAttribute('data-loaded', '1');
        var note = q('st-teams-note');
        if (note && d.note) note.textContent = d.note;
        var rows = (d && d.leaderboard) || [];
        if (!rows.length) { tb.innerHTML = '<tr><td colspan="7">No qualifying teams yet.</td></tr>'; return; }
        tb.innerHTML = rows.map(function (t, i) {
          return '<tr><td>' + (i + 1) + '</td><td>' + (t.name || '—') + '</td><td>' + t.member_count +
            '</td><td>' + t.active_stakers + '</td><td>' + Number(t.total_staked_mn2 || 0).toFixed(2) +
            '</td><td>' + (t.pooled_avg_longevity_days != null ? t.pooled_avg_longevity_days : '—') +
            '</td><td class="mult">' + Number(t.team_multiplier || 1).toFixed(3) + '×</td></tr>';
        }).join('');
      })
      .catch(function () { tb.innerHTML = '<tr><td colspan="7">Could not load.</td></tr>'; });
  }

  function renderPoR(d) {
    if (!d || !d.success) return;
    var cov = d.coverage_ratio;
    var banner = q('pr-banner');
    var text = q('pr-banner-text');
    if (!banner || !text) return;
    var icon = banner.querySelector('.big');
    var reconOk = d.reconcile && d.reconcile.ok === true;
    var onchainOk = d.assets && d.assets.onchain && d.assets.onchain.status === 'ok';
    if (!onchainOk) {
      banner.className = 'banner warn';
      icon.textContent = '⏳';
      text.textContent = 'Daemon balance temporarily unavailable — showing user liabilities only.';
    } else if (d.fully_backed) {
      banner.className = 'banner ok';
      icon.textContent = '✅';
      text.textContent = 'Fully backed — all user MN2 is covered by custodial reserves.';
    } else if (cov !== null && cov >= 1.0) {
      banner.className = 'banner warn';
      icon.textContent = '⚠️';
      text.textContent = 'Reserves cover liabilities, but reconciliation reported a check to review.';
    } else {
      banner.className = 'banner bad';
      icon.textContent = '⚠️';
      text.textContent = 'Coverage is below 1.0 — reserves do not currently cover all user MN2.';
    }
    q('t-coverage').textContent = cov === null ? '—' : (cov * 100).toFixed(2) + '%';
    q('t-assets').textContent = mn2(d.assets ? d.assets.total_mn2 : null);
    q('t-liab').textContent = mn2(d.liabilities ? d.liabilities.total_mn2 : null);
    q('t-surplus').textContent = mn2(d.surplus_mn2);
    if (d.liabilities) q('t-liab-sub').textContent = d.liabilities.holders + ' holders';
    var oc = (d.assets && d.assets.onchain) || {};
    var rows = [
      ['On-chain wallet balance', mn2(oc.balance)],
      ['Immature (staking)', mn2(oc.immature_balance)],
      ['Unconfirmed', mn2(oc.unconfirmed_balance)],
      ['Stabilization reserve', mn2(d.assets ? d.assets.stabilization_reserve_mn2 : null)],
      ['User liquid balances', mn2(d.liabilities ? d.liabilities.user_liquid_mn2 : null)],
      ['User staked balances', mn2(d.liabilities ? d.liabilities.user_staked_mn2 : null)],
      ['Reconcile status', reconOk ? 'PASS ✅' : 'review ⚠️']
    ];
    q('pr-breakdown').innerHTML = rows.map(function (r) {
      return '<tr><td>' + r[0] + '</td><td class="num">' + r[1] + '</td></tr>';
    }).join('');
    if (d.generated_at) q('pr-ts').textContent = 'As of ' + d.generated_at;
  }

  function renderYield(d) {
    if (!d || !d.success) return;
    var lt = d.lifetime || {};
    q('y-yield').textContent = mn2(lt.realized_yield_mn2);
    q('y-paid').textContent = mn2(lt.rewards_paid_mn2);
    q('y-margin').textContent = mn2(lt.site_margin_mn2);
    q('y-margin-sub').textContent = (d.site_margin_percent || 0) + '% stated';
    q('y-ratio').textContent = lt.payout_ratio == null ? '—' : (lt.payout_ratio * 100).toFixed(1) + '%';
    var body = q('y-body');
    var days = d.by_day || [];
    if (!days.length) { body.innerHTML = '<tr><td colspan="3">No reward intervals recorded yet.</td></tr>'; return; }
    body.innerHTML = days.map(function (r) {
      return '<tr><td>' + r.date + '</td><td class="num">' + fmtNum(r.pool_budget_mn2, 4) + '</td><td class="num">' + fmtNum(r.reward_mn2, 4) + '</td></tr>';
    }).join('');
  }

  function loadProofOfReserves() {
    fetch('/api/mn2/staking/proof-of-reserves').then(function (r) { return r.json(); })
      .then(renderPoR).catch(function () {
        var text = q('pr-banner-text');
        if (text) text.textContent = 'Could not load reserve data. Please retry shortly.';
      });
    fetch('/api/mn2/staking/yield-report').then(function (r) { return r.json(); })
      .then(renderYield).catch(function () {});
    setInterval(function () {
      if (q('mn2-tab-reserves') && !q('mn2-tab-reserves').hidden) {
        fetch('/api/mn2/staking/proof-of-reserves').then(function (r) { return r.json(); }).then(renderPoR).catch(function () {});
        fetch('/api/mn2/staking/yield-report').then(function (r) { return r.json(); }).then(renderYield).catch(function () {});
      }
    }, 60000);
  }

  function hubClass(status) {
    if (status === 'healthy' || status === 'active' || status === 'enabled') return 'ok';
    if (status === 'warn' || status === 'disabled' || status === 'unconfigured' || status === 'unknown') return 'warn';
    return 'bad';
  }

  function renderServicesGrid(gridId, services) {
    var grid = q(gridId);
    if (!grid) return;
    if (!services || !services.length) {
      grid.innerHTML = '<div class="hub-card warn"><div class="label">Services</div><div class="value">No data</div></div>';
      return;
    }
    grid.innerHTML = services.map(function (s) {
      var sub = (s.category || '') + (s.page_url ? ' · ' + s.page_url : '');
      return '<div class="hub-card ' + hubClass(s.status) + '">' +
        '<div class="label">' + (s.name || s.id) + '</div>' +
        '<div class="value">' + (s.status || '—') + '</div>' +
        (sub ? '<div class="sub">' + sub + '</div>' : '') +
        '</div>';
    }).join('');
  }

  function mnBadge(status) {
    var s = String(status || 'unknown').toLowerCase();
    var cls = 'mn-badge--planned';
    if (s === 'enabled' || s === 'active') cls = 'mn-badge--enabled';
    else if (s === 'queued' || s === 'pending_collateral') cls = 'mn-badge--queued';
    return '<span class="mn-badge ' + cls + '">' + (status || 'unknown') + '</span>';
  }

  function formatActivetime(seconds, status) {
    var s = Number(seconds);
    if (isNaN(s) || seconds == null || seconds === '') return '';
    if (s <= 0) {
      if (String(status || '').toUpperCase() === 'ACTIVE') return '0 · no ping';
      return '0s';
    }
    if (s < 3600) return Math.floor(s / 60) + 'm active';
    if (s < 86400) {
      var h = Math.floor(s / 3600);
      var m = Math.floor((s % 3600) / 60);
      return h + 'h ' + m + 'm active';
    }
    var d = Math.floor(s / 86400);
    var hr = Math.floor((s % 86400) / 3600);
    return d + 'd ' + hr + 'h active';
  }

  function activetimeBadge(seconds, status) {
    var label = formatActivetime(seconds, status);
    if (!label) return '';
    var cls = Number(seconds) > 0 ? 'mn-badge--active' : 'mn-badge--noping';
    return '<span class="mn-badge ' + cls + '" title="Network activetime (ping uptime)">' + label + '</span>';
  }

  function renderMnRpcBanner(msg) {
    var el = q('mn-rpc-banner');
    if (!el) return;
    if (msg) {
      el.hidden = false;
      el.textContent = 'Daemon RPC unavailable — network list may be empty or stale. (' + msg + ')';
    } else {
      el.hidden = true;
      el.textContent = '';
    }
  }

  function renderNodeCard(title, addr, badges, extraClass) {
    return '<div class="mn-node-card ' + (extraClass || '') + '">' +
      '<div class="mn-node-title">' + title + '</div>' +
      (addr ? '<div class="mn-node-addr">' + addr + '</div>' : '') +
      '<div class="mn-node-badges">' + badges + '</div></div>';
  }

  function loadMasternodeHosting() {
    fetch('/api/mn2/masternode/service?fresh=1', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d || !d.success) return;
        var max = d.max_hosted_nodes || 350;
        var used = d.hosted_count || 0;
        var open = d.slots_available != null ? d.slots_available : Math.max(0, max - used);
        var pct = max ? Math.min(100, Math.round((used / max) * 100)) : 0;
        if (q('mn-meter-label')) q('mn-meter-label').textContent = used + ' / ' + max + ' slots used';
        if (q('mn-meter-fill')) q('mn-meter-fill').style.width = pct + '%';
        if (q('mn-net-enabled')) q('mn-net-enabled').textContent = fmtNum((d.network || {}).enabled, 0);
        if (q('mn-net-total')) q('mn-net-total').textContent = fmtNum((d.network || {}).total, 0) + ' on chain';
        if (q('mn-slots')) q('mn-slots').textContent = used;
        if (q('mn-collateral')) q('mn-collateral').textContent = fmtNum(d.collateral_mn2, 0) + ' MN2 each';
        if (q('mn-open-slots')) q('mn-open-slots').textContent = open;
        if (q('mn-slots-cap')) q('mn-slots-cap').textContent = 'up to ' + max + ' total';
        applyMasternodeCheckoutSoldOut(open);
        var daemon = d.daemon || {};
        if (q('mn-daemon')) {
          q('mn-daemon').textContent = daemon.staking_active ? 'Minting' : 'Idle';
        }
        if (q('mn-daemon-sub')) {
          q('mn-daemon-sub').textContent = daemon.mnsync ? 'mnsync OK' : 'sync pending';
        }
        var pp = d.paypal || {};
        if (q('mn-price-label') && pp.price_usd_per_slot != null) {
          q('mn-price-label').textContent = '$' + fmtNum(pp.price_usd_per_slot, 2);
        }
        if (q('mn-checkout-slots') && pp.max_slots_per_order != null) {
          q('mn-checkout-slots').max = String(pp.max_slots_per_order);
        }
        applyMasternodeCheckoutPricing();
        var notes = q('mn-public-notes');
        if (notes) notes.textContent = d.public_notes || '';
        var hosts = d.hosts || [];
        if (q('mn-host-summary')) {
          q('mn-host-summary').textContent = '(' + hosts.length + ' in fleet · ' +
            (d.platform_enabled_on_chain || 0) + ' live on-chain)';
        }
        renderMnRpcBanner((d.network || {}).rpc_error || null);
        var grid = q('mn-node-grid');
        if (grid) {
          if (!hosts.length) {
            grid.innerHTML = renderNodeCard('No hosts yet', null, mnBadge('open'), 'mn-node-card--empty');
          } else {
            grid.innerHTML = hosts.map(function (h) {
              var st = h.on_chain_status || h.status || 'unknown';
              var cls = String(st).toUpperCase() === 'ENABLED' ? 'mn-node-card--enabled' :
                (h.status === 'queued' ? 'mn-node-card--queued' : 'mn-node-card--active');
              var act = h.on_chain_activetime != null ? h.on_chain_activetime : null;
              return renderNodeCard(
                h.label || h.id,
                h.broadcast_address || h.collateral_address || '—',
                mnBadge(st) + mnBadge(h.synced ? 'synced' : 'pending') +
                  activetimeBadge(act, st),
                cls
              );
            }).join('');
          }
        }
      }).catch(function () {});

    fetch('/api/mn2/masternodes?limit=50&fresh=1', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var tbody = q('mn-net-table');
        var grid = q('mn-net-grid');
        var list = (d && d.list) || [];
        var rpcErr = (d && d.rpc_error) ? String(d.rpc_error) : '';
        if (d && d.success) {
          if (q('mn-net-enabled')) q('mn-net-enabled').textContent = fmtNum(d.enabled, 0);
          if (q('mn-net-total')) q('mn-net-total').textContent = fmtNum(d.total, 0) + ' on chain';
        }
        renderMnRpcBanner(rpcErr || null);
        if (tbody) {
          if (!list.length) {
            tbody.innerHTML = '<tr><td colspan="4">' +
              (rpcErr ? ('RPC unavailable — ' + rpcErr) : 'No network masternodes.') +
              '</td></tr>';
          } else {
            tbody.innerHTML = list.map(function (m) {
              var st = m.status || '—';
              var addr = m.addr ? '<span class="mn-node-addr">' + m.addr + '</span>' : '—';
              return '<tr class="' + (String(st).toUpperCase() === 'ENABLED' ? 'mn-row-enabled' : '') + '">' +
                '<td>' + (m.rank != null ? m.rank : '—') + '</td>' +
                '<td>' + addr + '</td>' +
                '<td>' + mnBadge(st) + '</td>' +
                '<td>' + (formatActivetime(m.activetime, st) || '—') + '</td>' +
                '</tr>';
            }).join('');
          }
        }
        if (grid && list.length) {
          grid.innerHTML = list.map(function (m) {
            return renderNodeCard(
              'Rank #' + (m.rank != null ? m.rank : '?'),
              m.addr || '—',
              mnBadge(m.status) + activetimeBadge(m.activetime, m.status),
              String(m.status).toUpperCase() === 'ENABLED' ? 'mn-node-card--enabled' : ''
            );
          }).join('');
        }
      }).catch(function () {
        var tbody = q('mn-net-table');
        if (tbody) tbody.innerHTML = '<tr><td colspan="4">Could not load network masternodes.</td></tr>';
        renderMnRpcBanner('request failed');
      });

    fetch('/api/mn2/masternode/checkout/config', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (cfg) {
        if (cfg && cfg.success) {
          mnCheckoutConfig = cfg;
          applyMasternodeCheckoutPricing();
          applyMasternodeCheckoutRails();
        }
      }).catch(function () {});

    setupMasternodeCheckout();
  }

  function hostingRails() {
    var shop = (mnCheckoutConfig && mnCheckoutConfig.shop_payments) || {};
    return shop.payment_rails || ['paypal', 'mn2', 'credits', 'mn2_onchain'];
  }

  function hostingPriceSample() {
    return (mnCheckoutConfig && mnCheckoutConfig.pricing_sample) || {};
  }

  function applyMasternodeCheckoutPricing() {
    var sample = hostingPriceSample();
    var pp = (mnCheckoutConfig && mnCheckoutConfig.price_usd_per_slot != null)
      ? mnCheckoutConfig
      : {};
    var usd = Number(pp.price_usd_per_slot || sample.usd_per_slot || 4.99);
    var coins = Number(sample.coins_per_slot || Math.max(1, Math.round(usd * 100)));
    var mn2v = Number(sample.mn2_per_slot || (sample.mn2_total && sample.slots ? sample.mn2_total / sample.slots : coins / 100));
    if (q('mn-price-label')) q('mn-price-label').textContent = '$' + fmtNum(usd, 2);
    if (q('mn-price-alt')) q('mn-price-alt').textContent = coins + ' coins · ' + fmtNum(mn2v, 4) + ' MN2';
  }

  function applyMasternodeCheckoutSoldOut(openSlots) {
    var soldOut = openSlots != null && Number(openSlots) <= 0;
    var banner = q('mn-hosting-sold-out');
    var card = q('mn-checkout-card');
    if (banner) banner.hidden = !soldOut;
    if (card) card.classList.toggle('mn-checkout-card--sold-out', soldOut);
    var actions = q('mn-checkout-actions');
    if (actions) {
      actions.querySelectorAll('[data-mn-pay]').forEach(function (btn) {
        btn.disabled = soldOut;
        btn.style.opacity = soldOut ? '0.45' : '';
        btn.style.cursor = soldOut ? 'not-allowed' : '';
      });
    }
    var slotsInput = q('mn-checkout-slots');
    if (slotsInput) slotsInput.disabled = soldOut;
  }

  function applyMasternodeCheckoutRails() {
    var rails = hostingRails();
    var actions = q('mn-checkout-actions');
    if (!actions) return;
    actions.querySelectorAll('[data-mn-pay]').forEach(function (btn) {
      var rail = btn.getAttribute('data-mn-pay');
      var map = { paypal: 'paypal', coins: 'credits', mn2: 'mn2', onchain: 'mn2_onchain' };
      btn.style.display = rails.indexOf(map[rail] || rail) >= 0 ? '' : 'none';
    });
  }

  function setCheckoutBusy(busy) {
    var actions = q('mn-checkout-actions');
    if (actions) {
      actions.querySelectorAll('[data-mn-pay]').forEach(function (b) { b.disabled = !!busy; });
    }
  }

  function fetchHostingQuote(slots) {
    return fetch('/api/mn2/masternode/checkout/quote', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slots: slots, user_id: uid() })
    }).then(function (r) { return r.json(); });
  }

  function payHostingPayPal(quote) {
    var msg = q('mn-checkout-msg');
    if (msg) msg.textContent = 'Opening PayPal…';
    var returnUrl = window.location.origin + '/explorer?tab=masternodes&paypal=success&mn_quote=' + encodeURIComponent(quote.quote_id);
    var cancelUrl = window.location.origin + '/explorer?tab=masternodes&paypal=cancel';
    return fetch('/api/mn2/masternode/checkout/order', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        quote_id: quote.quote_id,
        user_id: uid(),
        return_url: returnUrl,
        cancel_url: cancelUrl
      })
    }).then(function (r) { return r.json(); }).then(function (order) {
      setCheckoutBusy(false);
      if (!order || !order.success) {
        if (msg) msg.textContent = (order && order.error) || 'PayPal order failed';
        return;
      }
      if (order.approve_url) window.location.href = order.approve_url;
    });
  }

  function payHostingInstant(endpoint, quote, okFallback) {
    var msg = q('mn-checkout-msg');
    return fetch(endpoint, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quote_id: quote.quote_id, user_id: uid() })
    }).then(function (r) { return r.json(); }).then(function (pay) {
      setCheckoutBusy(false);
      if (!pay || !pay.success) {
        if (msg) msg.textContent = (pay && pay.error) || 'Payment failed';
        return;
      }
      if (msg) msg.textContent = pay.message || okFallback;
      loadMasternodeHosting();
    }).catch(function () {
      setCheckoutBusy(false);
      if (msg) msg.textContent = 'Payment failed — try again.';
    });
  }

  function openHostingOnchainModal(data) {
    var modal = q('mn2-onchain-modal');
    var addrEl = q('mn2-onchain-address');
    var amountEl = q('mn2-onchain-amount');
    var qrEl = q('mn2-onchain-qr');
    var statusEl = q('mn2-onchain-status');
    if (!modal || !addrEl || !data || !data.payment_ref) return;
    addrEl.textContent = data.address || '';
    amountEl.textContent = 'Send exactly ' + fmtNum(data.amount_mn2 || 0, 8) + ' MN2';
    statusEl.textContent = 'Waiting for payment…';
    if (qrEl) qrEl.innerHTML = '';
    if (qrEl && window.QRCode && data.address) {
      try { new window.QRCode(qrEl, { text: data.address, width: 120, height: 120 }); } catch (e) { qrEl.innerHTML = 'QR N/A'; }
    }
    var copyBtn = q('mn2-onchain-copy');
    if (copyBtn) {
      copyBtn.onclick = function () {
        if (navigator.clipboard && data.address) {
          navigator.clipboard.writeText(data.address).catch(function () {});
        }
      };
    }
    modal.hidden = false;
    modal.setAttribute('aria-hidden', 'false');
    if (mnOnChainPollTimer) clearInterval(mnOnChainPollTimer);
    mnOnChainPollTimer = setInterval(function () {
      fetch('/api/mn2/order-payment/status?payment_ref=' + encodeURIComponent(data.payment_ref) + '&user_id=' + encodeURIComponent(uid()), { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (s) {
          if (s.status === 'fulfilled') {
            if (mnOnChainPollTimer) { clearInterval(mnOnChainPollTimer); mnOnChainPollTimer = null; }
            modal.hidden = true;
            modal.setAttribute('aria-hidden', 'true');
            var msg = q('mn-checkout-msg');
            if (msg) msg.textContent = 'Payment confirmed — your masternode is provisioning.';
            loadMasternodeHosting();
          } else if (s.status === 'expired') {
            if (mnOnChainPollTimer) { clearInterval(mnOnChainPollTimer); mnOnChainPollTimer = null; }
            if (statusEl) statusEl.textContent = 'Payment expired.';
          } else if (s.status === 'confirmed' && statusEl) {
            statusEl.textContent = 'Confirming…';
          }
        }).catch(function () {});
    }, 10000);
  }

  function payHostingOnchain(quote) {
    var msg = q('mn-checkout-msg');
    if (msg) msg.textContent = 'Creating on-chain payment…';
    return fetch('/api/mn2/masternode/checkout/pay-onchain', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quote_id: quote.quote_id, user_id: uid() })
    }).then(function (r) { return r.json(); }).then(function (pay) {
      setCheckoutBusy(false);
      if (!pay || !pay.success) {
        if (msg) msg.textContent = (pay && pay.error) || 'On-chain setup failed';
        return;
      }
      if (msg) msg.textContent = 'Send the exact MN2 amount in the modal.';
      openHostingOnchainModal(pay);
    }).catch(function () {
      setCheckoutBusy(false);
      if (msg) msg.textContent = 'On-chain setup failed.';
    });
  }

  function runMasternodeHostingCheckout(method) {
    var msg = q('mn-checkout-msg');
    var openEl = q('mn-open-slots');
    var open = openEl ? Number(openEl.textContent) : null;
    if (open != null && !isNaN(open) && open <= 0) {
      if (msg) msg.textContent = 'Sold out — no hosting slots available right now.';
      return;
    }
    var slots = parseInt((q('mn-checkout-slots') || {}).value, 10) || 1;
    setCheckoutBusy(true);
    if (msg) msg.textContent = 'Creating quote…';
    fetchHostingQuote(slots).then(function (quote) {
      if (!quote || !quote.success) {
        setCheckoutBusy(false);
        if (msg) msg.textContent = (quote && quote.error) || 'Quote failed';
        return null;
      }
      if (method === 'coins') {
        if (msg) msg.textContent = 'Paying with coins…';
        return payHostingInstant('/api/mn2/masternode/checkout/pay-coins', quote, 'Paid with coins — provisioning started.');
      }
      if (method === 'mn2') {
        if (msg) msg.textContent = 'Paying with MN2 balance…';
        return payHostingInstant('/api/mn2/masternode/checkout/pay-mn2', quote, 'Paid with MN2 — provisioning started.');
      }
      if (method === 'onchain') {
        return payHostingOnchain(quote);
      }
      return payHostingPayPal(quote);
    }).catch(function () {
      setCheckoutBusy(false);
      if (msg) msg.textContent = 'Checkout failed — try again.';
    });
  }

  var mnCheckoutBound = false;
  function setupMasternodeCheckout() {
    if (mnCheckoutBound) return;
    mnCheckoutBound = true;
    var actions = q('mn-checkout-actions');
    if (!actions) return;
    actions.addEventListener('click', function (ev) {
      var btn = ev.target.closest('[data-mn-pay]');
      if (!btn || !actions.contains(btn)) return;
      runMasternodeHostingCheckout(btn.getAttribute('data-mn-pay') || 'paypal');
    });
    var closeBtn = q('mn2-onchain-close');
    var modal = q('mn2-onchain-modal');
    if (closeBtn && modal) {
      closeBtn.addEventListener('click', function () {
        modal.hidden = true;
        modal.setAttribute('aria-hidden', 'true');
        if (mnOnChainPollTimer) { clearInterval(mnOnChainPollTimer); mnOnChainPollTimer = null; }
      });
    }
  }

  function handleMasternodePayPalReturn() {
    if (mnPayPalReturnDone) return;
    var params = new URLSearchParams(window.location.search);
    if (params.get('paypal') !== 'success') return;
    var quoteId = params.get('mn_quote');
    if (!quoteId) return;
    mnPayPalReturnDone = true;
    var msg = q('mn-checkout-msg');
    if (msg) msg.textContent = 'Confirming payment…';
    fetch('/api/mn2/masternode/checkout/capture', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ order_id: quoteId, user_id: uid() })
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (msg) {
          msg.textContent = d.success
            ? (d.message || 'Payment confirmed — your masternode is being provisioned automatically.')
            : (d.error || 'Capture failed');
        }
        if (d.success) loadMasternodeHosting();
        try {
          var url = new URL(window.location.href);
          url.searchParams.delete('paypal');
          url.searchParams.delete('mn_quote');
          window.history.replaceState({}, document.title, url.pathname + url.search);
        } catch (e) { /* ignore */ }
      }).catch(function () {
        if (msg) msg.textContent = 'Could not confirm payment.';
      });
  }

  function checkMarketEnabled() {
    fetch('/api/mn2/p2p/config').then(function (r) { return r.json(); }).then(function (cfg) {
      var paypalOn = cfg && cfg.success && cfg.enabled;
      var disabled = q('market-disabled');
      var paypalPanel = q('mn2-p2p-panel');
      var paypalSection = q('mn2-paypal-market-section');
      if (paypalOn) {
        if (disabled) disabled.style.display = 'none';
        if (paypalPanel) paypalPanel.style.display = '';
        if (paypalSection) paypalSection.style.display = '';
      } else {
        if (paypalPanel) paypalPanel.style.display = 'none';
        if (paypalSection) paypalSection.style.display = 'none';
      }
    }).catch(function () {
      var paypalPanel = q('mn2-p2p-panel');
      var paypalSection = q('mn2-paypal-market-section');
      if (paypalPanel) paypalPanel.style.display = 'none';
      if (paypalSection) paypalSection.style.display = 'none';
    });
    if (window.MN2InternalMarket && window.MN2InternalMarket.refresh) {
      window.MN2InternalMarket.refresh();
    }
  }

  initTabs();
})();
