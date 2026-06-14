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

  // ----------------------------------------------------------- charts (#2)

  // Prepare a canvas for crisp drawing at the element's CSS pixel size.
  function prepCanvas(canvas) {
    var dpr = window.devicePixelRatio || 1;
    var w = canvas.clientWidth || 320;
    var h = canvas.clientHeight || canvas.height || 150;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    var ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    return { ctx: ctx, w: w, h: h };
  }

  function niceMax(v) {
    if (!(v > 0)) return 1;
    var pow = Math.pow(10, Math.floor(Math.log10(v)));
    var n = v / pow;
    var step = n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10;
    return step * pow;
  }

  function drawLineSeries(canvas, seriesList, maxY) {
    var p = prepCanvas(canvas), ctx = p.ctx;
    var padL = 6, padR = 6, padT = 8, padB = 8;
    var plotW = p.w - padL - padR, plotH = p.h - padT - padB;
    // baseline
    ctx.strokeStyle = 'rgba(255,255,255,0.12)';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(padL, p.h - padB); ctx.lineTo(p.w - padR, p.h - padB); ctx.stroke();
    seriesList.forEach(function (s) {
      var pts = s.data;
      if (!pts.length) return;
      var n = pts.length;
      ctx.strokeStyle = s.color;
      ctx.lineWidth = s.width || 2;
      if (s.dashed) ctx.setLineDash([4, 4]); else ctx.setLineDash([]);
      ctx.beginPath();
      for (var i = 0; i < n; i++) {
        var x = padL + (n === 1 ? plotW / 2 : (plotW * i) / (n - 1));
        var y = padT + plotH - (maxY > 0 ? (plotH * pts[i]) / maxY : 0);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.stroke();
    });
    ctx.setLineDash([]);
  }

  function drawBars(canvas, values, color, maxY) {
    var p = prepCanvas(canvas), ctx = p.ctx;
    var padL = 6, padR = 6, padT = 8, padB = 8;
    var plotW = p.w - padL - padR, plotH = p.h - padT - padB;
    ctx.strokeStyle = 'rgba(255,255,255,0.12)';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(padL, p.h - padB); ctx.lineTo(p.w - padR, p.h - padB); ctx.stroke();
    var n = values.length;
    if (!n) return;
    var gap = n > 60 ? 0 : 1;
    var bw = Math.max(1, (plotW / n) - gap);
    ctx.fillStyle = color;
    for (var i = 0; i < n; i++) {
      var x = padL + (plotW * i) / n;
      var bh = maxY > 0 ? (plotH * values[i]) / maxY : 0;
      ctx.fillRect(x, padT + plotH - bh, bw, bh);
    }
  }

  var _lastRewardsRes = null;

  function renderCharts(res) {
    if (res) _lastRewardsRes = res; else res = _lastRewardsRes;
    var wrap = q('mn2-staking-charts');
    var empty = q('mn2-staking-charts-empty');
    var rows = (res && res.rows) || [];
    if (!wrap) return;
    if (!rows.length) {
      wrap.style.display = 'none';
      if (empty) empty.style.display = 'block';
      return;
    }
    if (empty) empty.style.display = 'none';
    wrap.style.display = 'block';

    // rows arrive newest-first; chart chronologically
    var chrono = rows.slice().reverse();
    var rewards = chrono.map(function (r) { return Number(r.reward_mn2 || 0); });
    var cumulative = [];
    var run = 0;
    rewards.forEach(function (v) { run += v; cumulative.push(run); });

    // Projected trend: straight line at the average per-interval reward.
    var total = cumulative.length ? cumulative[cumulative.length - 1] : 0;
    var avg = rewards.length ? total / rewards.length : 0;
    var projected = rewards.map(function (_, i) { return avg * (i + 1); });

    var cumMax = niceMax(Math.max(total, projected[projected.length - 1] || 0));
    drawLineSeries(q('mn2-chart-cumulative'), [
      { data: projected, color: 'rgba(0,212,255,0.55)', width: 1.5, dashed: true },
      { data: cumulative, color: '#00ff88', width: 2 }
    ], cumMax);

    var rMax = niceMax(Math.max.apply(null, rewards.concat([0])));
    drawBars(q('mn2-chart-intervals'), rewards, '#00d4ff', rMax);

    var legend = q('mn2-chart-legend');
    if (legend) {
      var avgApr = (res.summary && res.summary.avg_effective_apr) || 0;
      legend.innerHTML =
        '<span style="color:#00ff88;">\u25cf</span> actual cumulative &nbsp; ' +
        '<span style="color:#00d4ff;">\u254c</span> projected trend &nbsp;|&nbsp; ' +
        rewards.length + ' intervals \u00b7 total ' + fmt(total, 6) + ' MN2 \u00b7 avg/interval ' + fmt(avg, 6) +
        ' MN2 \u00b7 avg APR ' + fmt(avgApr, 2) + '%';
    }
  }

  function refreshRewards() {
    return api('/api/mn2/staking/rewards-table?limit=200').then(function (res) {
      renderCharts(res);
      var el = q('mn2-staking-rewards-table');
      if (!el) return;
      if (!res || !res.rows || !res.rows.length) { el.textContent = 'No rewards yet.'; return; }
      var rows = res.rows.slice(0, 25).map(function (r) {
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
    hookOpsKillSwitch();
    var rzT;
    window.addEventListener('resize', function () {
      clearTimeout(rzT);
      rzT = setTimeout(function () { if (_lastRewardsRes) renderCharts(null); }, 200);
    });
  }

  window.MN2Staking = {
    refresh: function () { refreshStatus(); refreshRewards(); }
  };

  function hookOpsKillSwitch() {
    var bannerId = 'mn2-staking-halt-banner';
    function showHalt(on) {
      var el = q(bannerId);
      if (!el && on) {
        el = document.createElement('div');
        el.id = bannerId;
        el.style.cssText = 'margin:10px 0;padding:10px 14px;border-radius:8px;background:rgba(255,80,80,0.15);border-left:4px solid #ff6666;font-size:0.9em;';
        card.insertBefore(el, card.firstChild);
      }
      if (el) {
        el.textContent = on ? 'Agent automation is halted by ops — staking actions may be blocked.' : '';
        el.style.display = on ? 'block' : 'none';
      }
    }
    function applyKs(data) {
      if (data && data.agent_kill_switch) {
        showHalt(!!data.agent_kill_switch.global_halt);
      }
    }
    fetch('/api/ops/snapshot', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (j) { if (j.success) applyKs(j); })
      .catch(function () {});
    if (typeof EventSource !== 'undefined') {
      try {
        var es = new EventSource('/api/ops/stream?interval=30');
        es.onmessage = function (ev) {
          try {
            var d = JSON.parse(ev.data);
            if (d.type === 'ops') applyKs(d);
          } catch (e) { /* ignore */ }
        };
        es.onerror = function () { if (es) es.close(); };
      } catch (e) { /* ignore */ }
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
