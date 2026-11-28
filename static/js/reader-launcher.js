/**
 * Reader Launcher — retired.
 *
 * The floating left Library / reading-progress bar is removed site-wide.
 * Compendium pages still use calm-reader.js for the in-page reader shell.
 */
(function () {
  'use strict';

  function removeExistingLauncher() {
    var el = document.getElementById('cr-launcher');
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  removeExistingLauncher();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', removeExistingLauncher);
  }
})();
