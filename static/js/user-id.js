/**
 * Shared user id lookup. Never invents default_user.
 * Legacy ids such as "jon" and "Sander Sahk" are kept.
 * Placeholders (empty, default_user, undefined, null, [object Promise]) are not.
 */
(function (global) {
  'use strict';

  function isUsable(id) {
    if (typeof id !== 'string') return false;
    var value = id.trim();
    if (!value || value === '[object Promise]') return false;
    var lowered = value.toLowerCase();
    return lowered !== 'default_user' && lowered !== 'undefined' && lowered !== 'null';
  }

  function read() {
    try {
      var keys = ['game_user_id', 'user_id', 'mn_user_id'];
      for (var i = 0; i < keys.length; i++) {
        var raw = global.localStorage.getItem(keys[i]);
        if (isUsable(raw)) return raw.trim();
      }
    } catch (e) {}
    return '';
  }

  function encode(id) {
    return encodeURIComponent(id == null ? '' : String(id));
  }

  async function resolve() {
    try {
      if (global.backendConnector && typeof global.backendConnector.getUserId === 'function') {
        var fromConnector = await global.backendConnector.getUserId();
        if (isUsable(fromConnector)) return String(fromConnector).trim();
      }
      if (global.userIdentification && typeof global.userIdentification.getUserId === 'function') {
        var fromIdentify = await global.userIdentification.getUserId();
        if (isUsable(fromIdentify)) return String(fromIdentify).trim();
      }
    } catch (e) {}
    return read() || null;
  }

  global.MnUserId = { isUsable: isUsable, read: read, encode: encode, resolve: resolve };
})(typeof window !== 'undefined' ? window : globalThis);
