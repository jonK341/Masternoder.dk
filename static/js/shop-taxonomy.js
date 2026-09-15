/**
 * Shared shop taxonomy — catalog parents + inventory/auction subcategories.
 */
(function (global) {
  'use strict';

  var CATALOG_PARENTS = [
    { id: 'all', label: 'All', categories: [] },
    { id: 'play', label: 'Play', categories: ['battle', 'boosts', 'starmap25', 'trophies', 'achievement', 'skill'] },
    { id: 'look', label: 'Look', categories: ['themes', 'cosmetic', 'stories'] },
    { id: 'build', label: 'Build', categories: ['tech', 'upgrades', 'lab', 'generation', 'progression'] },
    { id: 'wallet', label: 'Wallet', categories: ['currency', 'buy_coins', 'unified_points', 'mn2_services', 'mn2_crypto'] },
    { id: 'collect', label: 'Collect', categories: ['top25', 'exclusive', 'premium', 'bundles', 'digital_goods'] },
    { id: 'ops', label: 'Ops & packs', categories: ['inventory', 'marketing', 'social'] },
  ];

  var INVENTORY_SUBCATS = [
    { id: 'all', label: 'All' },
    { id: 'stacks', label: 'Super stacks' },
    { id: 'kits', label: 'Kits & tools' },
    { id: 'maps', label: 'Star maps' },
    { id: 'lab', label: 'Lab' },
    { id: 'media', label: 'Media' },
    { id: 'knowledge', label: 'Knowledge' },
    { id: 'boosts', label: 'Boosts' },
    { id: 'look', label: 'Cosmetics' },
    { id: 'battle', label: 'Battle' },
    { id: 'collect', label: 'Collectibles' },
    { id: 'wallet', label: 'Wallet' },
    { id: 'hosting', label: 'Hosting' },
    { id: 'other', label: 'Other' },
  ];

  var PARENT_BY_CAT = {};
  CATALOG_PARENTS.forEach(function (p) {
    (p.categories || []).forEach(function (c) {
      PARENT_BY_CAT[c] = p.id;
    });
  });

  function parentForCategory(category) {
    var cat = String(category || 'other').toLowerCase();
    return PARENT_BY_CAT[cat] || (cat === 'inventory' ? 'ops' : 'other');
  }

  function subcategoryFor(itemId, name, category) {
    var cat = String(category || '').toLowerCase();
    var blob = (String(itemId || '') + ' ' + String(name || '') + ' ' + cat).toLowerCase();
    if (
      (cat === 'themes' || cat === 'cosmetic' || cat === 'stories' ||
        /theme|cosmetic|avatar|skin|banner/.test(blob)) &&
      cat !== 'boosts' &&
      cat !== 'battle'
    ) {
      return 'look';
    }
    if (
      (cat === 'top25' || cat === 'exclusive' || cat === 'premium' || cat === 'bundles' ||
        cat === 'digital_goods' || /legend|top25|bundle|exclusive/.test(blob)) &&
      blob.indexOf('booster') === -1
    ) {
      return 'collect';
    }
    if (blob.indexOf('masternode') !== -1 || (cat === 'mn2_services' && blob.indexOf('host') !== -1)) {
      return 'hosting';
    }
    if (
      (cat === 'currency' || cat === 'buy_coins' || cat === 'unified_points' ||
        cat === 'mn2_services' || cat === 'mn2_crypto' || blob.indexOf('mn2') !== -1) &&
      cat !== 'boosts' &&
      cat !== 'battle'
    ) {
      return 'wallet';
    }
    if (cat === 'boosts' || blob.indexOf('booster') !== -1 || blob.indexOf('game time') !== -1) return 'boosts';
    if (cat === 'battle' || blob.indexOf('battle') !== -1) return 'battle';
    if (/star map|starmap|star-map/.test(blob)) return 'maps';
    if (blob.indexOf('lab') !== -1) return 'lab';
    if (/clip|video|3d monitor|flyer/.test(blob)) return 'media';
    if (/rulebook|knowledge|psych|theory|framing|influence/.test(blob)) return 'knowledge';
    if (/super stack|super-stack| pack t|engine pack| ops pack|vault stack/.test(blob)) return 'stacks';
    if (/kit|verification|dna|magnet|tracker|geo|aggregator/.test(blob)) return 'kits';
    if (cat === 'inventory') return blob.indexOf('pack') !== -1 ? 'stacks' : 'kits';
    return 'other';
  }

  function classify(item) {
    item = item || {};
    var iid = item.item_id || item.id || '';
    var name = item.item_name || item.name || '';
    var cat = String(item.category || 'other').toLowerCase() || 'other';
    return {
      category: cat,
      parent: parentForCategory(cat),
      subcategory: item.subcategory || subcategoryFor(iid, name, cat),
    };
  }

  function enrich(item) {
    var row = Object.assign({}, item || {});
    var c = classify(row);
    row.category = c.category;
    row.parent = c.parent;
    row.subcategory = c.subcategory;
    return row;
  }

  function renderChips(nav, tabs, activeId, onPick) {
    if (!nav) return;
    nav.innerHTML = (tabs || [])
      .map(function (t) {
        var on = t.id === activeId;
        var count = t.count != null ? ' (' + t.count + ')' : '';
        return (
          '<button type="button" class="shop-subnav-btn' +
          (on ? ' active' : '') +
          '" data-tax-id="' +
          t.id +
          '" role="tab" aria-selected="' +
          (on ? 'true' : 'false') +
          '">' +
          t.label +
          count +
          '</button>'
        );
      })
      .join('');
    nav.querySelectorAll('[data-tax-id]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (typeof onPick === 'function') onPick(btn.getAttribute('data-tax-id'));
      });
    });
  }

  function subcatLabel(id) {
    var hit = INVENTORY_SUBCATS.find(function (s) {
      return s.id === id;
    });
    return hit ? hit.label : id;
  }

  function formatOrderAmount(row) {
    row = row || {};
    var source = row.source || '';
    if (source === 'masternode_hosting' || row.price_type === 'paypal_mn2_hosting') {
      var usd = row.usd_total != null ? Number(row.usd_total) : null;
      if (usd == null && row.price_paid_points && row.price_paid_points.usd != null) {
        usd = Number(row.price_paid_points.usd);
      }
      var method = row.payment_method || row.price_type || '';
      if (method === 'credits' && row.coins_total) return Number(row.coins_total) + ' coins';
      if ((method === 'mn2' || method === 'mn2_onchain') && row.mn2_total) {
        return Number(row.mn2_total).toFixed(4) + ' MN2' + (method === 'mn2_onchain' ? ' (on-chain)' : '');
      }
      if (usd != null && !isNaN(usd) && usd > 0) return '$' + usd.toFixed(2);
    }
    if (row.price_type === 'coins') return (row.price_paid_coins || 0) + ' coins';
    if (row.price_type === 'mn2' || row.price_type === 'mn2_onchain') {
      var mn2Paid = row.price_paid_points && typeof row.price_paid_points === 'object' && row.price_paid_points.mn2 != null
        ? row.price_paid_points.mn2
        : (row.mn2_total || row.price_paid_points || '');
      return (typeof mn2Paid === 'number' ? mn2Paid.toFixed(4) : mn2Paid) + ' MN2' +
        (row.price_type === 'mn2_onchain' ? ' (on-chain)' : '');
    }
    if (row.amount_label) return String(row.amount_label);
    if (row.price_paid_points) return 'points';
    return '—';
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (ch) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
    });
  }

  function renderOrderList(el, orders, opts) {
    if (!el) return;
    opts = opts || {};
    var activeId = opts.activeId || 'all';
    var classified = (orders || []).map(enrich);
    var rows = activeId === 'all' ? classified : classified.filter(function (r) {
      return r.subcategory === activeId;
    });
    if (opts.nav) {
      var counts = {};
      classified.forEach(function (r) {
        var key = r.subcategory || 'other';
        counts[key] = (counts[key] || 0) + 1;
      });
      var tabs = [{ id: 'all', label: 'All', count: classified.length }].concat(
        INVENTORY_SUBCATS.filter(function (s) { return s.id !== 'all' && counts[s.id]; })
          .map(function (s) { return { id: s.id, label: s.label, count: counts[s.id] }; })
      );
      renderChips(opts.nav, tabs, activeId, opts.onPick);
    }
    if (!classified.length) {
      el.innerHTML = '<p style="margin:0;">No orders yet.</p>';
      return classified;
    }
    if (!rows.length) {
      el.innerHTML = '<p style="margin:0;">No orders in this subcategory.</p>';
      return classified;
    }
    var groups = {};
    rows.forEach(function (p) {
      var key = p.subcategory || 'other';
      (groups[key] = groups[key] || []).push(p);
    });
    el.innerHTML = Object.keys(groups).map(function (key) {
      var label = subcatLabel(key);
      var body = groups[key].map(function (p) {
        var dateRaw = p.paid_at || p.created_at || '';
        var date = '';
        try { date = dateRaw ? new Date(dateRaw).toLocaleString() : ''; } catch (e) { date = String(dateRaw || ''); }
        var oid = p.order_id || p.id || '';
        var tx = p.txid ? String(p.txid) : '';
        if (tx.length > 18) tx = tx.slice(0, 10) + '…' + tx.slice(-6);
        return '<tr>' +
          '<td>' + escapeHtml(date) + '</td>' +
          '<td><code>' + escapeHtml(String(oid)) + '</code></td>' +
          '<td>' + escapeHtml(p.item_name || p.item_id || 'Order') +
            (p.source === 'masternode_hosting' ? ' <span style="opacity:0.7;font-size:0.78rem;">hosting</span>' : '') +
          '</td>' +
          '<td>' + escapeHtml(p.status || p.purchase_status || '') + '</td>' +
          '<td>' + escapeHtml(formatOrderAmount(p)) + '</td>' +
          '<td>' + (tx ? '<code title="' + escapeHtml(p.txid) + '">' + escapeHtml(tx) + '</code>' : '—') + '</td>' +
        '</tr>';
      }).join('');
      return '<h4 style="margin:14px 0 6px;color:var(--secondary,#00d4ff);font-size:0.92rem;">' + escapeHtml(label) + '</h4>' +
        '<div style="overflow-x:auto;"><table class="shop-order-table">' +
        '<thead><tr><th>Date</th><th>Id</th><th>Item</th><th>Status</th><th>Amount</th><th>Tx / ref</th></tr></thead>' +
        '<tbody>' + body + '</tbody></table></div>';
    }).join('');
    return classified;
  }

  global.ShopTaxonomy = {
    CATALOG_PARENTS: CATALOG_PARENTS,
    INVENTORY_SUBCATS: INVENTORY_SUBCATS,
    parentForCategory: parentForCategory,
    subcategoryFor: subcategoryFor,
    classify: classify,
    enrich: enrich,
    renderChips: renderChips,
    subcatLabel: subcatLabel,
    formatOrderAmount: formatOrderAmount,
    renderOrderList: renderOrderList,
  };
})(typeof window !== 'undefined' ? window : globalThis);
