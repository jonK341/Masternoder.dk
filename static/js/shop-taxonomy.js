/**
 * Shared shop taxonomy — catalog parents + inventory/auction/special subcategories.
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

  var SPECIAL_GROUPS = {
    coin_packs: [
      { id: 'all', label: 'All packs' },
      { id: 'starter', label: 'Starter' },
      { id: 'value', label: 'Best value' },
      { id: 'whale', label: 'Whale' },
    ],
    mn2_services: [
      { id: 'all', label: 'All services' },
      { id: 'hosting', label: 'Hosting' },
      { id: 'wallet', label: 'Wallet & on-ramp' },
      { id: 'staking', label: 'Staking' },
      { id: 'market', label: 'Markets' },
      { id: 'reports', label: 'Reports' },
    ],
    boosters: [
      { id: 'all', label: 'All' },
      { id: 'resources', label: 'Battle resources' },
      { id: 'boosts', label: 'XP & boosts' },
      { id: 'gametime', label: 'Game time' },
      { id: 'battle', label: 'Battle power' },
    ],
    mystery_boxes: [
      { id: 'all', label: 'All boxes' },
      { id: 'common', label: 'Bronze' },
      { id: 'rare', label: 'Silver' },
      { id: 'legendary', label: 'Gold' },
    ],
  };

  var TX_SUBCATS = [
    { id: 'all', label: 'All' },
    { id: 'deposit', label: 'Deposits' },
    { id: 'withdraw', label: 'Withdrawals' },
    { id: 'spend', label: 'Shop spend' },
    { id: 'reward', label: 'Rewards' },
    { id: 'other', label: 'Other' },
  ];

  var CASINO_PARENTS = [
    { id: 'all', label: 'All', categories: [] },
    { id: 'look', label: 'Look', categories: ['avatar', 'table_skin', 'card_back', 'slot_theme', 'display', 'banner'] },
    { id: 'play', label: 'Play', categories: ['booster', 'token', 'emote', 'celebration'] },
    { id: 'vip', label: 'VIP', categories: ['vip_flair'] },
  ];

  var EXCHANGE_PARENTS = [
    { id: 'all', label: 'All', categories: [] },
    { id: 'play', label: 'Play', categories: ['skill', 'boost', 'reward'] },
    { id: 'rent', label: 'Rent', categories: ['rental', 'rental_voucher'] },
    { id: 'ops', label: 'Ops', categories: ['trust', 'fee', 'tool'] },
  ];

  var PROFILE_HUB_PARENTS = [
    { id: 'all', label: 'All', routes: [] },
    { id: 'you', label: 'You', routes: ['overview', 'avatar', 'account', 'settings'] },
    { id: 'play', label: 'Play', routes: ['skills', 'trophies', 'points', 'battle', 'progress'] },
    { id: 'market', label: 'Shop & wallet', routes: ['shop', 'wallet'] },
    { id: 'ops', label: 'Ops', routes: ['security', 'agents', 'activity', 'lab', 'leaderboard'] },
  ];

  var NAV_GROUPS = [
    { id: 'all', label: 'All', ids: [] },
    { id: 'play', label: 'Play', ids: ['game', 'battle', 'trophies', 'quests', 'casino', 'battlegrounds', 'starmap25'] },
    { id: 'create', label: 'Create', ids: ['generator', 'podcast', 'gallery', 'lab', 'library'] },
    { id: 'market', label: 'Market', ids: ['shop', 'exchange', 'market', 'wallets', 'explorer', 'staking_leaderboard', 'staking_teams'] },
    { id: 'people', label: 'People', ids: ['profile', 'agents', 'social', 'chat', 'customers', 'camgirls'] },
    { id: 'ops', label: 'Ops', ids: ['agent_support', 'debugger', 'aggregator', 'agents_control', 'hosting', 'profit', 'news'] },
  ];

  var PARENT_BY_CAT = {};
  CATALOG_PARENTS.forEach(function (p) {
    (p.categories || []).forEach(function (c) {
      PARENT_BY_CAT[c] = p.id;
    });
  });

  var CASINO_BY_CAT = {};
  CASINO_PARENTS.forEach(function (p) {
    (p.categories || []).forEach(function (c) {
      CASINO_BY_CAT[c] = p.id;
    });
  });

  var EXCHANGE_BY_CAT = {};
  EXCHANGE_PARENTS.forEach(function (p) {
    (p.categories || []).forEach(function (c) {
      EXCHANGE_BY_CAT[c] = p.id;
    });
  });

  var PROFILE_BY_ROUTE = {};
  PROFILE_HUB_PARENTS.forEach(function (p) {
    (p.routes || []).forEach(function (r) {
      PROFILE_BY_ROUTE[r] = p.id;
    });
  });

  var NAV_BY_ID = {};
  NAV_GROUPS.forEach(function (p) {
    (p.ids || []).forEach(function (id) {
      NAV_BY_ID[id] = p.id;
    });
  });

  function parentForCategory(category) {
    var cat = String(category || 'other').toLowerCase();
    return PARENT_BY_CAT[cat] || (cat === 'inventory' ? 'ops' : 'other');
  }

  function casinoParentFor(category) {
    return CASINO_BY_CAT[String(category || '').toLowerCase()] || 'other';
  }

  function exchangeParentFor(category) {
    return EXCHANGE_BY_CAT[String(category || '').toLowerCase()] || 'other';
  }

  function profileHubParentFor(route) {
    return PROFILE_BY_ROUTE[String(route || '').toLowerCase()] || 'other';
  }

  function navGroupFor(linkId) {
    var id = String(linkId || '').toLowerCase();
    if (id === 'home') return 'all';
    return NAV_BY_ID[id] || 'ops';
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
    if (/kit|verification|dna|magnet|tracker|geo|aggregator|navigator/.test(blob)) return 'kits';
    if (cat === 'inventory') return blob.indexOf('pack') !== -1 ? 'stacks' : 'kits';
    return 'other';
  }

  function specialSubcategoryFor(table, row) {
    row = row || {};
    var kind = String(table || '').toLowerCase();
    var blob = [row.id, row.name, row.description, row.service_id, row.category, row.rarity, row.kind]
      .map(function (v) { return String(v || ''); })
      .join(' ')
      .toLowerCase();

    if (kind === 'coin_packs') {
      var coins = Number(row.coins_granted || 0);
      var price = Number(row.price_usd || 0);
      var featured = !!(row.featured || String(row.tag || '').toLowerCase() === 'featured');
      if (coins >= 1500 || price >= 9) return 'whale';
      if (featured || (coins >= 400 && coins < 1500) || (price >= 3 && price < 9)) return 'value';
      return 'starter';
    }
    if (kind === 'mn2_services') {
      if (/hosting|masternode/.test(blob)) return 'hosting';
      if (blob.indexOf('stak') !== -1) return 'staking';
      if (/p2p|trader|market/.test(blob)) return 'market';
      if (/onramp|on-ramp|wallet/.test(blob)) return 'wallet';
      if (/reserve|proof|report/.test(blob)) return 'reports';
      return 'wallet';
    }
    if (kind === 'boosters') {
      if (row.kind === 'resource' || blob.indexOf('resource') !== -1) return 'resources';
      if (/game time|gametime|weekend pass/.test(blob)) return 'gametime';
      if (blob.indexOf('battle') !== -1) return 'battle';
      return 'boosts';
    }
    if (kind === 'mystery_boxes') {
      var rarity = String(row.rarity || '').toLowerCase();
      if (rarity === 'common' || rarity === 'rare' || rarity === 'legendary') return rarity;
      if (/bronze|common/.test(blob)) return 'common';
      if (/silver|rare/.test(blob)) return 'rare';
      if (/gold|legend|whale/.test(blob)) return 'legendary';
      return 'common';
    }
    return 'other';
  }

  function txSubcategoryFor(txType) {
    var blob = String(txType || '').toLowerCase();
    if (/deposit|credit_in|onramp/.test(blob)) return 'deposit';
    if (/withdraw|payout/.test(blob)) return 'withdraw';
    if (/spend|purchase|shop|buy/.test(blob)) return 'spend';
    if (/reward|stake|interest|earn|airdrop/.test(blob)) return 'reward';
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

  function countedTabs(source, rows, keyFn) {
    var counts = {};
    (rows || []).forEach(function (row) {
      var id = keyFn(row) || 'other';
      counts[id] = (counts[id] || 0) + 1;
    });
    var tabs = [];
    (source || []).forEach(function (s) {
      if (s.id === 'all') {
        tabs.push({ id: 'all', label: s.label, count: (rows || []).length });
        return;
      }
      if (counts[s.id]) tabs.push({ id: s.id, label: s.label, count: counts[s.id] });
    });
    Object.keys(counts).forEach(function (id) {
      if (!tabs.some(function (t) { return t.id === id; })) {
        tabs.push({ id: id, label: subcatLabel(id), count: counts[id] });
      }
    });
    return tabs;
  }

  function subcatLabel(id) {
    var pools = INVENTORY_SUBCATS.concat(TX_SUBCATS);
    Object.keys(SPECIAL_GROUPS).forEach(function (k) {
      pools = pools.concat(SPECIAL_GROUPS[k]);
    });
    var hit = pools.find(function (s) {
      return s.id === id;
    });
    return hit ? hit.label : id;
  }

  global.ShopTaxonomy = {
    CATALOG_PARENTS: CATALOG_PARENTS,
    INVENTORY_SUBCATS: INVENTORY_SUBCATS,
    SPECIAL_GROUPS: SPECIAL_GROUPS,
    TX_SUBCATS: TX_SUBCATS,
    CASINO_PARENTS: CASINO_PARENTS,
    EXCHANGE_PARENTS: EXCHANGE_PARENTS,
    PROFILE_HUB_PARENTS: PROFILE_HUB_PARENTS,
    NAV_GROUPS: NAV_GROUPS,
    parentForCategory: parentForCategory,
    casinoParentFor: casinoParentFor,
    exchangeParentFor: exchangeParentFor,
    profileHubParentFor: profileHubParentFor,
    navGroupFor: navGroupFor,
    subcategoryFor: subcategoryFor,
    specialSubcategoryFor: specialSubcategoryFor,
    txSubcategoryFor: txSubcategoryFor,
    classify: classify,
    enrich: enrich,
    renderChips: renderChips,
    countedTabs: countedTabs,
    subcatLabel: subcatLabel,
  };
})(window);
