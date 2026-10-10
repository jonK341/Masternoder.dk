/**
 * Rewrite toolbar / in-page links on camgirls.masternoder.dk studio (Phase 4).
 */
(function () {
  'use strict';

  var MAIN = 'https://masternoder.dk';

  function onStudioHost() {
    return typeof window.cgIsAppMount === 'function' && window.cgIsAppMount();
  }

  function rewriteHref(href) {
    if (!href || href.indexOf('mailto:') === 0 || href.indexOf('javascript:') === 0) {
      return href;
    }
    if (href.indexOf('http://') === 0 || href.indexOf('https://') === 0) {
      return href;
    }
    var path = href.split('#')[0].split('?')[0];
    var qs = href.indexOf('?') >= 0 ? href.slice(href.indexOf('?')) : '';
    if (path === '/' || path === '') {
      return '/';
    }
    if (path === '/camgirls' || path === '/camgirls/') {
      return typeof window.cgPageBase === 'function' ? window.cgPageBase() : '/app/';
    }
    if (path === '/shop' || path === '/shop/') {
      return typeof window.cgShopUrl === 'function' ? window.cgShopUrl(qs.slice(1)) : '/app/shop/' + qs;
    }
    if (path.indexOf('/shop') === 0) {
      var q = href.indexOf('?') >= 0 ? href.slice(href.indexOf('?') + 1) : '';
      return typeof window.cgShopUrl === 'function' ? window.cgShopUrl(q) : '/app' + href;
    }
    if (path.indexOf('/camgirls/p/') === 0) {
      var rest = path.slice('/camgirls/p/'.length);
      return (typeof window.cgPageBase === 'function' ? window.cgPageBase() : '/app/') + 'p/' + rest + (href.endsWith('/') ? '' : '');
    }
    if (path.indexOf('/app/') === 0 || path.indexOf('/static/') === 0) {
      return href;
    }
    return MAIN + (path.charAt(0) === '/' ? path : '/' + path) + qs;
  }

  function patchAnchors(root) {
    if (!onStudioHost()) {
      return;
    }
    (root || document).querySelectorAll('a[href]').forEach(function (a) {
      var href = a.getAttribute('href');
      if (!href) {
        return;
      }
      var next = rewriteHref(href);
      if (next && next !== href) {
        a.setAttribute('href', next);
      }
    });
  }

  function boot() {
    if (!onStudioHost()) {
      return;
    }
    window.APP_BASE = '/app';
    patchAnchors(document);
    setTimeout(function () {
      patchAnchors(document);
    }, 400);
    setTimeout(function () {
      patchAnchors(document);
    }, 1500);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
