/**
 * Camgirls API/static/page base — masternoder.dk/camgirls vs camgirls.masternoder.dk/app/
 */
(function (global) {
  'use strict';

  function hostname() {
    return global.location && global.location.hostname ? global.location.hostname : '';
  }

  function isAppMount() {
    var p = global.location && global.location.pathname ? global.location.pathname : '';
    if (p === '/app' || p.indexOf('/app/') === 0) {
      return true;
    }
    return hostname() === 'camgirls.masternoder.dk';
  }

  function cgApi(path) {
    var suffix = path.charAt(0) === '/' ? path : '/' + path;
    if (suffix.indexOf('/api/camgirls') === 0) {
      suffix = suffix.slice('/api/camgirls'.length) || '/';
    }
    if (isAppMount()) {
      return '/app/api' + suffix;
    }
    return '/api/camgirls' + suffix;
  }

  function cgStatic(path) {
    var rel = path.charAt(0) === '/' ? path.slice(1) : path;
    if (rel.indexOf('static/') === 0) {
      rel = rel.slice(7);
    }
    if (isAppMount()) {
      return '/app/static/' + rel;
    }
    return '/static/' + rel;
  }

  function cgPageBase() {
    return isAppMount() ? '/app/' : '/camgirls/';
  }

  function cgPerformerPath(performerId) {
    var id = (performerId || '').replace(/^\//, '');
    return cgPageBase() + 'p/' + encodeURIComponent(id) + '/';
  }

  function cgShopUrl(query) {
    var q = query || '';
    if (q.charAt(0) !== '?' && q) {
      q = '?' + q;
    }
    return isAppMount() ? '/app/shop/' + q : '/shop/' + q;
  }

  global.cgApi = cgApi;
  global.cgStatic = cgStatic;
  global.cgIsAppMount = isAppMount;
  global.cgPageBase = cgPageBase;
  global.cgPerformerPath = cgPerformerPath;
  global.cgShopUrl = cgShopUrl;
})(typeof window !== 'undefined' ? window : this);
