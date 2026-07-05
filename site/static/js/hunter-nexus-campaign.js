/**
 * Nexus arc — loads levels from API, blurbs (LLM or template), faction, streak,
 * co-op, daily challenge, copilot, trophy echo, shop links; gates + claims.
 */
(function (global) {
  "use strict";

  const STORAGE_PLAY = "hunter_nexus_session_plays";

  const DIRECTORS = [
    { id: "analyst", label: "Analyst director", tone: "Telemetry favors concise actions. Favor precision clicks over bursts." },
    { id: "poet", label: "Poet director", tone: "Narrative texture is thicker today—read each beat twice before claiming." },
    { id: "operator", label: "Operator director", tone: "Systems-first: treat each tab like a route in a healthy stack." },
    { id: "archivist", label: "Archivist director", tone: "Milestones and history carry extra weight this session." },
    { id: "navigator", label: "Navigator director", tone: "Star Map and walkthroughs feel connected—chart both." },
  ];

  const HOOKS = [
    "Micro-twist: trophy triggers feel slightly snappier after a timeline glance.",
    "Ambient: soft combo glow lingers a breath longer between clicks.",
    "Session flavor: rewards copy reads warmer for this visit.",
    "Narrative: Season 2 threads echo in the trophy lattice.",
    "UX: progress chips emphasize deltas over absolutes today.",
  ];

  function hash32(str) {
    let h = 2166136261;
    const s = String(str);
    for (let i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }

  function userId() {
    try {
      const u = localStorage.getItem("game_user_id") || "default_user";
      localStorage.setItem("game_user_id", u);
      return u;
    } catch (e) {
      return "default_user";
    }
  }

  function bumpPlayCount() {
    try {
      const n = parseInt(localStorage.getItem(STORAGE_PLAY) || "0", 10) || 0;
      localStorage.setItem(STORAGE_PLAY, String(n + 1));
      return n + 1;
    } catch (e) {
      return 1;
    }
  }

  function playCount() {
    try {
      return parseInt(localStorage.getItem(STORAGE_PLAY) || "0", 10) || 0;
    } catch (e) {
      return 0;
    }
  }

  function sessionDirector() {
    const uid = userId();
    const day = new Date().toISOString().slice(0, 10);
    const plays = playCount();
    const h = hash32(uid + "|" + day + "|" + plays);
    const d = DIRECTORS[h % DIRECTORS.length];
    const hook = HOOKS[(h >>> 3) % HOOKS.length];
    const mut = 0.92 + (h % 17) / 100;
    return { director: d, hook, mut, plays, day };
  }

  function tabVisited(tab) {
    try {
      return sessionStorage.getItem("hunter_tab_visit_" + tab) === "1";
    } catch (e) {
      return false;
    }
  }

  function clickCount() {
    try {
      if (global.clickGame && typeof global.clickGame.getStats === "function") {
        return Number(global.clickGame.getStats().clicks || 0);
      }
    } catch (e) {}
    return 0;
  }

  function resolveGate(level, faction) {
    const g = level.gates;
    if (g && typeof g === "object" && faction && g[faction]) return g[faction];
    if (g && typeof g === "object" && Object.keys(g).length && !faction) return { type: "faction_chosen" };
    return level.gate;
  }

  function gateOk(gate, state, faction) {
    if (!gate) return true;
    const t = gate.type;
    if (t === "clicks") return clickCount() >= (gate.min || 0);
    if (t === "tab") return tabVisited(gate.tab);
    if (t === "faction_chosen") return !!(state.faction || faction);
    if (t === "battle_total_min") return Number(state.battle_total || 0) >= (gate.min || 1);
    if (t === "friends_min") return Number(state.friends_count || 0) >= (gate.min || 1);
    return true;
  }

  function gateLabel(gate, state) {
    if (!gate) return "Claim the previous chapter first.";
    const t = gate.type;
    if (t === "clicks") return "Gate: " + gate.min + " relaxed clicks (Trophy Hunt).";
    if (t === "tab") return 'Gate: open the “' + gate.tab + "” tab once this session.";
    if (t === "faction_chosen") return "Gate: choose Pathfinder, Vanguard, or Weaver below.";
    if (t === "battle_total_min")
      return "Gate: battle total ≥ " + gate.min + " (yours: " + (state.battle_total || 0) + "). Open Battle if needed.";
    if (t === "friends_min")
      return "Gate: friends ≥ " + gate.min + " (yours: " + (state.friends_count || 0) + ").";
    return "";
  }

  function notify(msg, kind) {
    if (window.gameNotifications && typeof window.gameNotifications.showNotification === "function") {
      window.gameNotifications.showNotification(msg, kind || "info");
    } else {
      alert(msg);
    }
  }

  async function refreshGlance() {
    const uid = userId();
    try {
      const r = await fetch(global.location.origin + "/api/points/all?user_id=" + encodeURIComponent(uid));
      const d = await r.json();
      const p = d && d.points ? d.points : {};
      function el(id, v) {
        var x = document.getElementById(id);
        if (x) x.textContent = v;
      }
      el("game-overview-level", String(p.level != null ? p.level : 1));
      el("game-overview-xp", String(p.xp_total != null ? p.xp_total : 0).replace(/\B(?=(\d{3})+(?!\d))/g, ","));
      el("game-overview-coins", String(p.coins != null ? p.coins : 0).replace(/\B(?=(\d{3})+(?!\d))/g, ","));
    } catch (e) {}
    try {
      if (global.unifiedPointCounters && typeof global.unifiedPointCounters.updateAllCounters === "function") {
        await global.unifiedPointCounters.updateAllCounters();
      }
    } catch (e) {}
  }

  async function claimLevel(levelId, meta) {
    const uid = userId();
    const res = await fetch(global.location.origin + "/api/game/hunters/nexus-claim", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: uid, level_id: levelId, metadata: meta || {} }),
    });
    return res.json();
  }

  async function postFaction(fac) {
    const uid = userId();
    const res = await fetch(global.location.origin + "/api/game/hunters/nexus-faction", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: uid, faction: fac }),
    });
    return res.json();
  }

  async function postDailyComplete() {
    const uid = userId();
    const res = await fetch(global.location.origin + "/api/game/hunters/nexus-daily-complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: uid }),
    });
    return res.json();
  }

  function goCopilot(tab) {
    if (tab === "battle") {
      global.location.href = "/battle";
      return;
    }
    var btn = document.querySelector('.game-tab[data-tab="' + tab + '"]');
    if (btn) btn.click();
    else notify("Open the " + tab + " section from the game tabs.", "info");
  }

  function render(root) {
    if (!root) return;
    root.innerHTML = '<div class="nexus-spin">Loading Nexus arc…</div>';
    const dir = sessionDirector();
    const uid = userId();
    const origin = global.location.origin;

    Promise.all([
      fetch(origin + "/api/game/hunters/nexus-levels").then(function (r) {
        return r.json();
      }),
      fetch(origin + "/api/game/hunters/nexus-state?user_id=" + encodeURIComponent(uid)).then(function (r) {
        return r.json();
      }),
    ])
      .then(function (pair) {
        var lvRes = pair[0];
        var state = pair[1];
        if (!lvRes.success || !lvRes.data || !lvRes.data.levels) throw new Error("levels");
        if (!state.success) throw new Error("state");
        var levels = lvRes.data.levels;
        var seasons = lvRes.data.seasons || {};
        var ids = levels
          .map(function (l) {
            return l.id;
          })
          .join(",");
        return fetch(
          origin +
            "/api/game/hunters/nexus-blurbs?user_id=" +
            encodeURIComponent(uid) +
            "&ids=" +
            encodeURIComponent(ids) +
            "&play_seed=" +
            encodeURIComponent(String(dir.plays)) +
            "&mood=" +
            encodeURIComponent(dir.director.id) +
            "&llm=1"
        )
          .then(function (r) {
            return r.json();
          })
          .then(function (bl) {
            return { levels: levels, seasons: seasons, state: state, blurbs: bl && bl.blurbs ? bl : { blurbs: {}, source: "template" } };
          });
      })
      .then(function (pack) {
        var levels = pack.levels;
        var state = pack.state;
        var blurbs = pack.blurbs.blurbs || {};
        var blurbSource = pack.blurbs.source || "template";
        var claimed = state.claimed || [];
        var faction = state.faction || null;

        root.innerHTML = "";

        var banner = document.createElement("div");
        banner.className = "nexus-session-banner";
        banner.innerHTML =
          "<div><h3>Session director</h3><p><strong>" +
          dir.director.label +
          "</strong> — " +
          dir.director.tone +
          '</p><span class="nexus-director-tag">Variant ' +
          dir.director.id +
          " · play #" +
          dir.plays +
          " · blurbs: " +
          blurbSource +
          "</span></div>" +
          "<div><h3>Live adjustment</h3><p>" +
          dir.hook +
          "</p><p class=\"nexus-muted\">Feel factor ≈ " +
          dir.mut.toFixed(2) +
          "×</p>" +
          '<p class="nexus-muted"><button type="button" class="nexus-claim-btn" id="nexus-new-play-btn" style="margin-top:8px;width:100%">New play seed</button></p></div>';
        root.appendChild(banner);
        document.getElementById("nexus-new-play-btn").addEventListener("click", function () {
          bumpPlayCount();
          render(root);
        });

        var strip = document.createElement("div");
        strip.className = "nexus-feature-strip";
        var streakN = Math.min(1.25, 1 + 0.02 * Math.min(12, Number(state.streak_days || 0)));
        strip.innerHTML =
          '<div class="nexus-mini-card"><strong>Nexus streak</strong> — ' +
          (state.streak_days || 0) +
          " consecutive visit day(s). Flavor bonus hint: up to ×" +
          streakN.toFixed(2) +
          " on director copy (cosmetic).</div>" +
          '<div class="nexus-mini-card"><strong>Co-op filament</strong> — friends: ' +
          (state.friends_count || 0) +
          '/3 for milestone gates. Progress ~' +
          (state.co_op_progress_pct || 0) +
          "%.</div>" +
          '<div class="nexus-mini-card"><strong>World phase</strong> — ' +
          (state.world_phase === 2 ? "Season 2 open (after nx_10)." : "Season 1 — reach nx_10.") +
          "</div>" +
          (function () {
            var te = String(state.trophy_echo || "");
            return te
              ? '<div class="nexus-mini-card"><strong>Trophy echo</strong> — ' +
                  escapeHtml(te).slice(0, 320) +
                  (te.length > 320 ? "…" : "") +
                  "</div>"
              : "";
          })();

        var cop = state.copilot || {};
        var copHtml =
          '<div class="nexus-mini-card"><strong>Agent co-pilot</strong> — ' +
          escapeHtml(cop.reason || "Follow the next chapter gate.") +
          " ";
        if (cop.next_tab === "battle") {
          copHtml += '<a class="nexus-copilot-go" href="/battle">Open Battle →</a>';
        } else if (cop.next_tab) {
          copHtml +=
            '<button type="button" class="nexus-copilot-go" data-copilot-tab="' +
            escapeHtml(cop.next_tab) +
            '">Go to tab</button>';
        }
        copHtml += "</div>";
        strip.insertAdjacentHTML("beforeend", copHtml);

        var dc = state.daily_challenge || {};
        var dcTab = dc.tab || "overview";
        var dcVisited = tabVisited(dcTab);
        var dailyHtml =
          '<div class="nexus-mini-card"><strong>Daily director</strong> — ' +
          escapeHtml(dc.title || "Daily visit") +
          '. <span class="nexus-muted">Open the “' +
          escapeHtml(dcTab) +
          "” tab, then claim +20 XP / +15 game points (once/day).</span> ";
        if (state.daily_bonus_claimed) {
          dailyHtml += '<em class="nexus-muted">Redeemed today.</em>';
        } else {
          dailyHtml +=
            '<button type="button" class="nexus-claim-btn" id="nexus-daily-btn" style="margin-top:8px;padding:6px 12px;font-size:0.8rem;" ' +
            (!dcVisited ? "disabled" : "") +
            ">Claim daily bonus</button>";
          if (!dcVisited) dailyHtml += ' <span class="nexus-muted">(open tab first)</span>';
        }
        dailyHtml += "</div>";
        strip.insertAdjacentHTML("beforeend", dailyHtml);

        root.appendChild(strip);

        var shopParts = [];
        if (state.shop_bundle_ch5) shopParts.push('<a href="/shop?nexus=ch5">Shop · ch5 unlock</a>');
        if (state.shop_bundle_ch10) shopParts.push('<a href="/shop?nexus=ch10">Shop · ch10 unlock</a>');
        if (state.shop_bundle_s2) shopParts.push('<a href="/shop?nexus=season2">Shop · Season 2</a>');
        if (shopParts.length) {
          var shop = document.createElement("p");
          shop.className = "nexus-shop-links";
          shop.innerHTML = "<strong>Bundles</strong> — " + shopParts.join(" ");
          root.appendChild(shop);
        }

        var factionCard = document.createElement("div");
        factionCard.className = "nexus-story-block";
        factionCard.innerHTML =
          "<h3>Branching path (Season 2)</h3><p>Choose once; nx_12 gates split by path. <strong>Pathfinder</strong> (guides), <strong>Vanguard</strong> (battle), <strong>Weaver</strong> (friends).</p>";
        var row = document.createElement("div");
        row.className = "nexus-faction-row";
        ["pathfinder", "vanguard", "weaver"].forEach(function (f) {
          var b = document.createElement("button");
          b.type = "button";
          b.className = "nexus-faction-btn" + (faction === f ? " active" : "");
          b.textContent = f;
          b.addEventListener("click", function () {
            postFaction(f).then(function (r) {
              if (r && r.success) render(root);
              else notify((r && r.error) || "Faction save failed", "warning");
            });
          });
          row.appendChild(b);
        });
        factionCard.appendChild(row);
        root.appendChild(factionCard);

        var story = document.createElement("div");
        story.className = "nexus-story-block";
        story.innerHTML =
          "<h3>" +
          (pack.seasons["1"] || "Season 1") +
          " · " +
          (pack.seasons["2"] || "Season 2") +
          "</h3><p>Twenty chapters write to your profile. Blurbs refresh per play (OpenAI when <code>OPENAI_API_KEY</code> is set).</p>";
        root.appendChild(story);

        var grid = document.createElement("div");
        grid.className = "nexus-level-grid";
        var orderIds = levels.map(function (L) {
          return L.id;
        });

        for (var i = 0; i < levels.length; i++) {
          (function (L, idx) {
            var prevId = idx === 0 ? null : orderIds[idx - 1];
            var prevDone = prevId ? claimed.indexOf(prevId) !== -1 : true;
            var isClaimed = claimed.indexOf(L.id) !== -1;
            var g = resolveGate(L, faction);
            var gateReady = gateOk(g, state, faction);
            var card = document.createElement("div");
            card.className = "nexus-level-card";
            if (isClaimed) card.classList.add("claimed");
            else if (!prevDone || !gateReady) card.classList.add("locked");
            var season = L.season != null ? "S" + L.season : "";
            var gateText = !prevDone ? "Complete previous chapter on the server." : gateLabel(g, state);
            var btnDisabled = isClaimed || !prevDone || !gateReady;
            var blurbText = blurbs[L.id] || "";
            card.innerHTML =
              "<h4>" +
              (idx + 1) +
              ". " +
              escapeHtml(L.title) +
              (season ? ' <span class="nexus-muted">(' + season + ")</span>" : "") +
              "</h4>" +
              '<div class="nexus-level-meta">+' +
              L.xp +
              " XP · +" +
              L.game_points +
              " game points</div>" +
              '<div class="nexus-level-story">' +
              escapeHtml(L.story || "") +
              "</div>" +
              (blurbText ? '<div class="nexus-blurb">' + escapeHtml(blurbText) + "</div>" : "") +
              '<div class="nexus-muted">' +
              escapeHtml(gateText) +
              "</div>" +
              '<button type="button" class="nexus-claim-btn" data-nexus-claim="' +
              escapeHtml(L.id) +
              '" ' +
              (btnDisabled ? "disabled" : "") +
              ">" +
              (isClaimed ? "Claimed" : !prevDone ? "Locked" : !gateReady ? "Gate open soon" : "Claim rewards") +
              "</button>";
            grid.appendChild(card);
            var btn = card.querySelector("[data-nexus-claim]");
            if (btn && !btnDisabled) {
              btn.addEventListener("click", function () {
                btn.disabled = true;
                claimLevel(L.id, { director: dir.director.id, day: dir.day, blurb_source: blurbSource })
                  .then(function (r) {
                    if (r && r.success) {
                      return refreshGlance().then(function () {
                        render(root);
                      });
                    }
                    btn.disabled = false;
                    var msg = (r && r.error) || "Claim failed";
                    if (r && r.error === "previous_level_required" && r.required_level_id) {
                      msg = "Claim the previous chapter first (" + r.required_level_id + ").";
                    }
                    notify(msg, "warning");
                  })
                  .catch(function () {
                    btn.disabled = false;
                    notify("Network error", "warning");
                  });
              });
            }
          })(levels[i], i);
        }
        root.appendChild(grid);

        var db = document.getElementById("nexus-daily-btn");
        if (db && !state.daily_bonus_claimed) {
          db.addEventListener("click", function () {
            db.disabled = true;
            postDailyComplete()
              .then(function (r) {
                if (r && r.success) {
                  notify("Daily bonus applied (+20 XP, +15 game points).", "info");
                  return refreshGlance().then(function () {
                    render(root);
                  });
                }
                db.disabled = false;
                notify((r && r.error) || "Daily claim failed", "warning");
              })
              .catch(function () {
                db.disabled = false;
                notify("Network error", "warning");
              });
          });
        }

        strip.querySelectorAll("[data-copilot-tab]").forEach(function (el) {
          el.addEventListener("click", function () {
            goCopilot(el.getAttribute("data-copilot-tab"));
          });
        });

        var foot = document.createElement("p");
        foot.className = "nexus-muted";
        foot.style.marginTop = "1rem";
        foot.innerHTML =
          '<a href="/profile?tab=points" style="color:#7fdbff">Unified points</a> · <a href="/battle" style="color:#7fdbff">Battle</a> · <a href="/social" style="color:#7fdbff">Social</a>';
        root.appendChild(foot);
      })
      .catch(function () {
        root.innerHTML =
          '<p class="nexus-muted">Could not load Nexus arc. Check API and refresh.</p>';
      });
  }

  function escapeHtml(s) {
    if (!s) return "";
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  global.HunterNexusCampaign = {
    render: render,
    refreshGlance: refreshGlance,
    sessionDirector: sessionDirector,
    bumpPlayCount: bumpPlayCount,
  };
})(typeof window !== "undefined" ? window : globalThis);
