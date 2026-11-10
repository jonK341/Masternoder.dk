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
    battle: 'drum_hit',
    generator: 'guitar_riff',
    profit: 'chime_cash',
    social: 'bubble_ping',
    system: 'tick_blip',
    network: 'coin_sparkle',
    trade: 'chime_cash',
    action: 'whoosh_rise',
    finale: 'guitar_riff',
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
      case 'drum_hit':
        this._noise(now, 0.05, 0.2, 2200);
        this._tone(90, 'sine', now, 0.12, 0.22, 40);
        this._tone(180, 'triangle', now + 0.02, 0.06, 0.1);
        break;
      case 'guitar_riff':
        this._tone(196 + variation * 0.2, 'sawtooth', now, 0.18, 0.11, 220);
        this._tone(246.94, 'sawtooth', now + 0.06, 0.16, 0.1, 280);
        this._tone(293.66, 'triangle', now + 0.12, 0.2, 0.09, 330);
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

  LandingMusic.prototype.snare = function (when) {
    if (!this.ctx || !this.master) return;
    var len = Math.max(1, Math.floor(this.ctx.sampleRate * 0.08));
    var buf = this.ctx.createBuffer(1, len, this.ctx.sampleRate);
    var data = buf.getChannelData(0);
    for (var i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;
    var src = this.ctx.createBufferSource();
    src.buffer = buf;
    var filter = this.ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.value = 1800;
    var g = this.ctx.createGain();
    g.gain.setValueAtTime(0.22 * this.boost, when);
    g.gain.exponentialRampToValueAtTime(0.0001, when + 0.1);
    src.connect(filter);
    filter.connect(g);
    g.connect(this.master);
    src.start(when);
    src.stop(when + 0.12);
  };

  LandingMusic.prototype.hihat = function (when) {
    if (!this.ctx || !this.master) return;
    var len = Math.max(1, Math.floor(this.ctx.sampleRate * 0.03));
    var buf = this.ctx.createBuffer(1, len, this.ctx.sampleRate);
    var data = buf.getChannelData(0);
    for (var i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;
    var src = this.ctx.createBufferSource();
    src.buffer = buf;
    var filter = this.ctx.createBiquadFilter();
    filter.type = 'highpass';
    filter.frequency.value = 7000;
    var g = this.ctx.createGain();
    g.gain.setValueAtTime(0.08 * this.boost, when);
    g.gain.exponentialRampToValueAtTime(0.0001, when + 0.04);
    src.connect(filter);
    filter.connect(g);
    g.connect(this.master);
    src.start(when);
    src.stop(when + 0.05);
  };

  LandingMusic.prototype.guitar = function (when) {
    if (!this.ctx || !this.master) return;
    var chord = [
      [110, 164.81, 220],
      [130.81, 196, 261.63],
      [146.83, 220, 293.66],
      [98, 146.83, 196],
    ][this.step % 4];
    for (var i = 0; i < chord.length; i++) {
      var o = this.ctx.createOscillator();
      var g = this.ctx.createGain();
      var f = this.ctx.createBiquadFilter();
      o.type = 'sawtooth';
      o.frequency.value = chord[i];
      f.type = 'lowpass';
      f.frequency.setValueAtTime(1400, when);
      f.frequency.exponentialRampToValueAtTime(600, when + 0.35);
      g.gain.setValueAtTime(0.0001, when);
      g.gain.exponentialRampToValueAtTime(0.05 * this.boost, when + 0.02 + i * 0.01);
      g.gain.exponentialRampToValueAtTime(0.0001, when + 0.45);
      o.connect(f);
      f.connect(g);
      g.connect(this.master);
      o.start(when);
      o.stop(when + 0.5);
    }
  };

  LandingMusic.prototype.schedule = function () {
    var self = this;
    if (!this.active) return;
    var now = this.ctx.currentTime;
    var beat = 60 / this.bpm;
    var step = this.step;
    // Drum kit: kick on 1/3, snare on 2/4, hats every beat.
    this.kick(now);
    if (step % 2 === 1) this.snare(now);
    this.hihat(now);
    this.hihat(now + beat * 0.5);
    // Guitar chord every other bar + melodic lead.
    if (step % 4 === 0) this.guitar(now);
    this.note(SCALE[step % SCALE.length], beat * 0.4, now + 0.01, 0.07);
    if (step % 2 === 0) {
      this.note(SCALE[(step + 2) % SCALE.length] * 0.5, beat * 0.55, now + beat * 0.5, 0.05);
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


  function renderOnlineBoard(rows) {
    var board = $('lm-online-board');
    if (!board) return;
    board.innerHTML = '';
    var list = (rows || []).slice(0, 25);
    function appendRow(row) {
      var li = document.createElement('li');
      var online = !!row.online;
      li.innerHTML =
        '<span class="dot' + (online ? '' : ' is-off') + '"></span>' +
        '<span class="rank">#' + (row.rank || '—') + '</span>' +
        '<span class="name"></span>' +
        '<span class="xp"></span>';
      li.querySelector('.name').textContent = row.username || row.user_id || 'user';
      li.querySelector('.xp').textContent = fmtCompact(row.xp || 0) + ' XP';
      board.appendChild(li);
    }
    list.forEach(appendRow);
    // Duplicate for seamless rightward ticker.
    if (list.length) list.forEach(appendRow);
    if (!list.length) {
      var empty = document.createElement('li');
      empty.innerHTML = '<span class="name">Online board warming up…</span>';
      board.appendChild(empty);
    }
    board.classList.toggle('is-scrolling', list.length > 0);
  }

  function setSceneArt(url, kind) {
    var img = $('lm-scene-art');
    if (!img) return;
    if (!url) {
      img.classList.remove('is-on');
      img.removeAttribute('data-art-kind');
      return;
    }
    img.classList.remove('is-on');
    img.setAttribute('data-art-kind', kind || 'still');
    var next = new Image();
    next.onload = function () {
      img.src = url;
      requestAnimationFrame(function () {
        img.classList.add('is-on');
      });
    };
    next.onerror = function () {
      img.classList.remove('is-on');
    };
    next.src = url;
  }

  function currentPipelineScene(stream) {
    if (!stream || !stream.scenes || !stream.scenes.length) return null;
    var idx = Math.max(0, Math.min(stream.index || 0, stream.scenes.length - 1));
    return stream.scenes[idx] || null;
  }

  function requestSceneArt(stream, kind) {
    var scene = currentPipelineScene(stream);
    var payload = {
      kind: kind || 'still',
      category: (scene && scene.category) || 'generator',
      title: (scene && scene.title) || 'Lobby scene',
      body: (scene && (scene.body || scene.speak)) || 'MasterNoder2 pipeline frame',
    };
    return fetch('/api/landing/monitor/scene-art', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.success || !data.url) throw new Error('scene-art');
        if (scene) {
          if (kind === 'gif') scene.gif_url = data.url;
          else scene.image_url = data.url;
        }
        setSceneArt(data.url, kind);
        setText('lm-voice-line', kind === 'gif' ? 'AI gif frame locked to this scene.' : 'AI picture locked to this scene.');
        return data;
      });
  }

  function PipelinePlayer(opts) {
    this.show = opts.show;
    this.music = opts.music;
    this.sfx = opts.sfx;
    this.root = opts.root;
    this.scenes = [];
    this.index = 0;
    this.playing = false;
    this.timer = null;
    this.speechDone = true;
    this.cutId = null;
    this.loading = false;
  }

  PipelinePlayer.prototype.renderIdle = function () {
    var first = this.scenes[0];
    setText('lm-stream-pos', '0/' + (this.scenes.length || 50));
    setText('lm-hud-kicker', first ? (first.category || 'Ready') : 'Ready');
    setText('lm-hud-value', first ? (first.sats_label || first.title || '—') : '—');
    setText(
      'lm-hud-label',
      first
        ? 'Start pipeline — 50 AI scenes / 12 min with voice + art.'
        : 'Loading 12-minute AI pipeline…'
    );
    var bar = $('lm-stream-bar');
    if (bar) bar.style.width = '0%';
    if (first && (first.image_url || first.gif_url)) {
      setSceneArt(first.image_url || first.gif_url, first.image_url ? 'still' : 'gif');
    }
  };

  PipelinePlayer.prototype.load = function (force) {
    var self = this;
    if (this.loading) return Promise.resolve(this.scenes);
    this.loading = true;
    var url = force ? '/api/landing/monitor/pipeline?refresh=1' : '/api/landing/monitor/pipeline';
    var req = force
      ? fetch('/api/landing/monitor/pipeline', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify({ use_llm: false }),
        })
      : fetch(url, { headers: { Accept: 'application/json' } });
    return req
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        self.loading = false;
        if (!data || !data.success || !Array.isArray(data.scenes)) throw new Error('pipeline');
        self.scenes = data.scenes;
        self.cutId = data.cut_id;
        renderOnlineBoard(data.online_leaderboard || []);
        setText(
          'lm-pipeline-progress',
          (data.scene_count || self.scenes.length) + ' / 12:00'
        );
        setText('lm-pipeline-gen', data.generator || 'AI');
        setText('lm-pipeline-reason', data.regen_reason || 'live');
        var totals = (data.sats && data.sats.totals) || {};
        setText(
          'lm-pipeline-sats',
          'sats ' + fmtCompact(totals.combined_sats || 0)
        );
        if (!self.playing) self.renderIdle();
        return self.scenes;
      })
      .catch(function () {
        self.loading = false;
        setText('lm-hud-label', 'Pipeline retrying…');
        return self.scenes;
      });
  };

  PipelinePlayer.prototype.start = function () {
    var self = this;
    var go = function () {
      if (!self.scenes.length) {
        setText('lm-hud-label', 'No scenes yet — regenerating…');
        return;
      }
      self.playing = true;
      self.index = 0;
      var btn = $('lm-stream-play');
      if (btn) {
        btn.setAttribute('aria-pressed', 'true');
        btn.textContent = 'Streaming…';
      }
      if (self.show && !self.show.running) self.show.start();
      self.next();
    };
    if (!this.scenes.length) {
      this.load(false).then(go);
      return;
    }
    go();
  };

  PipelinePlayer.prototype.stop = function () {
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
      btn.textContent = 'Start pipeline';
    }
    this.renderIdle();
  };

  PipelinePlayer.prototype.skip = function () {
    if (!this.playing) {
      this.start();
      return;
    }
    if (this.timer) clearTimeout(this.timer);
    if (window.MNCamgirlsStreamVoice) window.MNCamgirlsStreamVoice.cancel();
    this.speechDone = true;
    this.index = (this.index + 1) % Math.max(1, this.scenes.length);
    this.next();
  };

  PipelinePlayer.prototype.regen = function () {
    var self = this;
    var was = this.playing;
    this.stop();
    setText('lm-hud-label', 'Generating a new 50-scene cut…');
    return this.load(true).then(function () {
      if (was) self.start();
      else self.renderIdle();
    });
  };

  PipelinePlayer.prototype.next = function () {
    var self = this;
    if (!this.playing || !this.scenes.length) return;
    if (this.index >= this.scenes.length) this.index = 0;

    var scene = this.scenes[this.index];
    var hud = document.querySelector('.lm-hud');
    if (hud) {
      hud.classList.add('is-swap');
      setTimeout(function () {
        hud.classList.remove('is-swap');
      }, 160);
    }

    var value =
      scene.sats_label ||
      (scene.sats ? fmtCompact(scene.sats) : null) ||
      scene.title ||
      '—';
    setText('lm-hud-kicker', (scene.category || 'scene') + ' · ' + (this.index + 1) + '/' + this.scenes.length);
    setText('lm-hud-value', value);
    setText('lm-hud-label', scene.body || scene.title || '');
    setText('lm-stream-pos', this.index + 1 + '/' + this.scenes.length);
    setText('lm-pipeline-scene', scene.title || '');
    var bar = $('lm-stream-bar');
    if (bar) bar.style.width = ((this.index + 1) / this.scenes.length) * 100 + '%';
    setSceneArt(scene.image_url || scene.gif_url, scene.image_url ? 'still' : 'gif');

    var fx = scene.fx || {};
    if (this.root) {
      this.root.classList.add('is-sync-hit');
      this.root.style.setProperty('--lm-scene-color', fx.color || '#00ff88');
      setTimeout(function () {
        if (self.root) self.root.classList.remove('is-sync-hit');
      }, 180);
    }
    if (this.show) {
      this.show.setMode(fx.lightshow || 'pulse');
      this.show.setAccent(fx.color || CAT_COLOR[scene.category] || '#00ff88');
      this.show.setBoost(1.3);
      this.show.pulse();
    }
    if (this.music) this.music.boost = 1.15;
    if (this.sfx) {
      this.sfx.playAction({
        category: scene.category,
        fx: { sound: fx.sound || CAT_SOUND[scene.category] || 'tick_blip' },
      });
    }

    this.speechDone = false;
    var line = scene.speak || scene.body || scene.title || String(value);
    var voice = window.MNCamgirlsStreamVoice;
    var started = Date.now();
    var sceneHold = Math.max(9000, Math.min(18000, Number(scene.duration_ms) || 14000));
    var minHold = Math.min(sceneHold, Math.max(2800, 55 * line.length));

    function finishSpeech() {
      self.speechDone = true;
      if (self.root) self.root.classList.remove('is-speaking');
    }

    if (voice && voice.isEnabled()) {
      if (this.root) this.root.classList.add('is-speaking');
      voice.speak(line, {
        force: true,
        interrupt: true,
        rotate: !scene.speaker_id,
        queue: false,
        speakerId: scene.speaker_id,
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
        self.timer = setTimeout(advance, 120);
        return;
      }
      var rem = waited % BEAT_MS;
      var pad = rem === 0 ? 0 : BEAT_MS - rem;
      // Soft cap so one slow TTS line cannot stall the whole 12m cut forever.
      var remain = Math.max(0, sceneHold - waited);
      self.timer = setTimeout(function () {
        if (!self.playing) return;
        self.index = (self.index + 1) % self.scenes.length;
        self.next();
      }, Math.min(remain + pad, Math.max(pad, 400)));
    }
    advance();
  };

  function mount() {
    var root = $('fp-landing-monitor');
    if (!root) return;

    var canvas = $('lm-canvas');
    if (canvas) {
      canvas.width = Math.max(480, canvas.clientWidth || 720);
      canvas.height = 200;
    }
    var show = canvas ? new Lightshow(canvas) : null;
    var music = new LandingMusic(BPM);
    var sfx = new ActionSFX();
    var stream = new PipelinePlayer({ show: show, music: music, sfx: sfx, root: root });
    var beatTimer = null;
    var lightBtn = $('lm-light-toggle');
    var musicBtn = $('lm-music-toggle');
    var sfxBtn = $('lm-sfx-toggle');
    var voiceBtn = $('lm-voice-toggle');
    var playBtn = $('lm-stream-play');
    var skipBtn = $('lm-stream-skip');
    var regenBtn = $('lm-pipeline-regen');
    var artStillBtn = $('lm-art-gen');
    var artGifBtn = $('lm-art-gif');
    var voiceLead = $('lm-voice-lead');

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
          preferServerTts: true,
          ttsEndpoint: '/api/landing/monitor/tts',
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

    function refreshOnline() {
      fetch('/api/landing/monitor/online?limit=25', { headers: { Accept: 'application/json' } })
        .then(function (r) {
          return r.json();
        })
        .then(function (d) {
          if (d && d.success) renderOnlineBoard(d.leaderboard || []);
        })
        .catch(function () {});
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
    stream.load(false);
    refreshOnline();

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
            window.MNCamgirlsStreamVoice.speak(
              'Voice online. I will read each pipeline scene with a human daemon tone.',
              { force: true, interrupt: true, rotate: true }
            );
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
    if (regenBtn) {
      regenBtn.addEventListener('click', function () {
        armStream();
        stream.regen();
      });
    }
    if (artStillBtn) {
      artStillBtn.addEventListener('click', function () {
        artStillBtn.disabled = true;
        requestSceneArt(stream, 'still')
          .catch(function () {
            setText('lm-voice-line', 'AI picture unavailable — try Movie AI.');
          })
          .finally(function () {
            artStillBtn.disabled = false;
          });
      });
    }
    if (artGifBtn) {
      artGifBtn.addEventListener('click', function () {
        var scene = currentPipelineScene(stream);
        if (scene && scene.gif_url && !artGifBtn.dataset.force) {
          setSceneArt(scene.gif_url, 'gif');
          setText('lm-voice-line', 'Pipeline gif frame on screen.');
          return;
        }
        artGifBtn.disabled = true;
        requestSceneArt(stream, 'gif')
          .catch(function () {
            setText('lm-voice-line', 'AI gif unavailable — try Movie AI.');
          })
          .finally(function () {
            artGifBtn.disabled = false;
          });
      });
    }

    function fillMatrixRail(el, lines) {
      if (!el) return;
      el.innerHTML = '';
      (lines || []).slice(0, 24).forEach(function (line, i) {
        var span = document.createElement('span');
        span.textContent = line;
        span.style.animationDelay = (i * 0.18) + 's';
        el.appendChild(span);
      });
    }

    function refreshMatrix() {
      fetch('/api/landing/monitor/matrix?limit=40', { headers: { Accept: 'application/json' } })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d || !d.success) return;
          fillMatrixRail($('lm-matrix-left'), d.left || []);
          fillMatrixRail($('lm-matrix-right'), d.right || []);
        })
        .catch(function () {});
    }

    function refreshBattlefield() {
      fetch('/api/landing/monitor/battlefield', { headers: { Accept: 'application/json' } })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d || !d.success) return;
          root.classList.add('is-battlefield-3500');
          var banner = $('lm-battlefield-banner');
          if (banner && d.title) {
            var strong = banner.querySelector('strong');
            if (strong) strong.textContent = d.title;
          }
          var comm = $('lm-comm-lines');
          if (comm && Array.isArray(d.comm_lines)) {
            comm.textContent = d.comm_lines
              .map(function (c) {
                return (c.label || c.id) + ' ' + (c.status || '');
              })
              .join(' · ');
          }
        })
        .catch(function () {});
    }

    function renderYt(videos) {
      var box = $('lm-yt-results');
      if (!box) return;
      box.innerHTML = '';
      (videos || []).slice(0, 6).forEach(function (v) {
        var a = document.createElement('a');
        a.className = 'lm-yt-card';
        a.href = v.url || ('https://www.youtube.com/watch?v=' + v.id);
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        a.innerHTML = '<img alt="" /><span></span>';
        a.querySelector('img').src = v.thumbnail || '';
        a.querySelector('span').textContent = v.title || 'YouTube';
        box.appendChild(a);
      });
    }

    function runYtSearch(q, randomize) {
      var url =
        '/api/landing/monitor/youtube?limit=6&random=' +
        (randomize ? '1' : '0') +
        (q ? '&q=' + encodeURIComponent(q) : '');
      fetch(url, { headers: { Accept: 'application/json' } })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d || !d.success) return;
          renderYt(d.videos || []);
          var input = $('lm-yt-q');
          if (input && d.query && !q) input.value = d.query;
        })
        .catch(function () {});
    }

    function wireShareFb() {
      var a = $('lm-share-fb');
      if (!a) return;
      var page = window.location.href.split('#')[0];
      var quote = 'Jon Film lobby · MasterNoder2 battlefield 3500';
      a.href =
        'https://www.facebook.com/sharer/sharer.php?u=' +
        encodeURIComponent(page) +
        '&quote=' +
        encodeURIComponent(quote);
      fetch(
        '/api/landing/monitor/share/facebook?url=' +
          encodeURIComponent(page) +
          '&quote=' +
          encodeURIComponent(quote),
        { headers: { Accept: 'application/json' } }
      )
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d && d.share_url) a.href = d.share_url;
        })
        .catch(function () {});
    }

    function refreshVotes() {
      fetch('/api/landing/monitor/votes', { headers: { Accept: 'application/json' } })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          var poll = d && (d.open || (d.polls && d.polls[0]));
          if (!poll) return;
          setText('lm-vote-q', poll.question || 'Discord vote');
          var box = $('lm-vote-opts');
          if (!box) return;
          box.innerHTML = '';
          (poll.options || []).forEach(function (opt) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.textContent = (opt.label || opt.id) + ' · ' + (opt.votes || 0);
            btn.addEventListener('click', function () {
              fetch('/api/landing/monitor/votes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
                body: JSON.stringify({ option_id: opt.id, poll_id: poll.id }),
              })
                .then(function () { refreshVotes(); })
                .catch(function () {});
            });
            box.appendChild(btn);
          });
        })
        .catch(function () {});
    }

    function refreshJonFilm() {
      fetch('/api/landing/monitor/jon-film', { headers: { Accept: 'application/json' } })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d || !d.success) return;
          setText(
            'lm-cal-meta',
            (d.appointments || []).length +
              ' appts · level +1 / ' +
              (d.assignments_per_level || 20) +
              ' assignments'
          );
          var list = $('lm-cal-list');
          if (list) {
            list.innerHTML = '';
            (d.appointments || []).slice(0, 10).forEach(function (a) {
              var li = document.createElement('li');
              li.textContent =
                (a.starts_at || '').slice(11, 16) +
                ' · ' +
                (a.actor_name || a.actor_id) +
                ' · ' +
                (a.stage || a.title || '');
              list.appendChild(li);
            });
          }
          var levels = $('lm-actor-levels');
          if (levels) {
            levels.innerHTML = '';
            (d.actors || []).forEach(function (actor) {
              var li = document.createElement('li');
              li.textContent =
                (actor.name || actor.id) +
                ' · L' +
                (actor.level || 1) +
                ' · ' +
                (actor.assignments || 0) +
                ' jobs';
              levels.appendChild(li);
            });
          }
        })
        .catch(function () {});
    }

    var ytForm = $('lm-yt-form');
    if (ytForm) {
      ytForm.addEventListener('submit', function (ev) {
        ev.preventDefault();
        runYtSearch(($('lm-yt-q') && $('lm-yt-q').value) || '', false);
      });
    }
    var ytRandom = $('lm-yt-random');
    if (ytRandom) {
      ytRandom.addEventListener('click', function () {
        runYtSearch('', true);
      });
    }

    wireShareFb();
    refreshBattlefield();
    refreshMatrix();
    refreshVotes();
    refreshJonFilm();
    runYtSearch('', true);

    refresh();
    setInterval(refresh, REFRESH_MS);
    setInterval(refreshOnline, 30000);
    setInterval(refreshMatrix, 20000);
    setInterval(refreshVotes, 45000);
    setInterval(refreshJonFilm, 60000);
    setInterval(function () {
      if (!stream.playing) stream.load(false);
    }, 60000);
    if (!prefersReducedMotion() && lightBtn) lightBtn.click();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
})();
