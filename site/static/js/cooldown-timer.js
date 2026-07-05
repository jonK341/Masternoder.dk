/**
 * Reusable cooldown timer for Game + Battle (and any page).
 *
 * - Survives refresh: end timestamp in localStorage (scoped per storageScope + id).
 * - API: new CooldownTimer({ storageScope, id }), .start(ms), .clear(), .onTick(fn), .remainingMs()
 * - UI: CooldownTimer.mount(element, { label, storageScope, id, showBar })
 *
 * Example:
 *   var t = CooldownTimer.create({ storageScope: 'battle', id: 'quick_match' });
 *   t.start(2 * 60 * 1000);
 *   t.onTick(function (ms, formatted) { console.log(formatted); });
 */
(function (global) {
  'use strict';

  function pad2(n) {
    return n < 10 ? '0' + n : String(n);
  }

  function formatMs(ms) {
    if (ms <= 0) return '0:00';
    var s = Math.ceil(ms / 1000);
    var m = Math.floor(s / 60);
    s = s % 60;
    if (m >= 60) {
      var h = Math.floor(m / 60);
      m = m % 60;
      return h + 'h ' + m + 'm ' + pad2(s) + 's';
    }
    return m + ':' + pad2(s);
  }

  var PREFIX = 'cdTimer_v1_';

  function CooldownTimer(options) {
    var o = options || {};
    this.storageScope = (o.storageScope || 'app').replace(/[^a-z0-9_-]/gi, '_');
    this.id = (o.id || 'default').replace(/[^a-z0-9_-]/gi, '_');
    this._keyEnd = PREFIX + 'end_' + this.storageScope + '_' + this.id;
    this._keyTotal = PREFIX + 'total_' + this.storageScope + '_' + this.id;
    this._endAt = 0;
    this._totalMs = 0;
    this._interval = null;
    this._listeners = [];
    this._restore();
  }

  CooldownTimer.prototype._restore = function () {
    try {
      var end = localStorage.getItem(this._keyEnd);
      if (end) {
        var n = parseInt(end, 10);
        if (n > Date.now()) {
          this._endAt = n;
          var tot = localStorage.getItem(this._keyTotal);
          this._totalMs = tot ? parseInt(tot, 10) : 0;
        } else {
          localStorage.removeItem(this._keyEnd);
          localStorage.removeItem(this._keyTotal);
        }
      }
    } catch (e) {}
  };

  CooldownTimer.prototype._persist = function () {
    try {
      if (this._endAt > Date.now()) {
        localStorage.setItem(this._keyEnd, String(this._endAt));
        if (this._totalMs > 0) {
          localStorage.setItem(this._keyTotal, String(this._totalMs));
        }
      } else {
        localStorage.removeItem(this._keyEnd);
        localStorage.removeItem(this._keyTotal);
      }
    } catch (e) {}
  };

  CooldownTimer.prototype.remainingMs = function () {
    var r = this._endAt - Date.now();
    return r > 0 ? r : 0;
  };

  CooldownTimer.prototype.isActive = function () {
    return this.remainingMs() > 0;
  };

  CooldownTimer.prototype.start = function (durationMs) {
    var d = Math.max(0, durationMs | 0);
    this._endAt = Date.now() + d;
    this._totalMs = d;
    this._persist();
    this._emit();
    this._ensureTick();
  };

  CooldownTimer.prototype.clear = function () {
    this._endAt = 0;
    this._totalMs = 0;
    try {
      localStorage.removeItem(this._keyEnd);
      localStorage.removeItem(this._keyTotal);
    } catch (e) {}
    this._emit();
    this._stopTick();
  };

  CooldownTimer.prototype._emit = function () {
    var rem = this.remainingMs();
    var str = formatMs(rem);
    for (var i = 0; i < this._listeners.length; i++) {
      try {
        this._listeners[i](rem, str, this);
      } catch (e) {}
    }
  };

  CooldownTimer.prototype._ensureTick = function () {
    var self = this;
    if (self._interval) return;
    self._interval = setInterval(function () {
      if (self.remainingMs() <= 0) {
        self._endAt = 0;
        self._totalMs = 0;
        try {
          localStorage.removeItem(self._keyEnd);
          localStorage.removeItem(self._keyTotal);
        } catch (e) {}
        self._emit();
        self._stopTick();
      } else {
        self._emit();
      }
    }, 250);
  };

  CooldownTimer.prototype._stopTick = function () {
    if (this._interval) {
      clearInterval(this._interval);
      this._interval = null;
    }
  };

  CooldownTimer.prototype.onTick = function (fn) {
    this._listeners.push(fn);
    if (this.isActive()) this._ensureTick();
    try {
      fn(this.remainingMs(), formatMs(this.remainingMs()), this);
    } catch (e) {}
  };

  CooldownTimer.create = function (options) {
    return new CooldownTimer(options);
  };

  function mount(el, options) {
    if (!el) return null;
    var o = options || {};
    var timer = new CooldownTimer({
      storageScope: o.storageScope || 'page',
      id: o.id || 'main',
    });
    el.classList.add('cd-timer', 'cd-timer--theme-' + (o.theme || 'default'));
    el.setAttribute('role', 'status');
    el.setAttribute('aria-live', 'polite');
    el.innerHTML =
      '<div class="cd-timer-inner">' +
      '<span class="cd-timer-label"></span> ' +
      '<time class="cd-timer-remaining"></time>' +
      (o.showBar
        ? '<div class="cd-timer-bar" aria-hidden="true"><span class="cd-timer-bar-fill"></span></div>'
        : '') +
      '</div>';
    el.querySelector('.cd-timer-label').textContent = o.label || 'Cooldown';
    var timeEl = el.querySelector('.cd-timer-remaining');
    var barFill = el.querySelector('.cd-timer-bar-fill');
    var totalForBar = 0;
    timer.onTick(function (rem) {
      timeEl.textContent = rem > 0 ? formatMs(rem) : 'Ready';
      if (rem > 0) {
        el.classList.add('cd-timer--active');
        if (barFill) {
          totalForBar = timer._totalMs || rem;
          if (totalForBar < rem) totalForBar = rem;
          barFill.style.width = totalForBar > 0 ? Math.min(100, (100 * rem) / totalForBar) + '%' : '100%';
        }
      } else {
        el.classList.remove('cd-timer--active');
        if (barFill) barFill.style.width = '0%';
      }
    });
    if (o.demoSeconds && o.demoSeconds > 0) {
      timer.start(o.demoSeconds * 1000);
    }
    return timer;
  }

  function autoMount() {
    var nodes = document.querySelectorAll('[data-cd-timer]');
    for (var i = 0; i < nodes.length; i++) {
      var node = nodes[i];
      if (node.querySelector('.cd-timer-inner')) continue;
      var t = mount(node, {
        label: node.getAttribute('data-cd-label') || 'Cooldown',
        storageScope: node.getAttribute('data-cd-scope') || 'page',
        id: node.getAttribute('data-cd-id') || 'default',
        theme: node.getAttribute('data-cd-theme') || 'default',
        showBar: node.getAttribute('data-cd-bar') === '1' || node.getAttribute('data-cd-bar') === 'true',
        demoSeconds: parseInt(node.getAttribute('data-cd-demo-seconds') || '0', 10) || 0,
      });
      if (t) node.cooldownTimer = t;
    }
  }

  global.CooldownTimer = CooldownTimer;
  global.CooldownTimer.mount = mount;
  global.CooldownTimer.formatMs = formatMs;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoMount);
  } else {
    autoMount();
  }
})(typeof window !== 'undefined' ? window : this);
