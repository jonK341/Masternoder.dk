/**
 * Exchange — profile, platform MN2, and custodial exchange wallet (same rails as Shop / Wallets).
 */
(function (global) {
  'use strict';

  var glanceInitialized = false;

  function q(id) {
    return global.document.getElementById(id);
  }

  function uid() {
    if (global.Mn2SiteBridge && global.Mn2SiteBridge.uid) {
      return global.Mn2SiteBridge.uid();
    }
    try {
      return (
        global.localStorage.getItem('game_user_id') ||
        global.localStorage.getItem('user_id') ||
        'default_user'
      );
    } catch (e) {
      return 'default_user';
    }
  }

  function fmtMn2(n) {
    if (global.Mn2SiteBridge && global.Mn2SiteBridge.fmtMn2) {
      return global.Mn2SiteBridge.fmtMn2(n);
    }
    var v = Number(n);
    if (!isFinite(v)) return '—';
    return v.toLocaleString(undefined, { maximumFractionDigits: 4 });
  }

  function fetchJson(path, opts) {
    if (global.ExchangeHub && global.ExchangeHub.fetchJson) {
      return global.ExchangeHub.fetchJson(path, opts || { timeout: 9000 });
    }
    return fetch(path, { credentials: 'same-origin' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function setText(id, text) {
    var el = q(id);
    if (el) el.textContent = text;
  }

  function pulseGlance() {
    var strip = q('cex-glance-stats');
    if (!strip) return;
    strip.classList.remove('cex-stats-pulse');
    void strip.offsetWidth;
    strip.classList.add('cex-stats-pulse');
  }

  function updateMn2Glow(balance) {
    var stat = q('cex-glance-mn2-stat');
    if (!stat) return;
    stat.classList.toggle('cex-glance-mn2-glow', isFinite(balance) && balance > 0);
  }

  function shortUid(id) {
    if (!id || id === 'default_user') return 'Guest · set up profile';
    return id.length > 20 ? id.slice(0, 8) + '…' + id.slice(-4) : id;
  }

  function renderProfileAggregated(data, userId) {
    var profile = (data && data.profile) || {};
    var prefs = profile.preferences || {};
    var pts =
      data && data.unified_points && data.unified_points.points
        ? data.unified_points.points
        : {};
    var display =
      prefs.display_name ||
      profile.display_name ||
      profile.username ||
      shortUid(userId);
    setText('cex-account-display', String(display).slice(0, 32));
    setText('cex-account-user-id', shortUid(userId));
    var pill = q('cex-hero-user-pill');
    if (pill) {
      pill.textContent =
        String(display).slice(0, 20) + (String(display).length > 20 ? '…' : '');
    }
    if (pts.coins != null) {
      setText('cex-account-coins', fmtNum(pts.coins));
      setText('cex-glance-coins', fmtNum(pts.coins));
    }
    if (pts.level != null) {
      setText('cex-account-level', String(pts.level));
      setText('cex-glance-level', String(pts.level));
    }
    try {
      if (display) global.localStorage.setItem('game_display_name', display);
    } catch (e) { /* ignore */ }
  }

  function fmtNum(n) {
    var x = Number(n);
    if (!isFinite(x)) return '—';
    if (x >= 10000) return Math.round(x).toLocaleString();
    if (Number.isInteger(x)) return String(x);
    return x.toFixed(x < 10 ? 2 : 1);
  }

  function renderMn2Balance(data, priceUsd) {
    var bal = NaN;
    if (data && data.success) {
      bal = Number(data.mn2_balance != null ? data.mn2_balance : data.balance);
    }
    var label = isFinite(bal) ? fmtMn2(bal) + ' MN2' : '—';
    setText('cex-account-mn2', label);
    setText('cex-glance-mn2', isFinite(bal) ? fmtMn2(bal) : '—');
    updateMn2Glow(bal);
    if (isFinite(priceUsd) && isFinite(bal)) {
      setText(
        'cex-account-mn2-usd',
        '≈ $' + (bal * priceUsd).toLocaleString(undefined, { maximumFractionDigits: 2 })
      );
    } else {
      setText('cex-account-mn2-usd', 'USD estimate unavailable');
    }
    var stripBal = q('cex-mn2-balance');
    if (stripBal && isFinite(bal) && (!stripBal.textContent || stripBal.textContent === '—')) {
      stripBal.textContent = fmtMn2(bal) + ' MN2';
    }
  }

  function renderExchangeWallet(data) {
    if (!data || !data.success) {
      setText('cex-account-exchange-assets', '—');
      return;
    }
    var assets = data.assets || {};
    var keys = Object.keys(assets).filter(function (k) {
      return Number(assets[k]) > 0;
    });
    setText('cex-glance-balances', String(keys.length));
    if (!keys.length) {
      setText('cex-account-exchange-assets', 'Empty — swap or PayPal buy');
      return;
    }
    var preview = keys
      .slice(0, 4)
      .map(function (k) {
        return k + ' ' + Number(assets[k]).toFixed(4);
      })
      .join(' · ');
    if (keys.length > 4) preview += ' +' + (keys.length - 4);
    setText('cex-account-exchange-assets', preview);
  }

  function refreshAccountBridge(opts) {
    opts = opts || {};
    var userId = uid();
    var u = encodeURIComponent(userId);
    var jobs = [
      fetchJson('/api/user/profile/' + u + '/aggregated').catch(function () {
        return fetchJson('/api/user/profile/' + u + '/display').catch(function () {
          return null;
        });
      }),
      global.Mn2SiteBridge
        ? global.Mn2SiteBridge.loadBalance().catch(function () {
            return null;
          })
        : fetchJson('/api/mn2/balance?user_id=' + u).catch(function () {
            return null;
          }),
      global.Mn2SiteBridge
        ? global.Mn2SiteBridge.loadPrice().catch(function () {
            return null;
          })
        : fetchJson('/api/mn2/price').catch(function () {
            return null;
          }),
      fetchJson('/api/exchange/wallet?user_id=' + u).catch(function () {
        return null;
      }),
      fetchJson('/api/exchange/rewards?user_id=' + u).catch(function () {
        return null;
      }),
      fetchJson('/api/exchange/health').catch(function () {
        return null;
      }),
      fetchJson('/api/exchange/catalog').catch(function () {
        return null;
      }),
    ];

    return Promise.all(jobs).then(function (res) {
      var profileData = res[0];
      var mn2Bal = res[1];
      var mn2Price = res[2];
      var exWallet = res[3];
      var rewards = res[4];
      var health = res[5];
      var catalog = res[6];

      if (profileData) {
        if (profileData.profile || profileData.unified_points) {
          renderProfileAggregated(profileData, userId);
        } else if (profileData.display_name) {
          setText('cex-account-display', profileData.display_name);
          var pill = q('cex-hero-user-pill');
          if (pill) pill.textContent = profileData.display_name;
        }
      } else {
        setText('cex-account-display', 'Guest trader');
        setText('cex-account-user-id', shortUid(userId));
      }

      var priceUsd = mn2Price && (mn2Price.price_usd != null ? mn2Price.price_usd : mn2Price.usd);
      renderMn2Balance(mn2Bal, Number(priceUsd));
      renderExchangeWallet(exWallet);

      if (rewards && rewards.success && rewards.tier) {
        setText('cex-glance-tier', rewards.tier.label || 'Bronze');
        var tierStrip = q('cex-fee-tier');
        if (tierStrip && tierStrip.textContent === '—') {
          tierStrip.textContent = rewards.tier.label || 'Bronze';
        }
      }
      if (health) {
        setText('cex-glance-agents', String(health.agent_count || 0));
        setText('cex-glance-kill', health.kill_switch ? 'ON' : 'Off');
      }
      if (catalog && catalog.success) {
        setText(
          'cex-glance-markets',
          String(catalog.asset_count || (catalog.assets && catalog.assets.length) || 25)
        );
      }

      var sync = q('cex-account-sync-status');
      if (sync) {
        sync.textContent =
          'Profile · MN2 · exchange wallet synced ' + new Date().toLocaleTimeString();
      }

      if (opts.animate !== false && glanceInitialized) pulseGlance();
      glanceInitialized = true;
    });
  }

  function onExchangeWallet(walletPayload) {
    renderExchangeWallet(walletPayload);
  }

  function initStripResync() {
    if (global.Mn2PageStripInit && global.Mn2PageStripInit.init) {
      global.Mn2PageStripInit.init();
    }
    global.setTimeout(function () {
      refreshAccountBridge({ animate: false });
    }, 2200);
  }

  global.CexAccountBridge = {
    refresh: refreshAccountBridge,
    onExchangeWallet: onExchangeWallet,
    uid: uid,
  };

  function init() {
    refreshAccountBridge({ animate: false });
    initStripResync();
    global.setInterval(function () {
      refreshAccountBridge({ animate: false });
    }, 120000);
  }

  if (global.document.readyState === 'loading') {
    global.document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(typeof window !== 'undefined' ? window : globalThis);
