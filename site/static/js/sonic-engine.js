/**
 * MasterNoder Sonic Engine
 * =========================
 * Version 10.07.9 — a single shared Web-Audio sound engine used across the whole
 * platform (front page, forum, game, casino, battle, nav toolbar…).
 *
 * One engine, one AudioContext, exposed as `window.SonicEngine`. It stays dormant
 * until the user opts in (browser autoplay policy), remembers the preference in
 * localStorage, and offers ambient "modes" plus short interaction "cues" that any
 * page/process can trigger via SonicEngine.cue('click' | 'success' | ...).
 */
(function () {
  'use strict';

  if (window.SonicEngine && window.SonicEngine.VERSION) return; // singleton guard

  var VERSION = '10.07.9';
  var STORE_KEY = 'mn_sonic_v10';

  var MODES = {
    focus:  { label: 'Focus hum',   wave: 'sine',     tones: [92, 184, 276],  filter: 820,  noise: 0.055, beatMs: 2200, beatFreq: 740 },
    stars:  { label: 'Star pulse',  wave: 'triangle', tones: [136, 272, 408], filter: 1380, noise: 0.04,  beatMs: 980,  beatFreq: 1080 },
    battle: { label: 'Battle drive',wave: 'sawtooth', tones: [55, 110, 165],  filter: 620,  noise: 0.075, beatMs: 560,  beatFreq: 320 },
    arcade: { label: 'Arcade',      wave: 'square',   tones: [110, 220, 330], filter: 1600, noise: 0.03,  beatMs: 700,  beatFreq: 880 },
    calm:   { label: 'Calm library',wave: 'sine',     tones: [110, 165, 220], filter: 700,  noise: 0.025, beatMs: 3200, beatFreq: 520 }
  };

  // Named short cues any process can play. [freq, level, durationMs, wave]
  var CUES = {
    click:    [880, 0.012, 120, 'sine'],
    hover:    [1040, 0.008, 90, 'sine'],
    navigate: [660, 0.02, 200, 'triangle'],
    success:  [720, 0.03, 260, 'sine'],
    reward:   [990, 0.035, 320, 'triangle'],
    error:    [180, 0.03, 240, 'sawtooth'],
    level:    [523, 0.03, 180, 'square'],
    vote:     [820, 0.018, 140, 'sine'],
    post:     [600, 0.022, 220, 'triangle']
  };

  function loadState() {
    try {
      var raw = localStorage.getItem(STORE_KEY);
      if (raw) return JSON.parse(raw);
    } catch (_) {}
    return { enabled: false, mode: 'focus', volume: 0.35 };
  }

  function makeNoise(ctx) {
    var seconds = 2;
    var buffer = ctx.createBuffer(1, ctx.sampleRate * seconds, ctx.sampleRate);
    var data = buffer.getChannelData(0);
    for (var i = 0; i < data.length; i += 1) data[i] = (Math.random() * 2 - 1) * 0.24;
    return buffer;
  }

  var SonicEngine = {
    VERSION: VERSION,
    MODES: MODES,
    CUES: CUES,
    ctx: null,
    masterGain: null,
    nodes: [],
    beatTimer: null,
    isActive: false,
    _uiWired: false,

    _init: function () {
      var s = loadState();
      this.mode = s.mode && MODES[s.mode] ? s.mode : 'focus';
      this.volume = typeof s.volume === 'number' ? s.volume : 0.35;
      this._wantEnabled = !!s.enabled;
      this.attachUiFeedback();
      // If the user previously enabled sound, resume on their first gesture (autoplay policy).
      if (this._wantEnabled) {
        var self = this;
        var resume = function () {
          document.removeEventListener('pointerdown', resume);
          document.removeEventListener('keydown', resume);
          self.start().catch(function () {});
        };
        document.addEventListener('pointerdown', resume, { once: true });
        document.addEventListener('keydown', resume, { once: true });
      }
      try { console.info('%c♪ SonicEngine v' + VERSION + ' ready', 'color:#00ff88'); } catch (_) {}
      return this;
    },

    _save: function () {
      try {
        localStorage.setItem(STORE_KEY, JSON.stringify({
          enabled: this.isActive || this._wantEnabled, mode: this.mode, volume: this.volume
        }));
      } catch (_) {}
    },

    ensureContext: function () {
      var Ctor = window.AudioContext || window.webkitAudioContext;
      if (!Ctor) return Promise.reject(new Error('Web Audio API unavailable'));
      if (!this.ctx) this.ctx = new Ctor();
      if (this.ctx.state === 'suspended') return this.ctx.resume();
      return Promise.resolve();
    },

    start: function () {
      var self = this;
      if (this.isActive) return Promise.resolve();
      return this.ensureContext().then(function () {
        self.isActive = true;
        self._wantEnabled = true;
        self.rebuild();
        self._save();
        self._emit();
      });
    },

    stop: function () {
      this.isActive = false;
      this._wantEnabled = false;
      this.clearBeat();
      this.stopNodes();
      if (this.masterGain && this.ctx) {
        var g = this.masterGain;
        try {
          g.gain.cancelScheduledValues(this.ctx.currentTime);
          g.gain.setTargetAtTime(0, this.ctx.currentTime, 0.08);
          var self = this;
          setTimeout(function () { try { g.disconnect(); } catch (_) {} if (self.masterGain === g) self.masterGain = null; }, 180);
        } catch (_) { try { g.disconnect(); } catch (__) {} this.masterGain = null; }
      }
      this._save();
      this._emit();
    },

    toggle: function () { return this.isActive ? (this.stop(), Promise.resolve()) : this.start(); },

    setMode: function (mode) {
      if (!MODES[mode]) return;
      this.mode = mode;
      this._save();
      if (this.isActive) { this.rebuild(); this.ping(900, 0.025); }
      this._emit();
    },

    setVolume: function (v) {
      this.volume = Math.max(0, Math.min(1, v));
      this.applyVolume();
      this._save();
    },

    rebuild: function () {
      if (!this.ctx || !this.isActive) return;
      this.clearBeat();
      this.stopNodes();
      if (this.masterGain) { try { this.masterGain.disconnect(); } catch (_) {} this.masterGain = null; }
      var cfg = MODES[this.mode] || MODES.focus;
      this.masterGain = this.ctx.createGain();
      this.masterGain.gain.value = 0;
      this.masterGain.connect(this.ctx.destination);
      this.applyVolume();

      var droneFilter = this.ctx.createBiquadFilter();
      droneFilter.type = 'lowpass';
      droneFilter.frequency.value = cfg.filter;
      droneFilter.Q.value = 0.7;
      droneFilter.connect(this.masterGain);
      this.nodes.push(droneFilter);

      var self = this;
      cfg.tones.forEach(function (freq, index) {
        var osc = self.ctx.createOscillator();
        var gain = self.ctx.createGain();
        osc.type = cfg.wave;
        osc.frequency.value = freq;
        osc.detune.value = (index - 1) * 5;
        gain.gain.value = 0.035 / (index + 1);
        osc.connect(gain);
        gain.connect(droneFilter);
        osc.start();
        self.nodes.push(osc, gain);
      });

      var noise = this.ctx.createBufferSource();
      noise.buffer = makeNoise(this.ctx);
      noise.loop = true;
      var nf = this.ctx.createBiquadFilter();
      var ng = this.ctx.createGain();
      nf.type = 'bandpass';
      nf.frequency.value = cfg.filter * 0.9;
      nf.Q.value = 0.5;
      ng.gain.value = cfg.noise;
      noise.connect(nf); nf.connect(ng); ng.connect(this.masterGain);
      noise.start();
      this.nodes.push(noise, nf, ng);

      this.ping(cfg.beatFreq, 0.028);
      this.beatTimer = window.setInterval(function () { self.ping(cfg.beatFreq, 0.022); }, cfg.beatMs);
    },

    applyVolume: function () {
      if (!this.masterGain || !this.ctx) return;
      var target = this.isActive ? Math.pow(this.volume, 1.35) * 0.085 : 0;
      try {
        this.masterGain.gain.cancelScheduledValues(this.ctx.currentTime);
        this.masterGain.gain.setTargetAtTime(target, this.ctx.currentTime, 0.08);
      } catch (_) { this.masterGain.gain.value = target; }
    },

    ping: function (freq, level, durationMs, wave) {
      if (!this.ctx || !this.masterGain || !this.isActive) return;
      var now = this.ctx.currentTime;
      var dur = (durationMs || 180) / 1000;
      var osc = this.ctx.createOscillator();
      var gain = this.ctx.createGain();
      osc.type = wave || 'sine';
      osc.frequency.setValueAtTime(freq, now);
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(level, now + 0.015);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + dur);
      osc.connect(gain); gain.connect(this.masterGain);
      osc.start(now); osc.stop(now + dur + 0.02);
    },

    // Play a named interaction cue (no-op when the engine is off).
    cue: function (name) {
      var c = CUES[name];
      if (!c) return;
      this.ping(c[0], c[1], c[2], c[3]);
    },

    // playPing alias kept for the front-page sound console wiring.
    playPing: function (freq, level) { this.ping(freq, level); },

    stopNodes: function () {
      this.nodes.forEach(function (node) {
        try { if (typeof node.stop === 'function') node.stop(); } catch (_) {}
        try { node.disconnect(); } catch (_) {}
      });
      this.nodes = [];
    },

    clearBeat: function () {
      if (this.beatTimer) { window.clearInterval(this.beatTimer); this.beatTimer = null; }
    },

    // Subtle platform-wide interaction feedback (buttons, links, nav).
    attachUiFeedback: function () {
      if (this._uiWired) return;
      this._uiWired = true;
      var self = this;
      document.addEventListener('click', function (e) {
        if (!self.isActive) return;
        var t = e.target && e.target.closest && e.target.closest(
          'a, button, .nav-toolbar-link, .nav-toolbar-portal-grid-link, .forum-tab, .forum-chip, .fp-agent-card, .fp-smart-card'
        );
        if (!t) return;
        var isNav = t.matches('a, .nav-toolbar-link, .nav-toolbar-portal-grid-link, .fp-agent-card, .fp-smart-card');
        self.cue(isNav ? 'navigate' : 'click');
      }, true);
    },

    // Simple subscribe for UI (returns unsubscribe).
    _listeners: [],
    onChange: function (fn) {
      this._listeners.push(fn);
      var self = this;
      return function () { self._listeners = self._listeners.filter(function (f) { return f !== fn; }); };
    },
    _emit: function () {
      var self = this;
      this._listeners.forEach(function (fn) { try { fn(self.state()); } catch (_) {} });
    },
    state: function () {
      return { version: VERSION, active: this.isActive, mode: this.mode, volume: this.volume, label: (MODES[this.mode] || MODES.focus).label };
    }
  };

  window.SonicEngine = SonicEngine;
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { SonicEngine._init(); });
  } else {
    SonicEngine._init();
  }
})();
