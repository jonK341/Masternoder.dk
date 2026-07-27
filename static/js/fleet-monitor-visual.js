/**
 * Fleet monitor themes + generator encoded background pool.
 */
(function () {
  "use strict";

  var API = "/api/exchange/fleet-progress-monitor/visual";
  var STORAGE_KEY = "mn-f5-theme";

  var state = {
    themes: [],
    theme: null,
    encodedPool: [],
    themeIndex: 0,
  };

  function applyBodyTheme(theme) {
    if (!theme || !theme.id) return;
    document.body.setAttribute("data-f5-theme", theme.id);
  }

  function setThemeById(id) {
    var t = state.themes.filter(function (x) {
      return x.id === id;
    })[0];
    if (t) {
      state.theme = t;
      state.themeIndex = state.themes.indexOf(t);
      applyBodyTheme(t);
      try {
        localStorage.setItem(STORAGE_KEY, t.id);
      } catch (e) {
        /* ignore */
      }
      return Promise.resolve(t);
    }
    return Promise.resolve(state.theme);
  }

  function cycleTheme(dir) {
    if (!state.themes.length) return state.theme;
    state.themeIndex = (state.themeIndex + (dir || 1) + state.themes.length) % state.themes.length;
    state.theme = state.themes[state.themeIndex];
    applyBodyTheme(state.theme);
    try {
      localStorage.setItem(STORAGE_KEY, state.theme.id);
    } catch (e) {
      /* ignore */
    }
    return fetch(API + "?theme=" + encodeURIComponent(state.theme.id), { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (d && d.encoded_pool) state.encodedPool = d.encoded_pool;
        return state.theme;
      })
      .catch(function () {
        return state.theme;
      });
  }

  function getTheme() {
    return state.theme || { primary: "#5dffb0", secondary: "#00d4ff", accent: "#ff64ff" };
  }

  function getEncodedPool() {
    return state.encodedPool || [];
  }

  function fillThemeSelect(sel) {
    if (!sel || !state.themes.length) return;
    sel.innerHTML = state.themes
      .map(function (t) {
        return '<option value="' + t.id + '">' + (t.name || t.id) + "</option>";
      })
      .join("");
    if (state.theme) sel.value = state.theme.id;
    sel.addEventListener("change", function () {
      setThemeById(sel.value).then(function () {
        return fetch(API + "?theme=" + encodeURIComponent(sel.value), { credentials: "same-origin" });
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (d) {
          if (d && d.encoded_pool) state.encodedPool = d.encoded_pool;
        });
    });
  }

  function init() {
    var saved = "";
    try {
      saved = localStorage.getItem(STORAGE_KEY) || "";
    } catch (e) {
      saved = "";
    }
    var url = API + (saved ? "?theme=" + encodeURIComponent(saved) : "");
    return fetch(url, { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (!d || !d.success) return;
        state.themes = d.themes || [];
        state.theme = d.active_theme || state.themes[0];
        state.encodedPool = d.encoded_pool || [];
        state.themeIndex = Math.max(
          0,
          state.themes.findIndex(function (t) {
            return t.id === (state.theme && state.theme.id);
          })
        );
        applyBodyTheme(state.theme);
        fillThemeSelect(document.getElementById("f5-theme-pick"));
      });
  }

  window.F5MonitorVisual = {
    init: init,
    getTheme: getTheme,
    getEncodedPool: getEncodedPool,
    cycleTheme: cycleTheme,
    setThemeById: setThemeById,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
