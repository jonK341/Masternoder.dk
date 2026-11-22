/**
 * MasterNoder Meta Pixel bootstrap — loads fbq when a pixel id is configured.
 * Safe no-op without an id. Used by casino + Invite Party landing.
 */
(function (global) {
  'use strict';

  var state = {
    pixelId: null,
    ready: false,
    queued: [],
  };

  function ensureFbq(pixelId) {
    if (!pixelId) return false;
    if (state.pixelId && state.pixelId !== String(pixelId)) return !!global.fbq;
    if (global.fbq && state.ready) return true;
    state.pixelId = String(pixelId);
    (function (f, b, e, v) {
      if (f.fbq) return;
      var n = f.fbq = function () {
        n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
      };
      if (!f._fbq) f._fbq = n;
      n.push = n;
      n.loaded = true;
      n.version = '2.0';
      n.queue = [];
      var t = b.createElement(e);
      t.async = true;
      t.src = v;
      var s = b.getElementsByTagName(e)[0];
      s.parentNode.insertBefore(t, s);
    })(global, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');
    global.fbq('init', state.pixelId);
    state.ready = true;
    return true;
  }

  function track(name, params, opts) {
    opts = opts || {};
    if (!state.ready && state.pixelId) ensureFbq(state.pixelId);
    if (!state.ready || !global.fbq) {
      state.queued.push([name, params, opts]);
      return false;
    }
    try {
      if (opts.standard) {
        global.fbq('track', name, params || {});
      } else {
        global.fbq('trackCustom', name, params || {});
      }
      return true;
    } catch (e) {
      return false;
    }
  }

  function flushQueue() {
    while (state.queued.length) {
      var item = state.queued.shift();
      track(item[0], item[1], item[2]);
    }
  }

  function bootFromConfig(cfg) {
    if (!cfg || cfg.enabled === false) return null;
    var id = (cfg.pixel_id || '').toString().trim();
    if (!id) return null;
    if (!ensureFbq(id)) return null;
    if (cfg.auto_page_view !== false) {
      track('PageView', {}, { standard: true });
      track('ViewContent', {
        content_name: (cfg.content_name || 'MasterNoder2 Casino'),
        content_category: 'casino',
      }, { standard: true });
    }
    flushQueue();
    return id;
  }

  function fetchAndBoot(apiUrl) {
    var url = apiUrl || '/api/casino/meta/pixel';
    return fetch(url, { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data || !data.success) return null;
        return bootFromConfig(data);
      })
      .catch(function () { return null; });
  }

  global.MnMetaPixel = {
    bootFromConfig: bootFromConfig,
    fetchAndBoot: fetchAndBoot,
    track: track,
    trackStandard: function (name, params) { return track(name, params, { standard: true }); },
    trackCustom: function (name, params) { return track(name, params, { standard: false }); },
    getPixelId: function () { return state.pixelId; },
    isReady: function () { return state.ready; },
  };
})(typeof window !== 'undefined' ? window : this);
