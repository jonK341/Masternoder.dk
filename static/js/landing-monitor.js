/**
 * Compact lobby monitor — one-stat stream, AI voice, synced lights + SFX.
 */
(function () {
  'use strict';

  var BPM = 180;
  var BEAT_MS = Math.round(60000 / BPM);
  var REFRESH_MS = 5000;
  var SCALE = [220.0, 261.63, 329.63, 392.0, 440.0, 523.25];

  var CAT_COLOR = {
    wallet: '#00ff88',
    battle: '#ff5a6a',
    generator: '#00d4ff',
    profit: '#ffd166',
    social: '#c77dff',
    system: '#9aa4b2',
    network: '#00ff88',
    trade: '#ffd166',
  };

  var CAT_SOUND = {
    wallet: 'coin_sparkle',
    battle: 'impact_blast',
    generator: 'whoosh_rise',
    profit: 'chime_cash',
    social: 'bubble_ping',
    system: 'tick_blip',
    network: 'coin_sparkle',
    trade: 'chime_cash',
    action: 'whoosh_rise',
  };

  function $(id) {
    return document.getElementById(id);
  }

  function prefersReducedMotion() {
    try {
      return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch (e) {
      return false;
    }
  }

  function hexAlpha(hex, alpha) {
    var h = String(hex || '#00ff88').replace('#', '');
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    var r = parseInt(h.slice(0, 2), 16) || 0;
    var g = parseInt(h.slice(2, 4), 16) || 0;
    var b = parseInt(h.slice(4, 6), 16) || 0;
    return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
  }

  function setText(id, text) {
    var el = $(id);
    if (el) el.textContent = text == null ? '' : String(text);
  }

  function fmtCompact(n) {
    var v = Number(n);
    if (!isFinite(v)) return '—';
    var abs = Math.abs(v);
    if (abs >= 1e12) return (v / 1e12).toFixed(2).replace(/\.00$/, '') + 'T';
    if (abs >= 1e9) return (v / 1e9).toFixed(2).replace(/\.00$/, '') + 'B';
    if (abs >= 1e6) return (v / 1e6).toFixed(2).replace(/\.00$/, '') + 'M';
    if (abs >= 1e3) return (v / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
    try {
      return Math.round(v).toLocaleString();
    } catch (e) {
      return String(Math.round(v));
    }
  }

  function ActionSFX() {
    this.ctx = null;
    this.master = null;
    this.enabled = false;
    this.volume = 0.38;
    this.seq = 0;
  }

  ActionSFX.prototype.ensure = function () {
    var Ctor = window.AudioContext || window.webkitAudioContext;
    if (!Ctor) throw new Error('Web Audio unavailable');
    if (!this.ctx) this.ctx = new Ctor();
    if (!this.master) {
      this.master = this.ctx.createGain();
      this.master.gain.value = this.volume;
      this.master.connect(this.ctx.destination);
    }
    if (this.ctx.state === 'suspended') return this.ctx.resume();
    return Promise.resolve();
  };

  ActionSFX.prototype.enable = function () {
    var self = this;
    return this.ensure().then(function () {
      self.enabled = true;
    });
  };

  ActionSFX.prototype.disable = function () {
    this.enabled = false;
  };

  ActionSFX.prototype._tone = function (freq, type, when, dur, gain, slideTo) {
    if (!this.ctx || !this.master) return;
    var o = this.ctx.createOscillator();
    var g = this.ctx.createGain();
    var f = this.ctx.createBiquadFilter();
    o.type = type || 'sine';
    o.frequency.setValueAtTime(freq, when);
    if (slideTo) o.frequency.exponentialRampToValueAtTime(Math.max(20, slideTo), when + dur);
    f.type = 'lowpass';
    f.frequency.value = 4200;
    g.gain.setValueAtTime(0.0001, when);
    g.gain.exponentialRampToValueAtTime(Math.max(0.001, gain), when + 0.012);
    g.gain.exponentialRampToValueAtTime(0.0001, when + dur);
    o.connect(f);
    f.connect(g);
    g.connect(this.master);
    o.start(when);
    o.stop(when + dur + 0.04);
  };

  ActionSFX.prototype._noise = function (when, dur, gain, bandHz) {
    if (!this.ctx || !this.master) return;
    var len = Math.max(1, Math.floor(this.ctx.sampleRate * dur));
    var buf = this.ctx.createBuffer(1, len, this.ctx.sampleRate);
    var data = buf.getChannelData(0);
    for (var i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;
    var src = this.ctx.createBufferSource();
    src.buffer = buf;
    var filter = this.ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.value = bandHz || 1800;
    filter.Q.value = 0.8;
    var g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, when);
    g.gain.exponentialRampToValueAtTime(Math.max(0.001, gain), when + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, when + dur);
    src.connect(filter);
    filter.connect(g);
    g.connect(this.master);
    src.start(when);
    src.stop(when + dur + 0.02);
  };

  ActionSFX.prototype.playAction = function (scene) {
    if (!this.enabled || !this.ctx || !this.master) return;
    var cat = (scene && scene.category) || 'system';
    var sound = (scene && scene.fx && scene.fx.sound) || CAT_SOUND[cat] || 'tick_blip';
    var now = this.ctx.currentTime + 0.01;
    var variation = (this.seq % 5) * 16;
    this.seq += 1;
    switch (sound) {
      case 'coin_sparkle':
        this._tone(880 + variation, 'triangle', now, 0.1, 0.18);
        this._tone(1320 + variation, 'sine', now + 0.05, 0.12, 0.12);
        break;
      case 'impact_blast':
        this._noise(now, 0.12, 0.22, 700);
        this._tone(140, 'sawtooth', now, 0.18, 0.16, 50);
        break;
      case 'whoosh_rise':
        this._noise(now, 0.2, 0.14, 1500);
        this._tone(240 + variation, 'triangle', now, 0.24, 0.12, 780);
        break;
      case 'chime_cash':
        this._tone(523.25, 'sine', now, 0.2, 0.14);
        this._tone(659.25, 'sine', now + 0.07, 0.22, 0.12);
        break;
      case 'bubble_ping':
        this._tone(640 + variation, 'sine', now, 0.08, 0.12, 980);
        break;
      default:
        this._tone(440 + variation, 'square', now, 0.05, 0.08);
        break;
    }
  };

  function LandingMusic(bpm) {
    this.bpm = bpm || BPM;
    this.ctx = null;
    this.master = null;
    this.timer = null;
    this.step = 0;
    this.active = false;
    this.volume = 0.22;
    this.boost = 1;
  }

  LandingMusic.prototype.ensure = function () {
    var Ctor = window.AudioContext || window.webkitAudioContext;
    if (!Ctor) throw new Error('Web Audio unavailable');
    if (!this.ctx) this.ctx = new Ctor();
    if (this.ctx.state === 'suspended') return this.ctx.resume();
    return Promise.resolve();
  };

  LandingMusic.prototype.start = function () {
    var self = this;
    return this.ensure().then(function () {
      if (self.active) return;
      self.active = true;
      self.master = self.ctx.createGain();
      self.master.gain.value = self.volume;
      self.master.connect(self.ctx.destination);
      self.schedule();
    });
  };

  LandingMusic.prototype.stop = function () {
    this.active = false;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    if (this.master) {
      try {
        this.master.disconnect();
      } catch (e) {}
      this.master = null;
    }
  };

  LandingMusic.prototype.note = function (freq, dur, when, gain) {
    if (!this.ctx || !this.master) return;
    var o = this.ctx.createOscillator();
    var g = this.ctx.createGain();
    o.type = this.step % 8 === 0 ? 'sawtooth' : 'triangle';
    o.frequency.value = freq;
    g.gain.setValueAtTime(0.0001, when);
    g.gain.exponentialRampToValueAtTime(gain * this.boost, when + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, when + dur);
    o.connect(g);
    g.connect(this.master);
    o.start(when);
    o.stop(when + dur + 0.04);
  };

  LandingMusic.prototype.kick = function (when) {
    if (!this.ctx || !this.master) return;
    var o = this.ctx.createOscillator();
    var g = this.ctx.createGain();
    o.type = 'sine';
    o.frequency.setValueAtTime(130, when);
    o.frequency.exponentialRampToValueAtTime(42, when + 0.16);
    g.gain.setValueAtTime(0.35 * this.boost, when);
    g.gain.exponentialRampToValueAtTime(0.0001, when + 0.2);
    o.connect(g);
    g.connect(this.master);
    o.start(when);
    o.stop(when + 0.22);
  };

  LandingMusic.prototype.schedule = function () {
    var self = this;
    if (!this.active) return;
    var now = this.ctx.currentTime;
    var beat = 60 / this.bpm;
    this.kick(now);
    this.note(SCALE[this.step % SCALE.length], beat * 0.4, now + 0.01, 0.08);
    this.step += 1;
    this.timer = setTimeout(function () {
      self.schedule();
    }, Math.round(beat * 1000));
  };

  function Lightshow(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.mode = 'pulse';
    this.beat = 0;
    this.t0 = performance.now();
    this.raf = 0;
    this.running = false;
    this.accent = '#00ff88';
    this.boost = 1;
  }

  Lightshow.prototype.setMode = function (id) {
    this.mode = id || 'pulse';
  };
  Lightshow.prototype.setAccent = function (color) {
    this.accent = color || '#00ff88';
  };
  Lightshow.prototype.setBoost = function (n) {
    this.boost = Math.max(1, Math.min(2, Number(n) || 1));
    if (this.canvas) this.canvas.classList.toggle('is-boost', this.boost > 1.1);
  };
  Lightshow.prototype.pulse = function () {
    this.beat = Math.min(1.4, 1 * this.boost);
  };
  Lightshow.prototype.start = function () {
    if (this.running || prefersReducedMotion()) return;
    this.running = true;
    var self = this;
    var draw = function (ts) {
      self.draw(ts);
      self.raf = requestAnimationFrame(draw);
    };
    this.raf = requestAnimationFrame(draw);
  };
  Lightshow.prototype.stop = function () {
    this.running = false;
    if (this.raf) cancelAnimationFrame(this.raf);
  };
  Lightshow.prototype.draw = function (ts) {
    var ctx = this.ctx;
    var w = this.canvas.width;
    var h = this.canvas.height;
    var t = (ts - this.t0) / 1000;
    this.beat *= 0.86;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = 'rgba(4,8,18,0.88)';
    ctx.fillRect(0, 0, w, h);
    var mode = this.mode;
    var boost = this.boost;
    if (mode === 'spectrum') {
      var bars = 28;
      for (var b = 0; b < bars; b++) {
        var bh = (0.2 + 0.8 * Math.abs(Math.sin(t * 7 * boost + b * 0.35))) * h * (0.4 + this.beat * 0.35);
        ctx.fillStyle = this.accent;
        ctx.globalAlpha = 0.5 + (b % 3) * 0.12;
        ctx.fillRect((b / bars) * w + 2, h - bh, w / bars - 3, bh);
      }
      ctx.globalAlpha = 1;
    } else if (mode === 'chase') {
      var n = 14;
      var idx = Math.floor(t * (BPM / 60) * boost) % n;
      for (var c = 0; c < n; c++) {
        var a = (c / n) * Math.PI * 2;
        var r = Math.min(w, h) * 0.28;
        ctx.beginPath();
        ctx.arc(w / 2 + Math.cos(a) * r, h / 2 + Math.sin(a) * r, c === idx ? 8 + this.beat * 5 : 4, 0, Math.PI * 2);
        ctx.fillStyle = c === idx ? this.accent : 'rgba(0,212,255,0.3)';
        ctx.fill();
      }
    } else if (mode === 'wave') {
      for (var i = 0; i < 4; i++) {
        ctx.beginPath();
        for (var x = 0; x < w; x += 5) {
          var y = h / 2 + Math.sin(x * 0.02 + t * 5 + i) * (12 + i * 6 + this.beat * 14);
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = 'hsla(' + ((t * 70 + i * 40) % 360) + ',90%,60%,0.45)';
        ctx.stroke();
      }
    } else {
      var rad = Math.min(w, h) * (0.2 + this.beat * 0.14 * boost);
      var g = ctx.createRadialGradient(w / 2, h / 2, 3, w / 2, h / 2, rad * 2);
      g.addColorStop(0, hexAlpha(this.accent, 0.5 + this.beat * 0.3));
      g.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, w, h);
    }
  };

  function paintHidden(payload) {
    if (!payload || !payload.success) return payload && payload.lightshow;
    var stats = payload.stats || {};
    setText('lm-stat-videos', (stats.total_videos || 0).toLocaleString());
    setText('lm-stat-users', (stats.total_users || 0).toLocaleString());
    setText('lm-stat-battles', (stats.total_battles || 0).toLocaleString());
    setText(
      'lm-stat-mn2',
      stats.mn2_usd_price != null ? '$' + Number(stats.mn2_usd_price).toFixed(4) : '—'
    );
    setText('lm-stat-daemon', stats.daemon_ok === true ? 'online' : stats.daemon_ok === false ? 'offline' : '—');
    setText('lm-stat-height', stats.block_height != null ? String(stats.block_height) : '—');
    var totals = (payload.sats && payload.sats.totals) || {};
    setText('lm-stat-network-sats', fmtCompact(totals.network_sats || stats.network_sats || 0));
    setText('lm-stat-trade-sats', fmtCompact(totals.trade_sats || stats.trade_sats || 0));
    setText('lm-stat-combined-sats', fmtCompact(totals.combined_sats || stats.combined_sats || 0));
    var special = payload.special || {};
    setText('lm-special-title', special.title || '');
    setText('lm-special-body', special.body || '');
    var cta = $('lm-special-cta');
    if (cta) {
      cta.href = special.href || '/';
      cta.textContent = special.cta || 'Open';
    }
    setText('lm-bpm', String(payload.bpm || BPM) + ' BPM');
    setText('lm-updated', payload.updated_at ? String(payload.updated_at).slice(11, 19) + 'Z' : '');
    if (stats.total_videos != null && $('stat-videos')) $('stat-videos').textContent = (stats.total_videos || 0).toLocaleString();
    if (stats.total_users != null && $('stat-users')) $('stat-users').textContent = (stats.total_users || 0).toLocaleString();
    if (stats.total_battles != null && $('stat-battles')) $('stat-battles').textContent = (stats.total_battles || 0).toLocaleString();
    if (stats.mn2_usd_price != null && $('stat-mn2-price')) {
      $('stat-mn2-price').textContent = '$' + Number(stats.mn2_usd_price).toFixed(4);
    }
    return payload.lightshow || {};
  }

  function buildStatStream(payload) {
    var stats = (payload && payload.stats) || {};
    var totals = ((payload && payload.sats) || {}).totals || {};
    var special = (payload && payload.special) || {};
    var actions = (payload && (payload.actions || payload.reel)) || [];
    var items = [];

    function push(id, category, kicker, value, label, speak, sound, mode) {
      items.push({
        id: id,
        category: category,
        kicker: kicker,
        value: value,
        label: label,
        speak: speak,
        fx: { sound: sound || CAT_SOUND[category] || 'tick_blip', lightshow: mode || 'pulse', color: CAT_COLOR[category] || '#00ff88' },
      });
    }

    push(
      'videos',
      'generator',
      'Platform',
      fmtCompact(stats.total_videos || 0),
      'Videos on the platform',
      'Videos on the platform: ' + fmtCompact(stats.total_videos || 0) + '.',
      'whoosh_rise',
      'wave'
    );
    push(
      'users',
      'social',
      'Platform',
      fmtCompact(stats.total_users || 0),
      'Active users',
      'Users online in the ledger: ' + fmtCompact(stats.total_users || 0) + '.',
      'bubble_ping',
      'pulse'
    );
    push(
      'battles',
      'battle',
      'Arena',
      fmtCompact(stats.total_battles || 0),
      'Battles logged',
      'Battle count: ' + fmtCompact(stats.total_battles || 0) + '.',
      'impact_blast',
      'chase'
    );
    if (stats.mn2_usd_price != null) {
      push(
        'mn2',
        'wallet',
        'MN2',
        '$' + Number(stats.mn2_usd_price).toFixed(4),
        'MN2 spot price',
        'M N 2 price is ' + Number(stats.mn2_usd_price).toFixed(4) + ' dollars.',
        'coin_sparkle',
        'spectrum'
      );
    }
    push(
      'daemon',
      'system',
      'Daemon',
      stats.daemon_ok === true ? 'online' : stats.daemon_ok === false ? 'offline' : '—',
      'Chain daemon status',
      'Daemon status: ' + (stats.daemon_ok === true ? 'online' : stats.daemon_ok === false ? 'offline' : 'unknown') + '.',
      'tick_blip',
      'pulse'
    );
    if (stats.block_height != null) {
      push(
        'height',
        'system',
        'Chain',
        fmtCompact(stats.block_height),
        'Block height',
        'Block height ' + fmtCompact(stats.block_height) + '.',
        'tick_blip',
        'pulse'
      );
    }
    push(
      'network_sats',
      'network',
      'Network sats',
      fmtCompact(totals.network_sats || stats.network_sats || 0),
      'On-chain + venue sats',
      'Network sats on screen: ' + fmtCompact(totals.network_sats || stats.network_sats || 0) + '.',
      'coin_sparkle',
      'spectrum'
    );
    push(
      'trade_sats',
      'trade',
      'Trade sats',
      fmtCompact(totals.trade_sats || stats.trade_sats || 0),
      'Daemon trade sats',
      'Daemon trade sats: ' + fmtCompact(totals.trade_sats || stats.trade_sats || 0) + '.',
      'chime_cash',
      'chase'
    );
    if (special.title) {
      push(
        'special',
        'social',
        'Special',
        special.title,
        special.body || 'Lobby special',
        'Lobby special: ' + special.title + '. ' + (special.body || ''),
        'bubble_ping',
        'rainbow'
      );
    }
    for (var i = 0; i < Math.min(3, actions.length); i++) {
      var a = actions[i] || {};
      var cat = a.category || 'action';
      push(
        'act_' + (a.id || i),
        cat,
        'Action',
        a.title || a.type || 'event',
        a.text || 'Live action',
        a.speak || ('Action update: ' + (a.title || a.type || 'event') + '.'),
        (a.fx && a.fx.sound) || CAT_SOUND[cat] || 'whoosh_rise',
        (a.fx && a.fx.lightshow) || 'wave'
      );
    }
    return items;
  }

  function StatStream(opts) {
    this.show = opts.show;
    this.music = opts.music;
    this.sfx = opts.sfx;
    this.root = opts.root;
    this.items = [];
    this.index = 0;
    this.playing = false;
    this.timer = null;
    this.speechDone = true;
    this.fingerprint = '';
  }

  StatStream.prototype.setItems = function (items, fingerprint) {
    var next = Array.isArray(items) ? items.slice() : [];
    var changed = fingerprint && fingerprint !== this.fingerprint;
    this.fingerprint = fingerprint || this.fingerprint;
    if (!next.length) return;
    if (!this.playing) {
      this.items = next;
      this.renderIdle();
      return;
    }
    if (changed) {
      // Keep the stream moving — swap queue, continue from current index modulo.
      var keepId = this.items[this.index] && this.items[this.index].id;
      this.items = next;
      var found = -1;
      for (var i = 0; i < next.length; i++) {
        if (next[i].id === keepId) {
          found = i;
          break;
        }
      }
      this.index = found >= 0 ? found : 0;
    } else {
      this.items = next;
    }
  };

  StatStream.prototype.renderIdle = function () {
    var first = this.items[0];
    setText('lm-stream-pos', '0/' + this.items.length);
    setText('lm-hud-kicker', first ? first.kicker : 'Ready');
    setText('lm-hud-value', first ? first.value : '—');
    setText('lm-hud-label', first ? 'Tap Start stream — AI reads each stat in order.' : 'Waiting for live stats…');
    var bar = $('lm-stream-bar');
    if (bar) bar.style.width = '0%';
  };

  StatStream.prototype.start = function () {
    if (!this.items.length) {
      setText('lm-hud-label', 'No stats yet — refreshing…');
      return;
    }
    this.playing = true;
    this.index = 0;
    var btn = $('lm-stream-play');
    if (btn) {
      btn.setAttribute('aria-pressed', 'true');
      btn.textContent = 'Streaming…';
    }
    if (this.show && !this.show.running) this.show.start();
    this.next();
  };

  StatStream.prototype.stop = function () {
    this.playing = false;
    this.speechDone = true;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    if (window.MNCamgirlsStreamVoice) window.MNCamgirlsStreamVoice.cancel();
    if (this.root) {
      this.root.classList.remove('is-speaking');
      this.root.classList.remove('is-sync-hit');
    }
    if (this.show) this.show.setBoost(1);
    if (this.music) this.music.boost = 1;
    var btn = $('lm-stream-play');
    if (btn) {
      btn.setAttribute('aria-pressed', 'false');
      btn.textContent = 'Start stream';
    }
    this.renderIdle();
  };

  StatStream.prototype.skip = function () {
    if (!this.playing) {
      this.start();
      return;
    }
    if (this.timer) clearTimeout(this.timer);
    if (window.MNCamgirlsStreamVoice) window.MNCamgirlsStreamVoice.cancel();
    this.speechDone = true;
    this.index = (this.index + 1) % Math.max(1, this.items.length);
    this.next();
  };

  StatStream.prototype.next = function () {
    var self = this;
    if (!this.playing || !this.items.length) return;
    if (this.index >= this.items.length) this.index = 0;

    var item = this.items[this.index];
    var hud = document.querySelector('.lm-hud');
    if (hud) {
      hud.classList.add('is-swap');
      setTimeout(function () {
        hud.classList.remove('is-swap');
      }, 160);
    }

    setText('lm-hud-kicker', item.kicker);
    setText('lm-hud-value', item.value);
    setText('lm-hud-label', item.label);
    setText('lm-stream-pos', this.index + 1 + '/' + this.items.length);
    var bar = $('lm-stream-bar');
    if (bar) bar.style.width = ((this.index + 1) / this.items.length) * 100 + '%';

    var fx = item.fx || {};
    if (this.root) {
      this.root.classList.add('is-sync-hit');
      this.root.style.setProperty('--lm-scene-color', fx.color || '#00ff88');
      setTimeout(function () {
        if (self.root) self.root.classList.remove('is-sync-hit');
      }, 180);
    }
    if (this.show) {
      this.show.setMode(fx.lightshow || 'pulse');
      this.show.setAccent(fx.color || '#00ff88');
      this.show.setBoost(1.25);
      this.show.pulse();
    }
    if (this.music) this.music.boost = 1.15;
    if (this.sfx) this.sfx.playAction(item);

    this.speechDone = false;
    var line = item.speak || item.label || String(item.value);
    var voice = window.MNCamgirlsStreamVoice;
    var started = Date.now();
    var minHold = Math.max(2200, Math.min(7000, 55 * line.length));

    function finishSpeech() {
      self.speechDone = true;
      if (self.root) self.root.classList.remove('is-speaking');
    }

    if (voice && voice.isEnabled()) {
      if (this.root) this.root.classList.add('is-speaking');
      voice.speak(line, {
        force: true,
        interrupt: true,
        rotate: true,
        queue: false,
        onstart: function (sp) {
          if (sp) {
            setText('lm-voice-name', sp.name || 'AI host');
            var av = $('lm-voice-avatar');
            if (av && sp.avatar) av.src = sp.avatar;
          }
          setText('lm-voice-line', line);
        },
        onend: finishSpeech,
      });
    } else {
      setText('lm-voice-line', line);
      finishSpeech();
    }

    function advance() {
      if (!self.playing) return;
      var waited = Date.now() - started;
      if (!self.speechDone || waited < minHold) {
        self.timer = setTimeout(advance, 100);
        return;
      }
      var rem = waited % BEAT_MS;
      var pad = rem === 0 ? 0 : BEAT_MS - rem;
      self.timer = setTimeout(function () {
        if (!self.playing) return;
        self.index = (self.index + 1) % self.items.length;
        self.next();
      }, pad);
    }
    advance();
  };

  function mount() {
    var root = $('fp-landing-monitor');
    if (!root) return;

    var canvas = $('lm-canvas');
    if (canvas) {
      canvas.width = Math.max(480, canvas.clientWidth || 720);
      canvas.height = 160;
    }
    var show = canvas ? new Lightshow(canvas) : null;
    var music = new LandingMusic(BPM);
    var sfx = new ActionSFX();
    var stream = new StatStream({ show: show, music: music, sfx: sfx, root: root });
    var beatTimer = null;
    var lightBtn = $('lm-light-toggle');
    var musicBtn = $('lm-music-toggle');
    var sfxBtn = $('lm-sfx-toggle');
    var voiceBtn = $('lm-voice-toggle');
    var playBtn = $('lm-stream-play');
    var skipBtn = $('lm-stream-skip');
    var voiceLead = $('lm-voice-lead');
    var lastFp = '';

    function enableSfx() {
      return sfx.enable().then(function () {
        if (sfxBtn) {
          sfxBtn.setAttribute('aria-pressed', 'true');
          sfxBtn.textContent = 'SFX on';
        }
      });
    }

    function fillVoiceLead(speakers) {
      if (!voiceLead) return;
      voiceLead.innerHTML = '';
      (speakers || []).forEach(function (sp) {
        var opt = document.createElement('option');
        opt.value = sp.id;
        opt.textContent = sp.name || sp.id;
        voiceLead.appendChild(opt);
      });
      if (window.MNCamgirlsStreamVoice && window.MNCamgirlsStreamVoice.getLeadSpeakerId) {
        voiceLead.value = window.MNCamgirlsStreamVoice.getLeadSpeakerId() || '';
      }
    }

    function initVoice() {
      if (!window.MNCamgirlsStreamVoice) return Promise.resolve();
      return window.MNCamgirlsStreamVoice
        .init({
          performersApi: '/api/camgirls/performers',
          storageKey: 'mn-lm-camgirl-voice',
          onActiveSpeaker: function (id) {
            var speakers = window.MNCamgirlsStreamVoice.getSpeakers() || [];
            var sp = speakers.filter(function (s) {
              return s.id === id;
            })[0];
            if (!sp) return;
            setText('lm-voice-name', sp.name || 'AI host');
            var av = $('lm-voice-avatar');
            if (av && sp.avatar) av.src = sp.avatar;
          },
          onLine: function (sp, text) {
            if (sp) setText('lm-voice-name', sp.name || 'AI host');
            setText('lm-voice-line', text || '');
          },
        })
        .then(fillVoiceLead);
    }

    function onBeat() {
      if (show) show.pulse();
      root.classList.add('is-beat');
      setTimeout(function () {
        root.classList.remove('is-beat');
      }, 100);
    }

    function startBeatClock() {
      if (beatTimer) clearInterval(beatTimer);
      if (prefersReducedMotion()) return;
      beatTimer = setInterval(onBeat, BEAT_MS);
      onBeat();
    }

    function fingerprint(payload) {
      var s = (payload && payload.stats) || {};
      var t = ((payload && payload.sats) || {}).totals || {};
      return [s.total_videos, s.total_users, s.total_battles, s.block_height, t.network_sats, t.trade_sats].join('|');
    }

    async function refresh() {
      try {
        var res = await fetch('/api/landing/monitor', { headers: { Accept: 'application/json' } });
        if (!res.ok) throw new Error('monitor ' + res.status);
        var data = await res.json();
        if (!data || !data.success) throw new Error('monitor payload');
        var light = paintHidden(data) || {};
        if (show && !stream.playing) show.setMode(light.id || 'pulse');
        if (data.bpm) music.bpm = data.bpm;
        var fp = fingerprint(data);
        stream.setItems(buildStatStream(data), fp);
        if (fp !== lastFp) lastFp = fp;
      } catch (e) {
        setText('lm-updated', 'retrying');
      }
    }

    function armStream() {
      if (lightBtn && lightBtn.getAttribute('aria-pressed') !== 'true') lightBtn.click();
      if (!sfx.enabled) enableSfx().catch(function () {});
      if (window.MNCamgirlsStreamVoice && !window.MNCamgirlsStreamVoice.isEnabled()) {
        window.MNCamgirlsStreamVoice.setEnabled(true);
        if (voiceBtn) {
          voiceBtn.setAttribute('aria-pressed', 'true');
          voiceBtn.textContent = 'Voice on';
        }
      }
    }

    initVoice().catch(function () {});

    if (lightBtn) {
      lightBtn.addEventListener('click', function () {
        var on = lightBtn.getAttribute('aria-pressed') !== 'true';
        lightBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
        lightBtn.textContent = on ? 'Lights on' : 'Lights off';
        if (on) {
          if (show) show.start();
          startBeatClock();
          if (!sfx.enabled) enableSfx().catch(function () {});
        } else {
          if (show) show.stop();
          if (beatTimer) clearInterval(beatTimer);
        }
      });
    }

    if (musicBtn) {
      musicBtn.addEventListener('click', function () {
        var on = musicBtn.getAttribute('aria-pressed') !== 'true';
        if (on) {
          music
            .start()
            .then(function () {
              musicBtn.setAttribute('aria-pressed', 'true');
              musicBtn.textContent = 'Music on';
              if (lightBtn && lightBtn.getAttribute('aria-pressed') !== 'true') lightBtn.click();
            })
            .catch(function () {
              musicBtn.textContent = 'Music n/a';
            });
        } else {
          music.stop();
          musicBtn.setAttribute('aria-pressed', 'false');
          musicBtn.textContent = 'Music off';
        }
      });
    }

    if (sfxBtn) {
      sfxBtn.addEventListener('click', function () {
        var on = sfxBtn.getAttribute('aria-pressed') !== 'true';
        if (on) {
          enableSfx()
            .then(function () {
              sfx.playAction({ category: 'wallet', fx: { sound: 'coin_sparkle' } });
            })
            .catch(function () {
              sfxBtn.textContent = 'SFX n/a';
            });
        } else {
          sfx.disable();
          sfxBtn.setAttribute('aria-pressed', 'false');
          sfxBtn.textContent = 'SFX off';
        }
      });
    }

    if (voiceBtn) {
      voiceBtn.addEventListener('click', function () {
        if (!window.MNCamgirlsStreamVoice) {
          voiceBtn.textContent = 'Voice n/a';
          return;
        }
        var on = voiceBtn.getAttribute('aria-pressed') !== 'true';
        initVoice().then(function () {
          window.MNCamgirlsStreamVoice.setEnabled(on);
          voiceBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
          voiceBtn.textContent = on ? 'Voice on' : 'Voice off';
          if (on) {
            window.MNCamgirlsStreamVoice.speak('Voice online. I will read each stat on the monitor.', {
              force: true,
              interrupt: true,
              rotate: true,
            });
          }
        });
      });
    }

    if (voiceLead) {
      voiceLead.addEventListener('change', function () {
        if (window.MNCamgirlsStreamVoice) window.MNCamgirlsStreamVoice.setLeadSpeaker(voiceLead.value);
      });
    }

    if (playBtn) {
      playBtn.addEventListener('click', function () {
        if (stream.playing) {
          stream.stop();
          return;
        }
        armStream();
        stream.start();
      });
    }
    if (skipBtn) {
      skipBtn.addEventListener('click', function () {
        armStream();
        stream.skip();
      });
    }

    refresh();
    setInterval(refresh, REFRESH_MS);
    if (!prefersReducedMotion() && lightBtn) lightBtn.click();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
})();
