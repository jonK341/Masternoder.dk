/*
 * MN2 staking wallet panel controller.
 * Wires the profile staking card to /api/mn2/staking/* and manages the browser rig worker.
 */
(function () {
  'use strict';

  var card = document.getElementById('profile-mn2-staking-card');
  if (!card) return;

  function uid() {
    try { return localStorage.getItem('game_user_id') || 'default_user'; }
    catch (e) { return 'default_user'; }
  }

  function q(id) { return document.getElementById(id); }
  function fmt(n, d) { return Number(n || 0).toFixed(d == null ? 4 : d); }

  function api(path, opts) {
    opts = opts || {};
    var sep = path.indexOf('?') === -1 ? '?' : '&';
    var url = path + sep + 'user_id=' + encodeURIComponent(uid());
    return fetch(url, Object.assign({ credentials: 'same-origin' }, opts))
      .then(function (r) { return r.json(); });
  }

  function post(path, body) {
    body = body || {};
    body.user_id = uid();
    return fetch(path, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }).then(function (r) { return r.json(); });
  }

  function msg(text, ok) {
    var el = q('mn2-staking-msg');
    if (!el) return;
    el.textContent = text || '';
    el.style.color = ok ? '#00ff88' : '#ffaa44';
    if (text) setTimeout(function () { if (el.textContent === text) el.textContent = ''; }, 6000);
  }

  // ---------------------------------------------------------------- worker

  var worker = null;
  var rigOn = false;
  var workerCfg = { difficulty: 16, intervalSec: 30 };

  function startRig() {
    if (rigOn) return;
    try {
      worker = new Worker('/static/js/mn2-staking-worker.js');
      worker.onmessage = function (e) {
        var d = e.data || {};
        if (d.type === 'proof' && d.payload) {
          post('/api/mn2/staking/work', d.payload).then(function (res) {
            if (res && res.uptime_ratio != null) {
              var u = q('mn2-staking-uptime'); if (u) u.textContent = Math.round(res.uptime_ratio * 100);
            }
          }).catch(function () {});
        }
      };
      worker.postMessage({ cmd: 'start', difficulty: workerCfg.difficulty, intervalSec: workerCfg.intervalSec });
      rigOn = true;
      updateRigUi();
    } catch (e) {
      msg('Staking rig unavailable in this browser', false);
    }
  }

  function stopRig() {
    if (worker) { try { worker.postMessage({ cmd: 'stop' }); worker.terminate(); } catch (e) {} }
    worker = null;
    rigOn = false;
    updateRigUi();
  }

  function updateRigUi() {
    var btn = q('mn2-staking-rig-toggle');
    var status = q('mn2-staking-rig-status');
    if (btn) btn.textContent = rigOn ? '■ Stop staking rig' : '▶ Start staking rig';
    if (status) { status.textContent = rigOn ? 'on' : 'off'; status.style.color = rigOn ? '#00ff88' : '#ffaa44'; }
  }

  // Pause rig when tab hidden to respect the user's CPU/battery.
  document.addEventListener('visibilitychange', function () {
    if (!worker) return;
    worker.postMessage({ cmd: document.hidden ? 'stop' : 'start', difficulty: workerCfg.difficulty, intervalSec: workerCfg.intervalSec });
  });

  // ----------------------------------------------------------- status render

  function renderStatus(s) {
    if (!s) return;
    q('mn2-staking-staked').textContent = fmt(s.staked);
    q('mn2-staking-balance').textContent = fmt(s.mn2_balance);
    q('mn2-staking-apr').textContent = fmt(s.effective_apr_percent, 2);
    q('mn2-staking-earned').textContent = fmt(s.total_earned);
    q('mn2-staking-tier').textContent = s.longevity_label || s.longevity_tier || '--';
    var prog = q('mn2-staking-tier-progress');
    if (prog) {
      prog.textContent = (s.days_to_next_tier != null && s.next_tier)
        ? (fmt(s.days_to_next_tier, 1) + 'd to ' + s.next_tier)
        : (fmt(s.longevity_days, 1) + ' days staked');
    }
    var ac = q('mn2-staking-autocompound');
    if (ac) ac.checked = !!s.auto_compound;
    var u = q('mn2-staking-uptime'); if (u) u.textContent = Math.round((s.uptime_ratio || 0) * 100);

    // Consent gate vs controls
    var consent = q('mn2-staking-consent');
    var controls = q('mn2-staking-controls');
    if (s.terms_accepted) {
      if (consent) consent.style.display = 'none';
      if (controls) controls.style.display = 'flex';
    } else {
      if (consent) consent.style.display = 'block';
      if (controls) controls.style.display = 'none';
    }
  }

  function refreshStatus() {
    return api('/api/mn2/staking/status').then(function (s) {
      if (s && s.success !== false) renderStatus(s);
    }).catch(function () {});
  }

  function refreshRewards() {
    return api('/api/mn2/staking/rewards-table&limit=25').then(function (res) {
      var el = q('mn2-staking-rewards-table');
      if (!el) return;
      if (!res || !res.rows || !res.rows.length) { el.textContent = 'No rewards yet.'; return; }
      var rows = res.rows.map(function (r) {
        return '<tr><td style="padding:2px 8px;">' + (r.accrued_at || '').slice(0, 16).replace('T', ' ') +
          '</td><td style="padding:2px 8px; color:#00ff88;">+' + fmt(r.reward_mn2, 6) +
          '</td><td style="padding:2px 8px;">' + fmt(r.staked, 2) +
          '</td><td style="padding:2px 8px;">' + fmt(r.effective_apr, 2) + '%</td></tr>';
      }).join('');
      el.innerHTML = '<table style="width:100%; border-collapse:collapse;"><thead><tr style="opacity:0.7;">' +
        '<th style="text-align:left; padding:2px 8px;">Time</th><th style="text-align:left; padding:2px 8px;">Reward</th>' +
        '<th style="text-align:left; padding:2px 8px;">Staked</th><th style="text-align:left; padding:2px 8px;">APR</th></tr></thead><tbody>' +
        rows + '</tbody></table>' +
        '<p style="opacity:0.7; margin-top:6px;">Total: ' + fmt(res.summary && res.summary.total_earned_mn2, 6) + ' MN2 over ' +
        (res.summary ? res.summary.intervals : 0) + ' intervals.</p>';
    }).catch(function () {});
  }

  // ----------------------------------------------------------- calculator

  function runCalc() {
    var amount = q('mn2-calc-amount').value || 0;
    var days = q('mn2-calc-days').value || 30;
    var uptime = (q('mn2-calc-uptime').value || 100) / 100;
    fetch('/api/mn2/staking/calculator?amount=' + amount + '&days=' + days + '&uptime=' + uptime, { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (c) {
        if (!c || !c.success) return;
        q('mn2-calc-result').textContent =
          '≈ ' + fmt(c.projected_reward_mn2, 6) + ' MN2 over ' + c.days + ' days at ' + fmt(c.apr_percent, 2) +
          '% APR (total ≈ ' + fmt(c.projected_total_mn2, 4) + ' MN2). Estimate only — not guaranteed.';
      }).catch(function () {});
  }

  // ----------------------------------------------------------- consent

  function loadTerms() {
    fetch('/api/mn2/staking/terms', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        var t = (res && res.terms) || {};
        var txt = q('mn2-staking-consent-text');
        if (txt) txt.textContent = t.summary || '';
        var st = q('mn2-staking-consent-statement');
        if (st) st.textContent = t.acceptance_statement || 'I accept the staking terms and risk disclosure.';
      }).catch(function () {});
  }

  // ----------------------------------------------------------- wire events

  function wire() {
    q('mn2-staking-stake-btn').addEventListener('click', function () {
      var amt = parseFloat(q('mn2-staking-amount').value);
      if (!amt || amt <= 0) { msg('Enter an amount', false); return; }
      post('/api/mn2/stake', { amount: amt }).then(function (res) {
        if (res && res.success) { msg('Staked ' + amt + ' MN2', true); renderStatus(res); refreshRewards(); }
        else { msg((res && res.error) || 'Stake failed', false); if (res && res.code === 'consent_required') refreshStatus(); }
      });
    });

    q('mn2-staking-unstake-btn').addEventListener('click', function () {
      var amt = parseFloat(q('mn2-staking-amount').value);
      if (!amt || amt <= 0) { msg('Enter an amount', false); return; }
      post('/api/mn2/unstake', { amount: amt }).then(function (res) {
        if (res && res.success) { msg('Unstaked ' + amt + ' MN2', true); renderStatus(res); }
        else { msg((res && res.error) || 'Unstake failed', false); }
      });
    });

    q('mn2-staking-autocompound').addEventListener('change', function (e) {
      post('/api/mn2/staking/auto-compound', { enabled: e.target.checked })
        .then(function (res) { msg(res && res.success ? 'Auto-compound ' + (e.target.checked ? 'on' : 'off') : 'Failed', !!(res && res.success)); });
    });

    q('mn2-staking-rig-toggle').addEventListener('click', function () {
      if (rigOn) stopRig(); else startRig();
    });

    var check = q('mn2-staking-consent-check');
    var accept = q('mn2-staking-consent-accept');
    if (check && accept) {
      check.addEventListener('change', function () { accept.disabled = !check.checked; });
      accept.addEventListener('click', function () {
        post('/api/mn2/staking/accept-terms', {}).then(function (res) {
          if (res && res.success) { msg('Terms accepted', true); refreshStatus(); }
          else { msg((res && res.error) || 'Could not accept', false); }
        });
      });
    }

    ['mn2-calc-amount', 'mn2-calc-days'].forEach(function (id) {
      var el = q(id); if (el) el.addEventListener('input', runCalc);
    });
    var up = q('mn2-calc-uptime');
    if (up) up.addEventListener('input', function () { q('mn2-calc-uptime-val').textContent = up.value; runCalc(); });

    var csv = q('mn2-staking-rewards-csv');
    if (csv) csv.href = '/api/mn2/staking/rewards-table?format=csv&user_id=' + encodeURIComponent(uid());
  }

  function init() {
    wire();
    loadTerms();
    refreshStatus();
    refreshRewards();
    runCalc();
    setInterval(refreshStatus, 30000);
  }

  window.MN2Staking = {
    refresh: function () { refreshStatus(); refreshRewards(); }
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
