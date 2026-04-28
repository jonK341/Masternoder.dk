/**
 * 5D story monitor: dimensions x₁,x₂,x₃ (micro-drift), τ (chroniton), σ (narrative arc).
 * Optional Web Audio resonance (user gesture required — button).
 */
(function () {
  'use strict';

  var BEATS = {
    battle: [
      { sigma: 0.12, t: 'Signals converge — the arena remembers every duel.' },
      { sigma: 0.28, t: 'Streak heat maps to σ; one round can rewrite the ladder echo.' },
      { sigma: 0.44, t: 'Clan threads pull rank; tournaments braid timelines in the matrix.' },
      { sigma: 0.62, t: 'The core flashes: RPS is law inside the holodeck viewport.' },
      { sigma: 0.78, t: 'Victory prints to battle points; loss still feeds the chronicle.' },
      { sigma: 0.94, t: 'Return to the hunt — the story loops until you own the arc.' },
    ],
    game: [
      { sigma: 0.1, t: 'Calm sessions stack XP without stealing tomorrow’s breath.' },
      { sigma: 0.26, t: 'Trophies mark paths, not pressure — the nexus arc unfolds at your pace.' },
      { sigma: 0.42, t: 'Quests are invitations; Star Map nodes light when you choose them.' },
      { sigma: 0.58, t: 'Coins and milestones respect pacing — no FOMO engine under the hood.' },
      { sigma: 0.74, t: 'Social threads tie to progress, not grind — walkthroughs stay optional.' },
      { sigma: 0.9, t: 'The Hunter story is yours to narrate; σ rises with gentle consistency.' },
    ],
    aggregator: [
      { sigma: 0.15, t: 'Five dimensions: spatial drift x₁–x₃, chroniton τ, narrative σ — sound optional.' },
      { sigma: 0.33, t: 'The grid is a holodeck; the duel lives at the golden core of the monitor.' },
      { sigma: 0.5, t: 'Encoder links stitch APIs; intelligence panels mirror the rest of the site.' },
      { sigma: 0.67, t: 'Engagement points trace exploration, chat, decode, and intel loads.' },
      { sigma: 0.85, t: 'Unified points reconcile activity, game, and knowledge in one ledger.' },
      { sigma: 0.96, t: 'σ completes the arc — reopen the monitor anytime to resume the story field.' },
    ],
  };

  function prefersReducedMotion() {
    try {
      return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch (e) {
      return false;
    }
  }

  function mount(container) {
    var context =
      (container.getAttribute('data-story-context') || 'aggregator').toLowerCase();
    if (!BEATS[context]) context = 'aggregator';

    var tech =
      container.getAttribute('data-tech-label') ||
      (context === 'battle'
        ? 'Chroniton resonance driver · Web Audio × σ-phase'
        : context === 'game'
          ? 'Eidetic calm-memory buffer · adaptive σ pacing'
          : 'Panoptic σ field · Web Audio storyscape');

    var root = document.createElement('div');
    root.className = 'sm5d-root';
    root.innerHTML =
      '<p class="sm5d-tech"></p>' +
      '<div class="sm5d-bezel">' +
      '<span class="sm5d-bezel-title">5D monitor · σ narrative · τ chroniton</span>' +
      '<button type="button" class="sm5d-sound-btn" aria-pressed="false">Sound: off</button>' +
      '</div>' +
      '<div class="sm5d-readout" aria-live="polite"></div>' +
      '<div class="sm5d-viewport">' +
      '<p class="sm5d-story"></p>' +
      '<div class="sm5d-sigma-bar" aria-hidden="true"><div class="sm5d-sigma-bar-fill"></div></div>' +
      '</div>';

    var techEl = root.querySelector('.sm5d-tech');
    techEl.textContent = 'Technology · ' + tech;

    container.appendChild(root);

    var readout = root.querySelector('.sm5d-readout');
    var storyEl = root.querySelector('.sm5d-story');
    var sigmaFill = root.querySelector('.sm5d-sigma-bar-fill');
    var soundBtn = root.querySelector('.sm5d-sound-btn');

    var phase = 0;
    var beats = BEATS[context];
    var micro = { x1: 0.2, x2: 0.5, x3: 0.8, tau: 0 };
    var audio = null;

    function renderReadout() {
      var σ = beats[phase].sigma;
      readout.innerHTML =
        '<span><span class="sm5d-dim-name">x₁</span>' +
        micro.x1.toFixed(3) +
        '</span>' +
        '<span><span class="sm5d-dim-name">x₂</span>' +
        micro.x2.toFixed(3) +
        '</span>' +
        '<span><span class="sm5d-dim-name">x₃</span>' +
        micro.x3.toFixed(3) +
        '</span>' +
        '<span><span class="sm5d-dim-name">τ</span>' +
        String(micro.tau % 24).padStart(2, '0') +
        ':00</span>' +
        '<span><span class="sm5d-dim-name">σ</span>' +
        σ.toFixed(2) +
        ' arc</span>';
      storyEl.textContent = beats[phase].t;
      sigmaFill.style.width = Math.round(σ * 100) + '%';
    }

    function tickMicro() {
      var t = Date.now() / 1800;
      micro.x1 = 0.5 + 0.45 * Math.sin(t * 0.7);
      micro.x2 = 0.5 + 0.45 * Math.sin(t * 0.9 + 1);
      micro.x3 = 0.5 + 0.45 * Math.sin(t * 0.55 + 2);
      micro.tau = Math.floor((Date.now() / 60000) % 1440);
    }

    function chime() {
      if (!audio || !audio.ctx) return;
      try {
        var ctx = audio.ctx;
        var o = ctx.createOscillator();
        var g = ctx.createGain();
        o.type = 'sine';
        o.frequency.value = 330;
        g.gain.value = 0.0001;
        o.connect(g);
        g.connect(ctx.destination);
        var now = ctx.currentTime;
        g.gain.exponentialRampToValueAtTime(0.06, now + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, now + 0.09);
        o.start(now);
        o.stop(now + 0.1);
      } catch (e) {}
    }

    function startDrone() {
      if (audio && audio.ctx) return;
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      try {
        var ctx = new Ctx();
        var g = ctx.createGain();
        g.gain.value = 0.0001;
        g.connect(ctx.destination);

        var o1 = ctx.createOscillator();
        o1.type = 'sine';
        o1.frequency.value = 55;
        o1.connect(g);

        var o2 = ctx.createOscillator();
        o2.type = 'triangle';
        o2.frequency.value = 110;
        o2.connect(g);

        var now = ctx.currentTime;
        g.gain.exponentialRampToValueAtTime(0.018, now + 0.15);

        o1.start();
        o2.start();
        audio = { ctx: ctx, gain: g, o1: o1, o2: o2 };
      } catch (e) {
        audio = null;
      }
    }

    function stopDrone() {
      if (!audio || !audio.ctx) return;
      try {
        var ctx = audio.ctx;
        var now = ctx.currentTime;
        audio.gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.2);
        setTimeout(function () {
          try {
            audio.o1.stop();
            audio.o2.stop();
            ctx.close();
          } catch (e2) {}
        }, 300);
      } catch (e) {}
      audio = null;
    }

    soundBtn.addEventListener('click', function () {
      var on = soundBtn.getAttribute('aria-pressed') === 'true';
      if (on) {
        stopDrone();
        soundBtn.setAttribute('aria-pressed', 'false');
        soundBtn.textContent = 'Sound: off';
      } else {
        startDrone();
        soundBtn.setAttribute('aria-pressed', 'true');
        soundBtn.textContent = 'Sound: on';
        chime();
      }
    });

    var intervalMs = prefersReducedMotion() ? 14000 : 9000;
    var microTimer = setInterval(function () {
      tickMicro();
      renderReadout();
    }, prefersReducedMotion() ? 2000 : 400);

    var storyTimer = setInterval(function () {
      phase = (phase + 1) % beats.length;
      if (soundBtn.getAttribute('aria-pressed') === 'true') chime();
      renderReadout();
    }, intervalMs);

    tickMicro();
    renderReadout();

    container._sm5dDispose = function () {
      clearInterval(microTimer);
      clearInterval(storyTimer);
      stopDrone();
    };
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-story-monitor-5d]').forEach(function (el) {
      if (el.querySelector('.sm5d-root')) return;
      mount(el);
    });
  });
})();
