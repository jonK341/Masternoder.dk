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
      case 'bubble_ping':
        this._tone(640 + variation, 'sine', now, 0.1, 0.16, 980);
        this._tone(520, 'triangle', now + 0.09, 0.14, 0.12, 760);
        this._noise(now + 0.02, 0.08, 0.08, 2400);
        break;
      case 'tick_blip':
      default:
        this._tone(440 + variation, 'square', now, 0.06, 0.1);
        this._tone(660, 'sine', now + 0.05, 0.08, 0.08);
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
    var beatTimer = null;
    var musicBtn = $('lm-music-toggle');
    var lightBtn = $('lm-light-toggle');
    var sfxBtn = $('lm-sfx-toggle');
    var playBtn = $('lm-reel-play');
    var skipBtn = $('lm-reel-skip');

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

    async function refresh() {
      try {
        var res = await fetch('/api/landing/monitor', { headers: { Accept: 'application/json' } });
        if (!res.ok) throw new Error('monitor ' + res.status);
        var data = await res.json();
        if (!data || !data.success) throw new Error('monitor payload');
        var light = paint(data) || {};
        if (show && !reel.playing) show.setMode(light.id || 'pulse');
        if (data.bpm) music.bpm = data.bpm;
        reel.setScenes(data.reel || data.actions || []);
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

    refresh();
    setInterval(refresh, REFRESH_MS);
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
