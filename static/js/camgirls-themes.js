/**
 * Camgirls studio themes — persisted palette (cosmic, velvet, signal, aurora, champagne).
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

  function applyTheme(id) {
    var theme = id || 'cosmic';
    if (!THEMES.some(function (t) { return t.id === theme; })) {
      theme = 'cosmic';
    }
    document.documentElement.classList.add('cg-giga');
    document.documentElement.setAttribute('data-cg-theme', theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      /* ignore */
    }
    document.querySelectorAll('.cg-theme-btn').forEach(function (btn) {
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
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'champagne';
    }
    return 'cosmic';
  }

  function mountThemeDock() {
    if (document.getElementById('cg-theme-dock')) return;
    var page = document.querySelector('.cg-page');
    if (!page) return;
    var dock = document.createElement('nav');
    dock.id = 'cg-theme-dock';
    dock.className = 'cg-theme-dock';
    dock.setAttribute('aria-label', 'Studio theme');
    dock.innerHTML =
      '<span class="cg-theme-dock-label">Theme</span>' +
      THEMES.map(function (t) {
        return (
          '<button type="button" class="cg-theme-btn" data-theme="' +
          t.id +
          '" title="' +
          t.label +
          ' studio">' +
          t.label +
          '</button>'
        );
      }).join('');
    page.insertBefore(dock, page.firstChild);
    dock.querySelectorAll('.cg-theme-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        applyTheme(btn.getAttribute('data-theme'));
      });
    });
    applyTheme(document.documentElement.getAttribute('data-cg-theme') || resolveInitialTheme());
  }

  applyTheme(document.documentElement.getAttribute('data-cg-theme') || resolveInitialTheme());

  document.addEventListener('DOMContentLoaded', mountThemeDock);

  window.CamgirlsThemes = { apply: applyTheme, list: THEMES };
})();
