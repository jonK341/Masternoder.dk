/* Owner-only Business Control board. All data + controls are admin-key gated. */
(function () {
  "use strict";

  var KEY_STORE = "mn_exchange_admin_key";
  var OVERVIEW_TIMEOUT_MS = 55000;
  var RUN_TIMEOUT_MS = 300000;
  var lastOverview = null;
  var loadGen = 0;
  var runInFlight = false;

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
      return { ok: false, status: 0, data: { success: false, error: (err && err.message) || "network_error" } };
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

  var FLEET_KIND_LABELS = {
    analytics: "Profit Analyst",
    extended_profit: "Extended Profit",
    treasury: "Treasury",
    risk: "Risk Officer",
    winnable_pairs: "Winnable Pairs",
  };

  function renderFleetPreflight(pf) {
    var el = $("fleetPreflightPanel");
    if (!el) return;
    if (!pf || !pf.checks) {
      el.innerHTML = "";
      return;
    }
    var rows = (pf.checks || []).map(function (c) {
      var st = c.ok ? '<span class="pill on">ok</span>' : (c.optional ? '<span class="pill off">warn</span>' : '<span class="pill off">fail</span>');
      return "<tr><td>" + c.id + "</td><td>" + st + "</td><td class='muted'>" + (c.detail || "") + "</td></tr>";
    }).join("");
    el.innerHTML =
      "<strong style='font-size:12px'>Preflight</strong> " +
      (pf.success ? '<span class="pill on">pass</span>' : '<span class="pill off">fail</span>') +
      "<div class='table-wrap' style='margin-top:8px'><table><thead><tr><th>Check</th><th></th><th>Detail</th></tr></thead><tbody>" +
      rows + "</tbody></table></div>";
  }

  function fleetXpBar(prog) {
    prog = prog || {};
    var pct = Math.max(0, Math.min(100, prog.xp_progress_pct || 0));
    var inLv = prog.xp_in_level != null ? prog.xp_in_level : 0;
    var need = prog.xp_to_next != null ? prog.xp_to_next : 200;
    return (
      '<div class="fleet-xp-wrap">' +
      '<div class="muted" style="font-size:11px">XP ' + inLv + " / " + need + "</div>" +
      '<div class="fleet-xp-bar"><span style="width:' + pct + '%"></span></div></div>'
    );
  }

  function renderFleetCommander(fleet, elId) {
    var el = $(elId);
    if (!el) return;
    var ps = (fleet && fleet.progression_summary) || {};
    if (!ps.fleet_total_xp && ps.fleet_total_xp !== 0) {
      el.style.display = "none";
      el.innerHTML = "";
      return;
    }
    el.style.display = "block";
    var rewards = fleet.rewards || [];
    var unlocked = ps.total_rewards_unlocked || 0;
    var catalog = ps.reward_catalog_size || rewards.length || 0;
    el.innerHTML =
      "<strong>Fleet commander</strong> " +
      '<span class="fleet-level-pill">Lv ' + (ps.fleet_commander_level || 1) + " · " + (ps.fleet_commander_rank || "Recruit") + "</span>" +
      '<p class="muted" style="margin:8px 0 0">' +
      (ps.fleet_total_xp || 0) + " total XP · avg bot Lv " + (ps.avg_bot_level || 1) +
      " · " + unlocked + "/" + catalog + " reward tiers unlocked fleet-wide</p>";
  }

  function renderFleetOps(fleet) {
    var el = $("fleetOpsPanel");
    if (!el) return;
    fleet = fleet || {};
    var health = fleet.health || {};
    var meta = fleet.meta || {};
    var lastAt = meta.last_run_at || health.last_fleet_run_at;
    var head = lastAt
      ? "Last fleet run " + new Date(lastAt).toLocaleString() + " · " + (meta.last_run_kind || "all") +
        (meta.last_run_ok === false ? " · some kinds failed" : meta.last_run_ok ? " · ok" : "")
      : "No fleet-only run yet — use Run fleet or buttons below.";
    var stats =
      "<div class='grid2' style='margin-top:10px'><div><strong style='font-size:12px'>Health</strong><p class='muted' style='margin:6px 0 0'>" +
      (health.bot_count || 0) + " bots · " + (health.last_tick_failed_bots || 0) + " last tick failed · " +
      (health.never_ran_bots || 0) + " never ran</p></div>" +
      "<div><strong style='font-size:12px'>Mechanics</strong><p class='muted' style='margin:6px 0 0'>" +
      (fleet.mechanics_count || 27) + " registered (M01–M" + String(fleet.mechanics_count || 27).padStart(2, "0") + ")</p></div></div>";
    var ps = fleet.progression_summary;
    if (ps) {
      stats +=
        "<div class='fleet-commander' style='margin-top:10px'><strong>Fleet XP</strong> " +
        '<span class="fleet-level-pill">Cmd Lv ' + (ps.fleet_commander_level || 1) + "</span>" +
        "<p class='muted' style='margin:6px 0 0'>" +
        (ps.fleet_total_xp || 0) + " XP · avg Lv " + (ps.avg_bot_level || 1) +
        " · " + (ps.total_rewards_unlocked || 0) + " rewards unlocked</p></div>";
    }
    var rows = "";
    var lr = meta.last_results || {};
    Object.keys(lr).forEach(function (k) {
      var r = lr[k] || {};
      var detail = r.bot_count != null ? (r.ok_count + "/" + r.bot_count + " bots ok") : (r.success ? "ok" : "fail");
      rows += "<tr><td>" + (FLEET_KIND_LABELS[k] || k) + "</td><td>" + detail + "</td><td>" + (r.error || "—") + "</td></tr>";
    });
    var hist = (meta.history || []).slice().reverse().slice(0, 8).map(function (h) {
      return "<div class='muted'>" + (h.ran_at || "") + " · " + (h.kind || "all") + " · " + (h.ok ? "ok" : "fail") + "</div>";
    }).join("");
    el.innerHTML =
      "<p class='muted'>" + head + "</p>" + stats +
      "<table style='margin-top:12px'><thead><tr><th>Kind</th><th>Status</th><th>Error</th></tr></thead><tbody>" +
      (rows || "<tr><td colspan='3'>No fleet run results yet.</td></tr>") + "</tbody></table>" +
      (hist ? "<div style='margin-top:12px'><strong style='font-size:12px'>Recent fleet runs</strong>" + hist + "</div>" : "");
  }

  function loadFleetPreflight() {
    api("/api/exchange/control-board/preflight", { timeoutMs: 90000 }).then(function (res) {
      if (res.ok && res.data) renderFleetPreflight(res.data);
    });
  }

  function runFleetKind(kind, btn) {
    if (runInFlight) {
      status("A run is already in progress — wait for it to finish.", true);
      return;
    }
    if (!getKey()) {
      status("Enter admin key to run fleet.", true);
      showGate();
      return;
    }
    runInFlight = true;
    setRunButtonsDisabled(true);
    status(kind ? "Running fleet: " + (FLEET_KIND_LABELS[kind] || kind) + "…" : "Running full supervisor fleet…");
    var body = kind ? { kind: kind } : {};
    api("/api/exchange/control-board/run-fleet", { method: "POST", body: body, timeoutMs: RUN_TIMEOUT_MS })
      .then(function (res) {
        if (handleRunAuth(res)) return;
        if (res.timedOut) {
          status("Fleet run timed out — server may still be working. Refresh in a minute.", true);
          load({ force: true, timeoutMs: 90000 });
          return;
        }
        status(
          res.data && res.data.success ? "Fleet tick finished." : ("Fleet: " + ((res.data && res.data.error) || "partial fail")),
          !res.data || !res.data.success
        );
        load({ force: true, timeoutMs: 90000 });
      })
      .catch(function () {
        status("Fleet run failed — network error.", true);
        load({ force: true, timeoutMs: 90000 });
      })
      .finally(function () {
        runInFlight = false;
        setRunButtonsDisabled(false);
      });
  }

  function startRunAll(btn) {
    if (runInFlight) {
      status("A run is already in progress — wait for it to finish.", true);
      return;
    }
    if (!getKey()) {
      status("Enter admin key to run bots.", true);
      showGate();
      return;
    }
    runInFlight = true;
    setRunButtonsDisabled(true);
    status("Running all bots on server (1–3 min)…");
    api("/api/exchange/control-board/run", { method: "POST", body: {}, timeoutMs: RUN_TIMEOUT_MS })
      .then(function (res) {
        if (handleRunAuth(res)) return;
        if (res.timedOut) {
          status("Run still processing — refresh overview in a minute.", true);
          load({ force: true, timeoutMs: 90000 });
          return;
        }
        if (res.data && res.data.success) {
          status("Run finished · refreshing overview…");
        } else {
          status("Run returned: " + ((res.data && res.data.error) || "see orchestration tab"), true);
        }
        load({ force: true, timeoutMs: 90000 });
      })
      .catch(function () {
        status("Run request failed — network error.", true);
        load({ force: true, timeoutMs: 90000 });
      })
      .finally(function () {
        runInFlight = false;
        setRunButtonsDisabled(false);
      });
  }

  function bindFleetRunButtons() {
    /* Delegated in init — kept for tab switch compatibility */
  }

  function onAppClick(e) {
    var app = $("app");
    if (!app || app.classList.contains("hidden")) return;
    var t = e.target;
    if (!t || !t.closest) return;
    var btn = t.closest("button");
    if (!btn) return;
    if (btn.id === "runAll") {
      e.preventDefault();
      startRunAll(btn);
      return;
    }
    if (btn.id === "runFleet") {
      e.preventDefault();
      runFleetKind(null, btn);
      return;
    }
    if (btn.getAttribute("data-fleet-kind") != null) {
      e.preventDefault();
      var k = btn.getAttribute("data-fleet-kind");
      runFleetKind(k === "all" || k === "" ? null : k, btn);
    }
  }

  function botTypeLabel(b) {
    if (b.type_label) return b.type_label;
    if (b.kind === "arbitrage_paper") return "Arbitrage";
    if (b.kind === "winnable_pairs") return "Winnable Pairs";
    if (b.kind === "analytics") return "Profit Analyst";
    if (b.kind === "extended_profit") return "Extended Profit";
    if (b.kind === "treasury") return "Treasury";
    if (b.kind === "risk") return "Risk Officer";
    if (b.fleet) return "Fleet";
    return "Cross-trade";
  }

  function renderFleetRoster(fleet, containerId) {
    var grid = $(containerId || "fleetRoster");
    if (!grid) return;
    grid.innerHTML = "";
    fleet = fleet || {};
    var bots = fleet.bots || [];
    var byKind = {};
    bots.forEach(function (b) {
      var k = b.kind || "fleet";
      if (!byKind[k]) byKind[k] = [];
      byKind[k].push(b);
    });
    Object.keys(byKind).forEach(function (kind) {
      var group = document.createElement("div");
      group.className = "section";
      var sample = byKind[kind][0] || {};
      group.innerHTML = "<h3 style='font-size:13px;margin:0 0 8px'>" +
        (sample.supervisor_name || sample.type_label || kind) + "</h3>";
      var inner = document.createElement("div");
      inner.className = "sup-grid";
      byKind[kind].forEach(function (b) {
        var d = document.createElement("div");
        d.className = "sup";
        var pill = b.enabled !== false ? '<span class="pill on">on</span>' : '<span class="pill off">off</span>';
        var tag = b.label ? '<span class="pill on" style="margin-left:6px;opacity:.85">' + b.label + "</span>" : "";
        var lastRun = "";
        if (b.last_run_at) {
          var ok = b.last_run_ok !== false;
          lastRun = '<div class="muted" style="margin-top:6px">Last ' +
            (ok ? "ok" : (b.last_run_error || "fail")) + "</div>";
        }
        var prog = b.progression || {};
        var lvl = prog.level || 1;
        var rank = prog.rank_title || "";
        var levelPill = '<span class="fleet-level-pill">Lv ' + lvl + (rank ? " · " + rank : "") + "</span>";
        var rewardsLine = "";
        if (prog.rewards_unlocked_count != null) {
          rewardsLine = '<div class="fleet-rewards-mini muted">' + prog.rewards_unlocked_count + " reward tiers unlocked</div>";
        }
        if (prog.last_xp_gain) {
          lastRun += '<div class="muted" style="font-size:11px">+' + prog.last_xp_gain + " XP last tick</div>";
        }
        var skillLine = "";
        if (b.skill_meta && b.skill_meta.blended_edge_bps != null) {
          skillLine =
            '<div class="fleet-skills-mini muted">' +
            (b.skill_meta.skill_count || 0) +
            " skills · ~" +
            b.skill_meta.blended_edge_bps +
            " bps edge</div>";
        }
        d.innerHTML =
          '<div class="top"><strong>' + (b.name || b.id) + "</strong>" + tag + levelPill + pill + "</div>" +
          '<div class="role">' + (b.role_label || b.badge || "") + "</div>" +
          fleetXpBar(prog) +
          skillLine +
          rewardsLine +
          lastRun;
        inner.appendChild(d);
      });
      group.appendChild(inner);
      grid.appendChild(group);
    });
    if (!bots.length) {
      grid.innerHTML = "<p class='muted'>No fleet bots registered.</p>";
    }
  }

  function renderBots(bots) {
    var tb = $("bots");
    tb.innerHTML = "";
    (bots || []).forEach(function (b) {
      var tr = document.createElement("tr");
      var state = b.enabled ? '<span class="pill on">on</span>' : '<span class="pill off">off</span>';
      var nameCell = (b.name || b.id);
      if (b.label) nameCell += ' <span class="pill on label-tag">' + b.label + "</span>";
      if (b.wallet_label && b.wallet_label !== b.label) {
        nameCell += ' <span class="muted" style="font-size:11px">(' + b.wallet_label + ")</span>";
      }
      var supName = b.supervisor_name || b.supervisor || "";
      tr.innerHTML =
        "<td>" + nameCell + "</td>" +
        "<td>" + botTypeLabel(b) + (b.role_label ? "<br><span class='muted' style='font-size:11px'>" + b.role_label + "</span>" : "") + "</td>" +
        "<td>" + supName + "</td>" +
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
    if (el) {
      el.textContent = msg || "";
      el.style.color = isErr ? "#f87171" : "#8b93a7";
    }
    var fleetSt = $("fleetRunStatus");
    if (fleetSt && (runInFlight || (msg && /run|fleet|bot/i.test(msg)))) {
      fleetSt.textContent = msg || "";
      fleetSt.style.color = isErr ? "#f87171" : "#4ade80";
    }
  }

  function setRunButtonsDisabled(disabled) {
    ["runAll", "runFleet"].forEach(function (id) {
      var b = $(id);
      if (b) b.disabled = !!disabled;
    });
    var bar = $("fleetRunBar");
    if (bar) {
      Array.prototype.forEach.call(bar.querySelectorAll("button"), function (b) {
        b.disabled = !!disabled;
      });
    }
    if ($("app")) {
      $("app").classList.toggle("bc-run-busy", !!disabled);
    }
  }

  function handleRunAuth(res) {
    if (res && res.status === 401) {
      clearKey();
      showGate();
      var gs = $("gateStatus");
      if (gs) gs.textContent = "Session expired — enter admin key again.";
      return true;
    }
    return false;
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
      var detail = r.success ? "ok" : "fail";
      if (r.bot_count != null) {
        detail = (r.ok_count != null ? r.ok_count : "?") + "/" + r.bot_count + " bots · " + detail;
      }
      rows += "<tr><td>" + (FLEET_KIND_LABELS[k] || k) + "</td><td>" + detail + "</td><td>" + (r.error || "—") + "</td></tr>";
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
      if (d.supervisor_fleet) {
        renderFleetRoster(d.supervisor_fleet);
        renderFleetRoster(d.supervisor_fleet, "fleetRosterTab");
        renderFleetOps(d.supervisor_fleet);
        renderFleetCommander(d.supervisor_fleet, "fleetCommander");
        renderFleetCommander(d.supervisor_fleet, "fleetCommanderTab");
        var fs = $("fleetSummary");
        if (fs) {
          var fc = (d.supervisor_fleet.bots || []).length;
          var ps = d.supervisor_fleet.progression_summary || {};
          var xpBit = ps.fleet_total_xp != null ? " · " + ps.fleet_total_xp + " fleet XP · cmd Lv " + (ps.fleet_commander_level || 1) : "";
          fs.textContent = fc + " fleet bots · " + (d.supervisor_fleet.mechanics_count || 27) + " mechanics" + xpBit;
        }
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
    if (runInFlight && !opts.force) {
      return Promise.resolve();
    }
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
    if (name === "orchestration" || name === "livepack" || name === "fleet") {
      if (lastOverview) {
        applyOverview(lastOverview);
      } else {
        load();
      }
      if (name === "fleet") {
        bindFleetRunButtons();
        loadFleetPreflight();
      }
    }
  }

  function init() {
    document.addEventListener("click", onAppClick, true);
    var unlock = $("unlock");
    if (unlock) unlock.addEventListener("click", function () {
      var k = $("key").value.trim();
      if (!k) return;
      setKey(k);
      load().then(function () { if (getKey()) showApp(); });
    });
    var keyEl = $("key");
    if (keyEl) keyEl.addEventListener("keydown", function (e) { if (e.key === "Enter" && $("unlock")) $("unlock").click(); });
    var lockBtn = $("lock");
    if (lockBtn) lockBtn.addEventListener("click", function () { clearKey(); showGate(); });
    var refreshBtn = $("refresh");
    if (refreshBtn) refreshBtn.addEventListener("click", function () { load({ force: true }); });
    var killBtn = $("kill");
    if (killBtn) killBtn.addEventListener("click", function () {
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
