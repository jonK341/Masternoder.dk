/* Owner-only Business Control board. All data + controls are admin-key gated. */
(function () {
  "use strict";

  var KEY_STORE = "mn_exchange_admin_key";
  var $ = function (id) { return document.getElementById(id); };

  function getKey() { return sessionStorage.getItem(KEY_STORE) || ""; }
  function setKey(k) { sessionStorage.setItem(KEY_STORE, k); }
  function clearKey() { sessionStorage.removeItem(KEY_STORE); }

  function api(path, opts) {
    opts = opts || {};
    var headers = opts.headers || {};
    headers["X-Exchange-Admin-Key"] = getKey();
    if (opts.body) headers["Content-Type"] = "application/json";
    return fetch(path, {
      method: opts.method || "GET",
      headers: headers,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, status: r.status, data: j }; }); });
  }

  function money(n) {
    var v = Number(n || 0);
    return (v < 0 ? "-$" : "$") + Math.abs(v).toFixed(2);
  }
  function cls(n) { return Number(n || 0) >= 0 ? "pos" : "neg"; }

  function showApp() { $("gate").classList.add("hidden"); $("app").classList.remove("hidden"); }
  function showGate() { $("app").classList.add("hidden"); $("gate").classList.remove("hidden"); }

  function renderKpis(t, killSwitch) {
    var c = $("kpis");
    c.innerHTML = "";
    var items = [
      { label: "Total profit", value: money(t.total_profit_usd), cls: cls(t.total_profit_usd) },
      { label: "Realized", value: money(t.total_realized_pnl_usd), cls: cls(t.total_realized_pnl_usd) },
      { label: "Unrealized", value: money(t.total_unrealized_pnl_usd), cls: cls(t.total_unrealized_pnl_usd) },
      { label: "Active bots", value: (t.active_bots || 0) + " / " + (t.bot_count || 0), cls: "" },
      { label: "Total trades", value: t.trade_count || 0, cls: "" },
      { label: "Kill switch", value: killSwitch ? "ON" : "off", cls: killSwitch ? "neg" : "" },
    ];
    items.forEach(function (it) {
      var d = document.createElement("div");
      d.className = "card";
      d.innerHTML = '<div class="label">' + it.label + '</div><div class="value ' + it.cls + '">' + it.value + "</div>";
      c.appendChild(d);
    });
  }

  function renderSupervisors(sups) {
    var c = $("supervisors");
    c.innerHTML = "";
    (sups || []).forEach(function (s) {
      var d = document.createElement("div");
      d.className = "sup";
      var pill = s.enabled ? '<span class="pill on">active</span>' : '<span class="pill off">paused</span>';
      d.innerHTML =
        '<div class="top"><strong>' + s.name + "</strong>" + pill + "</div>" +
        '<div class="role">' + (s.role || "") + "</div>" +
        '<div class="stat">Profit <span class="' + cls(s.profit_usd) + '">' + money(s.profit_usd) + "</span> · " +
        (s.active_bot_count || 0) + "/" + (s.bot_count || 0) + " bots · " + (s.trade_count || 0) + " trades</div>" +
        '<div style="margin-top:10px"><button class="btn small" data-sup="' + s.id + '" data-on="' + (!s.enabled) + '">' +
        (s.enabled ? "Pause" : "Resume") + "</button></div>";
      c.appendChild(d);
    });
    Array.prototype.forEach.call(c.querySelectorAll("button[data-sup]"), function (b) {
      b.addEventListener("click", function () {
        toggleSupervisor(b.getAttribute("data-sup"), b.getAttribute("data-on") === "true");
      });
    });
  }

  function renderBots(bots) {
    var tb = $("bots");
    tb.innerHTML = "";
    (bots || []).forEach(function (b) {
      var tr = document.createElement("tr");
      var state = b.enabled ? '<span class="pill on">on</span>' : '<span class="pill off">off</span>';
      tr.innerHTML =
        "<td>" + (b.name || b.id) + "</td>" +
        "<td>" + (b.kind === "arbitrage_paper" ? "Arbitrage" : "Cross-trade") + "</td>" +
        "<td>" + (b.supervisor || "") + "</td>" +
        '<td class="' + cls(b.realized_pnl_usd) + '">' + money(b.realized_pnl_usd) + "</td>" +
        '<td class="' + cls(b.unrealized_pnl_usd) + '">' + money(b.unrealized_pnl_usd) + "</td>" +
        '<td class="' + cls(b.total_pnl_usd) + '">' + money(b.total_pnl_usd) + "</td>" +
        "<td>" + (b.trade_count || 0) + "</td>" +
        '<td><span class="toggle" data-bot="' + b.id + '" data-on="' + (!b.enabled) + '">' + state + "</span></td>";
      tb.appendChild(tr);
    });
    Array.prototype.forEach.call(tb.querySelectorAll(".toggle[data-bot]"), function (el) {
      el.addEventListener("click", function () {
        toggleBot(el.getAttribute("data-bot"), el.getAttribute("data-on") === "true");
      });
    });
  }

  function status(msg, isErr) {
    var el = $("topStatus");
    el.textContent = msg || "";
    el.style.color = isErr ? "#f87171" : "#8b93a7";
  }

  function load() {
    status("Loading…");
    return api("/api/exchange/control-board/overview").then(function (res) {
      if (res.status === 401) { clearKey(); showGate(); $("gateStatus").textContent = "Invalid key."; return; }
      if (!res.ok || !res.data || !res.data.success) { status("Failed to load.", true); return; }
      var d = res.data;
      renderKpis(d.totals || {}, d.kill_switch);
      renderSupervisors(d.supervisors || []);
      renderBots(d.bots || []);
      var note = "Updated " + new Date().toLocaleTimeString() + (d.arbitrage_live ? " · LIVE" : " · paper");
      if (d.paper_mode && d.treasury) {
        note += " · treasury paper $" + Number(d.treasury.ledger_stashed_usd_paper || 0).toFixed(2);
        if (d.treasury.ledger_stashed_usd_live > 0) {
          note += " · live $" + Number(d.treasury.ledger_stashed_usd_live).toFixed(2);
        }
      }
      if (d.monthly_projection_note) note += " — " + d.monthly_projection_note;
      status(note);
    }).catch(function () { status("Network error.", true); });
  }

  function toggleBot(botId, on) {
    api("/api/exchange/control-board/bot", { method: "POST", body: { bot_id: botId, enabled: on } }).then(load);
  }
  function toggleSupervisor(supId, on) {
    api("/api/exchange/control-board/supervisor", { method: "POST", body: { supervisor_id: supId, enabled: on } }).then(load);
  }

  function loadPredictions() {
    api("/api/exchange/prediction/batch").then(function (res) {
      var tb = $("predRows");
      if (!tb) return;
      var rows = (res && res.predictions) || [];
      tb.innerHTML = rows.map(function (p) {
        return "<tr><td>" + p.symbol + "</td><td>" + p.direction + "</td><td>" + p.confidence_pct +
          "%</td><td>" + p.expected_move_bps + " bps</td><td>" + p.edge_uplift_bps + " bps</td><td>" +
          (Number(p.edge_uplift_bps) + Number(p.arb_edge_bps)).toFixed(2) + "</td></tr>";
      }).join("") || '<tr><td colspan="6">No live signals yet.</td></tr>';
    });
  }

  function runBoost() {
    var skills = ($("boostSkills").value || "").split(",").map(function (s) { return s.trim(); }).filter(Boolean);
    api("/api/exchange/profit-tools/boost", { method: "POST", body: { capital_usd: Number($("boostCapital").value || 0), skills: skills } })
      .then(function (res) {
        var tb = $("boostRows");
        if (!tb) return;
        tb.innerHTML = ((res && res.scenarios) || []).map(function (s) {
          return "<tr><td>" + s.name + "</td><td>" + (s.premium ? "yes" : "—") + "</td><td>" + s.edge_bps +
            " bps</td><td>" + s.cycles_per_day + "</td><td class='pos'>" + money(s.daily_profit_usd) +
            "</td><td class='pos'>" + money(s.monthly_profit_usd) + "</td><td>" + s.monthly_roi_pct + "%</td></tr>";
        }).join("");
      });
  }

  function renderPayout(st) {
    var el = $("payoutStatus");
    if (!el || !st || !st.success) { if (el) el.textContent = "Failed to load payout status."; return; }
    var pp = st.paypal || {};
    el.innerHTML =
      "<div class='big'>" + money(st.paypal_sweepable_usd || st.net_unswept_usd) + " <span class='muted'>→ PayPal</span></div>" +
      "<div class='muted'>PayPal: " + (pp.email || "not set") + " · share " + (pp.share_pct || 100) + "% · mode: " + st.mode + "</div>" +
      "<div class='muted'>Pool " + money(st.realized_total_usd) + " (treasury " + money(st.treasury_stashed_usd) + ") · swept " + money(st.swept_total_usd) +
      " · min " + money(st.min_sweep_usd) + " · ready: " + (st.ready_to_sweep ? "yes" : "no") + "</div>";
    if ($("ppEmail") && pp.email) $("ppEmail").value = pp.email;
    if ($("ppShare") && pp.share_pct) $("ppShare").value = pp.share_pct;
    if ($("ppMin") && st.min_sweep_usd) $("ppMin").value = st.min_sweep_usd;
  }

  function loadPayout() { api("/api/exchange/payout/status").then(renderPayout); }

  function savePayPal() {
    api("/api/exchange/payout/configure-paypal", { method: "POST", body: {
      email: ($("ppEmail").value || "").trim(),
      share_pct: Number($("ppShare").value || 50),
    } }).then(function (r) {
      $("payoutResult").textContent = r && r.success ? "PayPal payout saved." : ("Save failed: " + ((r && r.error) || "error"));
      loadPayout();
    });
  }

  function saveBinance() {
    var addrs = {};
    var usdt = ($("binUsdt").value || "").trim();
    if (usdt) addrs.USDT = usdt;
    api("/api/exchange/payout/configure-binance", { method: "POST", body: {
      api_key: ($("binKey").value || "").trim(),
      api_secret: ($("binSecret").value || "").trim(),
      deposit_addresses: addrs,
    } }).then(function (r) {
      $("payoutResult").textContent = r && r.success ? "Saved." : ("Save failed: " + ((r && r.error) || "error"));
      loadPayout();
    });
  }

  function planSweep() {
    var mn = Number(($("ppMin") || {}).value || ($("binMin") || {}).value || 0);
    api("/api/exchange/payout/plan", { method: "POST", body: { min_sweep_usd: mn } }).then(function (r) {
      if (!r) return;
      $("payoutResult").textContent = r.actionable
        ? ("Plan: send " + money(r.amount_usd) + " to " + (r.receiver_email || r.deposit_address || "destination") + " (" + r.mode + ")")
        : ("Not actionable: " + (r.reason || r.hint || ""));
    });
  }

  function doSweep() {
    var mn = Number(($("ppMin") || {}).value || ($("binMin") || {}).value || 0);
    api("/api/exchange/payout/sweep", { method: "POST", body: { min_sweep_usd: mn } }).then(function (r) {
      $("payoutResult").textContent = (r && r.success)
        ? ("Swept " + money(r.swept.amount_usd) + " (" + r.swept.mode + "). " + (r.note || ""))
        : ("Sweep failed: " + ((r && r.error) || "error"));
      loadPayout();
    });
  }

  function loadOwnerWatch() {
    api("/api/exchange/live-watch/owner?limit=60").then(function (d) {
      var el = $("watchTotals");
      if (!el || !d || !d.success) return;
      var t = d.totals || {};
      el.textContent = t.users + " users · " + t.agents + " agents · " + t.active_agents + " active · " + t.pending_activation + " pending activation";
      var tb = $("watchUsers");
      if (tb) tb.innerHTML = (d.users || []).map(function (u) {
        return "<tr><td>" + u.user_id + "</td><td>" + u.trust_score + "</td><td>" +
          (u.tier && u.tier.icon ? u.tier.icon + " " : "") + (u.tier ? u.tier.name : "") + "</td><td>" + u.agent_count +
          "</td><td>" + u.active_agents + "</td><td>" + u.pending_activation + "</td><td>" + money(u.realized_profit_usd) +
          "</td><td>" + u.avg_composite_iq + "</td></tr>";
      }).join("") || "<tr><td colspan='8'>No user agents yet.</td></tr>";
      var ff = $("watchFeed");
      if (ff) ff.innerHTML = (d.feed || []).map(function (f) {
        return "<div style='padding:4px 0;border-top:1px solid var(--line);font-size:12px'>" +
          (f.ts || "") + " · " + (f.action || "") + " · " + (f.user_id || "") + " · $" + Number(f.amount_usd || 0).toFixed(2) + "</div>";
      }).join("") || "No trust/trading events yet.";
    });
  }

  function switchTab(name) {
    Array.prototype.forEach.call(document.querySelectorAll(".tab"), function (t) {
      t.classList.toggle("active", t.getAttribute("data-tab") === name);
    });
    Array.prototype.forEach.call(document.querySelectorAll(".tabpane"), function (p) {
      p.classList.toggle("active", p.id === "pane-" + name);
    });
    if (name === "predictions") loadPredictions();
    if (name === "payout") loadPayout();
    if (name === "boost") runBoost();
    if (name === "watch") loadOwnerWatch();
  }

  function init() {
    $("unlock").addEventListener("click", function () {
      var k = $("key").value.trim();
      if (!k) return;
      setKey(k);
      load().then(function () { if (getKey()) showApp(); });
    });
    $("key").addEventListener("keydown", function (e) { if (e.key === "Enter") $("unlock").click(); });
    $("lock").addEventListener("click", function () { clearKey(); showGate(); });
    $("refresh").addEventListener("click", load);
    $("runAll").addEventListener("click", function () {
      status("Running all bots…");
      api("/api/exchange/control-board/run", { method: "POST", body: {} }).then(load);
    });
    $("kill").addEventListener("click", function () {
      if (!confirm("Toggle the global kill switch? This pauses/resumes ALL bots.")) return;
      api("/api/exchange/control-board/overview").then(function (res) {
        var on = !(res.data && res.data.kill_switch);
        api("/api/exchange/control-board/kill-switch", { method: "POST", body: { on: on } }).then(load);
      });
    });

    Array.prototype.forEach.call(document.querySelectorAll(".tab"), function (t) {
      t.addEventListener("click", function () { switchTab(t.getAttribute("data-tab")); });
    });
    var bb = $("boostRun"); if (bb) bb.addEventListener("click", runBoost);
    var ps = $("ppSave"); if (ps) ps.addEventListener("click", savePayPal);
    var pp = $("ppPlan"); if (pp) pp.addEventListener("click", planSweep);
    var pw = $("ppSweep"); if (pw) pw.addEventListener("click", doSweep);
    var bs = $("binSave"); if (bs) bs.addEventListener("click", saveBinance);

    if (getKey()) { showApp(); load(); } else { showGate(); }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
