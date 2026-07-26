/**
 * 5D Fleet Progress Navigation Monitor — canvas, roster orbit, audio, camgirl voice.
 */
(function () {
  "use strict";

  var API = "/api/exchange/fleet-progress-monitor/public?light=1";
  var PERFORMERS_API = "/api/camgirls/performers";
  var POLL_MS = 12000;
  var state = {
    data: null,
    w: 0,
    bots: [],
    botPositions: [],
    tick: 0,
    audio: null,
    soundOn: false,
    voiceOn: false,
    speakers: [],
    speakerIndex: 0,
    leadSpeakerId: "",
    commentaryQueue: [],
    speaking: false,
    lastNarrationKey: "",
    extraNodes: [],
  };

  var VOICE_PROFILE = {
    performer_nova: { rate: 1.05, pitch: 1.15 },
    performer_luna: { rate: 0.9, pitch: 1.05 },
    performer_sage: { rate: 0.88, pitch: 0.95 },
    performer_ember: { rate: 1.12, pitch: 1.2 },
    performer_iris: { rate: 1.0, pitch: 1.1 },
  };

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

  function sourceTag(src) {
    if (src === "casino") return '<span class="f5-src casino">casino</span> ';
    if (src === "agents") return '<span class="f5-src agents">agents</span> ';
    return '<span class="f5-src fleet">fleet</span> ';
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

  function loadSpeakers() {
    return fetch(PERFORMERS_API, { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        var rows = (d && d.performers) || (d && d.catalog) || [];
        if (!Array.isArray(rows) && d && d.success && d.performers) rows = d.performers;
        state.speakers = (rows || [])
          .filter(function (p) {
            return p && p.active !== false;
          })
          .slice(0, 6)
          .map(function (p) {
            return {
              id: p.id,
              name: p.display_name || p.name || "Host",
              avatar: p.avatar_url || "/static/camgirls/avatar-demo.svg",
              tagline: p.tagline || "",
            };
          });
        renderSpeakerDock();
        fillSpeakerSelect();
        return state.speakers;
      })
      .catch(function () {
        state.speakers = [
          { id: "performer_nova", name: "Nova Star", avatar: "/static/camgirls/avatar-demo.svg" },
        ];
        renderSpeakerDock();
        fillSpeakerSelect();
      });
  }

  function fillSpeakerSelect() {
    var sel = $("f5-speaker-pick");
    if (!sel) return;
    sel.innerHTML = state.speakers
      .map(function (s) {
        return '<option value="' + s.id + '">' + s.name + "</option>";
      })
      .join("");
    if (!state.leadSpeakerId && state.speakers[0]) {
      state.leadSpeakerId = state.speakers[0].id;
    }
    sel.value = state.leadSpeakerId || state.speakers[0].id;
  }

  function renderSpeakerDock(activeId) {
    var dock = $("f5-speakers");
    if (!dock) return;
    dock.innerHTML = state.speakers
      .map(function (s) {
        var cls = s.id === activeId ? " f5-speaker is-active" : " f5-speaker";
        return (
          '<div class="' + cls.trim() + '" data-id="' + s.id + '">' +
          '<img src="' + s.avatar + '" alt="" width="28" height="28" loading="lazy" />' +
          "<span>" + s.name + "</span></div>"
        );
      })
      .join("");
  }

  function renderFloatingRoster(d) {
    var el = $("f5-roster-orbit");
    if (!el) return;
    var bots = (d.fleet && d.fleet.bots) || [];
    if (!bots.length) {
      el.innerHTML = "<h3>Fleet roster</h3><p class='f5-meta'>No bots yet</p>";
      return;
    }
    var hotIdx = state.hotBotIndex != null ? state.hotBotIndex : 0;
    el.innerHTML =
      "<h3>Fleet roster · " + bots.length + "</h3>" +
      bots
        .map(function (b, i) {
          var pct = Math.round(b.xp_progress_pct || 0);
          return (
            '<div class="f5-roster-card' + (i === hotIdx ? " is-hot" : "") + '" data-idx="' + i + '">' +
            '<span class="f5-roster-dot"></span>' +
            "<div><strong>" + (b.label || "?") + "</strong><br>Lv " + (b.level || 1) +
            " · " + (b.rank_title || "") + "</div>" +
            '<div class="f5-roster-xp"><span style="width:' + pct + '%"></span></div></div>'
          );
        })
        .join("");
  }

  function buildCommentary(d) {
    var lines = [];
    if (d.narration) lines.push(d.narration);
    var bots = (d.fleet && d.fleet.bots) || [];
    var top = bots.slice().sort(function (a, b) {
      return (b.level || 0) - (a.level || 0);
    })[0];
    if (top) {
      lines.push(
        (top.label || "Fleet lead") + " is level " + (top.level || 1) + " with " +
        Math.round(top.xp_progress_pct || 0) + " percent progress in this band."
      );
    }
    var cas = (d.casino && d.casino.stats) || {};
    if (cas.bets_today) {
      lines.push("Casino floor reports " + cas.bets_today + " bets today. Volume band " + (cas.volume_band || "steady") + ".");
    }
    var ag = (d.agents && d.agents.stats) || {};
    if (ag.total_executions) {
      lines.push("Agent mesh logged " + ag.total_executions + " skill executions across " + (ag.total_agents || 0) + " operators.");
    }
    var act = (d.activity || [])[0];
    if (act && act.headline) lines.push(act.headline);
    return lines;
  }

  function pickSpeaker(rotate) {
    if (!state.speakers.length) return null;
    if (state.leadSpeakerId) {
      var lead = state.speakers.filter(function (s) {
        return s.id === state.leadSpeakerId;
      })[0];
      if (lead && !rotate) return lead;
    }
    if (rotate) {
      state.speakerIndex = (state.speakerIndex + 1) % state.speakers.length;
    }
    return state.speakers[state.speakerIndex] || state.speakers[0];
  }

  function speakLine(text, speaker, rotate) {
    if (!state.voiceOn || !text || !window.speechSynthesis) return;
    var sp = speaker || pickSpeaker(rotate);
    if (!sp) return;
    renderSpeakerDock(sp.id);
    var voiceLine = $("f5-voice-line");
    if (voiceLine) voiceLine.textContent = sp.name + ": " + text;

    var u = new SpeechSynthesisUtterance(text);
    var prof = VOICE_PROFILE[sp.id] || { rate: streamMode ? 0.95 : 1, pitch: 1 };
    u.rate = prof.rate;
    u.pitch = prof.pitch;
    state.speaking = true;
    u.onend = function () {
      state.speaking = false;
      processCommentaryQueue();
    };
    window.speechSynthesis.speak(u);
  }

  function queueCommentary(lines) {
    state.commentaryQueue = (lines || []).filter(Boolean);
    if (!state.speaking) processCommentaryQueue();
  }

  function processCommentaryQueue() {
    if (!state.voiceOn || state.speaking || !state.commentaryQueue.length) return;
    var line = state.commentaryQueue.shift();
    speakLine(line, pickSpeaker(true), true);
  }

  function maybeNarrate(d) {
    if (!state.voiceOn || !d) return;
    var key = (d.generated_at || "") + "|" + ((d.progression && d.progression.fleet_total_xp) || 0);
    if (key === state.lastNarrationKey) return;
    state.lastNarrationKey = key;
    queueCommentary(buildCommentary(d));
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
        state.hotBotIndex = Math.floor((state.tick / 90) % Math.max(1, state.bots.length));
        renderPanels(d);
        renderHud(d);
        renderFloatingRoster(d);
        maybeNarrate(d);
        if (state.soundOn && state.audio) {
          state.audio.contextualPing(d);
        }
        return d;
      });
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
        "P&amp;L " + (tr.profit_band || "—") + " · 🎰 " + (cas.bets_today || 0) +
        " · 🤖 " + (ag.total_executions || 0);
    }
    var tk = $("f5-ticker-text");
    if (tk) {
      var acts = (d.activity || []).map(function (a) {
        return a.headline || a.action || "signal";
      });
      var hot = ((d.lanes || {}).hot_symbols || []).join(" · ");
      var line = acts.concat(["Hot: " + (hot || "scanning")]).join("   ◆   ");
      tk.textContent = line + "   ◆   " + line;
    }
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
    if (casinoEl && d.casino) {
      var cs = d.casino.stats || {};
      casinoEl.innerHTML =
        '<div class="f5-row">Bets today: <strong>' + (cs.bets_today || 0) + "</strong></div>" +
        '<div class="f5-row">Tournament joins: ' + (cs.tournament_joins || 0) + "</div>" +
        ((d.casino.recent || []).slice(0, 5).map(function (r) {
          return '<div class="f5-row">' + sourceTag("casino") + (r.headline || "") + "</div>";
        }).join(""));
    }
    var agentsEl = $("f5-agents");
    if (agentsEl && d.agents) {
      var ags = d.agents.stats || {};
      agentsEl.innerHTML =
        '<div class="f5-row">Tracked agents: <strong>' + (ags.total_agents || 0) + "</strong></div>" +
        ((d.agents.recent || []).slice(0, 6).map(function (r) {
          return '<div class="f5-row">' + sourceTag("agents") + (r.headline || "") + "</div>";
        }).join(""));
    }
    var bots = $("f5-bots");
    if (bots && d.fleet) {
      bots.innerHTML = (d.fleet.bots || [])
        .slice(0, 12)
        .map(function (b) {
          return (
            '<div class="f5-row"><strong>' + (b.label || "?") + "</strong> Lv" + (b.level || 1) +
            " · " + Math.round(b.xp_progress_pct || 0) + "%</div>"
          );
        })
        .join("");
    }
    var gen = $("f5-generated");
    if (gen) gen.textContent = "Updated " + (d.generated_at || "—");
  }

  function FleetAudio() {
    this.ctx = null;
    this.master = null;
    this.ambientNodes = [];
  }

  FleetAudio.prototype.ensure = function () {
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return Promise.reject(new Error("no audio"));
    if (!this.ctx) {
      this.ctx = new AC();
      this.master = this.ctx.createGain();
      this.master.gain.value = 0.14;
      this.master.connect(this.ctx.destination);
    }
    if (this.ctx.state === "suspended") return this.ctx.resume();
    return Promise.resolve();
  };

  FleetAudio.prototype.chime = function (freq, dur, type) {
    var self = this;
    return this.ensure().then(function () {
      var o = self.ctx.createOscillator();
      var g = self.ctx.createGain();
      o.type = type || "sine";
      o.frequency.value = freq;
      g.gain.value = 0.0001;
      o.connect(g);
      g.connect(self.master);
      var t = self.ctx.currentTime;
      g.gain.exponentialRampToValueAtTime(0.09, t + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, t + (dur || 0.35));
      o.start(t);
      o.stop(t + (dur || 0.35) + 0.05);
    });
  };

  FleetAudio.prototype.startAmbient = function () {
    var self = this;
    return this.ensure().then(function () {
      if (self.ambientNodes.length) return;
      var o1 = self.ctx.createOscillator();
      var o2 = self.ctx.createOscillator();
      var g = self.ctx.createGain();
      o1.type = "sine";
      o2.type = "triangle";
      o1.frequency.value = 55;
      o2.frequency.value = 110;
      g.gain.value = 0.018;
      o1.connect(g);
      o2.connect(g);
      g.connect(self.master);
      o1.start();
      o2.start();
      self.ambientNodes = [o1, o2, g];
    });
  };

  FleetAudio.prototype.tick = function () {
    return this.chime(520 + Math.random() * 80, 0.1);
  };

  FleetAudio.prototype.levelUp = function () {
    var self = this;
    return this.chime(660, 0.18).then(function () {
      return self.chime(880, 0.28, "triangle");
    });
  };

  FleetAudio.prototype.contextualPing = function (d) {
    var acts = d.activity || [];
    var src = (acts[0] && acts[0].source) || "fleet";
    if (src === "casino") return this.chime(740, 0.14, "square");
    if (src === "agents") return this.chime(420, 0.16, "sawtooth");
    return this.tick();
  };

  function resizeCanvas() {
    var c = $("f5-canvas");
    if (!c) return;
    var rect = c.parentElement.getBoundingClientRect();
    var rosterW = Math.min(220, rect.width * 0.34);
    var w = Math.min(1200, Math.floor(rect.width));
    var h = streamMode ? Math.max(440, Math.floor(w * 0.4)) : Math.max(340, Math.floor(w * 0.36));
    c.width = w;
    c.height = h;
    state.rosterPad = rosterW;
  }

  function drawFrame() {
    var c = $("f5-canvas");
    if (!c) return;
    var ctx = c.getContext("2d");
    var w = c.width;
    var h = c.height;
    var padR = state.rosterPad || 200;
    state.tick += 1;
    state.w = (state.w + 0.008) % (Math.PI * 2);

    ctx.fillStyle = "rgba(3, 6, 15, 0.4)";
    ctx.fillRect(0, 0, w, h);

    var bots = state.bots.length ? state.bots : [{ label: "…", level: 1, xp_progress_pct: 0, kind: "fleet" }];
    var kinds = {};
    bots.forEach(function (b, i) {
      kinds[b.kind] = kinds[b.kind] || i;
    });
    var padR = state.rosterPad || 200;
    var usableW = w - padR - 24;
    state.botPositions = [];

    bots.forEach(function (b, i) {
      var lane = kinds[b.kind] || 0;
      var laneCount = Math.max(1, Object.keys(kinds).length);
      var x = (lane + 0.5) / laneCount;
      var y = 0.22 + ((i % 6) + 0.5) / 7;
      var z = Math.min(1, (b.level || 1) / 20);
      var v = (b.xp_progress_pct || 0) / 100;
      var wx = Math.cos(state.w + i * 0.4) * 0.05 * (1 + v);
      var wy = Math.sin(state.w * 1.3 + i * 0.25) * 0.04;

      var px = 16 + (x + wx) * usableW;
      var py = 24 + (y + wy) * (h * 0.52);
      var r = 5 + z * 12 + v * 5;
      state.botPositions[i] = { px: px, py: py, r: r };

      var grd = ctx.createRadialGradient(px, py, 0, px, py, r * 2.4);
      grd.addColorStop(0, "rgba(93,255,176," + (0.35 + v * 0.5) + ")");
      grd.addColorStop(0.55, "rgba(0,212,255," + (0.12 + z * 0.28) + ")");
      grd.addColorStop(1, "rgba(255,100,255,0)");

      ctx.beginPath();
      ctx.fillStyle = grd;
      ctx.arc(px, py, r, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = "rgba(93,255,176,0.28)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(px, py);
      ctx.lineTo(px, h - 100);
      ctx.stroke();

      if (i === state.hotBotIndex) {
        ctx.strokeStyle = "rgba(255,100,255,0.5)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(px, py, r + 6 + Math.sin(state.w * 2) * 2, 0, Math.PI * 2);
        ctx.stroke();
      }

      if (streamMode || i < 10) {
        ctx.fillStyle = "rgba(232,238,252,0.88)";
        ctx.font = "10px system-ui,sans-serif";
        ctx.fillText(b.label || "?", px + r + 3, py + 3);
      }
    });

    (state.extraNodes || []).forEach(function (n, idx) {
      var px = 20 + ((idx % 5) + 0.5) / 5 * (usableW * 0.35);
      var py = h * 0.12 + Math.sin(state.w * 1.7 + idx) * 12;
      ctx.beginPath();
      ctx.fillStyle = n.hue || "#00d4ff";
      ctx.globalAlpha = 0.5 + Math.sin(state.w + idx) * 0.2;
      ctx.arc(px, py, 4 + (idx % 2), 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
    });

    ctx.strokeStyle = "rgba(0,212,255,0.22)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(w * 0.42, h * 0.45, Math.min(usableW, h) * 0.28, state.w, state.w + Math.PI * 1.15);
    ctx.stroke();

    requestAnimationFrame(drawFrame);
  }

  function bindControls() {
    var soundBtn = $("f5-sound");
    if (soundBtn) {
      soundBtn.addEventListener("click", function () {
        if (!state.audio) state.audio = new FleetAudio();
        state.audio.ensure().then(function () {
          state.soundOn = true;
          return state.audio.startAmbient();
        }).then(function () {
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
        voiceBtn.textContent = state.voiceOn ? "Voice on" : "Camgirl voice";
        if (state.voiceOn && state.data) {
          state.lastNarrationKey = "";
          maybeNarrate(state.data);
        }
        if (!state.voiceOn && window.speechSynthesis) window.speechSynthesis.cancel();
      });
    }
    $("f5-refresh") &&
      $("f5-refresh").addEventListener("click", function () {
        fetchData().catch(function (e) {
          setStatus(e.message || "Refresh failed");
        });
      });
    var sel = $("f5-speaker-pick");
    if (sel) {
      sel.addEventListener("change", function () {
        state.leadSpeakerId = sel.value;
      });
    }
  }

  function poll() {
    fetchData()
      .then(function (d) {
        setStatus(d.paper_mode ? "Paper mode · audience-safe" : "Live · audience-safe");
        if (state.soundOn && state.audio) state.audio.tick();
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
    loadSpeakers();
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
