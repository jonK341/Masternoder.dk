/**
 * Camgirl AI stream voice — Web Speech with performer profiles, chapter narration, queues.
 */
(function () {
  "use strict";

  var DEFAULT_PROFILES = {
    performer_nova: { rate: 1.05, pitch: 1.15 },
    performer_luna: { rate: 0.9, pitch: 1.05 },
    performer_sage: { rate: 0.88, pitch: 0.95 },
    performer_ember: { rate: 1.12, pitch: 1.2 },
    performer_iris: { rate: 1.0, pitch: 1.1 },
  };

  var state = {
    enabled: false,
    autoChapters: true,
    readEncodeTag: true,
    volume: 1,
    rateMul: 1,
    pitchMul: 1,
    speakers: [],
    speakerIndex: 0,
    leadSpeakerId: "",
    speaking: false,
    queue: [],
    lastChapterId: "",
    lastChapter: null,
    profiles: DEFAULT_PROFILES,
    onActiveSpeaker: null,
    onLine: null,
    storageKey: "mn-camgirls-stream-voice",
  };

  function loadPrefs() {
    try {
      var raw = sessionStorage.getItem(state.storageKey);
      if (!raw) return;
      var p = JSON.parse(raw);
      if (typeof p.autoChapters === "boolean") state.autoChapters = p.autoChapters;
      if (typeof p.readEncodeTag === "boolean") state.readEncodeTag = p.readEncodeTag;
      if (typeof p.volume === "number") state.volume = Math.min(1, Math.max(0, p.volume));
      if (typeof p.rateMul === "number") state.rateMul = Math.min(1.35, Math.max(0.7, p.rateMul));
      if (typeof p.pitchMul === "number") state.pitchMul = Math.min(1.35, Math.max(0.75, p.pitchMul));
      if (p.leadSpeakerId) state.leadSpeakerId = p.leadSpeakerId;
    } catch (e) {
      /* ignore */
    }
  }

  function savePrefs() {
    try {
      sessionStorage.setItem(
        state.storageKey,
        JSON.stringify({
          autoChapters: state.autoChapters,
          readEncodeTag: state.readEncodeTag,
          volume: state.volume,
          rateMul: state.rateMul,
          pitchMul: state.pitchMul,
          leadSpeakerId: state.leadSpeakerId,
        })
      );
    } catch (e) {
      /* ignore */
    }
  }

  function pickSpeaker(rotate) {
    if (!state.speakers.length) return null;
    if (state.leadSpeakerId && !rotate) {
      var lead = state.speakers.filter(function (s) {
        return s.id === state.leadSpeakerId;
      })[0];
      if (lead) return lead;
    }
    if (rotate) {
      state.speakerIndex = (state.speakerIndex + 1) % state.speakers.length;
    }
    return state.speakers[state.speakerIndex] || state.speakers[0];
  }

  function formatChapter(ch) {
    if (!ch) return "";
    var parts = [];
    if (state.readEncodeTag && ch.encode_profile) {
      parts.push("Decoded " + String(ch.encode_profile).replace(/_/g, " ") + " chapter.");
    }
    if (ch.title) parts.push(ch.title);
    if (ch.ai_content) parts.push(ch.ai_content);
    return parts.join(" ");
  }

  function setLine(speaker, text) {
    if (typeof state.onLine === "function") {
      state.onLine(speaker, text);
    }
  }

  function cancelSpeech() {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    state.speaking = false;
    state.queue = [];
  }

  function processQueue() {
    if (state.speaking || !state.queue.length) return;
    var next = state.queue.shift();
    speakUtterance(next.text, next.speaker, { force: next.force, rotate: next.rotate });
  }

  function speakUtterance(text, speaker, opts) {
    opts = opts || {};
    if (!text || !window.speechSynthesis) return;
    if (!opts.force && !state.enabled) return;

    var sp = speaker || pickSpeaker(opts.rotate);
    if (!sp) return;

    if (state.speaking && opts.interrupt) {
      window.speechSynthesis.cancel();
      state.speaking = false;
      state.queue = [];
    } else if (state.speaking && opts.queue) {
      state.queue.push({ text: text, speaker: sp, force: opts.force, rotate: opts.rotate });
      return;
    } else if (state.speaking && !opts.force) {
      state.queue.push({ text: text, speaker: sp, force: opts.force, rotate: opts.rotate });
      return;
    }

    if (typeof state.onActiveSpeaker === "function") state.onActiveSpeaker(sp.id);
    setLine(sp, text);

    var prof = state.profiles[sp.id] || { rate: 1, pitch: 1 };
    var u = new SpeechSynthesisUtterance(text);
    u.volume = state.volume;
    u.rate = (prof.rate || 1) * state.rateMul;
    u.pitch = (prof.pitch || 1) * state.pitchMul;

    state.speaking = true;
    u.onend = function () {
      state.speaking = false;
      if (state.queue.length) {
        var next = state.queue.shift();
        speakUtterance(next.text, next.speaker, { force: next.force, rotate: next.rotate });
      }
    };
    u.onerror = function () {
      state.speaking = false;
    };
    window.speechSynthesis.speak(u);
  }

  function speak(text, opts) {
    opts = opts || {};
    speakUtterance(text, null, {
      force: !!opts.force,
      rotate: !!opts.rotate,
      interrupt: !!opts.interrupt,
      queue: opts.queue !== false,
    });
  }

  function speakChapter(ch, opts) {
    opts = opts || {};
    if (!ch) return;
    state.lastChapter = ch;
    state.lastChapterId = ch.id || "";
    var line = formatChapter(ch);
    speakUtterance(line, null, {
      force: !!opts.force,
      rotate: opts.rotate !== false,
      interrupt: !!opts.interrupt,
      queue: !opts.interrupt,
    });
  }

  function repeatChapter() {
    if (state.lastChapter) speakChapter(state.lastChapter, { force: true, interrupt: true });
  }

  function onStreamChapter(ev) {
    var ch = ev.detail && ev.detail.chapter;
    if (!ch) return;
    if (ev.detail.speak) {
      speakChapter(ch, { force: true, interrupt: true });
      return;
    }
    if (ch.id && ch.id === state.lastChapterId && !ev.detail.speak) return;
    state.lastChapter = ch;
    state.lastChapterId = ch.id || "";
    if (state.enabled && state.autoChapters) {
      speakChapter(ch, { force: true, interrupt: true });
    } else {
      setLine(null, "Chapter: " + (ch.title || "") + " — " + (ch.ai_content || "").slice(0, 120));
    }
  }

  function loadSpeakers(apiUrl) {
    var url = apiUrl || "/api/camgirls/performers";
    return fetch(url, { credentials: "same-origin" })
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
          .slice(0, 8)
          .map(function (p) {
            return {
              id: p.id,
              name: p.display_name || p.name || "Host",
              avatar: p.avatar_url || "/static/camgirls/avatar-demo.svg",
            };
          });
        if (!state.speakers.length) {
          state.speakers = [
            { id: "performer_nova", name: "Nova Star", avatar: "/static/camgirls/avatar-demo.svg" },
          ];
        }
        if (!state.leadSpeakerId) state.leadSpeakerId = state.speakers[0].id;
        return state.speakers;
      })
      .catch(function () {
        state.speakers = [
          { id: "performer_nova", name: "Nova Star", avatar: "/static/camgirls/avatar-demo.svg" },
        ];
        if (!state.leadSpeakerId) state.leadSpeakerId = state.speakers[0].id;
        return state.speakers;
      });
  }

  function bindDeck(root) {
    var el = typeof root === "string" ? document.getElementById(root) : root;
    if (!el) return;

    el.innerHTML =
      '<div class="cgv-deck">' +
      '<div class="cgv-deck-head"><span class="cgv-deck-title">Camgirl AI voice</span>' +
      '<button type="button" class="cgv-btn" id="cgv-stop" title="Stop speech">Stop</button>' +
      '<button type="button" class="cgv-btn primary" id="cgv-repeat" title="Repeat last chapter">Repeat chapter</button></div>' +
      '<div class="cgv-grid">' +
      '<label class="cgv-field"><span>Volume</span><input type="range" id="cgv-volume" min="0" max="100" value="100" /></label>' +
      '<label class="cgv-field"><span>Speech rate</span><input type="range" id="cgv-rate" min="70" max="130" value="100" /></label>' +
      '<label class="cgv-field"><span>Pitch</span><input type="range" id="cgv-pitch" min="75" max="125" value="100" /></label>' +
      '<label class="cgv-check"><input type="checkbox" id="cgv-auto-chapters" checked /> Auto-read chapters</label>' +
      '<label class="cgv-check"><input type="checkbox" id="cgv-encode-tag" checked /> Say encode profile</label>' +
      "</div></div>";

    var vol = el.querySelector("#cgv-volume");
    var rate = el.querySelector("#cgv-rate");
    var pitch = el.querySelector("#cgv-pitch");
    var autoCh = el.querySelector("#cgv-auto-chapters");
    var enc = el.querySelector("#cgv-encode-tag");
    var stop = el.querySelector("#cgv-stop");
    var rep = el.querySelector("#cgv-repeat");

    if (vol) {
      vol.value = String(Math.round(state.volume * 100));
      vol.addEventListener("input", function () {
        state.volume = parseInt(vol.value, 10) / 100;
        savePrefs();
      });
    }
    if (rate) {
      rate.value = String(Math.round(state.rateMul * 100));
      rate.addEventListener("input", function () {
        state.rateMul = parseInt(rate.value, 10) / 100;
        savePrefs();
      });
    }
    if (pitch) {
      pitch.value = String(Math.round(state.pitchMul * 100));
      pitch.addEventListener("input", function () {
        state.pitchMul = parseInt(pitch.value, 10) / 100;
        savePrefs();
      });
    }
    if (autoCh) {
      autoCh.checked = state.autoChapters;
      autoCh.addEventListener("change", function () {
        state.autoChapters = autoCh.checked;
        savePrefs();
      });
    }
    if (enc) {
      enc.checked = state.readEncodeTag;
      enc.addEventListener("change", function () {
        state.readEncodeTag = enc.checked;
        savePrefs();
      });
    }
    if (stop) stop.addEventListener("click", cancelSpeech);
    if (rep) rep.addEventListener("click", repeatChapter);
  }

  function syncDeckFromPrefs(root) {
    var el = typeof root === "string" ? document.getElementById(root) : root;
    if (!el) return;
    var vol = el.querySelector("#cgv-volume");
    var rate = el.querySelector("#cgv-rate");
    var pitch = el.querySelector("#cgv-pitch");
    var autoCh = el.querySelector("#cgv-auto-chapters");
    var enc = el.querySelector("#cgv-encode-tag");
    if (vol) vol.value = String(Math.round(state.volume * 100));
    if (rate) rate.value = String(Math.round(state.rateMul * 100));
    if (pitch) pitch.value = String(Math.round(state.pitchMul * 100));
    if (autoCh) autoCh.checked = state.autoChapters;
    if (enc) enc.checked = state.readEncodeTag;
  }

  function setEnabled(on) {
    state.enabled = !!on;
    if (!state.enabled) cancelSpeech();
    document.dispatchEvent(
      new CustomEvent("mn:voice-state", { detail: { enabled: state.enabled, autoChapters: state.autoChapters } })
    );
  }

  function init(options) {
    options = options || {};
    if (options.profiles) state.profiles = options.profiles;
    if (options.storageKey) state.storageKey = options.storageKey;
    state.onActiveSpeaker = options.onActiveSpeaker || null;
    state.onLine = options.onLine || null;
    loadPrefs();
    if (!document._mnVoiceChapterBound) {
      document.addEventListener("mn:stream-chapter", onStreamChapter);
      document._mnVoiceChapterBound = true;
    }
    return loadSpeakers(options.performersApi).then(function () {
      if (options.deckId) {
        bindDeck(options.deckId);
      }
      return state.speakers;
    });
  }

  window.MNCamgirlsStreamVoice = {
    init: init,
    bindDeck: bindDeck,
    syncDeck: syncDeckFromPrefs,
    loadSpeakers: loadSpeakers,
    setEnabled: setEnabled,
    isEnabled: function () {
      return state.enabled;
    },
    setLeadSpeaker: function (id) {
      state.leadSpeakerId = id || "";
      savePrefs();
    },
    getSpeakers: function () {
      return state.speakers.slice();
    },
    pickSpeaker: pickSpeaker,
    speak: speak,
    speakChapter: speakChapter,
    repeatChapter: repeatChapter,
    formatChapter: formatChapter,
    cancel: cancelSpeech,
    getLastChapter: function () {
      return state.lastChapter;
    },
    getLeadSpeakerId: function () {
      return state.leadSpeakerId;
    },
    setAutoChapters: function (v) {
      state.autoChapters = !!v;
      savePrefs();
    },
  };
})();
