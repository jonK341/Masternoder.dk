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

  global.ShopTaxonomy = {
    CATALOG_PARENTS: CATALOG_PARENTS,
    INVENTORY_SUBCATS: INVENTORY_SUBCATS,
    parentForCategory: parentForCategory,
    subcategoryFor: subcategoryFor,
    classify: classify,
    enrich: enrich,
    renderChips: renderChips,
    subcatLabel: subcatLabel,
  };
})(window);
