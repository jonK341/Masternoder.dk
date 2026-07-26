/* Owner-only Business Control board. All data + controls are admin-key gated. */
(function () {
  "use strict";

  var KEY_STORE = "mn_exchange_admin_key";
  var OVERVIEW_TIMEOUT_MS = 55000;
  var RUN_TIMEOUT_MS = 300000;
  var lastOverview = null;
  var loadGen = 0;

  var $ = function (id) { return document.getElementById(id); };

  function getKey() { return sessionStorage.getItem(KEY_STORE) || ""; }
  function setKey(k) { sessionStorage.setItem(KEY_STORE, k); }
  function clearKey() { sessionStorage.removeItem(KEY_STORE); }

  function api(path, opts) {
    opts = opts || {};
    var headers = opts.headers || {};
    headers["X-Exchange-Admin-Key"] = getKey();
    if (opts.body) headers["Content-Type"] = "application/json";
    var timeoutMs = opts.timeoutMs != null ? opts.timeoutMs : OVERVIEW_TIMEOUT_MS;
    var ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, timeoutMs) : null;
    return fetch(path, {
      method: opts.method || "GET",
      headers: headers,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
      signal: ctrl ? ctrl.signal : undefined,
    }).then(function (r) {
      return r.json().then(function (j) { return { ok: r.ok, status: r.status, data: j }; });
    }).catch(function (err) {
      if (err && err.name === "AbortError") {
        return { ok: false, status: 0, data: { success: false, error: "timeout" }, timedOut: true };
      }
      throw err;
    }).finally(function () {
      if (timer) clearTimeout(timer);
    });
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
      var lastRun = "";
      if (s.last_run_at) {
        var lr = new Date(s.last_run_at);
        var ok = s.last_run_ok !== false;
        lastRun = '<div class="muted" style="margin-top:6px">Last tick ' +
          (isNaN(lr.getTime()) ? s.last_run_at : lr.toLocaleString()) +
          (ok ? " · ok" : " · " + (s.last_run_error || "failed")) + "</div>";
      }
      d.innerHTML =
        '<div class="top"><strong>' + s.name + "</strong>" + pill + "</div>" +
        '<div class="role">' + (s.role || "") + "</div>" +
        '<div class="stat">Profit <span class="' + cls(s.profit_usd) + '">' + money(s.profit_usd) + "</span> · " +
        (s.active_bot_count || 0) + "/" + (s.bot_count || 0) + " bots · " + (s.trade_count || 0) + " trades</div>" +
        lastRun +
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
        "<td>" + (b.kind === "arbitrage_paper" ? "Arbitrage" : b.kind === "winnable_pairs" ? "Winnable" :
          b.kind === "analytics" ? "Profit analyst" : b.kind === "extended_profit" ? "Extended" :
          b.kind === "treasury" ? "Treasury" : b.kind === "risk" ? "Risk" : b.fleet ? "Fleet" :
          "Cross-trade") + (b.fleet ? " · fleet" : "") + "</td>" +
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

  function renderLivePack(lp, win) {
    var el = $("livePackPanel");
    if (!el) return;
    lp = lp || {};
    var mode = lp.mode || "unknown";
    var ready = lp.profit_live_ready ? '<span class="pill on">ready</span>' : '<span class="pill off">not ready</span>';
    var env = lp.env || {};
    var envRows = Object.keys(env).map(function (k) {
      return "<tr><td>" + k + "</td><td>" + (env[k] ? "on" : "off") + "</td></tr>";
    }).join("");
    var venues = ((lp.live_readiness || {}).venues || []).map(function (v) {
      return "<tr><td>" + (v.venue_id || "") + "</td><td>" + (v.live_ready ? "ready" : "—") + "</td><td>" +
        (v.credentials_configured ? "keys" : "no keys") + "</td></tr>";
    }).join("");
    var blockers = (lp.blockers || []).join(", ") || "none";
    el.innerHTML =
      "<div class='big'>" + mode.toUpperCase() + " " + ready + "</div>" +
      "<p class='muted'>Blockers: " + blockers + "</p>" +
      "<div class='grid2' style='margin-top:12px'>" +
      "<div><strong style='font-size:12px'>Env flags</strong><table><tbody>" + envRows + "</tbody></table></div>" +
      "<div><strong style='font-size:12px'>Venues</strong><table><thead><tr><th>Venue</th><th>Live</th><th>Creds</th></tr></thead><tbody>" +
      (venues || "<tr><td colspan='3'>No venue data</td></tr>") + "</tbody></table></div></div>";
    var wp = $("winnablePanel");
    if (!wp) return;
    win = win || {};
    var hits = win.top_hits || [];
    var hitRows = hits.map(function (h) {
      return "<tr><td>" + (h.symbol || "") + "</td><td>" + (h.buy_venue || "") + "→" + (h.sell_venue || "") +
        "</td><td>" + (h.avg_net_bps || h.net_bps || "—") + "</td><td>" + (h.search_score || "—") + "</td></tr>";
    }).join("");
    var hot = (win.hot_symbols || []).join(", ") || "—";
    wp.innerHTML =
      "<p class='muted'>Index " + (win.index_updated_at || "—") + " · " + (win.hit_count || 0) + " hits · hot: " + hot + "</p>" +
      "<p class='muted'>Thresholds: " + JSON.stringify(win.thresholds || {}) + "</p>" +
      "<table><thead><tr><th>Symbol</th><th>Route</th><th>Net bps</th><th>Score</th></tr></thead><tbody>" +
      (hitRows || "<tr><td colspan='4'>No ranked hits yet — run all bots.</td></tr>") + "</tbody></table>";
  }

  function renderOrchestration(orch) {
    var el = $("orchPanel");
    if (!el) return;
    orch = orch || {};
    var head = orch.last_run_at
      ? "Last orchestrator run " + new Date(orch.last_run_at).toLocaleString() +
        (orch.last_run_ok === false ? " · some steps failed" : " · all steps ok")
      : "No orchestrator run recorded yet — use Run all bots.";
    var rows = "";
    var lr = orch.last_results || {};
    Object.keys(lr).forEach(function (k) {
      var r = lr[k] || {};
      rows += "<tr><td>" + k + "</td><td>" + (r.success ? "ok" : "fail") + "</td><td>" + (r.error || "—") + "</td></tr>";
    });
    var hist = (orch.history || []).slice().reverse().slice(0, 10).map(function (h) {
      return "<div class='muted'>" + (h.ran_at || "") + " · " + (h.ok ? "ok" : "fail") + " · " + (h.keys || []).join(", ") + "</div>";
    }).join("");
    el.innerHTML =
      "<p class='muted'>" + head + "</p>" +
      "<table><thead><tr><th>Step</th><th>Status</th><th>Error</th></tr></thead><tbody>" +
      (rows || "<tr><td colspan='3'>No step results yet.</td></tr>") + "</tbody></table>" +
      (hist ? "<div style='margin-top:12px'><strong style='font-size:12px'>Recent runs</strong>" + hist + "</div>" : "");
  }

  function applyOverview(d) {
    if (!d || !d.success) return;
    lastOverview = d;
    renderKpis(d.totals || {}, d.kill_switch);
    renderSupervisors(d.supervisors || []);
    renderOrchestration(d.orchestration);
    renderLivePack(d.live_pack, d.winnable_pairs);
      renderBots(d.bots || []);
      var fs = $("fleetSummary");
      if (fs && d.supervisor_fleet) {
        var fc = (d.supervisor_fleet.bots || []).length;
        fs.textContent = fc + " fleet bots registered · " + (d.supervisor_fleet.mechanics_count || 25) + " mechanics active";
      }
  }

  function renderStalePanels(message) {
    if (lastOverview) {
      applyOverview(lastOverview);
      return;
    }
    renderOrchestration({});
    renderLivePack({}, {});
    var m = message || "Could not load data.";
    var lp = $("livePackPanel");
    var wp = $("winnablePanel");
    var op = $("orchPanel");
    if (lp) lp.innerHTML = "<p class='warn'>" + m + "</p>";
    if (wp) wp.innerHTML = "<p class='warn'>" + m + "</p>";
    if (op) op.innerHTML = "<p class='warn'>" + m + "</p>";
  }

  function load(opts) {
    opts = opts || {};
    var gen = ++loadGen;
    if (lastOverview && !opts.force) {
      applyOverview(lastOverview);
      status("Showing cached data · refreshing…");
    } else {
      status("Loading…");
    }
    var url = "/api/exchange/control-board/overview?light=1";
    if (opts.full) url = "/api/exchange/control-board/overview?light=0";
    return api(url, { timeoutMs: opts.timeoutMs || OVERVIEW_TIMEOUT_MS }).then(function (res) {
      if (gen !== loadGen) return;
      if (res.status === 401) { clearKey(); showGate(); $("gateStatus").textContent = "Invalid key."; return; }
      if (res.timedOut) {
        status("Overview timed out — showing last data if any. Try Refresh.", true);
        renderStalePanels("Request timed out.");
        return;
      }
      if (!res.ok || !res.data || !res.data.success) {
        status("Failed to load overview.", true);
        renderStalePanels("Failed to load overview.");
        return;
      }
      var d = res.data;
      applyOverview(d);
      var note = "Updated " + new Date().toLocaleTimeString();
      if (d.overview_light) note += " · fast overview";
      if (d.live_pack) {
        note += " · " + (d.live_pack.mode === "live" ? "LIVE pack ready" : "paper / partial");
        if (d.live_pack.blockers && d.live_pack.blockers.length) {
          note += " · blockers: " + d.live_pack.blockers.slice(0, 4).join(", ");
        }
      } else if (d.arbitrage_live) {
        note += " · LIVE";
      } else {
        note += " · paper";
      }
      if (d.paper_mode && d.treasury) {
        note += " · treasury paper $" + Number(d.treasury.ledger_stashed_usd_paper || 0).toFixed(2);
        if (d.treasury.ledger_stashed_usd_live > 0) {
          note += " · live $" + Number(d.treasury.ledger_stashed_usd_live).toFixed(2);
        }
      }
      if (d.monthly_projection_note) note += " — " + d.monthly_projection_note;
      status(note);
    }).catch(function () {
      if (gen !== loadGen) return;
      status("Network error — check connection or try Refresh.", true);
      renderStalePanels("Network error.");
    });
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
    var totalsEl = $("watchTotals");
    var usersEl = $("watchUsers");
    var feedEl = $("watchFeed");
    if (totalsEl) totalsEl.textContent = "Loading Live Watch…";
    api("/api/exchange/live-watch/owner?limit=60", { timeoutMs: 90000 }).then(function (res) {
      var d = res.data;
      if (res.timedOut || !res.ok || !d || !d.success) {
        if (totalsEl) totalsEl.textContent = "Live Watch failed — " + (res.timedOut ? "timed out" : (d && d.error) || "error");
        if (usersEl) usersEl.innerHTML = "<tr><td colspan='8'>Could not load users.</td></tr>";
        if (feedEl) feedEl.textContent = "No feed.";
        return;
      }
      var t = d.totals || {};
      if (totalsEl) {
        totalsEl.textContent = (t.users || 0) + " users · " + (t.agents || 0) + " agents · " +
          (t.active_agents || 0) + " active · " + (t.pending_activation || 0) + " pending activation";
      }
      if (usersEl) {
        usersEl.innerHTML = (d.users || []).map(function (u) {
          return "<tr><td>" + u.user_id + "</td><td>" + u.trust_score + "</td><td>" +
            (u.tier && u.tier.icon ? u.tier.icon + " " : "") + (u.tier ? u.tier.name : "") + "</td><td>" + u.agent_count +
            "</td><td>" + u.active_agents + "</td><td>" + u.pending_activation + "</td><td>" + money(u.realized_profit_usd) +
            "</td><td>" + u.avg_composite_iq + "</td></tr>";
        }).join("") || "<tr><td colspan='8'>No user agents yet.</td></tr>";
      }
      if (feedEl) {
        feedEl.innerHTML = (d.feed || []).map(function (f) {
          return "<div style='padding:4px 0;border-top:1px solid var(--line);font-size:12px'>" +
            (f.ts || "") + " · " + (f.action || "") + " · " + (f.user_id || "") + " · $" + Number(f.amount_usd || 0).toFixed(2) + "</div>";
        }).join("") || "No trust/trading events yet.";
      }
    }).catch(function () {
      if (totalsEl) totalsEl.textContent = "Live Watch network error.";
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
    if (name === "orchestration" || name === "livepack") {
      if (lastOverview) {
        applyOverview(lastOverview);
      } else {
        load();
      }
    }
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
    $("refresh").addEventListener("click", function () { load({ force: true }); });
    $("runAll").addEventListener("click", function () {
      var btn = $("runAll");
      if (btn) btn.disabled = true;
      status("Running all bots on server (1–3 min)…");
      api("/api/exchange/control-board/run", { method: "POST", body: {}, timeoutMs: RUN_TIMEOUT_MS })
        .then(function (res) {
          if (btn) btn.disabled = false;
          if (res.timedOut) {
            status("Run still processing — refresh overview in a minute.", true);
            load({ force: true, timeoutMs: 90000 });
            return;
          }
          if (res.data && res.data.success && res.data.results) {
            status("Run finished · refreshing overview…");
          } else {
            status("Run returned: " + ((res.data && res.data.error) || "see orchestration tab"), true);
          }
          load({ force: true, timeoutMs: 90000 });
        })
        .catch(function () {
          if (btn) btn.disabled = false;
          status("Run request failed — server may still be busy. Refresh shortly.", true);
          load({ force: true, timeoutMs: 90000 });
        });
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
