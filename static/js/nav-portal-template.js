/**
 * Portal nav templates + themes — one manifest for all sites using navigation-toolbar.js
 *
 * Override per page (before toolbar loads):
 *   window.MN_NAV_TEMPLATE = 'exchange_focus_v1';
 *   window.MN_NAV_THEME = 'exchange_ice';
 *
 * User preference (localStorage): mn_nav_template, mn_nav_theme
 * URL: ?nav_template=...&nav_theme=...
 */
(function (global) {
  'use strict';

  var APP_BASE = global.APP_BASE || '';
  var STORAGE_TEMPLATE = 'mn_nav_template';
  var STORAGE_THEME = 'mn_nav_theme';
  var MANIFEST_URL = APP_BASE + '/static/data/nav_portal_manifest.json';
  var THEMES_CSS = APP_BASE + '/static/css/nav-portal-themes.css?v=20261001';

  var manifest = null;
  var activeTemplate = null;
  var activeTheme = null;
  var bootPromise = null;
  var serverPrefs = { template: null, theme: null };

  function readQuery(key) {
    try {
      return new URLSearchParams(global.location.search).get(key);
    } catch (e) {
      return null;
    }
  }

  function loadStylesheet(href) {
    if (!href || global.document.querySelector('link[href*="nav-portal-themes.css"]')) return;
    var link = global.document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    global.document.head.appendChild(link);
  }

  function fetchManifest() {
    return fetch(MANIFEST_URL, { credentials: 'same-origin' })
      .then(function (r) {
        if (!r.ok) throw new Error('manifest HTTP ' + r.status);
        return r.json();
      })
      .catch(function () {
        return null;
      });
  }

  function matchPathRule() {
    var rules = manifest.pathTemplates || [];
    var path = global.location.pathname || '';
    for (var i = 0; i < rules.length; i++) {
      var rule = rules[i];
      if (rule.prefix && path.indexOf(rule.prefix) === 0) return rule;
    }
    return null;
  }

  function currentUserId() {
    try {
      return (
        global.localStorage.getItem('game_user_id') ||
        global.localStorage.getItem('user_id') ||
        'default_user'
      );
    } catch (e) {
      return 'default_user';
    }
  }

  function resolveTemplateId() {
    if (global.MN_NAV_TEMPLATE) return global.MN_NAV_TEMPLATE;
    var q = readQuery('nav_template');
    if (q) return q;
    if (serverPrefs.template) return serverPrefs.template;
    var pathRule = matchPathRule();
    if (pathRule && pathRule.template) return pathRule.template;
    try {
      var stored = global.localStorage.getItem(STORAGE_TEMPLATE);
      if (stored) return stored;
    } catch (e) { /* ignore */ }
    return manifest && manifest.defaultTemplate;
  }

  function resolveThemeId(template) {
    if (global.MN_NAV_THEME) return global.MN_NAV_THEME;
    var q = readQuery('nav_theme');
    if (q) return q;
    if (serverPrefs.theme) return serverPrefs.theme;
    var pathRule = matchPathRule();
    if (pathRule && pathRule.theme) return pathRule.theme;
    try {
      var stored = global.localStorage.getItem(STORAGE_THEME);
      if (stored) return stored;
    } catch (e) { /* ignore */ }
    if (template && template.theme) return template.theme;
    return manifest && manifest.defaultTheme;
  }

  function loadServerPrefs() {
    var uid = currentUserId();
    if (!uid || uid === 'default_user') {
      return Promise.resolve(null);
    }
    var url =
      APP_BASE +
      '/api/user/portal-nav-preferences?user_id=' +
      encodeURIComponent(uid);
    return fetch(url, { credentials: 'same-origin' })
      .then(function (r) {
        if (!r.ok) throw new Error('prefs HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.success) return null;
        serverPrefs.template = data.nav_template || null;
        serverPrefs.theme = data.nav_theme || null;
        try {
          if (serverPrefs.template) {
            global.localStorage.setItem(STORAGE_TEMPLATE, serverPrefs.template);
          }
          if (serverPrefs.theme) {
            global.localStorage.setItem(STORAGE_THEME, serverPrefs.theme);
          }
        } catch (e) { /* ignore */ }
        return data;
      })
      .catch(function () {
        return null;
      });
  }

  function saveServerPrefs(templateId, themeId) {
    var uid = currentUserId();
    if (!uid || uid === 'default_user') {
      return Promise.resolve(null);
    }
    var body = { user_id: uid };
    if (templateId) body.nav_template = templateId;
    if (themeId) body.nav_theme = themeId;
    return fetch(APP_BASE + '/api/user/portal-nav-preferences', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (data && data.success) {
          serverPrefs.template = data.nav_template || serverPrefs.template;
          serverPrefs.theme = data.nav_theme || serverPrefs.theme;
        }
        return data;
      })
      .catch(function () {
        return null;
      });
  }

  function applyTheme(theme) {
    if (!theme) return;
    var root = global.document.documentElement;
    var body = global.document.body;
    if (!root || !body) return;

    global.document.querySelectorAll('[class*="nav-tema-"]').forEach(function (el) {
      Array.prototype.slice.call(el.classList).forEach(function (c) {
        if (c.indexOf('nav-tema-') === 0) el.classList.remove(c);
      });
    });

    if (theme.className) body.classList.add(theme.className);
    root.setAttribute('data-nav-theme', theme.id || '');
    root.setAttribute('data-nav-template', activeTemplate && activeTemplate.id ? activeTemplate.id : '');

    var vars = theme.cssVars || {};
    Object.keys(vars).forEach(function (key) {
      root.style.setProperty(key, vars[key]);
    });
  }

  function hydrateActive() {
    var templates = manifest.templates || {};
    var themes = manifest.themes || {};
    var templateId = resolveTemplateId();
    activeTemplate = templates[templateId] || templates[manifest.defaultTemplate];
    if (activeTemplate) activeTemplate.id = templateId || manifest.defaultTemplate;

    var themeId = resolveThemeId(activeTemplate);
    activeTheme = themes[themeId] || themes[manifest.defaultTheme];
    if (activeTheme) activeTheme.id = themeId || manifest.defaultTheme;

    if (activeTemplate && activeTemplate.layout === 'portal_void') {
      global.MN_NAV_PORTAL_VOID = true;
    }

    applyTheme(activeTheme);
  }

  function boot() {
    if (bootPromise) return bootPromise;
    loadStylesheet(THEMES_CSS);
    bootPromise = fetchManifest()
      .then(function (data) {
        if (!data || !data.templates) {
          throw new Error('nav manifest missing');
        }
        manifest = data;
        return loadServerPrefs();
      })
      .then(function () {
        hydrateActive();
        return manifest;
      });
    return bootPromise;
  }

  function categoryGifBase() {
    var base = (activeTheme && activeTheme.categoryGifBase) || '/static/img/nav/categories/';
    if (base.indexOf('http') !== 0 && APP_BASE && base.charAt(0) === '/') {
      return APP_BASE + base;
    }
    return base;
  }

  function getCategories() {
    return (activeTemplate && activeTemplate.categories) ? activeTemplate.categories.slice() : [];
  }

  function getFavorites() {
    if (activeTemplate && activeTemplate.favorites && activeTemplate.favorites.length) {
      return activeTemplate.favorites.slice();
    }
    return ['generator', 'game', 'battle', 'trophies'];
  }

  function getLayout() {
    return (activeTemplate && activeTemplate.layout) || 'categorized';
  }

  function isPortalVoid() {
    return getLayout() === 'portal_void' || !!global.MN_NAV_PORTAL_VOID;
  }

  function listTemplates() {
    if (!manifest) return [];
    return Object.keys(manifest.templates || {}).map(function (id) {
      var t = manifest.templates[id];
      return { id: id, label: t.label || id, description: t.description || '', layout: t.layout, theme: t.theme };
    });
  }

  function listThemes() {
    if (!manifest) return [];
    return Object.keys(manifest.themes || {}).map(function (id) {
      var t = manifest.themes[id];
      return { id: id, label: t.label || id, className: t.className };
    });
  }

  function setTemplate(templateId, persist) {
    if (!manifest || !manifest.templates[templateId]) return false;
    if (persist !== false) {
      try { global.localStorage.setItem(STORAGE_TEMPLATE, templateId); } catch (e) { /* ignore */ }
      saveServerPrefs(templateId, null);
    }
    global.MN_NAV_TEMPLATE = templateId;
    serverPrefs.template = templateId;
    hydrateActive();
    return true;
  }

  function setTheme(themeId, persist) {
    if (!manifest || !manifest.themes[themeId]) return false;
    if (persist !== false) {
      try { global.localStorage.setItem(STORAGE_THEME, themeId); } catch (e) { /* ignore */ }
      saveServerPrefs(null, themeId);
    }
    global.MN_NAV_THEME = themeId;
    serverPrefs.theme = themeId;
    hydrateActive();
    return true;
  }

  function applyAndReloadToolbar() {
    hydrateActive();
    if (global.NavigationToolbar && global.NavigationToolbar.reinit) {
      global.NavigationToolbar.reinit();
    }
  }

  global.NavPortalTemplate = {
    boot: boot,
    getManifest: function () { return manifest; },
    getActiveTemplate: function () { return activeTemplate; },
    getActiveTheme: function () { return activeTheme; },
    getCategories: getCategories,
    getFavorites: getFavorites,
    getLayout: getLayout,
    isPortalVoid: isPortalVoid,
    categoryGifBase: categoryGifBase,
    listTemplates: listTemplates,
    listThemes: listThemes,
    setTemplate: setTemplate,
    setTheme: setTheme,
    applyAndReloadToolbar: applyAndReloadToolbar,
    saveServerPrefs: saveServerPrefs,
    getServerPrefs: function () {
      return { template: serverPrefs.template, theme: serverPrefs.theme };
    },
  };
})(typeof window !== 'undefined' ? window : globalThis);
