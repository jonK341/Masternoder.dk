/* Agent marketplace + cross-trade calculator widget for the exchange page. */
(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };
  function money(n) { var v = Number(n || 0); return (v < 0 ? "-$" : "$") + Math.abs(v).toFixed(2); }
  function skillChips(details, compact) {
    details = details || [];
    if (!details.length) return "";
    return '<div class="cex-skill-chips">' + details.map(function (s) {
      return '<span class="cex-skill-chip cex-skill-' + (s.category || "misc") + '" title="' +
        (s.description || "").replace(/"/g, "") + '">' + (s.name || s.id) +
        (compact ? "" : ' <small>' + (s.edge_bps || 0) + "bps</small>") + "</span>";
    }).join("") + "</div>";
  }
  function skillSetBadge(set) {
    if (!set || !set.name) return "";
    return '<span class="cex-skill-set-badge" title="' + (set.description || "").replace(/"/g, "") + '">' +
      set.name + "</span>";
  }
  function gameTime(sec) {
    sec = Number(sec || 0);
    var h = Math.floor(sec / 3600);
    if (h < 24) return h + "h";
    return Math.floor(h / 24) + "d " + (h % 24) + "h";
  }

  function api(path, opts) {
    opts = opts || {};
    var headers = {};
    if (opts.body) headers["Content-Type"] = "application/json";
    return fetch(path, {
      method: opts.method || "GET",
      headers: headers,
      credentials: "same-origin",
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    }).then(function (r) { return r.json().catch(function () { return {}; }); });
  }

  function renderCatalog(data) {
    var c = $("cex-market-catalog");
    if (!c) return;
    if (!data || !data.templates || !data.templates.length) { c.textContent = "No agents available."; return; }
    c.innerHTML = "";
    data.templates.forEach(function (t) {
      var p = t.projection || {};
      var card = document.createElement("div");
      card.className = "cex-market-card";
      card.innerHTML =
        '<div class="cex-market-tier">' + (t.tier || "") + "</div>" +
        "<h4>" + t.name + " " + skillSetBadge(t.skill_set) + "</h4>" +
        '<p class="cex-market-desc">' + (t.description || "") + "</p>" +
        skillChips(t.skill_details) +
        '<div class="cex-market-meta">Blended edge ' + (t.blended_edge_bps || p.blended_edge_bps || 0) +
        " bps · Capital " + money(t.capital_usd) + "</div>" +
        '<div class="cex-market-meta">Est. monthly ' + money(p.monthly_profit_usd) + " (" + (p.monthly_roi_pct || 0) + "%)</div>" +
        '<div class="cex-market-price">' + (t.price_mn2 || 0) + " MN2 · " + money(t.price_usd) + "</div>" +
        '<button type="button" class="cex-btn" data-buy="' + t.id + '">Buy bot</button>' +
        '<button type="button" class="cex-btn cex-btn--ghost" data-ctrl-buy="' + t.id + '">Checkout</button>';
      c.appendChild(card);
    });
    Array.prototype.forEach.call(c.querySelectorAll("button[data-buy]"), function (b) {
      b.addEventListener("click", function () { buy(b.getAttribute("data-buy"), b); });
    });
    Array.prototype.forEach.call(c.querySelectorAll("[data-ctrl-buy]"), function (b) {
      b.addEventListener("click", function () { ctrlPrefill("buy", b.getAttribute("data-ctrl-buy")); });
    });
  }

  function buy(templateId, btn) {
    if (btn) { btn.disabled = true; btn.textContent = "Buying…"; }
    api("/api/exchange/marketplace/purchase", { method: "POST", body: { template_id: templateId } }).then(function (res) {
      if (!res || !res.success) {
        alert("Purchase failed: " + ((res && res.error) || "error"));
        if (btn) { btn.disabled = false; btn.textContent = "Buy bot"; }
        return;
      }
      loadPortfolio();
      loadLevel();
      loadMonitor();
      loadWatch();
      loadTrust();
      loadCatalog();
      loadController();
      if (btn) { btn.textContent = "Owned ✓"; }
    });
  }

  function renderPortfolio(data) {
    var c = $("cex-market-portfolio");
    if (!c) return;
    if (!data || !data.success) { c.textContent = "Sign in to see your bots."; return; }
    if (!data.agents || !data.agents.length) { c.textContent = "No bots yet — buy one above."; return; }
    var proj = data.projection || {};
    var head = '<div class="cex-port-head">Realized ' + money(data.total_realized_profit_usd) +
      " · daily est " + money(proj.combined_daily_profit_usd) + "</div>";
    c.innerHTML = head + data.agents.map(function (a) {
      var set = a.skill_set && a.skill_set.name ? " · " + a.skill_set.name : "";
      return '<div class="cex-port-row"><div><span>' + a.name + set + "</span>" +
        skillChips(a.skill_details, true) +
        '</div><span class="cex-port-meta">' + money(a.realized_profit_usd) + " · " +
        gameTime(a.game_time_sec) + " · " + (a.trade_count || 0) + " ticks</span></div>";
    }).join("");
  }

  var LEVEL_STATE = { claimable: [] };

  function renderLevel(d) {
    if (!d || !d.success) return;
    var rank = $("cex-level-rank"); if (rank) rank.textContent = (d.rank && d.rank.icon ? d.rank.icon + " " : "") + (d.rank ? d.rank.name : "Trader");
    var num = $("cex-level-num"); if (num) num.textContent = "Level " + d.level;
    var xp = $("cex-level-xp"); if (xp) xp.textContent = Math.round(d.xp_into_level) + " / " + Math.round(d.xp_for_next) + " XP";
    var fill = $("cex-level-fill"); if (fill) fill.style.width = (d.progress_pct || 0) + "%";
    var perks = $("cex-level-perks");
    if (perks) perks.textContent = "Fee discount " + (d.fee_discount_bps || 0) + " bps · " +
      d.achievements_unlocked + "/" + d.achievements_total + " achievements";
    LEVEL_STATE.claimable = d.claimable_levels || [];
    var claim = $("cex-level-claim");
    if (claim) {
      if (LEVEL_STATE.claimable.length) { claim.style.display = ""; claim.textContent = "Claim level " + LEVEL_STATE.claimable[0]; }
      else claim.style.display = "none";
    }
    var ach = $("cex-ach");
    if (ach) {
      ach.innerHTML = (d.achievements || []).map(function (a) {
        return '<div class="cex-ach-item ' + (a.unlocked ? "on" : "off") + '" title="' +
          (a.desc || "").replace(/"/g, "") + " (" + a.progress + "/" + a.target + ")">' +
          '<span class="cex-ach-icon">' + (a.icon || "🏅") + "</span>" +
          '<span class="cex-ach-name">' + a.name + "</span></div>";
      }).join("");
    }
  }

  function loadLevel() { api("/api/exchange/leveling/me").then(renderLevel); }

  function renderTrust(d) {
    if (!d || !d.success) return;
    var tier = $("cex-trust-tier");
    if (tier) tier.textContent = (d.tier && d.tier.icon ? d.tier.icon + " " : "") + (d.tier ? d.tier.name : "Unverified");
    var sc = $("cex-trust-score");
    if (sc) sc.textContent = "Trust " + (d.trust_score || 0);
    var auto = $("cex-trust-auto");
    if (auto) auto.checked = !!(d.controls && d.controls.global_auto_run);
    var alerts = $("cex-trust-alerts");
    if (alerts) alerts.checked = d.controls ? d.controls.trust_alerts !== false : true;
    var acts = $("cex-trust-activations");
    if (acts) {
      acts.innerHTML = (d.activations || []).map(function (a) {
        return '<span class="cex-trust-act ' + (a.allowed ? "on" : "off") + '" title="' + (a.description || "") + '">' +
          a.name + (a.allowed ? " ✓" : " 🔒") + "</span>";
      }).join("");
    }
  }

  function saveTrustControls() {
    api("/api/exchange/trust/controls", { method: "POST", body: {
      global_auto_run: !!($("cex-trust-auto") && $("cex-trust-auto").checked),
      trust_alerts: !!($("cex-trust-alerts") && $("cex-trust-alerts").checked),
    } }).then(loadTrust);
  }

  function loadTrust() { api("/api/exchange/trust/me").then(renderTrust); }

  function activateAgent(agentId, mode) {
    api("/api/exchange/trust/agent/activate", { method: "POST", body: { agent_id: agentId, activation: mode || "active" } })
      .then(function () { loadWatch(); loadPortfolio(); loadMonitor(); });
  }

  function renderWatch(d) {
    if (!d || !d.success) return;
    var sm = $("cex-watch-summary");
    var t = d.totals || {};
    var tr = d.trust || {};
    if (sm) sm.innerHTML =
      '<span class="cex-mon-kpi"><b>' + (tr.tier && tr.tier.icon ? tr.tier.icon + " " : "") + (tr.trust_score || 0) + "</b> user trust</span>" +
      '<span class="cex-mon-kpi"><b>IQ ' + (t.avg_composite_iq || 100) + "</b> composite</span>" +
      '<span class="cex-mon-kpi"><b>' + (t.active_agents || 0) + "</b> active</span>" +
      '<span class="cex-mon-kpi"><b>' + (t.pending_activation || 0) + "</b> pending</span>";
    var ag = $("cex-watch-agents");
    if (ag) {
      ag.innerHTML = (d.agents || []).map(function (a) {
        var act = a.activation || "pending";
        var btns = act === "pending"
          ? '<button type="button" class="cex-btn cex-btn--ghost cex-act-btn" data-act="' + a.agent_id + '">Activate</button>'
          : (act === "active"
            ? '<button type="button" class="cex-btn cex-btn--ghost cex-act-btn" data-pause="' + a.agent_id + '">Pause</button>'
            : '<button type="button" class="cex-btn cex-btn--ghost cex-act-btn" data-act="' + a.agent_id + '">Resume</button>');
        return '<div class="cex-watch-row"><div><b>' + a.name + '</b> <span class="cex-port-lvl">' +
          act + " · trust " + (a.trust_score || 0) + " · IQ " + (a.composite_iq || 100) + "</span></div>" + btns + "</div>";
      }).join("") || '<div class="cex-mon-empty">No agents — buy one in the marketplace.</div>';
      Array.prototype.forEach.call(ag.querySelectorAll("[data-act]"), function (b) {
        b.addEventListener("click", function () { activateAgent(b.getAttribute("data-act"), "active"); });
      });
      Array.prototype.forEach.call(ag.querySelectorAll("[data-pause]"), function (b) {
        b.addEventListener("click", function () { activateAgent(b.getAttribute("data-pause"), "paused"); });
      });
    }
  }

  function loadAiTrading() {
    var panel = $("cex-ai-trading");
    if (!panel) return;
    api("/api/exchange/ai-trading/status").then(function (d) {
      var mode = $("cex-ai-mode");
      if (mode) mode.textContent = (d && d.mode) ? d.mode.toUpperCase() : "PAPER";
      var st = $("cex-ai-status");
      if (st && d && d.success) {
        var a = d.account || {};
        st.innerHTML =
          "<span>Profit " + money(a.realized_profit_usd) + "</span>" +
          "<span>Ticks " + (a.trade_count || 0) + "</span>" +
          "<span>Venues " + ((d.venue_capabilities && d.venue_capabilities.venues) ? d.venue_capabilities.venues.length : 0) + "</span>";
      }
    });
  }

  function runAiAnalyze(btn) {
    if (btn) { btn.disabled = true; btn.textContent = "Analyzing…"; }
    api("/api/exchange/ai-trading/analyze").then(function (d) {
      var pick = $("cex-ai-top-pick");
      if (pick && d && d.success && d.top_pick) {
        var t = d.top_pick;
        pick.innerHTML = "<strong>" + t.symbol + "</strong> buy@" + t.buy_venue + " sell@" + t.sell_venue +
          " · AI " + t.ai_score + " · net " + t.net_bps + " bps · est " + money(t.est_profit_usd) +
          (t.actionable ? " ✓ actionable" : "");
        pick.classList.remove("muted");
      } else if (pick) {
        pick.textContent = "No actionable spread right now.";
        pick.classList.add("muted");
      }
      loadAiTrading();
      if (btn) { btn.disabled = false; btn.textContent = "Analyze market"; }
    });
  }

  function loadWatch() {
    if (!$("cex-live-watch")) return;
    api("/api/exchange/live-watch?limit=50").then(renderWatch);
  }

  function renderMonitor(d) {
    if (!d || !d.success) return;
    var t = d.totals || {};
    var tot = $("cex-monitor-totals");
    if (tot) tot.innerHTML =
      '<span class="cex-mon-kpi"><b>' + money(t.realized_profit_usd) + "</b> realized</span>" +
      '<span class="cex-mon-kpi"><b>' + money(t.projected_daily_usd) + "</b>/day est</span>" +
      '<span class="cex-mon-kpi"><b>' + (t.active_bots || 0) + "/" + (t.bot_count || 0) + "</b> bots live</span>" +
      '<span class="cex-mon-kpi"><b>IQ ' + (t.avg_intelligence || 100) + "</b> avg</span>" +
      '<span class="cex-mon-kpi"><b>Trust ' + (t.avg_trust || 0) + "</b> avg</span>" +
      '<span class="cex-mon-kpi"><b>' + gameTime(t.total_game_time_sec) + "</b> run time</span>";
    var ut = d.user_trust || {};
    if (ut.tier && tot) {
      tot.innerHTML += '<span class="cex-mon-kpi"><b>' + (ut.tier.icon || "") + " " + (ut.trust_score || 0) + "</b> you</span>";
    }
    var bc = $("cex-monitor-bots");
    if (bc) {
      bc.innerHTML = (d.bots || []).map(function (b) {
        var skills = (b.top_skills || []).map(function (s) { return s.skill_id + " " + s.proficiency_pct + "%"; }).join(" · ");
        return '<div class="cex-mon-bot"><div class="cex-mon-bot-top"><span>' +
          (b.super ? "⭐ " : "") + b.name + ' <span class="cex-port-lvl">Lv ' + b.agent_level + " · IQ " + b.intelligence +
          " · trust " + (b.trust_score || 0) + " · " + (b.activation || "?") + "</span></span><span>" +
          money(b.realized_profit_usd) + "</span></div>" +
          '<div class="cex-mon-bot-sub">mastery ' + (b.mastery_pct || 0) + "% · +" + (b.learning_bonus_bps || 0) + " bps learned · " + gameTime(b.game_time_sec) +
          (skills ? " · " + skills : "") + "</div></div>";
      }).join("") || '<div class="cex-mon-empty">No bots running yet.</div>';
    }
    var fc = $("cex-monitor-feed");
    if (fc) {
      fc.innerHTML = (d.feed || []).map(function (f) {
        var when = f.ts ? new Date(f.ts).toLocaleTimeString() : "";
        return '<div class="cex-mon-feed-row ' + (f.scope === "you" ? "you" : "market") + '">' +
          '<span class="cex-mon-feed-ic">' + f.icon + "</span>" +
          '<span class="cex-mon-feed-tx">' + f.text + "</span>" +
          '<span class="cex-mon-feed-ts">' + when + "</span></div>";
      }).join("") || '<div class="cex-mon-empty">No activity yet — buy a bot and press “Run my bots”.</div>';
    }
  }

  function loadMonitor() {
    if (!$("cex-live-monitor")) return;
    api("/api/exchange/monitor/live?limit=40").then(renderMonitor);
  }

  function claimLevel() {
    if (!LEVEL_STATE.claimable.length) return;
    api("/api/exchange/leveling/claim", { method: "POST", body: { level: LEVEL_STATE.claimable[0] } }).then(loadLevel);
  }

  function renderRadar(data) {
    var c = $("cex-radar-list");
    if (!c) return;
    if (!data || !data.opportunities || !data.opportunities.length) { c.textContent = "No live signals yet."; return; }
    var arrow = { up: "▲", down: "▼", flat: "▬" };
    c.innerHTML = data.opportunities.map(function (o) {
      var dirCls = o.direction === "up" ? "up" : (o.direction === "down" ? "down" : "flat");
      return '<div class="cex-radar-row">' +
        '<span class="cex-radar-sym">' + o.symbol + "</span>" +
        '<span class="cex-radar-dir ' + dirCls + '">' + (arrow[o.direction] || "") + " " + o.direction + "</span>" +
        "<span>conf " + o.confidence_pct + "%</span>" +
        "<span>edge " + o.edge_uplift_bps + " bps</span>" +
        "<span>score " + o.score + "</span>" +
        "</div>";
    }).join("");
  }

  var ALL_SKILLS = [];

  function renderSkillSets(data) {
    var grid = $("cex-skill-set-grid");
    if (!grid || !data || !data.success) return;
    ALL_SKILLS = data.skills || [];
    var sets = data.skill_sets || [];
    grid.innerHTML = sets.map(function (s) {
      var ids = s.skills || [];
      var details = ids.map(function (id) {
        var sk = ALL_SKILLS.filter(function (x) { return x.id === id; })[0];
        return sk ? { id: id, name: sk.name, category: sk.category, description: sk.description, edge_bps: sk.base_edge_bps } : { id: id, name: id };
      });
      return '<div class="cex-skill-set-card"><div class="cex-skill-set-head">' +
        '<span class="cex-skill-set-tier">' + (s.tier || "Set") + "</span>" +
        "<h4>" + s.name + "</h4></div>" +
        '<p class="cex-market-desc">' + (s.description || "") + "</p>" +
        skillChips(details) + "</div>";
    }).join("") || '<div class="cex-mon-empty">No skill sets loaded.</div>';
    var pick = $("cex-calc-skills");
    if (pick && ALL_SKILLS.length) {
      var dl = $("cex-calc-skill-list");
      if (dl) dl.innerHTML = ALL_SKILLS.map(function (s) {
        return '<option value="' + s.id + '">' + s.name + "</option>";
      }).join("");
    }
  }

  function loadSkillSets() {
    if (!$("cex-skill-sets")) return;
    api("/api/exchange/bot-skills").then(renderSkillSets);
  }

  function loadCatalog() { api("/api/exchange/marketplace/catalog").then(renderCatalog); }
  function loadPortfolio() { api("/api/exchange/marketplace/portfolio").then(renderPortfolio); }
  function loadRadar() { api("/api/exchange/profit-tools/radar?limit=8").then(renderRadar); }

  function runAll() {
    var btn = $("cex-market-run-all");
    if (btn) { btn.disabled = true; btn.textContent = "Running…"; }
    api("/api/exchange/marketplace/run", { method: "POST", body: {} }).then(function () {
      loadPortfolio();
      loadLevel();
      loadMonitor();
      loadWatch();
      loadTrust();
      if (btn) { btn.disabled = false; btn.textContent = "Run my bots"; }
    });
  }

  function calculate() {
    var skills = ($("cex-calc-skills").value || "").split(",").map(function (s) { return s.trim(); }).filter(Boolean);
    var body = {
      capital_usd: Number($("cex-calc-capital").value || 0),
      skills: skills,
      volatility: Number($("cex-calc-vol").value || 0.35),
      cycles_per_day: Number($("cex-calc-cycles").value || 24),
      risk_level: $("cex-calc-risk").value,
    };
    api("/api/exchange/calculator/cross-trade", { method: "POST", body: body }).then(function (r) {
      var el = $("cex-calc-result");
      if (!r || !r.success) { el.textContent = "Calculation failed."; return; }
      el.innerHTML =
        '<div class="cex-calc-big">' + money(r.monthly_profit_usd) + " <span>/ month</span></div>" +
        "<div>Edge " + r.blended_edge_bps + " bps · position " + money(r.position_usd) + "</div>" +
        "<div>Daily " + money(r.daily_profit_usd) + " · ROI " + r.monthly_roi_pct + "%/mo</div>" +
        "<div>Annual " + money(r.annual_profit_usd) + "</div>";
    });
  }

  var RENT_AGENT = "";
  var MY_RENTALS = [];
  var CTRL_CATALOG = { rentals: [], addons: [], shop_items: [] };
  var CTRL_HUB = null;
  var CTRL_QUOTE = null;

  function rentalAgentOptions(selected) {
    var opts = (MY_RENTALS || []).filter(function (r) { return !r.expired; });
    if (!opts.length) return "";
    return '<label class="cex-addon-pick">Attach to: <select class="cex-rental-agent-select">' +
      opts.map(function (r) {
        return '<option value="' + r.agent_id + '"' + (r.agent_id === selected ? " selected" : "") + ">" +
          (r.name || r.agent_id) + " (" + (r.days_left || 0) + "d)</option>";
      }).join("") + "</select></label>";
  }

  function renderRentals(cat) {
    var c = $("cex-rental-catalog");
    if (!c || !cat) return;
    c.innerHTML = (cat.rentals || []).map(function (r) {
        return '<div class="cex-rental-card"><img src="' + (r.image || "") + '" alt="" class="cex-card-img" />' +
        "<h4>" + r.name + (r.daemon ? ' <span class="cex-daemon-badge-daemon">Daemon</span>' : "") +
        " " + skillSetBadge(r.skill_set) + "</h4><p>" + (r.description || "") + "</p>" +
        skillChips(r.skill_details) +
        '<div class="cex-market-price">' + r.price_mn2 + " MN2 · " + r.days + " days · " +
        (r.blended_edge_bps || 0) + " bps edge</div>" +
        '<button type="button" class="cex-btn" data-rent="' + r.id + '">Rent now</button>' +
        '<button type="button" class="cex-btn cex-btn--ghost" data-ctrl-rent="' + r.id + '">Checkout</button></div>';
    }).join("");
    Array.prototype.forEach.call(c.querySelectorAll("[data-rent]"), function (b) {
      b.addEventListener("click", function () {
        api("/api/exchange/rental/rent", { method: "POST", body: { rental_id: b.getAttribute("data-rent"), auto_renew: !!document.getElementById("cex-rent-auto-new") && document.getElementById("cex-rent-auto-new").checked } })
          .then(function (r) {
            if (!r || !r.success) { alert("Rent failed: " + ((r && r.error) || "")); return; }
            loadMyRentals(); loadPortfolio(); loadWatch(); loadController(); loadDaemonConfig();
          });
      });
    });
    Array.prototype.forEach.call(c.querySelectorAll("[data-ctrl-rent]"), function (b) {
      b.addEventListener("click", function () {
        ctrlPrefill("rent", b.getAttribute("data-ctrl-rent"));
      });
    });
    var ag = $("cex-rental-addons");
    if (ag) {
      ag.innerHTML = rentalAgentOptions(RENT_AGENT) + (cat.skill_addons || []).map(function (a) {
        return '<div class="cex-addon-card"><img src="' + (a.image || "") + '" alt="" width="48" height="48" />' +
          "<span>" + a.name + "</span><span>" + a.price_mn2 + " MN2</span>" +
          skillChips(a.skill_details, true) +
          '<button type="button" class="cex-btn cex-btn--ghost" data-addon="' + a.id + '">Add skill</button>' +
          '<button type="button" class="cex-btn cex-btn--ghost" data-ctrl-addon="' + a.id + '">Checkout</button></div>';
      }).join("");
      Array.prototype.forEach.call(ag.querySelectorAll("[data-addon]"), function (b) {
        b.addEventListener("click", function () {
          var sel = ag.querySelector(".cex-rental-agent-select");
          var aid = (sel && sel.value) || RENT_AGENT || prompt("Agent ID to attach skill to:");
          if (!aid) return;
          api("/api/exchange/rental/add-skill", { method: "POST", body: { agent_id: aid, addon_id: b.getAttribute("data-addon") } })
            .then(function (r) {
              if (!r || !r.success) { alert("Addon failed: " + ((r && r.error) || "")); return; }
              loadMyRentals(); loadPortfolio(); loadController();
            });
        });
      });
      Array.prototype.forEach.call(ag.querySelectorAll("[data-ctrl-addon]"), function (b) {
        b.addEventListener("click", function () {
          var sel = ag.querySelector(".cex-rental-agent-select");
          var aid = (sel && sel.value) || RENT_AGENT;
          ctrlPrefill("addon", b.getAttribute("data-ctrl-addon"), aid);
        });
      });
    }
  }

  function loadMyRentals() {
    api("/api/exchange/rental/mine").then(function (d) {
      var el = $("cex-my-rentals");
      if (!el || !d || !d.success) return;
      if (d.rentals && d.rentals[0]) RENT_AGENT = d.rentals[0].agent_id;
      MY_RENTALS = d.rentals || [];
      el.innerHTML = "<h4 class=\"cex-monitor-h4\">My rentals</h4>" + (d.rentals || []).map(function (r) {
        var venues = (r.farm_venues || []).slice(0, 4).join(", ");
        return '<div class="cex-watch-row"><div><b>' + r.name + "</b>" +
          (r.is_daemon ? ' <span class="cex-daemon-badge-daemon">Daemon</span>' : "") +
          " · " + (r.days_left || 0) + "d left · skills: " +
          (r.effective_skills || []).join(", ") +
          (venues ? " · venues: " + venues : "") +
          (r.expired ? " (expired)" : "") +
          (r.auto_renew ? " · auto-renew on" : "") + "</div>" +
          (!r.expired ? '<label class="cex-auto-renew"><input type="checkbox" data-auto-renew="' + r.agent_id + '"' +
            (r.auto_renew ? " checked" : "") + " /> Auto-renew (-10%)</label>" : "") +
          (r.expired && !r.reward_claimed ? '<button type="button" class="cex-btn cex-btn--ghost" data-claim="' + r.agent_id + '">Claim reward</button>' : "") +
          "</div>";
      }).join("") || '<div class="cex-mon-empty">No active rentals.</div>';
      Array.prototype.forEach.call(el.querySelectorAll("[data-auto-renew]"), function (cb) {
        cb.addEventListener("change", function () {
          api("/api/exchange/rental/auto-renew", { method: "POST", body: { agent_id: cb.getAttribute("data-auto-renew"), enabled: cb.checked } })
            .then(function (res) {
              if (!res || !res.success) { cb.checked = !cb.checked; alert("Auto-renew failed: " + ((res && res.error) || "")); }
            });
        });
      });
      Array.prototype.forEach.call(el.querySelectorAll("[data-claim]"), function (b) {
        b.addEventListener("click", function () {
          api("/api/exchange/rental/claim-reward", { method: "POST", body: { agent_id: b.getAttribute("data-claim") } }).then(loadMyRentals);
        });
      });
    });
  }

  function loadRentalCatalog() { api("/api/exchange/rental/catalog").then(renderRentals); }

  function renderShop(cat, st) {
    var c = $("cex-shop-catalog");
    if (c) {
      c.innerHTML = (cat.items || []).map(function (it) {
        return '<div class="cex-shop-card"><img src="' + (it.image || "") + '" alt="" width="56" height="56" />' +
          "<h4>" + it.name + "</h4><p>" + (it.description || "") + "</p>" +
          skillChips(it.skill_details, true) +
          '<div class="cex-market-price">' + it.price_mn2 + " MN2</div>" +
          '<button type="button" class="cex-btn" data-shop="' + it.id + '">Buy MN2</button>' +
          '<button type="button" class="cex-btn cex-btn--ghost" data-ctrl-shop="' + it.id + '">Checkout</button></div>';
      }).join("");
      Array.prototype.forEach.call(c.querySelectorAll("[data-shop]"), function (b) {
        b.addEventListener("click", function () {
          var id = b.getAttribute("data-shop");
          var body = { item_id: id };
          if (id === "ex_skill_pack_arb" || id === "ex_rental_extension_3d") {
            var sel = $("cex-rental-addons") && $("cex-rental-addons").querySelector(".cex-rental-agent-select");
            var aid = (sel && sel.value) || RENT_AGENT || prompt("Agent ID (for skill pack / extension):");
            if (aid) body.agent_id = aid;
          }
          api("/api/exchange/shop/purchase", { method: "POST", body: body }).then(function (r) {
            if (!r || !r.success) { alert("Purchase failed: " + ((r && r.error) || "")); return; }
            loadShop(); loadPortfolio(); loadMyRentals(); loadController();
          });
        });
      });
      Array.prototype.forEach.call(c.querySelectorAll("[data-ctrl-shop]"), function (b) {
        b.addEventListener("click", function () {
          ctrlPrefill("shop", b.getAttribute("data-ctrl-shop"));
        });
      });
    }
    var act = $("cex-shop-active");
    if (act && st && st.active_effects) {
      var e = st.active_effects;
      act.textContent = "Active: profit x" + e.profit_multiplier + " · trust +" + e.trust_bonus +
        " · fee -" + e.fee_discount_bps + " bps · scan tokens " + e.scan_tokens;
    }
  }

  function loadShop() {
    Promise.all([
      api("/api/exchange/shop/catalog"),
      api("/api/exchange/shop/state"),
    ]).then(function (arr) { renderShop(arr[0], arr[1]); });
  }

  function ctrlUpdatePayRails(q) {
    Array.prototype.forEach.call(document.querySelectorAll("[data-pay]"), function (b) {
      var m = b.getAttribute("data-pay");
      var ok = true;
      if (m === "mn2" && q) ok = !!q.can_pay_mn2;
      if (m === "coins" && q) ok = !!q.can_pay_coins;
      b.disabled = !ok;
      b.classList.toggle("cex-btn--disabled", !ok);
    });
  }

  function ctrlPrefill(type, targetId, agentId) {
    var hub = $("cex-control-center");
    if (hub) hub.scrollIntoView({ behavior: "smooth", block: "start" });
    var ct = $("cex-ctrl-type"); if (ct) ct.value = type || "rent";
    ctrlTargetOptions();
    var tg = $("cex-ctrl-target");
    if (tg && targetId) tg.value = targetId;
    if (agentId) {
      var ag = $("cex-ctrl-agent");
      if (ag) ag.value = agentId;
    }
    ctrlToggleAgentWrap();
    ctrlRefreshQuote();
    ctrlMsg("Ready — pick payment method.", true);
  }

  function ctrlMsg(text, ok) {
    var el = $("cex-ctrl-msg");
    if (el) { el.textContent = text || ""; el.style.color = ok ? "#6ee7b7" : (text ? "#fca5a5" : ""); }
  }

  function ctrlTargetOptions() {
    var type = ($("cex-ctrl-type") || {}).value || "rent";
    var sel = $("cex-ctrl-target");
    if (!sel) return;
    var list = type === "rent" ? CTRL_CATALOG.rentals
      : type === "addon" ? CTRL_CATALOG.addons
      : type === "buy" ? CTRL_CATALOG.buy_bots
      : CTRL_CATALOG.shop_items;
    sel.innerHTML = (list || []).map(function (it) {
      return '<option value="' + it.id + '">' + (it.name || it.id) + "</option>";
    }).join("") || '<option value="">— none —</option>';
    ctrlRefreshQuote();
    ctrlToggleAgentWrap();
  }

  function ctrlToggleAgentWrap() {
    var type = ($("cex-ctrl-type") || {}).value || "rent";
    var wrap = $("cex-ctrl-agent-wrap");
    var ar = $("cex-ctrl-autorenew-wrap");
    var needAgent = type === "addon" || (type === "shop" && CTRL_QUOTE && CTRL_QUOTE.requires_agent_id);
    if (wrap) wrap.style.display = needAgent ? "" : "none";
    if (ar) ar.style.display = type === "rent" ? "" : "none";
  }

  function ctrlFillAgents() {
    var sel = $("cex-ctrl-agent");
    if (!sel) return;
    var agents = (CTRL_HUB && CTRL_HUB.agents) || [];
    var rentals = (CTRL_HUB && CTRL_HUB.rentals) || [];
    var rows = rentals.filter(function (r) { return !r.expired; }).concat(agents.map(function (a) {
      return { agent_id: a.agent_id, name: a.name, days_left: "owned" };
    }));
    sel.innerHTML = '<option value="">— select bot —</option>' + rows.map(function (r) {
      return '<option value="' + r.agent_id + '">' + (r.name || r.agent_id) + "</option>";
    }).join("");
  }

  function ctrlRefreshQuote() {
    var type = ($("cex-ctrl-type") || {}).value || "rent";
    var tid = ($("cex-ctrl-target") || {}).value;
    var qel = $("cex-ctrl-quote");
    if (!tid || !qel) { CTRL_QUOTE = null; if (qel) qel.textContent = "Select an item."; return; }
    api("/api/exchange/controller/quote", { method: "POST", body: { action: type, target_id: tid } }).then(function (q) {
      CTRL_QUOTE = q;
      if (!q || !q.success) { qel.textContent = "Quote failed."; ctrlUpdatePayRails(null); return; }
      var img = q.image ? '<img src="' + q.image + '" alt="" width="48" height="48" style="vertical-align:middle;margin-right:8px;border-radius:8px;" />' : "";
      qel.innerHTML = img +
        "<strong>" + (q.name || tid) + "</strong><br>" +
        q.price_mn2 + " MN2 · " + q.price_coins + " coins · $" + Number(q.price_usd || 0).toFixed(2) + " PayPal<br>" +
        (q.can_pay_mn2 ? "✓ MN2" : "✗ MN2") + " · " +
        (q.can_pay_coins ? "✓ coins" : "✗ coins") + " · PayPal OK";
      ctrlToggleAgentWrap();
      ctrlUpdatePayRails(q);
    });
  }

  function renderControllerHub(h) {
    CTRL_HUB = h;
    var w = $("cex-ctrl-wallet");
    if (w && h && h.success) {
      w.innerHTML =
        "<span><b>" + Number(h.balances.mn2 || 0).toFixed(4) + "</b> MN2</span>" +
        "<span><b>" + Math.round(h.balances.coins || 0) + "</b> coins</span>" +
        "<span>Profit <b>" + money(h.cash_out_available_usd) + "</b> cash-out</span>" +
        "<span>" + (h.rental_count || 0) + " rentals · " + (h.agent_count || 0) + " bots</span>";
    }
    var ci = $("cex-ctrl-cash-info");
    if (ci && h) ci.textContent = "Available " + money(h.cash_out_available_usd) + " (min " + money(h.cash_out_min_usd) + ")";
    ctrlFillAgents();
    var ag = $("cex-ctrl-agents");
    if (ag && h && h.rentals && h.rentals.length) {
      ag.innerHTML = "<h4 class=\"cex-monitor-h4\">Active rentals</h4>" + h.rentals.map(function (r) {
        return '<div class="cex-watch-row"><b>' + r.name + "</b> · " + (r.days_left || 0) + "d · " +
          (r.effective_skills || []).slice(0, 3).join(", ") + "</div>";
      }).join("");
    }
  }

  function ctrlCheckout(payMethod) {
    var type = ($("cex-ctrl-type") || {}).value || "rent";
    var tid = ($("cex-ctrl-target") || {}).value;
    if (!tid) { ctrlMsg("Pick an item first.", false); return; }
    var body = {
      action: type,
      target_id: tid,
      payment_method: payMethod,
      auto_renew: !!($("cex-ctrl-autorenew") && $("cex-ctrl-autorenew").checked),
    };
    var aid = ($("cex-ctrl-agent") || {}).value;
    if (aid) body.agent_id = aid;
    if ((type === "addon" || (CTRL_QUOTE && CTRL_QUOTE.requires_agent_id)) && !aid) {
      ctrlMsg("Select a bot for this item.", false);
      return;
    }
    ctrlMsg("Processing…", true);
    if (payMethod === "paypal") {
      api("/api/exchange/controller/paypal/create", { method: "POST", body: body }).then(function (res) {
        if (!res || !res.success) { ctrlMsg("PayPal: " + ((res && res.error) || "failed"), false); return; }
        try {
          sessionStorage.setItem("cex_ctrl_paypal_order", res.order_id || "");
          sessionStorage.setItem("cex_ctrl_paypal_action", type + ":" + tid);
        } catch (e) { /* ignore */ }
        if (res.approve_url) window.location.href = res.approve_url;
        else ctrlMsg("No PayPal URL returned.", false);
      });
      return;
    }
    api("/api/exchange/controller/checkout", { method: "POST", body: body }).then(function (res) {
      if (!res || !res.success) { ctrlMsg((res && res.error) || "Checkout failed", false); return; }
      ctrlMsg("Success — " + payMethod + " payment applied.", true);
      loadController(); loadMyRentals(); loadPortfolio(); loadShop(); loadWatch(); loadBridgeProduct();
      loadCatalog(); loadSkillSets(); loadDaemonConfig();
    });
  }

  function ctrlCashOut() {
    var dest = ($("cex-ctrl-cash-dest") || {}).value || "mn2";
    var amt = parseFloat(($("cex-ctrl-cash-amt") || {}).value || "0");
    api("/api/exchange/controller/cash-out", { method: "POST", body: { destination: dest, amount_usd: amt || 0 } })
      .then(function (res) {
        if (!res || !res.success) { ctrlMsg("Cash-out: " + ((res && res.error) || "failed"), false); return; }
        ctrlMsg("Cashed out " + money(res.granted && res.granted.amount_usd) + " → " + dest, true);
        loadController(); loadBridgeProduct();
      });
  }

  function handleControllerPayPalReturn() {
    var params = new URLSearchParams(window.location.search);
    if (params.get("controller_paypal") !== "success") return;
    var orderId = params.get("token") || "";
    try { orderId = orderId || sessionStorage.getItem("cex_ctrl_paypal_order") || ""; } catch (e) { /* ignore */ }
    if (!orderId) return;
    ctrlMsg("Confirming PayPal…", true);
    api("/api/exchange/controller/paypal/capture", { method: "POST", body: { order_id: orderId } }).then(function (res) {
      if (res && res.success) {
        ctrlMsg("PayPal purchase complete.", true);
        try { sessionStorage.removeItem("cex_ctrl_paypal_order"); } catch (e) { /* ignore */ }
        loadController(); loadMyRentals(); loadPortfolio(); loadShop(); loadBridgeProduct();
      } else ctrlMsg("Capture failed: " + ((res && res.error) || ""), false);
      if (window.history && window.history.replaceState) {
        window.history.replaceState({}, "", window.location.pathname + window.location.hash);
      }
    });
  }

  function loadController() {
    if (!$("cex-control-center")) return;
    Promise.all([
      api("/api/exchange/controller/hub"),
      api("/api/exchange/controller/catalog"),
    ]).then(function (arr) {
      renderControllerHub(arr[0]);
      if (arr[1] && arr[1].success) {
        CTRL_CATALOG = arr[1];
        ctrlTargetOptions();
      }
    });
  }

  function loadBridgeProduct() {
    Promise.all([
      api("/api/exchange/casino-bridge/quests"),
      api("/api/exchange/casino-bridge/leaderboard"),
    ]).then(function (arr) {
      var qel = $("cex-bridge-quests");
      var lb = $("cex-bridge-leaderboard");
      var qd = arr[0];
      if (qel && qd && qd.success) {
        qel.innerHTML = "<div><b>" + (qd.completed_count || 0) + "/" + (qd.total_count || 0) + "</b> quests · week " + (qd.week || "") + "</div>" +
          (qd.quests || []).map(function (q) {
            return '<div class="cex-quest-row' + (q.completed ? " done" : "") + '"><span>' + (q.icon || "•") + " " + q.label +
              "</span><span>" + (q.progress || 0) + "/" + q.target + "</span></div>";
          }).join("");
      }
      var ld = arr[1];
      if (lb && ld && ld.success) {
        lb.innerHTML = "<div><b>" + (ld.title || "Leaderboard") + "</b> · " + (ld.week || "") + "</div>" +
          (ld.leaderboard || []).slice(0, 8).map(function (r) {
            return '<div class="cex-lb-row"><span>#' + r.rank + " " + r.user_id + "</span><span>" + r.score + " pts</span></div>";
          }).join("") +
          (ld.your_rank ? '<div class="cex-lb-row"><span>You #' + ld.your_rank.rank + "</span><span>" + ld.your_rank.score + " pts</span></div>" : "");
      }
    });
  }

  var DAEMON_STATE = { config: null, venues: [], symbols: [] };

  function daemonSelectedVenues() {
    var chips = document.querySelectorAll("#cex-daemon-venues .cex-venue-chip input:checked");
    return Array.prototype.map.call(chips, function (c) { return c.value; });
  }

  function daemonSelectedSymbols() {
    var chips = document.querySelectorAll("#cex-daemon-symbols .cex-venue-chip input:checked");
    return Array.prototype.map.call(chips, function (c) { return c.value; });
  }

  function daemonSelectedBots() {
    var boxes = document.querySelectorAll("#cex-daemon-bots input[data-daemon-bot]:checked");
    return Array.prototype.map.call(boxes, function (c) { return c.getAttribute("data-daemon-bot"); });
  }

  function renderDaemonVenues(venues, selected) {
    var el = $("cex-daemon-venues");
    if (!el) return;
    var sel = selected || [];
    el.innerHTML = (venues || []).map(function (v) {
      var on = sel.indexOf(v.id) >= 0;
      return '<label class="cex-venue-chip' + (on ? " active" : "") + '"><input type="checkbox" value="' + v.id + '"' +
        (on ? " checked" : "") + (v.enabled === false ? " disabled" : "") + "> " +
        (v.name || v.id) + " <small>" + (v.fee_taker_bps || 0) + "bps</small></label>";
    }).join("");
    el.querySelectorAll("input").forEach(function (inp) {
      inp.addEventListener("change", function () {
        inp.parentElement.classList.toggle("active", inp.checked);
      });
    });
  }

  function renderDaemonSymbols(symbols, selected) {
    var el = $("cex-daemon-symbols");
    if (!el) return;
    var sel = selected || [];
    el.innerHTML = (symbols || []).map(function (s) {
      var on = sel.indexOf(s) >= 0;
      return '<label class="cex-venue-chip' + (on ? " active" : "") + '"><input type="checkbox" value="' + s + '"' +
        (on ? " checked" : "") + "> " + s + "</label>";
    }).join("");
    el.querySelectorAll("input").forEach(function (inp) {
      inp.addEventListener("change", function () {
        inp.parentElement.classList.toggle("active", inp.checked);
      });
    });
  }

  function renderDaemonBots() {
    var el = $("cex-daemon-bots");
    if (!el) return;
    var cfg = (DAEMON_STATE.config || {});
    var selected = cfg.agent_ids || [];
    Promise.all([
      api("/api/exchange/rental/mine"),
      api("/api/exchange/marketplace/my-agents"),
    ]).then(function (arr) {
      var rentals = (arr[0] && arr[0].rentals) || [];
      var owned = (arr[1] && arr[1].agents) || [];
      var rows = rentals.filter(function (r) { return !r.expired; }).concat(owned);
      if (!rows.length) {
        el.innerHTML = '<span class="muted">Rent a daemon bot below or buy from marketplace.</span>';
        return;
      }
      el.innerHTML = rows.map(function (r) {
        var id = r.agent_id;
        var on = !selected.length || selected.indexOf(id) >= 0;
        var tag = r.is_daemon ? " (daemon)" : r.rented ? " (rental)" : " (owned)";
        return '<label><input type="checkbox" data-daemon-bot="' + id + '"' + (on ? " checked" : "") + "> " +
          (r.name || id) + tag + "</label>";
      }).join("");
    });
  }

  function loadDaemonConfig() {
    if (!$("cex-daemon-control")) return;
    api("/api/exchange/daemon/config").then(function (d) {
      if (!d || !d.success) return;
      DAEMON_STATE.config = d.config || {};
      DAEMON_STATE.venues = d.available_venues || [];
      DAEMON_STATE.symbols = d.supported_symbols || [];
      var st = $("cex-daemon-status");
      var badge = $("cex-daemon-badge");
      if (st) {
        st.innerHTML =
          '<span class="cex-mon-kpi"><b>' + (DAEMON_STATE.config.venues || []).length + "</b> venues</span>" +
          '<span class="cex-mon-kpi"><b>' + (DAEMON_STATE.config.symbols || []).length + "</b> assets</span>" +
          '<span class="cex-mon-kpi">' + (DAEMON_STATE.config.strategy || "farm") + "</span>";
      }
      if (badge) badge.textContent = DAEMON_STATE.config.enabled !== false ? "ON" : "OFF";
      var strat = $("cex-daemon-strategy");
      if (strat && DAEMON_STATE.config.strategy) strat.value = DAEMON_STATE.config.strategy;
      var not = $("cex-daemon-notional");
      if (not && DAEMON_STATE.config.notional_usd) not.value = DAEMON_STATE.config.notional_usd;
      var auto = $("cex-daemon-auto");
      if (auto) auto.checked = DAEMON_STATE.config.auto_run_with_marketplace !== false;
      renderDaemonVenues(DAEMON_STATE.venues, DAEMON_STATE.config.venues);
      renderDaemonSymbols(DAEMON_STATE.symbols, DAEMON_STATE.config.symbols);
      renderDaemonBots();
    });
  }

  function saveDaemonConfig() {
    var body = {
      strategy: ($("cex-daemon-strategy") || {}).value,
      venues: daemonSelectedVenues(),
      symbols: daemonSelectedSymbols(),
      agent_ids: daemonSelectedBots(),
      notional_usd: Number(($("cex-daemon-notional") || {}).value || 250),
      auto_run_with_marketplace: !!($("cex-daemon-auto") && $("cex-daemon-auto").checked),
      enabled: true,
    };
    return api("/api/exchange/daemon/config", { method: "POST", body: body }).then(function (r) {
      var prev = $("cex-daemon-preview");
      if (prev) prev.textContent = r && r.success ? "Config saved." : "Save failed.";
      loadDaemonConfig();
      return r;
    });
  }

  function previewDaemon() {
    var prev = $("cex-daemon-preview");
    if (prev) prev.textContent = "Scanning live spreads…";
    api("/api/exchange/daemon/preview", {
      method: "POST",
      body: {
        venues: daemonSelectedVenues(),
        symbols: daemonSelectedSymbols(),
        notional_usd: Number(($("cex-daemon-notional") || {}).value || 250),
      },
    }).then(function (d) {
      if (!prev) return;
      if (!d || !d.success) { prev.textContent = "Scan failed."; return; }
      var top = (d.top_opportunities || []).slice(0, 4);
      prev.innerHTML = (d.profitable_count || 0) + " profitable / " + (d.opportunity_count || 0) + " scanned<br>" +
        (top.length ? top.map(function (o) {
          return o.symbol + " " + o.buy_venue + "→" + o.sell_venue + " " + o.net_bps + "bps ~" + money(o.est_profit_usd);
        }).join("<br>") : "No spreads above threshold right now.");
      prev.classList.remove("muted");
    });
  }

  function runDaemonNow() {
    var btn = $("cex-daemon-run");
    if (btn) { btn.disabled = true; btn.textContent = "Running…"; }
    saveDaemonConfig().then(function () {
      return api("/api/exchange/daemon/run", { method: "POST", body: {} });
    }).then(function (r) {
      var prev = $("cex-daemon-preview");
      if (prev) {
        prev.textContent = r && r.success
          ? ("Ran " + (r.ran || 0) + " bots · +" + money(r.total_profit_usd) + " this tick")
          : ("Daemon: " + ((r && r.error) || "failed") + (r.hint ? " — " + r.hint : ""));
        prev.classList.remove("muted");
      }
      loadPortfolio(); loadMonitor(); loadMyRentals(); loadDaemonConfig();
      if (btn) { btn.disabled = false; btn.textContent = "Run daemon now"; }
    });
  }

  function initDaemonControl() {
    if (!$("cex-daemon-control")) return;
    var save = $("cex-daemon-save"); if (save) save.addEventListener("click", saveDaemonConfig);
    var scan = $("cex-daemon-preview-btn"); if (scan) scan.addEventListener("click", previewDaemon);
    var run = $("cex-daemon-run"); if (run) run.addEventListener("click", runDaemonNow);
    loadDaemonConfig();
  }

  function initController() {
    if (!$("cex-control-center")) return;
    var ct = $("cex-ctrl-type"); if (ct) ct.addEventListener("change", ctrlTargetOptions);
    var tg = $("cex-ctrl-target"); if (tg) tg.addEventListener("change", ctrlRefreshQuote);
    Array.prototype.forEach.call(document.querySelectorAll("[data-pay]"), function (b) {
      b.addEventListener("click", function () { ctrlCheckout(b.getAttribute("data-pay")); });
    });
    var cb = $("cex-ctrl-cash-btn"); if (cb) cb.addEventListener("click", ctrlCashOut);
    handleControllerPayPalReturn();
    loadController();
    loadBridgeProduct();
  }

  function init() {
    if (!$("cex-agent-marketplace")) return;
    loadCatalog();
    loadSkillSets();
    loadPortfolio();
    loadRadar();
    loadLevel();
    loadMonitor();
    loadWatch();
    loadAiTrading();
    loadTrust();
    loadRentalCatalog();
    loadMyRentals();
    loadShop();
    initController();
    initDaemonControl();
    api("/api/exchange/leveling/daily", { method: "POST", body: {} }).then(loadLevel);
    var runBtn = $("cex-market-run-all"); if (runBtn) runBtn.addEventListener("click", runAll);
    var aiBtn = $("cex-ai-analyze-btn"); if (aiBtn) aiBtn.addEventListener("click", function () { runAiAnalyze(aiBtn); });
    var calcBtn = $("cex-calc-run"); if (calcBtn) calcBtn.addEventListener("click", calculate);
    var claimBtn = $("cex-level-claim"); if (claimBtn) claimBtn.addEventListener("click", claimLevel);
    var ta = $("cex-trust-auto"); if (ta) ta.addEventListener("change", saveTrustControls);
    var tl = $("cex-trust-alerts"); if (tl) tl.addEventListener("change", saveTrustControls);
    calculate();
    if ($("cex-live-monitor")) setInterval(function () { loadMonitor(); loadWatch(); loadAiTrading(); }, 15000);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
