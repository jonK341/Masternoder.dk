/**
 * Frontpage landing monitor — live data, action learn/store reel, 180 BPM FX + action SFX.
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
    finale: 'sparkle_cascade',
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

  /** One-shot SFX bus — a fresh category sound fires on every new action. */
  function ActionSFX() {
    this.ctx = null;
    this.master = null;
    this.enabled = false;
    this.volume = 0.42;
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

  /** Play a unique one-shot for this action (category + novelty + sequence). */
  ActionSFX.prototype.playAction = function (scene) {
    if (!this.enabled || !this.ctx || !this.master) return;
    var cat = (scene && scene.category) || 'system';
    var sound = (scene && scene.fx && scene.fx.sound) || CAT_SOUND[cat] || 'tick_blip';
    var now = this.ctx.currentTime + 0.01;
    var variation = (this.seq % 5) * 18;
    this.seq += 1;

    switch (sound) {
      case 'coin_sparkle':
        this._tone(880 + variation, 'triangle', now, 0.12, 0.22);
        this._tone(1320 + variation, 'sine', now + 0.06, 0.16, 0.16);
        this._tone(1760 + variation * 0.5, 'sine', now + 0.12, 0.2, 0.1);
        break;
      case 'glitter_burst':
        this._tone(990 + variation, 'sine', now, 0.08, 0.14);
        this._tone(1480, 'triangle', now + 0.05, 0.1, 0.12);
        this._tone(1980, 'sine', now + 0.1, 0.14, 0.1);
        this._noise(now, 0.06, 0.06, 3200);
        break;
      case 'impact_blast':
        this._noise(now, 0.14, 0.28, 700);
        this._tone(160 + variation * 0.2, 'sawtooth', now, 0.22, 0.2, 55);
        this._tone(90, 'sine', now + 0.02, 0.18, 0.18, 40);
        break;
      case 'whoosh_rise':
        this._noise(now, 0.28, 0.18, 1400 + variation);
        this._tone(220 + variation, 'triangle', now, 0.32, 0.14, 720 + variation);
        this._tone(330, 'sine', now + 0.1, 0.22, 0.1, 990);
        break;
      case 'chime_cash':
        this._tone(523.25, 'sine', now, 0.28, 0.18);
        this._tone(659.25, 'sine', now + 0.08, 0.3, 0.15);
        this._tone(783.99 + variation * 0.3, 'triangle', now + 0.16, 0.36, 0.12);
        break;
      case 'fanfare_rise':
        this._tone(392, 'sawtooth', now, 0.18, 0.12);
        this._tone(523.25, 'triangle', now + 0.12, 0.2, 0.14);
        this._tone(659.25, 'sine', now + 0.24, 0.28, 0.16);
        this._tone(784, 'sine', now + 0.36, 0.32, 0.12);
        break;
      case 'bubble_ping':
        this._tone(640 + variation, 'sine', now, 0.1, 0.16, 980);
        this._tone(520, 'triangle', now + 0.09, 0.14, 0.12, 760);
        this._noise(now + 0.02, 0.08, 0.08, 2400);
        break;
      case 'sparkle_cascade':
        for (var i = 0; i < 5; i++) {
          this._tone(700 + i * 180 + variation, 'sine', now + i * 0.05, 0.12, 0.1 - i * 0.012);
        }
        this._noise(now, 0.16, 0.1, 2600);
        break;
      case 'soft_thud':
        this._tone(110, 'sine', now, 0.2, 0.22, 48);
        this._noise(now, 0.1, 0.12, 400);
        break;
      case 'laser_zip':
        this._tone(240 + variation, 'sawtooth', now, 0.16, 0.14, 1400);
        this._noise(now, 0.08, 0.08, 1800);
        break;
      case 'tick_blip':
      default:
        this._tone(440 + variation, 'square', now, 0.06, 0.1);
        this._tone(660, 'sine', now + 0.05, 0.08, 0.08);
        break;
    }
  };

  ActionSFX.prototype.playSyncHit = function () {
    this.playAction({ category: 'system', fx: { sound: 'soft_thud' } });
  };

  function LandingMusic(bpm) {
    this.bpm = bpm || BPM;
    this.ctx = null;
    this.master = null;
    this.timer = null;
    this.step = 0;
    this.active = false;
    this.volume = 0.28;
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
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
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
    var f = this.ctx.createBiquadFilter();
    o.type = this.step % 8 === 0 ? 'sawtooth' : 'triangle';
    o.frequency.value = freq;
    f.type = 'lowpass';
    f.frequency.value = 1400 + (this.step % 4) * 180;
    g.gain.setValueAtTime(0.0001, when);
    g.gain.exponentialRampToValueAtTime(gain * this.boost, when + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, when + dur);
    o.connect(f);
    f.connect(g);
    g.connect(this.master);
    o.start(when);
    o.stop(when + dur + 0.05);
  };

  LandingMusic.prototype.kick = function (when) {
    if (!this.ctx || !this.master) return;
    var o = this.ctx.createOscillator();
    var g = this.ctx.createGain();
    o.type = 'sine';
    o.frequency.setValueAtTime(140, when);
    o.frequency.exponentialRampToValueAtTime(42, when + 0.18);
    g.gain.setValueAtTime(0.45 * this.boost, when);
    g.gain.exponentialRampToValueAtTime(0.0001, when + 0.22);
    o.connect(g);
    g.connect(this.master);
    o.start(when);
    o.stop(when + 0.25);
  };

  LandingMusic.prototype.schedule = function () {
    var self = this;
    if (!this.active) return;
    var now = this.ctx.currentTime;
    var beat = 60 / this.bpm;
    this.kick(now);
    if (this.step % 2 === 0) this.kick(now + beat * 0.5);
    var deg = SCALE[(this.step * 3 + (this.step % 5)) % SCALE.length];
    var deg2 = SCALE[(this.step * 2 + 1) % SCALE.length];
    this.note(deg, beat * 0.42, now + 0.01, 0.12);
    this.note(deg2, beat * 0.28, now + beat * 0.25, 0.09);
    if (this.step % 4 === 3) {
      this.note(deg * 2, beat * 0.55, now + beat * 0.5, 0.08);
    }
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
    this.caption = '';
  }

  Lightshow.prototype.setMode = function (id) {
    this.mode = id || 'pulse';
  };

  Lightshow.prototype.setAccent = function (color) {
    this.accent = color || '#00ff88';
  };

  Lightshow.prototype.setBoost = function (n) {
    this.boost = Math.max(1, Math.min(2.2, Number(n) || 1));
    if (this.canvas) {
      if (this.boost > 1.15) this.canvas.classList.add('is-boost');
      else this.canvas.classList.remove('is-boost');
    }
  };

  Lightshow.prototype.pulse = function () {
    this.beat = Math.min(1.6, 1 * this.boost);
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
    ctx.fillStyle = 'rgba(4,8,18,0.92)';
    ctx.fillRect(0, 0, w, h);

    var mode = this.mode;
    var boost = this.boost;
    if (mode === 'wave') {
      for (var i = 0; i < 6 + Math.floor(boost); i++) {
        ctx.beginPath();
        for (var x = 0; x < w; x += 4) {
          var y = h / 2 + Math.sin(x * 0.02 + t * 6 * boost + i) * (18 + i * 8 + this.beat * 20 * boost);
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = 'hsla(' + ((t * 80 + i * 40) % 360) + ',90%,60%,' + (0.35 + this.beat * 0.4) + ')';
        ctx.lineWidth = 2 + (boost > 1.2 ? 1 : 0);
        ctx.stroke();
      }
    } else if (mode === 'spectrum') {
      var bars = 24 + Math.floor((boost - 1) * 8);
      for (var b = 0; b < bars; b++) {
        var bh = (0.2 + 0.8 * Math.abs(Math.sin(t * 8 * boost + b * 0.4))) * h * (0.35 + this.beat * 0.45 * boost);
        ctx.fillStyle = this.accent;
        ctx.globalAlpha = 0.55 + (b % 3) * 0.12;
        ctx.fillRect((b / bars) * w + 2, h - bh, w / bars - 4, bh);
        ctx.globalAlpha = 1;
      }
    } else if (mode === 'chase') {
      var n = 16;
      var idx = Math.floor(t * (BPM / 60) * boost) % n;
      for (var c = 0; c < n; c++) {
        var a = (c / n) * Math.PI * 2;
        var r = Math.min(w, h) * 0.32;
        var cx = w / 2 + Math.cos(a) * r;
        var cy = h / 2 + Math.sin(a) * r;
        var on = c === idx || c === (idx + 1) % n || (boost > 1.3 && c === (idx + 2) % n);
        ctx.beginPath();
        ctx.arc(cx, cy, on ? 10 + this.beat * 8 * boost : 5, 0, Math.PI * 2);
        ctx.fillStyle = on ? this.accent : 'rgba(0,212,255,0.35)';
        ctx.fill();
      }
    } else if (mode === 'rainbow') {
      var grd = ctx.createLinearGradient(0, 0, w, h);
      var hue = (t * 60 * boost) % 360;
      grd.addColorStop(0, 'hsla(' + hue + ',90%,50%,0.55)');
      grd.addColorStop(0.5, 'hsla(' + ((hue + 80) % 360) + ',90%,50%,0.45)');
      grd.addColorStop(1, 'hsla(' + ((hue + 160) % 360) + ',90%,50%,0.55)');
      ctx.fillStyle = grd;
      ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = 'rgba(0,0,0,' + (0.35 - this.beat * 0.15) + ')';
      ctx.fillRect(0, 0, w, h);
    } else {
      var rad = Math.min(w, h) * (0.22 + this.beat * 0.18 * boost);
      var g = ctx.createRadialGradient(w / 2, h / 2, 4, w / 2, h / 2, rad * 2.2);
      g.addColorStop(0, hexAlpha(this.accent, 0.55 + this.beat * 0.35));
      g.addColorStop(0.45, 'rgba(0,212,255,0.28)');
      g.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, w, h);
      ctx.beginPath();
      ctx.arc(w / 2, h / 2, rad, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(255,255,255,0.35)';
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    ctx.fillStyle = 'rgba(255,255,255,0.75)';
    ctx.font = '12px ui-monospace, monospace';
    ctx.fillText(String(BPM) + ' BPM · ' + mode + (boost > 1.05 ? ' · FX+' : ''), 12, 20);
    if (this.caption) {
      ctx.fillStyle = 'rgba(255,255,255,0.9)';
      ctx.font = 'bold 14px ui-sans-serif, system-ui, sans-serif';
      ctx.fillText(this.caption.slice(0, 48), 12, h - 16);
    }
  };

  function setText(id, text) {
    var el = $(id);
    if (el) el.textContent = text;
  }

  function fmtSats(n) {
    var v = Number(n || 0);
    if (!isFinite(v)) return '—';
    try {
      return Math.round(v).toLocaleString();
    } catch (e) {
      return String(Math.round(v));
    }
  }

  function flashStat(id) {
    var el = $(id);
    if (!el) return;
    var btn = el.closest ? el.closest('.lm-stat-btn') : null;
    var target = btn || el.parentElement;
    if (!target) return;
    target.classList.remove('is-flash');
    void target.offsetWidth;
    target.classList.add('is-flash');
    setTimeout(function () {
      target.classList.remove('is-flash');
    }, 750);
  }

  function paint(payload) {
    if (!payload || !payload.success) return;
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

    var sats = payload.sats || {};
    var totals = sats.totals || {};
    var net = totals.network_sats != null ? totals.network_sats : stats.network_sats;
    var trade = totals.trade_sats != null ? totals.trade_sats : stats.trade_sats;
    var combined = totals.combined_sats != null ? totals.combined_sats : stats.combined_sats;
    setText('lm-stat-network-sats', fmtSats(net));
    setText('lm-stat-trade-sats', fmtSats(trade));
    setText('lm-stat-combined-sats', fmtSats(combined));

    var special = payload.special || {};
    setText('lm-special-title', special.title || 'Special');
    setText('lm-special-body', special.body || '');
    var cta = $('lm-special-cta');
    if (cta) {
      cta.href = special.href || '/';
      cta.textContent = special.cta || 'Open';
    }

    var fx = payload.effect_explain || {};
    setText('lm-effect-title', fx.title || 'Effect');
    setText('lm-effect-body', fx.body || '');
    setText('lm-effect-safety', fx.safety || '');
    setText('lm-bpm', String(payload.bpm || BPM) + ' BPM');
    setText('lm-updated', payload.updated_at ? 'Updated ' + payload.updated_at : '');

    var learn = payload.learning || {};
    var cats = learn.categories || {};
    var catBits = Object.keys(cats)
      .map(function (k) {
        return k + ':' + (cats[k].count || 0);
      })
      .slice(0, 4)
      .join(' · ');
    setText(
      'lm-learn-stats',
      'Learned ' + (learn.total_actions || 0) + (catBits ? ' · ' + catBits : '')
    );

    var pipeMeta = payload.pipeline || {};
    if (pipeMeta.cut_id) setText('lm-pipeline-gen', 'cut ' + pipeMeta.cut_id + ' · ' + (pipeMeta.generator || 'AI'));
    if (pipeMeta.regen_reason) setText('lm-pipeline-reason', String(pipeMeta.regen_reason).replace(/_/g, ' '));
    setText('lm-pipeline-sats', 'net ' + fmtSats(net) + ' · trade ' + fmtSats(trade));

    if (stats.total_videos != null && $('stat-videos')) {
      $('stat-videos').textContent = (stats.total_videos || 0).toLocaleString();
    }
    if (stats.total_users != null && $('stat-users')) {
      $('stat-users').textContent = (stats.total_users || 0).toLocaleString();
    }
    if (stats.total_battles != null && $('stat-battles')) {
      $('stat-battles').textContent = (stats.total_battles || 0).toLocaleString();
    }
    if (stats.mn2_usd_price != null && $('stat-mn2-price')) {
      $('stat-mn2-price').textContent = '$' + Number(stats.mn2_usd_price).toFixed(4);
    }

    return payload.lightshow || {};
  }

  function formatClock(ms) {
    var total = Math.max(0, Math.floor(Number(ms || 0) / 1000));
    var m = Math.floor(total / 60);
    var s = total % 60;
    return m + ':' + (s < 10 ? '0' : '') + s;
  }

  function PipelinePlayer(opts) {
    this.show = opts.show;
    this.music = opts.music;
    this.sfx = opts.sfx;
    this.root = opts.root;
    this.panel = document.querySelector('.lm-pipeline-panel');
    this.playBtn = $('lm-pipeline-play');
    this.scenes = [];
    this.index = 0;
    this.playing = false;
    this.timer = null;
    this.elapsed = 0;
    this.duration = 12 * 60 * 1000;
    this.fingerprint = null;
    this.cutId = null;
    this.focus = 'combined';
  }

  PipelinePlayer.prototype.setFocus = function (focus) {
    this.focus = focus || 'combined';
    document.querySelectorAll('.lm-stat-btn').forEach(function (btn) {
      btn.classList.toggle('is-active', btn.getAttribute('data-sats-focus') === focus);
    });
  };

  PipelinePlayer.prototype.loadCut = function (pipe, opts) {
    opts = opts || {};
    var scenes = Array.isArray(pipe && pipe.scenes) ? pipe.scenes.slice() : [];
    if (this.focus === 'network') {
      scenes = scenes.filter(function (s) {
        return s.sats_kind === 'network' || s.category === 'network' || s.category === 'wallet';
      }).concat(scenes.filter(function (s) {
        return !(s.sats_kind === 'network' || s.category === 'network' || s.category === 'wallet');
      }));
    } else if (this.focus === 'trade') {
      scenes = scenes.filter(function (s) {
        return s.sats_kind === 'trade' || s.category === 'trade' || s.category === 'profit';
      }).concat(scenes.filter(function (s) {
        return !(s.sats_kind === 'trade' || s.category === 'trade' || s.category === 'profit');
      }));
    }
    var wasPlaying = this.playing;
    var fp = (pipe && pipe.fingerprint) || null;
    var cut = (pipe && pipe.cut_id) || null;
    var changed = fp && fp !== this.fingerprint;
    this.fingerprint = fp;
    this.cutId = cut;
    this.scenes = scenes;
    this.duration = Number((pipe && pipe.duration_ms) || this.duration) || 12 * 60 * 1000;
    setText(
      'lm-pipeline-gen',
      (cut ? 'cut ' + cut + ' · ' : '') + ((pipe && pipe.generator) || 'AI')
    );
    if (pipe && pipe.regen_reason) {
      setText('lm-pipeline-reason', String(pipe.regen_reason).replace(/_/g, ' '));
    }
    if (changed) {
      flashStat('lm-stat-combined-sats');
      flashStat('lm-stat-network-sats');
      flashStat('lm-stat-trade-sats');
    }
    // New stats / new cut → restart movie so every showing is different.
    if (wasPlaying && (changed || opts.restart)) {
      this.stop(true);
      this.start();
      return true;
    }
    if (!this.playing) {
      setText(
        'lm-pipeline-scene',
        scenes[0]
          ? scenes[0].title + ' — tap play for the live 12-min cut'
          : 'Waiting for live sats to generate a cut…'
      );
      setText('lm-pipeline-progress', '0 / ' + formatClock(this.duration));
      var bar = $('lm-pipeline-bar');
      if (bar) bar.style.width = '0%';
    }
    return changed;
  };

  PipelinePlayer.prototype.start = function () {
    if (!this.scenes.length) {
      setText('lm-pipeline-scene', 'No pipeline scenes yet — regenerating…');
      return;
    }
    this.playing = true;
    this.index = 0;
    this.elapsed = 0;
    if (this.panel) this.panel.classList.add('is-playing');
    if (this.playBtn) {
      this.playBtn.setAttribute('aria-pressed', 'true');
      this.playBtn.textContent = 'Playing 12-min cut…';
    }
    if (this.show && !this.show.running) this.show.start();
    this.nextScene();
  };

  PipelinePlayer.prototype.stop = function (silent) {
    this.playing = false;
    this._speechDone = true;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    if (this.panel) this.panel.classList.remove('is-playing');
    if (this.root) {
      this.root.classList.remove('is-speaking');
      this.root.classList.remove('is-sync-hit');
    }
    if (this.show) {
      this.show.setBoost(1);
      this.show.caption = '';
    }
    if (this.music) this.music.boost = 1;
    if (window.MNCamgirlsStreamVoice) window.MNCamgirlsStreamVoice.cancel();
    if (this.playBtn) {
      this.playBtn.setAttribute('aria-pressed', 'false');
      this.playBtn.textContent = 'Play 12-min AI pipeline';
    }
    if (!silent) {
      setText('lm-pipeline-scene', 'Cut stopped — next stats change builds a new movie (not saved).');
    }
  };

  PipelinePlayer.prototype._buildSpeak = function (scene) {
    if (scene.speak) return scene.speak;
    var cat = scene.category || 'system';
    var sats = fmtSats(scene.sats).replace(/,/g, ' ');
    if (scene.sats_kind === 'network' || cat === 'network') {
      return 'Network sats on screen: ' + sats + '. ' + (scene.title || '');
    }
    if (scene.sats_kind === 'trade' || cat === 'trade' || cat === 'profit') {
      return 'Daemon trade sats: ' + sats + '. ' + (scene.title || '');
    }
    if (scene.sats_kind === 'combined' || cat === 'finale') {
      return 'Combined sats: ' + sats + '. ' + (scene.title || '');
    }
    return (scene.title || 'Monitor update') + '. ' + (scene.body || '');
  };

  PipelinePlayer.prototype._advanceWhenReady = function (minMs, startedAt) {
    var self = this;
    function tryAdvance() {
      if (!self.playing) return;
      var waited = Date.now() - startedAt;
      if (!self._speechDone || waited < minMs) {
        self.timer = setTimeout(tryAdvance, 120);
        return;
      }
      // Beat-align the handoff so lights/SFX/voice stay a straight pipeline.
      var beat = BEAT_MS;
      var rem = waited % beat;
      var pad = rem === 0 ? 0 : beat - rem;
      self.timer = setTimeout(function () {
        if (!self.playing) return;
        self.index += 1;
        self.nextScene();
      }, pad);
    }
    tryAdvance();
  };

  PipelinePlayer.prototype.nextScene = function () {
    var self = this;
    if (!this.playing) return;
    if (this.index >= this.scenes.length) {
      setText('lm-pipeline-scene', '12-min window done — recounting a brand-new cut from live sats…');
      this.stop(true);
      fetch('/api/landing/monitor/pipeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ use_llm: true, force: true }),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (pipe) {
          self.loadCut(pipe, { restart: true });
        })
        .catch(function () {});
      return;
    }
    var scene = this.scenes[this.index];
    var fx = scene.fx || {};
    var cat = scene.category || 'system';
    var color = fx.color || CAT_COLOR[cat] || CAT_COLOR.system;
    var mode = fx.lightshow || 'pulse';
    var ms = Math.max(5000, Number(scene.duration_ms) || 12000);
    var startedAt = Date.now();
    this._speechDone = false;
    this.elapsed += ms;

    setText('lm-pipeline-scene', scene.title + (scene.body ? ' — ' + scene.body : ''));
    setText(
      'lm-pipeline-progress',
      formatClock(Math.min(this.elapsed, this.duration)) + ' / ' + formatClock(this.duration)
    );
    setText(
      'lm-pipeline-sats',
      (scene.sats_kind || cat) + ' · ' + fmtSats(scene.sats) + ' sats'
    );
    var bar = $('lm-pipeline-bar');
    if (bar) bar.style.width = Math.min(100, (this.elapsed / this.duration) * 100) + '%';

    if (scene.sats_kind === 'network' || cat === 'network') flashStat('lm-stat-network-sats');
    if (scene.sats_kind === 'trade' || cat === 'trade' || cat === 'profit') flashStat('lm-stat-trade-sats');
    if (scene.sats_kind === 'combined' || cat === 'finale') flashStat('lm-stat-combined-sats');

    setText('lm-effect-title', fx.title || mode);
    setText('lm-effect-body', fx.explain || scene.body || '');
    if (this.root) {
      this.root.classList.add('is-scene');
      this.root.classList.add('is-sync-hit');
      this.root.style.setProperty('--lm-scene-color', color);
      setTimeout(function () {
        if (self.root) self.root.classList.remove('is-sync-hit');
      }, 220);
    }
    if (this.show) {
      this.show.setMode(mode);
      this.show.setAccent(color);
      this.show.setBoost(1.35);
      this.show.caption = (scene.title || '').slice(0, 42);
      this.show.pulse();
    }
    if (this.music) this.music.boost = 1.25;

    // Synchronized hit: SFX + lights fire on the same beat as speech starts.
    if (this.sfx) {
      this.sfx.playAction({
        category: cat,
        fx: { sound: fx.sound || CAT_SOUND[cat] || 'tick_blip' },
      });
      var selfSfx = this.sfx;
      setTimeout(function () {
        if (self.playing) selfSfx.playSyncHit();
      }, BEAT_MS);
    }

    var line = this._buildSpeak(scene);
    var voice = window.MNCamgirlsStreamVoice;
    if (voice && voice.isEnabled()) {
      if (this.root) this.root.classList.add('is-speaking');
      voice.speak(line, {
        force: true,
        interrupt: true,
        rotate: !scene.speaker_id,
        speakerId: scene.speaker_id || fx.speaker,
        queue: false,
        onstart: function (sp) {
          if (sp) {
            setText('lm-voice-name', sp.name || 'Host');
            setText('lm-voice-line', line);
            var av = $('lm-voice-avatar');
            if (av && sp.avatar) av.src = sp.avatar;
          }
        },
        onend: function () {
          self._speechDone = true;
          if (self.root) self.root.classList.remove('is-speaking');
        },
      });
    } else {
      this._speechDone = true;
      setText('lm-voice-line', 'Voice off — enable Camgirl voice to hear sats spoken.');
    }

    this._advanceWhenReady(ms, startedAt);
  };

  function ActionReel(opts) {
    this.show = opts.show;
    this.music = opts.music;
    this.sfx = opts.sfx;
    this.root = opts.root;
    this.listEl = $('lm-reel-list');
    this.panel = document.querySelector('.lm-reel-panel');
    this.playBtn = $('lm-reel-play');
    this.scenes = [];
    this.index = 0;
    this.playing = false;
    this.timer = null;
    this.activeId = null;
    this.seenIds = {};
  }

  ActionReel.prototype.setScenes = function (reel) {
    var incoming = Array.isArray(reel) ? reel.slice() : [];
    // Fire a brand-new SFX for every newly synced action id.
    for (var i = 0; i < incoming.length; i++) {
      var row = incoming[i];
      if (!row || !row.id) continue;
      if (!this.seenIds[row.id]) {
        this.seenIds[row.id] = true;
        if (this.sfx) this.sfx.playAction(row);
      }
    }
    if (this.playing) return;
    this.scenes = incoming;
    this.renderList();
  };

  ActionReel.prototype.renderList = function () {
    if (!this.listEl) return;
    this.listEl.innerHTML = '';
    var max = Math.min(this.scenes.length, 8);
    for (var i = 0; i < max; i++) {
      var s = this.scenes[i];
      var li = document.createElement('li');
      if (s.id === this.activeId) li.className = 'is-active';
      else if (s.played) li.className = 'is-played';
      var dot = document.createElement('span');
      dot.className = 'lm-reel-cat-dot';
      dot.style.background = CAT_COLOR[s.category] || CAT_COLOR.system;
      var title = document.createElement('span');
      title.className = 'lm-reel-title-row';
      title.textContent = s.title || s.type || 'action';
      var tag = document.createElement('span');
      tag.textContent = s.category || 'system';
      li.appendChild(dot);
      li.appendChild(title);
      li.appendChild(tag);
      this.listEl.appendChild(li);
    }
  };

  ActionReel.prototype.start = function () {
    if (!this.scenes.length) {
      setText('lm-reel-scene', 'No new actions yet — waiting for sync.');
      return;
    }
    this.playing = true;
    this.index = 0;
    if (this.panel) this.panel.classList.add('is-playing');
    if (this.playBtn) {
      this.playBtn.setAttribute('aria-pressed', 'true');
      this.playBtn.textContent = 'Playing…';
    }
    if (this.show && !this.show.running) this.show.start();
    this.nextScene();
  };

  ActionReel.prototype.stop = function () {
    this.playing = false;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    if (this.panel) this.panel.classList.remove('is-playing');
    if (this.root) {
      this.root.classList.remove('is-scene');
      this.root.style.removeProperty('--lm-scene-color');
    }
    if (this.show) {
      this.show.setBoost(1);
      this.show.caption = '';
    }
    if (this.music) this.music.boost = 1;
    if (this.playBtn) {
      this.playBtn.setAttribute('aria-pressed', 'false');
      this.playBtn.textContent = 'Play action movie';
    }
  };

  ActionReel.prototype.skip = function () {
    if (!this.playing) return;
    if (this.timer) clearTimeout(this.timer);
    this.markCurrentPlayed();
    this.index += 1;
    this.nextScene();
  };

  ActionReel.prototype.markCurrentPlayed = function () {
    var scene = this.scenes[this.index];
    if (!scene || !scene.id) return;
    scene.played = true;
    try {
      fetch('/api/landing/monitor/played', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ ids: [scene.id] }),
      });
    } catch (e) {}
  };

  ActionReel.prototype.nextScene = function () {
    var self = this;
    if (!this.playing) return;
    if (this.index >= this.scenes.length) {
      setText('lm-reel-scene', 'Reel complete — learning stored. New actions sync every refresh.');
      setText('lm-reel-cat', 'done');
      this.stop();
      this.renderList();
      return;
    }
    var scene = this.scenes[this.index];
    this.activeId = scene.id;
    var cat = scene.category || 'system';
    var fx = scene.fx || {};
    var color = fx.color || CAT_COLOR[cat] || CAT_COLOR.system;
    var mode = fx.lightshow || 'pulse';
    var ms = Math.max(1200, Number(scene.scene_ms) || 1332);
    var sameStreak = 1;
    for (var i = this.index - 1; i >= 0; i--) {
      if ((this.scenes[i].category || 'system') === cat) sameStreak += 1;
      else break;
    }

    setText('lm-reel-scene', scene.title || scene.text || scene.type);
    setText(
      'lm-reel-cat',
      cat + ' · ' + (fx.sound || CAT_SOUND[cat] || 'sfx') + ' · ' + (fx.title || mode)
    );
    setText('lm-effect-title', fx.title || mode);
    setText('lm-effect-body', fx.explain || '');

    if (this.root) {
      this.root.classList.add('is-scene');
      this.root.style.setProperty('--lm-scene-color', color);
    }
    if (this.show) {
      this.show.setMode(mode);
      this.show.setAccent(color);
      this.show.setBoost(1 + Math.min(1.0, sameStreak * 0.22));
      this.show.caption = (scene.title || '').slice(0, 40);
      this.show.pulse();
    }
    if (this.music) this.music.boost = 1 + Math.min(0.8, sameStreak * 0.15);
    // Every scene hit gets its own category sound (critical).
    if (this.sfx) this.sfx.playAction(scene);

    this.renderList();
    this.timer = setTimeout(function () {
      self.markCurrentPlayed();
      self.index += 1;
      self.nextScene();
    }, ms);
  };

  function mount() {
    var root = $('fp-landing-monitor');
    if (!root) return;

    var canvas = $('lm-canvas');
    if (canvas) {
      canvas.width = Math.max(320, canvas.clientWidth || 640);
      canvas.height = 220;
    }
    var show = canvas ? new Lightshow(canvas) : null;
    var music = new LandingMusic(BPM);
    var sfx = new ActionSFX();
    var reel = new ActionReel({ show: show, music: music, sfx: sfx, root: root });
    var pipeline = new PipelinePlayer({ show: show, music: music, sfx: sfx, root: root });
    var beatTimer = null;
    var musicBtn = $('lm-music-toggle');
    var lightBtn = $('lm-light-toggle');
    var sfxBtn = $('lm-sfx-toggle');
    var playBtn = $('lm-reel-play');
    var skipBtn = $('lm-reel-skip');
    var pipePlayBtn = $('lm-pipeline-play');
    var pipeRegenBtn = $('lm-pipeline-regen');
    var voiceBtn = $('lm-voice-toggle');
    var voiceLead = $('lm-voice-lead');
    var lastSatsFp = null;

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
        voiceLead.value = window.MNCamgirlsStreamVoice.getLeadSpeakerId() || (speakers[0] && speakers[0].id) || '';
      }
    }

    function initCamgirlVoice() {
      if (!window.MNCamgirlsStreamVoice) return Promise.resolve();
      return window.MNCamgirlsStreamVoice
        .init({
          performersApi: '/api/camgirls/performers',
          deckId: 'lm-voice-deck',
          storageKey: 'mn-lm-camgirl-voice',
          onActiveSpeaker: function (id) {
            var speakers = window.MNCamgirlsStreamVoice.getSpeakers() || [];
            var sp = speakers.filter(function (s) {
              return s.id === id;
            })[0];
            if (!sp) return;
            setText('lm-voice-name', sp.name || 'Host');
            var av = $('lm-voice-avatar');
            if (av && sp.avatar) av.src = sp.avatar;
          },
          onLine: function (sp, text) {
            if (sp) setText('lm-voice-name', sp.name || 'Host');
            setText('lm-voice-line', text || '');
          },
        })
        .then(function (speakers) {
          fillVoiceLead(speakers);
          return speakers;
        });
    }

    initCamgirlVoice().catch(function () {});

    function setSfxHint(on) {
      setText('lm-sfx-hint', on ? 'Sounds: on (each action)' : 'Sounds: off');
    }

    function enableSfxUi() {
      return sfx.enable().then(function () {
        if (sfxBtn) {
          sfxBtn.setAttribute('aria-pressed', 'true');
          sfxBtn.textContent = 'Action sounds on';
        }
        setSfxHint(true);
      });
    }

    function onBeat() {
      if (show) show.pulse();
      root.classList.add('is-beat');
      setTimeout(function () {
        root.classList.remove('is-beat');
      }, 120);
    }

    function startBeatClock() {
      if (beatTimer) clearInterval(beatTimer);
      if (prefersReducedMotion()) return;
      beatTimer = setInterval(onBeat, BEAT_MS);
      onBeat();
    }

    async function fetchFullPipeline() {
      try {
        var res = await fetch('/api/landing/monitor/pipeline', { headers: { Accept: 'application/json' } });
        if (!res.ok) return null;
        return await res.json();
      } catch (e) {
        return null;
      }
    }

    async function regeneratePipeline(forceAi) {
      setText('lm-pipeline-reason', 'recounting');
      try {
        var res = await fetch('/api/landing/monitor/pipeline', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify({ use_llm: !!forceAi }),
        });
        var pipe = await res.json();
        pipeline.loadCut(pipe, { restart: pipeline.playing });
        return pipe;
      } catch (e) {
        setText('lm-pipeline-reason', 'regen failed');
        return null;
      }
    }

    async function refresh() {
      try {
        var res = await fetch('/api/landing/monitor', { headers: { Accept: 'application/json' } });
        if (!res.ok) throw new Error('monitor ' + res.status);
        var data = await res.json();
        if (!data || !data.success) throw new Error('monitor payload');
        var light = paint(data) || {};
        if (show && !reel.playing && !pipeline.playing) show.setMode(light.id || 'pulse');
        if (data.bpm) music.bpm = data.bpm;
        reel.setScenes(data.reel || data.actions || []);

        var fp = (data.pipeline && data.pipeline.fingerprint) || null;
        var statsChanged = fp && fp !== lastSatsFp;
        if (statsChanged) {
          lastSatsFp = fp;
          flashStat('lm-stat-network-sats');
          flashStat('lm-stat-trade-sats');
        }
        // Always pull the live cut when fingerprint changes so the movie differs.
        if (statsChanged || !(pipeline.scenes && pipeline.scenes.length)) {
          var full = await fetchFullPipeline();
          if (full && full.scenes) pipeline.loadCut(full, { restart: statsChanged && pipeline.playing });
          else if (data.pipeline) pipeline.loadCut(data.pipeline, { restart: false });
        } else if (data.pipeline) {
          // Keep meta fresh without forcing a restart mid-scene unless fingerprint moved.
          if (data.pipeline.regen_reason) {
            setText('lm-pipeline-reason', String(data.pipeline.regen_reason).replace(/_/g, ' '));
          }
        }
        return;
      } catch (e) {
        try {
          var sres = await fetch('/api/stats/summary', { headers: { Accept: 'application/json' } });
          var sdata = await sres.json();
          var st = (sdata && sdata.stats) || {};
          paint({
            success: true,
            bpm: BPM,
            updated_at: new Date().toISOString(),
            stats: {
              total_videos: st.total_videos || 0,
              total_users: st.total_users || 0,
              total_battles: st.total_battles || 0,
              mn2_usd_price: null,
              daemon_ok: null,
            },
            special: {
              id: 'wallet',
              title: 'New wallet arrived',
              body: 'Linux + Windows Qt, Flatpak daemon, and source downloads.',
              href: '/wallets',
              cta: 'Open wallets',
            },
            effect_explain: {
              title: 'Pulse Lightshow',
              body: 'Smooth sine pulse locked to 180 BPM — each beat lifts intensity then eases out.',
              safety: 'Gentle; fine for most visitors.',
              bpm: BPM,
            },
            lightshow: { id: 'pulse' },
            learning: { total_actions: 0, categories: {} },
            sats: { totals: {} },
          });
          if (show) show.setMode('pulse');
        } catch (e2) {
          setText('lm-updated', 'Monitor offline — retrying');
        }
      }
    }

    if (lightBtn) {
      lightBtn.addEventListener('click', function () {
        var on = lightBtn.getAttribute('aria-pressed') !== 'true';
        lightBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
        lightBtn.textContent = on ? 'Lightshow on' : 'Lightshow off';
        if (on) {
          if (show) show.start();
          startBeatClock();
          // Unlock action sounds on first intentional interaction.
          if (!sfx.enabled) enableSfxUi().catch(function () {});
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
              musicBtn.textContent = 'Music on (180 BPM)';
              if (lightBtn && lightBtn.getAttribute('aria-pressed') !== 'true') {
                lightBtn.click();
              }
              return enableSfxUi();
            })
            .catch(function () {
              musicBtn.textContent = 'Music unavailable';
            });
        } else {
          music.stop();
          musicBtn.setAttribute('aria-pressed', 'false');
          musicBtn.textContent = 'Play AI music';
        }
      });
    }

    if (sfxBtn) {
      sfxBtn.addEventListener('click', function () {
        var on = sfxBtn.getAttribute('aria-pressed') !== 'true';
        if (on) {
          enableSfxUi()
            .then(function () {
              // Demo ping so the visitor hears it immediately.
              sfx.playAction({ category: 'wallet', fx: { sound: 'coin_sparkle' } });
            })
            .catch(function () {
              sfxBtn.textContent = 'Sounds unavailable';
              setSfxHint(false);
            });
        } else {
          sfx.disable();
          sfxBtn.setAttribute('aria-pressed', 'false');
          sfxBtn.textContent = 'Action sounds off';
          setSfxHint(false);
        }
      });
    }

    if (playBtn) {
      playBtn.addEventListener('click', function () {
        if (reel.playing) {
          reel.stop();
          return;
        }
        if (pipeline.playing) pipeline.stop(true);
        if (lightBtn && lightBtn.getAttribute('aria-pressed') !== 'true') lightBtn.click();
        if (!sfx.enabled) {
          enableSfxUi().catch(function () {});
        }
        reel.start();
      });
    }
    if (skipBtn) {
      skipBtn.addEventListener('click', function () {
        reel.skip();
      });
    }

    if (pipePlayBtn) {
      pipePlayBtn.addEventListener('click', function () {
        if (pipeline.playing) {
          pipeline.stop();
          return;
        }
        if (reel.playing) reel.stop();
        if (lightBtn && lightBtn.getAttribute('aria-pressed') !== 'true') lightBtn.click();
        if (!sfx.enabled) enableSfxUi().catch(function () {});
        if (window.MNCamgirlsStreamVoice && !window.MNCamgirlsStreamVoice.isEnabled()) {
          window.MNCamgirlsStreamVoice.setEnabled(true);
          if (voiceBtn) {
            voiceBtn.setAttribute('aria-pressed', 'true');
            voiceBtn.textContent = 'Camgirl voice on';
          }
        }
        if (!pipeline.scenes.length) {
          regeneratePipeline(true).then(function () {
            pipeline.start();
          });
        } else {
          pipeline.start();
        }
      });
    }
    if (pipeRegenBtn) {
      pipeRegenBtn.addEventListener('click', function () {
        if (!sfx.enabled) enableSfxUi().catch(function () {});
        regeneratePipeline(true);
      });
    }

    if (voiceBtn) {
      voiceBtn.addEventListener('click', function () {
        var on = voiceBtn.getAttribute('aria-pressed') !== 'true';
        if (!window.MNCamgirlsStreamVoice) {
          voiceBtn.textContent = 'Voice unavailable';
          return;
        }
        initCamgirlVoice()
          .then(function () {
            window.MNCamgirlsStreamVoice.setEnabled(on);
            voiceBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
            voiceBtn.textContent = on ? 'Camgirl voice on' : 'Camgirl voice off';
            if (on) {
              if (!sfx.enabled) enableSfxUi().catch(function () {});
              window.MNCamgirlsStreamVoice.speak(
                'Voice online. I will speak the network and trade sats in the pipeline.',
                { force: true, interrupt: true, rotate: true }
              );
            }
          })
          .catch(function () {
            voiceBtn.textContent = 'Voice unavailable';
          });
      });
    }
    if (voiceLead) {
      voiceLead.addEventListener('change', function () {
        if (window.MNCamgirlsStreamVoice) {
          window.MNCamgirlsStreamVoice.setLeadSpeaker(voiceLead.value);
        }
      });
    }

    document.querySelectorAll('.lm-stat-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var focus = btn.getAttribute('data-sats-focus') || 'combined';
        pipeline.setFocus(focus);
        if (!sfx.enabled) enableSfxUi().catch(function () {});
        var spoken =
          focus === 'network'
            ? 'Network sats: ' + ($('lm-stat-network-sats') && $('lm-stat-network-sats').textContent)
            : focus === 'trade'
              ? 'Daemon trade sats: ' + ($('lm-stat-trade-sats') && $('lm-stat-trade-sats').textContent)
              : 'Combined sats recount: ' + ($('lm-stat-combined-sats') && $('lm-stat-combined-sats').textContent);
        if (window.MNCamgirlsStreamVoice) {
          if (!window.MNCamgirlsStreamVoice.isEnabled()) {
            window.MNCamgirlsStreamVoice.setEnabled(true);
            if (voiceBtn) {
              voiceBtn.setAttribute('aria-pressed', 'true');
              voiceBtn.textContent = 'Camgirl voice on';
            }
          }
          window.MNCamgirlsStreamVoice.speak(spoken + ' sats on the monitor.', {
            force: true,
            interrupt: true,
            rotate: true,
          });
        }
        sfx.playAction({
          category: focus === 'trade' ? 'profit' : focus === 'combined' ? 'social' : 'wallet',
          fx: {
            sound:
              focus === 'trade' ? 'chime_cash' : focus === 'combined' ? 'sparkle_cascade' : 'coin_sparkle',
          },
        });
        if (focus === 'combined') {
          regeneratePipeline(true);
          return;
        }
        if (pipeline.scenes.length) {
          pipeline.loadCut(
            {
              scenes: pipeline.scenes,
              duration_ms: pipeline.duration,
              fingerprint: pipeline.fingerprint + ':' + focus,
              cut_id: pipeline.cutId,
              generator: 'interactive_' + focus,
              regen_reason: 'stats_focus_' + focus,
            },
            { restart: pipeline.playing }
          );
        } else {
          regeneratePipeline(false);
        }
      });
    });

    refresh();
    setInterval(refresh, REFRESH_MS);
    // Soft 12-minute wall-clock recount even if sats are quiet.
    setInterval(function () {
      regeneratePipeline(false);
    }, 12 * 60 * 1000);
    if (!prefersReducedMotion() && lightBtn) {
      lightBtn.click();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
})();
