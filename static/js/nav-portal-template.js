/**
 * Portal nav templates + themes — one manifest for all sites using navigation-toolbar.js
 *
 * Site default matches the start page: home_portal_void_v1 (single Portals button).
 *
 * Override only when intentional (before toolbar loads):
 *   window.MN_NAV_TEMPLATE = 'categorized_portals_v1';
 *   window.MN_NAV_THEME = 'exchange_ice';
 *
 * URL: ?nav_template=...&nav_theme=...
 * localStorage / path / server prefs no longer switch the live toolbar layout —
 * that made inner pages look messy vs the start page.
 */
(function (global) {
  'use strict';

  var APP_BASE = global.APP_BASE || '';
  var STORAGE_TEMPLATE = 'mn_nav_template';
  var STORAGE_THEME = 'mn_nav_theme';
  var MANIFEST_URL = APP_BASE + '/static/data/nav_portal_manifest.json';
  var THEMES_CSS = APP_BASE + '/static/css/nav-portal-themes.css?v=20261113a';

  var manifest = null;
  var activeTemplate = null;
  var activeTheme = null;
  var bootPromise = null;
  var serverPrefs = { template: null, theme: null };

  function readQuery(key) {
    try {
      return new URLSearchParams(global.location.search).get(key);
    } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'nav-portal-template.js', context: 'catch' }); }
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
      .catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'nav-portal-template.js', context: 'catch' }); }
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
    } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'nav-portal-template.js', context: 'catch' }); }
      return 'default_user';
    }
  }

  function resolveTemplateId() {
    if (global.MN_NAV_TEMPLATE) return global.MN_NAV_TEMPLATE;
    var q = readQuery('nav_template');
    if (q) return q;
    // Keep the start-page Portals void bar on every route.
    return (manifest && manifest.defaultTemplate) || 'home_portal_void_v1';
  }

  function resolveThemeId(template) {
    if (global.MN_NAV_THEME) return global.MN_NAV_THEME;
    var q = readQuery('nav_theme');
    if (q) return q;
    if (template && template.theme) return template.theme;
    return (manifest && manifest.defaultTheme) || 'neon_masternoder';
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
        } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'nav-portal-template.js', context: 'catch' }); } /* ignore */ }
        return data;
      })
      .catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'nav-portal-template.js', context: 'catch' }); }
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
      .catch(function () { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'nav-portal-template.js', context: 'catch' }); }
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

    global.MN_NAV_PORTAL_VOID = !!(activeTemplate && activeTemplate.layout === 'portal_void');

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
    if (activeTemplate && Array.isArray(activeTemplate.favorites)) {
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
      try { global.localStorage.setItem(STORAGE_TEMPLATE, templateId); } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'nav-portal-template.js', context: 'catch' }); } /* ignore */ }
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
      try { global.localStorage.setItem(STORAGE_THEME, themeId); } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'nav-portal-template.js', context: 'catch' }); } /* ignore */ }
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
