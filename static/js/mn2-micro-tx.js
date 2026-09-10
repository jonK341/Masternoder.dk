/**
 * MN2 instant micro-reward client helper.
 * Prefer server-side instant_payout() for shop/casino/quest; this exposes stats + balance refresh.
 */
(function (global) {
  'use strict';

  async function fetchJson(url, opts) {
    const r = await fetch(url, opts);
    return r.json();
  }

  async function getConfig() {
    return fetchJson('/api/mn2/micro-tx/config');
  }

  async function getStats(userId) {
    const q = userId ? '?user_id=' + encodeURIComponent(userId) : '';
    return fetchJson('/api/mn2/micro-tx/stats' + q);
  }

  async function refreshBalance() {
    const bal = await fetchJson('/api/mn2/balance');
    if (bal && bal.success && global.dispatchEvent) {
      global.dispatchEvent(new CustomEvent('mn2-balance-updated', { detail: bal }));
    }
    return bal;
  }

  /**
   * Request payout via API (requires callback/ops token on server — use from trusted backend proxy).
   * For browser-only flows, call your own backend route that wraps instant_payout().
   */
  async function payout(body, token) {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['X-MN2-Callback-Token'] = token;
    const result = await fetchJson('/api/mn2/micro-tx/payout', {
      method: 'POST',
      headers,
      body: JSON.stringify(body || {}),
    });
    if (result && result.success) {
      await refreshBalance();
    }
    return result;
  }

  async function claimDaily(userId) {
    const body = userId ? { user_id: userId } : {};
    const uid = userId || localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || '';
    if (uid && uid !== 'default_user') body.user_id = uid;
    const result = await fetchJson('/api/mn2/micro-tx/claim-daily', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (result && result.success && !result.already_claimed) {
      await refreshBalance();
    }
    return result;
  }

  function wireDailyClaimButton(btnId) {
    const btn = document.getElementById(btnId || 'fp-claim-daily-btn');
    if (!btn) return;
    const uid = localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || '';
    if (!uid || uid === 'default_user') {
      btn.hidden = true;
      return;
    }
    btn.hidden = false;
    btn.addEventListener('click', async function () {
      btn.disabled = true;
      try {
        const r = await claimDaily(uid);
        if (r && r.success) {
          if (r.already_claimed) {
            btn.textContent = '✓ Daily claimed';
          } else {
            const amt = (r.micro_tx_reward && r.micro_tx_reward.amount_mn2) || '';
            btn.textContent = amt ? ('✓ +' + amt + ' MN2') : '✓ Claimed!';
          }
        } else {
          btn.textContent = r && r.error ? r.error.slice(0, 40) : 'Try again';
          btn.disabled = false;
        }
      } catch (e) {
        btn.disabled = false;
      }
    });
  }

  global.MN2MicroTx = {
    getConfig,
    getStats,
    refreshBalance,
    payout,
    claimDaily,
    wireDailyClaimButton,
  };
})(typeof window !== 'undefined' ? window : globalThis);
