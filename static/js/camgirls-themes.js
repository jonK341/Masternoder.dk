/**
 * Studio themes — shared camgirls + aggregator (localStorage cg_studio_theme_v1).
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'cg_studio_theme_v1';
  var THEMES = [
    { id: 'cosmic', label: 'Cosmic' },
    { id: 'velvet', label: 'Velvet' },
    { id: 'signal', label: 'Signal' },
    { id: 'aurora', label: 'Aurora' },
    { id: 'champagne', label: 'Champagne' },
  ];

  function isAggregator() {
    return document.body && document.body.classList.contains('layout-aggregator-linux');
  }

  function applyTheme(id) {
    var theme = id || 'cosmic';
    if (!THEMES.some(function (t) { return t.id === theme; })) {
      theme = 'cosmic';
    }
    document.documentElement.setAttribute('data-cg-theme', theme);
    if (isAggregator()) {
      document.documentElement.classList.add('agg-themed');
      document.documentElement.classList.remove('cg-giga');
    } else {
      document.documentElement.classList.add('cg-giga');
      document.documentElement.classList.remove('agg-themed');
    }
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      /* ignore */
    }
    document.querySelectorAll('.cg-theme-btn, .agg-theme-btn').forEach(function (btn) {
      btn.classList.toggle('active', btn.getAttribute('data-theme') === theme);
    });
  }

  function resolveInitialTheme() {
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return saved;
    } catch (e) {
      /* ignore */
    }
    if (isAggregator()) {
      return 'cosmic';
    }
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'champagne';
    }
    return 'cosmic';
  }

  function dockButtonsHtml() {
    return THEMES.map(function (t) {
      return (
        '<button type="button" class="cg-theme-btn agg-theme-btn" data-theme="' +
        t.id +
        '" title="' +
        t.label +
        ' theme">' +
        t.label +
        '</button>'
      );
    }).join('');
  }

  function wireDock(dock) {
    dock.querySelectorAll('.cg-theme-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        applyTheme(btn.getAttribute('data-theme'));
      });
    });
  }

  function mountThemeDock() {
    if (document.getElementById('cg-theme-dock') || document.getElementById('agg-theme-dock')) {
      return;
    }
    if (isAggregator()) {
      var row = document.querySelector('.agg-tech-row');
      if (!row || !row.parentNode) return;
      var dock = document.createElement('nav');
      dock.id = 'agg-theme-dock';
      dock.className = 'cg-theme-dock agg-theme-dock';
      dock.setAttribute('aria-label', 'Aggregator theme');
      dock.innerHTML =
        '<span class="cg-theme-dock-label">Theme</span>' + dockButtonsHtml();
      row.parentNode.insertBefore(dock, row.nextSibling);
      wireDock(dock);
      return;
    }
    var page = document.querySelector('.cg-page');
    if (!page) return;
    var dock = document.createElement('nav');
    dock.id = 'cg-theme-dock';
    dock.className = 'cg-theme-dock';
    dock.setAttribute('aria-label', 'Studio theme');
    dock.innerHTML = '<span class="cg-theme-dock-label">Theme</span>' + dockButtonsHtml();
    page.insertBefore(dock, page.firstChild);
    wireDock(dock);
  }

  applyTheme(document.documentElement.getAttribute('data-cg-theme') || resolveInitialTheme());

  document.addEventListener('DOMContentLoaded', mountThemeDock);

  var api = { apply: applyTheme, list: THEMES, storageKey: STORAGE_KEY };
  window.CamgirlsThemes = api;
  window.StudioThemes = api;
})();
