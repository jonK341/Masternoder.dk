/**
 * 5D Fleet Progress Navigation Monitor — canvas, audio, voice, public API.
 */
(function () {
  "use strict";

  var API = "/api/exchange/fleet-progress-monitor/public?light=1";
  var POLL_MS = 12000;
  var state = { data: null, w: 0, bots: [], tick: 0, audio: null, voiceOn: false, lastNarration: "" };

  function $(id) {
    return document.getElementById(id);
  }

  function qs(name) {
    var m = new RegExp("[?&]" + name + "=([^&]*)").exec(window.location.search);
    return m ? decodeURIComponent(m[1]) : "";
  }

  var streamMode = qs("mode") === "stream" || qs("stream") === "1";

  function setStatus(msg) {
    var el = $("f5-status");
    if (el) el.textContent = msg || "";
  }

  function buildExtraNodes(d) {
    var nodes = [];
    (d.casino && d.casino.recent || []).slice(0, 6).forEach(function (r, i) {
      nodes.push({ label: "🎰", kind: "casino", i: i, hue: "#ff64ff" });
    });
    (d.agents && d.agents.recent || []).slice(0, 6).forEach(function (r, i) {
      nodes.push({ label: "🤖", kind: "agents", i: i + 0.5, hue: "#00d4ff" });
    });
    return nodes;
  }

  function fetchData() {
    return fetch(API, { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (!d || !d.success) throw new Error((d && d.error) || "monitor_unavailable");
        state.data = d;
        state.bots = (d.fleet && d.fleet.bots) || [];
        state.extraNodes = buildExtraNodes(d);
        renderPanels(d);
        renderHud(d);
        maybeNarrate(d.narration);
        return d;
      });
  }

    function sourceTag(src) {
    if (src === "casino") return '<span class="f5-src casino">casino</span> ';
    if (src === "agents") return '<span class="f5-src agents">agents</span> ';
    return '<span class="f5-src fleet">fleet</span> ';
  }

  function renderHud(d) {
    var prog = d.progression || {};
    var tr = d.trades || {};
    var fl = d.fleet || {};
    var el = $("f5-hud-stats");
    if (el) {
      var cas = (d.casino && d.casino.stats) || {};
      var ag = (d.agents && d.agents.stats) || {};
      el.innerHTML =
        "<strong>Cmd Lv " + (prog.commander_level || 1) + "</strong> · " +
        (prog.fleet_total_xp || 0) + " XP<br>" +
        (fl.active_bots || 0) + "/" + (fl.bot_count || 0) + " bots · " +
        (tr.total_trades || 0) + " trades<br>" +
        "P&amp;L band: " + (tr.profit_band || "—") + "<br>" +
        "🎰 " + (cas.bets_today || 0) + " casino bets today · " +
        "🤖 " + (ag.total_executions || 0) + " agent runs";
    }
    var tk = $("f5-ticker-text");
    if (tk) {
      var acts = (d.activity || []).map(function (a) {
        return a.headline || a.action || "signal";
      });
      var hot = ((d.lanes || {}).hot_symbols || []).join(" · ");
      var line = acts.concat(["Hot lanes: " + (hot || "scanning")]).join("   ◆   ");
      tk.textContent = line + "   ◆   " + line;
    }
    var voice = $("f5-voice-line");
    if (voice && d.narration) voice.textContent = d.narration;
  }

  function renderPanels(d) {
    var act = $("f5-activity");
    if (act) {
      act.innerHTML = (d.activity || [])
        .slice(-10)
        .reverse()
        .map(function (a) {
          return '<div class="f5-row">' + sourceTag(a.source) + (a.headline || a.action || "—") + "</div>";
        })
        .join("") || '<div class="f5-row muted">Waiting for signals…</div>';
    }
    var casinoEl = $("f5-casino");
    if (casinoEl) {
      var cs = (d.casino && d.casino.stats) || {};
      casinoEl.innerHTML =
        '<div class="f5-row">Bets today: <strong>' + (cs.bets_today || 0) + "</strong></div>" +
        '<div class="f5-row">Tournament joins: ' + (cs.tournament_joins || 0) + "</div>" +
        '<div class="f5-row">Volume band: ' + (cs.volume_band || "—") + "</div>" +
        ((d.casino.recent || []).slice(0, 5).map(function (r) {
          return '<div class="f5-row">' + sourceTag("casino") + (r.headline || "") + "</div>";
        }).join(""));
    }
    var agentsEl = $("f5-agents");
    if (agentsEl) {
      var ags = (d.agents && d.agents.stats) || {};
      agentsEl.innerHTML =
        '<div class="f5-row">Tracked agents: <strong>' + (ags.total_agents || 0) + "</strong></div>" +
        '<div class="f5-row">Skill executions: ' + (ags.total_executions || 0) + "</div>" +
        ((d.agents.recent || []).slice(0, 6).map(function (r) {
          return '<div class="f5-row">' + sourceTag("agents") + (r.headline || "") + "</div>";
        }).join(""));
    }
    var bots = $("f5-bots");
    if (bots) {
      bots.innerHTML = (d.fleet.bots || [])
        .slice(0, 12)
        .map(function (b) {
          return (
            '<div class="f5-row"><strong>' + (b.label || "?") + "</strong> Lv" + (b.level || 1) +
            " · " + (b.rank_title || "") + " · " + Math.round(b.xp_progress_pct || 0) + "%</div>"
          );
        })
        .join("");
    }
    var gen = $("f5-generated");
    if (gen) gen.textContent = "Updated " + (d.generated_at || "—");
  }

  /* --- Web Audio --- */
  function FleetAudio() {
    this.ctx = null;
    this.master = null;
  }
  FleetAudio.prototype.ensure = function () {
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return Promise.reject(new Error("no audio"));
    if (!this.ctx) {
      this.ctx = new AC();
      this.master = this.ctx.createGain();
      this.master.gain.value = 0.12;
      this.master.connect(this.ctx.destination);
    }
    if (this.ctx.state === "suspended") return this.ctx.resume();
    return Promise.resolve();
  };
  FleetAudio.prototype.chime = function (freq, dur) {
    var self = this;
    return this.ensure().then(function () {
      var o = self.ctx.createOscillator();
      var g = self.ctx.createGain();
      o.type = "sine";
      o.frequency.value = freq;
      g.gain.value = 0.0001;
      o.connect(g);
      g.connect(self.master);
      var t = self.ctx.currentTime;
      g.gain.exponentialRampToValueAtTime(0.08, t + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, t + (dur || 0.35));
      o.start(t);
      o.stop(t + (dur || 0.35) + 0.05);
    });
  };
  FleetAudio.prototype.tick = function () {
    return this.chime(520 + Math.random() * 80, 0.12);
  };
  FleetAudio.prototype.levelUp = function () {
    var self = this;
    return this.chime(660, 0.2).then(function () {
      return self.chime(880, 0.35);
    });
  };

  /* --- Voice --- */
  function speak(text) {
    if (!state.voiceOn || !text || text === state.lastNarration) return;
    state.lastNarration = text;
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance(text);
    u.rate = streamMode ? 0.95 : 1;
    u.pitch = 1;
    window.speechSynthesis.speak(u);
  }

  function maybeNarrate(text) {
    if (state.voiceOn) speak(text);
  }

  /* --- 5D canvas: x,y lane · z level · w time · v XP intensity --- */
  function resizeCanvas() {
    var c = $("f5-canvas");
    if (!c) return;
    var rect = c.parentElement.getBoundingClientRect();
    var w = Math.min(1200, Math.floor(rect.width));
    var h = streamMode ? Math.max(480, Math.floor(w * 0.42)) : Math.max(320, Math.floor(w * 0.38));
    c.width = w;
    c.height = h;
  }

  function drawFrame() {
    var c = $("f5-canvas");
    if (!c) return;
    var ctx = c.getContext("2d");
    var w = c.width;
    var h = c.height;
    state.tick += 1;
    state.w = (state.w + 0.008) % (Math.PI * 2);

    ctx.fillStyle = "rgba(3, 6, 15, 0.35)";
    ctx.fillRect(0, 0, w, h);

    var bots = state.bots.length ? state.bots : [{ label: "…", level: 1, xp_progress_pct: 0, kind: "fleet" }];
    var kinds = {};
    bots.forEach(function (b, i) {
      kinds[b.kind] = kinds[b.kind] || i;
    });

    bots.forEach(function (b, i) {
      var lane = kinds[b.kind] || 0;
      var x = (lane + 0.5) / Math.max(1, Object.keys(kinds).length);
      var y = 0.25 + ((i % 5) + 0.5) / 6;
      var z = Math.min(1, (b.level || 1) / 20);
      var v = (b.xp_progress_pct || 0) / 100;
      var wx = Math.cos(state.w + i * 0.4) * 0.06 * (1 + v);
      var wy = Math.sin(state.w * 1.3 + i * 0.25) * 0.05;

      var px = (x + wx) * w;
      var py = (y + wy) * h * (0.55 + z * 0.35);
      var r = 6 + z * 14 + v * 6;

      var grd = ctx.createRadialGradient(px, py, 0, px, py, r * 2.2);
      grd.addColorStop(0, "rgba(93,255,176," + (0.35 + v * 0.5) + ")");
      grd.addColorStop(0.5, "rgba(0,212,255," + (0.15 + z * 0.3) + ")");
      grd.addColorStop(1, "rgba(255,100,255,0)");

      ctx.beginPath();
      ctx.fillStyle = grd;
      ctx.arc(px, py, r, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = "rgba(93,255,176,0.35)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(px, py);
      ctx.lineTo(px, h * 0.92);
      ctx.stroke();

      if (streamMode || i < 8) {
        ctx.fillStyle = "rgba(232,238,252,0.85)";
        ctx.font = "11px system-ui,sans-serif";
        ctx.fillText(b.label || "?", px + r + 4, py + 4);
      }
    });

    (state.extraNodes || []).forEach(function (n, idx) {
      var px = w * (0.08 + ((idx % 6) + 0.5) / 7);
      var py = h * (0.14 + Math.sin(state.w * 1.7 + idx) * 0.035);
      var r = 5 + (idx % 3);
      ctx.beginPath();
      ctx.fillStyle = n.hue || "#00d4ff";
      ctx.globalAlpha = 0.55 + Math.sin(state.w + idx) * 0.15;
      ctx.arc(px, py, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.font = "10px system-ui,sans-serif";
      ctx.fillStyle = "rgba(255,255,255,0.8)";
      ctx.fillText(n.label || "•", px + r + 2, py + 3);
    });

    /* time ring (w dimension) */
    ctx.strokeStyle = "rgba(0,212,255,0.25)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(w * 0.5, h * 0.48, Math.min(w, h) * 0.32, state.w, state.w + Math.PI * 1.2);
    ctx.stroke();

    requestAnimationFrame(drawFrame);
  }

  function bindControls() {
    var soundBtn = $("f5-sound");
    if (soundBtn) {
      soundBtn.addEventListener("click", function () {
        if (!state.audio) state.audio = new FleetAudio();
        state.audio.ensure().then(function () {
          state.audio.tick();
          soundBtn.textContent = "Sound on";
        }).catch(function () {
          setStatus("Audio unavailable in this browser.");
        });
      });
    }
    var voiceBtn = $("f5-voice");
    if (voiceBtn) {
      voiceBtn.addEventListener("click", function () {
        state.voiceOn = !state.voiceOn;
        voiceBtn.setAttribute("aria-pressed", state.voiceOn ? "true" : "false");
        voiceBtn.textContent = state.voiceOn ? "Voice on" : "Voice narrator";
        if (state.voiceOn && state.data) maybeNarrate(state.data.narration);
      });
    }
    var refreshBtn = $("f5-refresh");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", function () {
        fetchData().catch(function (e) {
          setStatus(e.message || "Refresh failed");
        });
      });
    }
  }

  function poll() {
    fetchData()
      .then(function (d) {
        setStatus(d.paper_mode ? "Paper mode · audience-safe telemetry" : "Live telemetry · audience-safe");
        if (state.audio) state.audio.tick();
        var lvl = (d.progression && d.progression.commander_level) || 1;
        if (state._lastLvl && lvl > state._lastLvl && state.audio) state.audio.levelUp();
        state._lastLvl = lvl;
      })
      .catch(function (e) {
        setStatus(e.message || "Monitor offline");
      });
    setTimeout(poll, POLL_MS);
  }

  function init() {
    if (streamMode) document.body.classList.add("f5-stream");
    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);
    bindControls();
    requestAnimationFrame(drawFrame);
    fetchData().finally(function () {
      poll();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
