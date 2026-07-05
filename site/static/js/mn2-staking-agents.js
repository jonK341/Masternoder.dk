/*
 * Trader staking agents panel — follow trader agents for mirrored stake + reward share.
 */
(function () {
  'use strict';

  var card = document.getElementById('profile-trader-staking-card');
  if (!card) return;

  function uid() {
    try { return localStorage.getItem('game_user_id') || 'default_user'; }
    catch (e) { return 'default_user'; }
  }

  function q(id) { return document.getElementById(id); }
  function fmt(n, d) { return Number(n || 0).toFixed(d == null ? 2 : d); }

  function api(path) {
    var sep = path.indexOf('?') === -1 ? '?' : '&';
    return fetch(path + sep + 'user_id=' + encodeURIComponent(uid()), { credentials: 'same-origin' })
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
    var el = q('trader-staking-msg');
    if (!el) return;
    el.textContent = text || '';
    el.style.color = ok ? '#00ff88' : '#ffaa44';
    if (text) setTimeout(function () { if (el.textContent === text) el.textContent = ''; }, 7000);
  }

  function renderAgents(agents) {
    var list = q('trader-staking-agents-list');
    if (!list) return;
    if (!agents || !agents.length) {
      list.innerHTML = '<p style="opacity:0.75;font-size:0.85rem;">No trader staking agents configured yet.</p>';
      return;
    }
    var html = agents.map(function (a) {
      var pct = a.target_staked_mn2 > 0 ? Math.min(100, (a.staked_mn2 / a.target_staked_mn2) * 100) : 0;
      return '<div style="padding:10px;margin-bottom:8px;border-radius:10px;background:rgba(0,0,0,0.25);border:1px solid rgba(0,212,255,0.2);">' +
        '<div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;">' +
        '<strong style="color:#00d4ff;">' + (a.label || a.agent_id) + '</strong>' +
        '<span style="font-size:0.8rem;opacity:0.85;">' + fmt(a.staked_mn2) + ' / ' + fmt(a.target_staked_mn2) + ' MN2 staked</span>' +
        '</div>' +
        '<div style="margin-top:6px;height:6px;border-radius:4px;background:rgba(255,255,255,0.08);overflow:hidden;">' +
        '<div style="height:100%;width:' + pct.toFixed(1) + '%;background:linear-gradient(90deg,#00ff88,#00d4ff);"></div></div>' +
        '<div style="margin-top:6px;font-size:0.75rem;opacity:0.8;">Rewards earned: ' + fmt(a.total_rewards_mn2, 4) + ' MN2</div>' +
        '</div>';
    }).join('');
    list.innerHTML = html;
  }

  function renderFollower(data) {
    var box = q('trader-staking-follower');
    var sel = q('trader-staking-leader');
    if (!box || !sel) return;

    var ct = data.copy_trading || {};
    var follower = data.follower || {};
    var following = follower.following && follower.follower;

    sel.innerHTML = (data.trader_agents || []).map(function (a) {
      var selected = following && follower.follower.leader_agent_id === a.agent_id ? ' selected' : '';
      return '<option value="' + a.agent_id + '"' + selected + '>' + (a.label || a.agent_id) + '</option>';
    }).join('');

    var scaleEl = q('trader-staking-scale');
    var capEl = q('trader-staking-cap');
    if (scaleEl && !scaleEl.dataset.touched) {
      scaleEl.value = following ? follower.follower.scale : (ct.default_scale || 0.25);
    }
    if (capEl && !capEl.dataset.touched) {
      capEl.value = following ? follower.follower.max_mn2_per_step : (ct.default_max_mn2_per_step || 25);
    }

    if (following) {
      box.innerHTML = '<p style="font-size:0.85rem;margin:0 0 8px;color:#00ff88;">Following <strong>' +
        follower.follower.leader_agent_id + '</strong> at scale ' + fmt(follower.follower.scale, 2) +
        ' (max ' + fmt(follower.follower.max_mn2_per_step, 2) + ' MN2 per mirror step).</p>' +
        '<p style="font-size:0.78rem;opacity:0.8;margin:0;">Stake mirrors and reward share apply when the agent stakes or earns.</p>';
      var unfBtn = q('trader-staking-unfollow-btn');
      var folBtn = q('trader-staking-follow-btn');
      if (unfBtn) unfBtn.style.display = 'inline-block';
      if (folBtn) folBtn.textContent = 'Update follow';
    } else {
      box.innerHTML = '<p style="font-size:0.85rem;margin:0;opacity:0.85;">Pick a trader agent to mirror stakes and earn a proportional reward share.</p>';
      var unfBtn2 = q('trader-staking-unfollow-btn');
      if (unfBtn2) unfBtn2.style.display = 'none';
      var folBtn2 = q('trader-staking-follow-btn');
      if (folBtn2) folBtn2.textContent = 'Follow agent';
    }
  }

  function refresh() {
    return api('/api/agents/trader-staking/status').then(function (data) {
      if (!data || !data.success) {
        msg((data && data.error) || 'Could not load trader agents', false);
        return;
      }
      var pool = q('trader-staking-pool-total');
      if (pool) pool.textContent = fmt(data.pool_staked_by_traders_mn2);
      renderAgents(data.trader_agents || []);
      renderFollower(data);
    }).catch(function () { msg('Network error loading trader agents', false); });
  }

  function follow() {
    var leader = (q('trader-staking-leader') || {}).value;
    var scale = parseFloat((q('trader-staking-scale') || {}).value || '0.25');
    var cap = parseFloat((q('trader-staking-cap') || {}).value || '25');
    if (!leader) { msg('Select an agent', false); return; }
    post('/api/mn2/copy-trading/follow', {
      leader_agent_id: leader,
      scale: scale,
      max_mn2_per_step: cap,
      enabled: true
    }).then(function (r) {
      if (r && r.success) {
        msg('Following ' + leader, true);
        refresh();
      } else {
        msg((r && r.error) || 'Follow failed', false);
      }
    }).catch(function () { msg('Follow request failed', false); });
  }

  function unfollow() {
    post('/api/mn2/copy-trading/unfollow', {}).then(function (r) {
      if (r && r.success) {
        msg('Unfollowed trader agent', true);
        refresh();
      } else {
        msg((r && r.error) || 'Unfollow failed', false);
      }
    }).catch(function () { msg('Unfollow request failed', false); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var scaleEl = q('trader-staking-scale');
    var capEl = q('trader-staking-cap');
    if (scaleEl) scaleEl.addEventListener('input', function () { scaleEl.dataset.touched = '1'; });
    if (capEl) capEl.addEventListener('input', function () { capEl.dataset.touched = '1'; });
    var folBtn = q('trader-staking-follow-btn');
    var unfBtn = q('trader-staking-unfollow-btn');
    if (folBtn) folBtn.addEventListener('click', follow);
    if (unfBtn) unfBtn.addEventListener('click', unfollow);
    refresh();
    setInterval(refresh, 60000);
  });
})();
