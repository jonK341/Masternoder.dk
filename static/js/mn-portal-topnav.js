/**
 * Single-page include for the static MasterNoder Portals topnav.
 *
 * Add only this on every page (refresh-safe):
 *   <script src="/static/js/mn-portal-topnav.js?v=20261128static" defer></script>
 *
 * Loads CSS, injects /static/html/mn-portal-topnav.html into the document body,
 * then boots navigation-toolbar.js to hydrate interactions / themes / currency.
 */
(function () {
  'use strict';

  if (window.__MN_PORTAL_TOPNAV_BOOTED__) return;
  window.__MN_PORTAL_TOPNAV_BOOTED__ = true;

  var APP_BASE = (typeof window !== 'undefined' && window.APP_BASE !== undefined) ? window.APP_BASE : '';
  var ASSET_V = '20261128nolaunch';
  var HTML_URL = APP_BASE + '/static/html/mn-portal-topnav.html?v=' + ASSET_V;
  var CSS_TOOLBAR = APP_BASE + '/static/css/navigation-toolbar.css?v=' + ASSET_V;
  var CSS_THEMES = APP_BASE + '/static/css/nav-portal-themes.css?v=' + ASSET_V;
  var JS_TOOLBAR = APP_BASE + '/static/js/navigation-toolbar.js?v=' + ASSET_V;

  window.MN_NAV_PORTAL_VOID = true;
  window.MN_PORTAL_TOPNAV_STATIC = true;
  if (!window.MN_NAV_TEMPLATE) {
    window.MN_NAV_TEMPLATE = 'home_portal_void_v1';
  }

  function ensureStylesheet(href) {
    if (!href || document.querySelector('link[href*="' + href.split('?')[0].split('/').pop() + '"]')) {
      return;
    }
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    document.head.appendChild(link);
  }

  function ensureScript(src, onload) {
    var key = src.split('?')[0];
    var existing = document.querySelector('script[src*="' + key.split('/').pop() + '"]');
    if (existing) {
      if (onload) {
        if (window.NavigationToolbar) onload();
        else existing.addEventListener('load', onload);
      }
      return;
    }
    var s = document.createElement('script');
    s.src = src;
    s.defer = true;
    if (onload) s.onload = onload;
    s.onerror = function () {
      console.warn('[mn-portal-topnav] failed to load', src);
    };
    document.head.appendChild(s);
  }

  function mountHtml(markup) {
    if (document.getElementById('navToolbar')) {
      return document.getElementById('navToolbar');
    }
    var wrap = document.createElement('div');
    wrap.id = 'mnPortalTopnavMount';
    wrap.setAttribute('data-mn-portal-static-mount', '1');
    wrap.innerHTML = markup;
    var node = wrap.firstElementChild;
    if (!node) return null;
    var target = document.body;
    if (!target) return null;
    target.insertBefore(node, target.firstChild);
    return node;
  }

  function bootToolbar() {
    function hydrate() {
      if (window.NavigationToolbar && typeof window.NavigationToolbar.hydrateStatic === 'function') {
        window.NavigationToolbar.hydrateStatic();
      } else if (window.NavigationToolbar && typeof window.NavigationToolbar.init === 'function') {
        window.NavigationToolbar.init();
      }
    }
    if (window.NavigationToolbar) {
      hydrate();
      return;
    }
    ensureScript(JS_TOOLBAR, hydrate);
  }

  function injectAndBoot() {
    ensureStylesheet(CSS_TOOLBAR);
    ensureStylesheet(CSS_THEMES);

    if (document.getElementById('navToolbar')) {
      bootToolbar();
      return;
    }

    fetch(HTML_URL, { credentials: 'same-origin', cache: 'no-cache' })
      .then(function (r) {
        if (!r.ok) throw new Error('portal topnav HTTP ' + r.status);
        return r.text();
      })
      .then(function (markup) {
        mountHtml(markup);
        bootToolbar();
      })
      .catch(function (err) {
        console.warn('[mn-portal-topnav] falling back to JS toolbar', err);
        window.MN_PORTAL_TOPNAV_STATIC = false;
        bootToolbar();
      });
  }

  function start() {
    if (!document.body) {
      document.addEventListener('DOMContentLoaded', injectAndBoot);
      return;
    }
    injectAndBoot();
  }

  start();
})();
