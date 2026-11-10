/**
 * Frontpage landing monitor — live data (5s), 180 BPM lightshow + generative AI music.
 */
(function () {
  'use strict';

  var BPM = 180;
  var BEAT_MS = Math.round(60000 / BPM);
  var REFRESH_MS = 5000;
  var SCALE = [220.0, 261.63, 329.63, 392.0, 440.0, 523.25]; // A3 C4 E4 G4 A4 C5

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

  function LandingMusic(bpm) {
    this.bpm = bpm || BPM;
    this.ctx = null;
    this.master = null;
    this.timer = null;
    this.step = 0;
    this.active = false;
    this.volume = 0.28;
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
    g.gain.exponentialRampToValueAtTime(gain, when + 0.02);
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
    g.gain.setValueAtTime(0.45, when);
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
    // Generative phrase: kick on 1/3, melody on 16th-ish pattern seeded by step.
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
  }

  Lightshow.prototype.setMode = function (id) {
    this.mode = id || 'pulse';
  };

  Lightshow.prototype.pulse = function () {
    this.beat = 1;
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
    if (mode === 'wave') {
      for (var i = 0; i < 6; i++) {
        ctx.beginPath();
        for (var x = 0; x < w; x += 4) {
          var y = h / 2 + Math.sin(x * 0.02 + t * 6 + i) * (18 + i * 8 + this.beat * 20);
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = 'hsla(' + ((t * 80 + i * 40) % 360) + ',90%,60%,' + (0.35 + this.beat * 0.4) + ')';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    } else if (mode === 'spectrum') {
      var bars = 24;
      for (var b = 0; b < bars; b++) {
        var bh = (0.2 + 0.8 * Math.abs(Math.sin(t * 8 + b * 0.4))) * h * (0.35 + this.beat * 0.45);
        ctx.fillStyle = 'hsla(' + ((b * 12 + t * 40) % 360) + ',85%,55%,0.85)';
        ctx.fillRect((b / bars) * w + 2, h - bh, w / bars - 4, bh);
      }
    } else if (mode === 'chase') {
      var n = 16;
      var idx = Math.floor(t * (BPM / 60)) % n;
      for (var c = 0; c < n; c++) {
        var a = (c / n) * Math.PI * 2;
        var r = Math.min(w, h) * 0.32;
        var x = w / 2 + Math.cos(a) * r;
        var y = h / 2 + Math.sin(a) * r;
        var on = c === idx || c === (idx + 1) % n;
        ctx.beginPath();
        ctx.arc(x, y, on ? 10 + this.beat * 8 : 5, 0, Math.PI * 2);
        ctx.fillStyle = on ? '#00ff88' : 'rgba(0,212,255,0.35)';
        ctx.fill();
      }
    } else if (mode === 'rainbow') {
      var grd = ctx.createLinearGradient(0, 0, w, h);
      var hue = (t * 60) % 360;
      grd.addColorStop(0, 'hsla(' + hue + ',90%,50%,0.55)');
      grd.addColorStop(0.5, 'hsla(' + ((hue + 80) % 360) + ',90%,50%,0.45)');
      grd.addColorStop(1, 'hsla(' + ((hue + 160) % 360) + ',90%,50%,0.55)');
      ctx.fillStyle = grd;
      ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = 'rgba(0,0,0,' + (0.35 - this.beat * 0.15) + ')';
      ctx.fillRect(0, 0, w, h);
    } else {
      // pulse default
      var rad = Math.min(w, h) * (0.22 + this.beat * 0.18);
      var g = ctx.createRadialGradient(w / 2, h / 2, 4, w / 2, h / 2, rad * 2.2);
      g.addColorStop(0, 'rgba(0,255,136,' + (0.55 + this.beat * 0.35) + ')');
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

    ctx.fillStyle = 'rgba(255,255,255,0.7)';
    ctx.font = '12px ui-monospace, monospace';
    ctx.fillText(String(BPM) + ' BPM · ' + mode, 12, 20);
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

    // Sync frontpage stats strip when present
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
    var beatTimer = null;
    var musicBtn = $('lm-music-toggle');
    var lightBtn = $('lm-light-toggle');

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
        if (show) show.setMode(light.id || 'pulse');
        if (data.bpm) music.bpm = data.bpm;
        return;
      } catch (e) {
        // Fallback: keep the lobby alive from /api/stats/summary + local specials.
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

    refresh();
    setInterval(refresh, REFRESH_MS);
    // Auto-start lightshow (visual only) unless reduced motion
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
