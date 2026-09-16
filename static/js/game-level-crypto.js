/**
 * Hunter level MN2 milestone rewards UI (Rewards / Earn tab).
 */
(function (global) {
  'use strict';

  function uid() {
    return localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function fmtMn2(n) {
    return (parseFloat(n) || 0).toFixed(8);
  }

  function render(data) {
    var host = document.getElementById('game-level-crypto-grid');
    var summary = document.getElementById('game-level-crypto-summary');
    if (!host) return;
    if (summary) {
      summary.textContent =
        'Level ' +
        (data.current_level || 1) +
        ' · ' +
        (data.claimable_count || 0) +
        ' ready to claim · Balance ' +
        fmtMn2(data.mn2_balance) +
        ' MN2';
    }
    var levels = data.levels || [];
    if (!levels.length) {
      host.innerHTML = '<p class="game-level-crypto-meta">No level rewards configured.</p>';
      return;
    }
    host.innerHTML = levels
      .map(function (row) {
        var cls = row.claimed ? 'claimed' : row.ready ? 'ready' : row.unlocked ? '' : 'locked';
        var state = row.claimed ? 'Claimed ✓' : row.ready ? 'Ready' : row.unlocked ? 'Unclaimed' : 'Lv ' + row.level;
        var btn =
          row.ready
            ? '<button type="button" class="game-level-claim" data-level="' + row.level + '">Claim</button>'
            : '<span class="lvl-state">' + esc(state) + '</span>';
        return (
          '<article class="game-level-crypto-card ' +
          cls +
          '">' +
          '<strong>Lv ' +
          row.level +
          '</strong>' +
          '<span class="lvl-mn2">+' +
          fmtMn2(row.reward_mn2) +
          ' MN2</span>' +
          '<div style="font-size:0.72rem;color:rgba(255,255,255,0.55);margin-bottom:6px;">' +
          esc(row.label || '') +
          '</div>' +
          btn +
          '</article>'
        );
      })
      .join('');

    host.querySelectorAll('.game-level-claim').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var level = parseInt(btn.getAttribute('data-level'), 10);
        if (!level) return;
        btn.disabled = true;
        btn.textContent = '…';
        fetch('/api/game/crypto/level-rewards/claim', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: uid(), level: level }),
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (d) {
            if (d.success && d.level_rewards) {
              render(d.level_rewards);
              if (global.GameTabulator && global.GameTabulator.refreshClaimable) {
                global.GameTabulator.refreshClaimable();
              }
              if (typeof global.loadCryptoExperience === 'function') {
                global.loadCryptoExperience().catch(function () {});
              }
            } else {
              btn.disabled = false;
              btn.textContent = d.error || 'Retry';
            }
          })
          .catch(function () {
            btn.disabled = false;
            btn.textContent = 'Retry';
          });
      });
    });
  }

  function load() {
    var host = document.getElementById('game-level-crypto-grid');
    if (!host) return Promise.resolve();
    host.innerHTML = '<p class="game-level-crypto-meta">Loading level MN2 rewards…</p>';
    return fetch('/api/game/crypto/level-rewards?user_id=' + encodeURIComponent(uid()))
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (d && d.levels) render(d);
        else host.innerHTML = '<p class="game-level-crypto-meta">Could not load level rewards.</p>';
      })
      .catch(function () {
        host.innerHTML = '<p class="game-level-crypto-meta">Level rewards unavailable.</p>';
      });
  }

  global.GameLevelCrypto = { load: load, render: render };

  document.addEventListener('DOMContentLoaded', function () {
    var rewardsTab = document.querySelector('.game-tab[data-tab="rewards"]');
    if (rewardsTab && rewardsTab.classList.contains('active')) load();
  });
})(window);
