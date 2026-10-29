/**
 * Camgirls — LiveKit fan microphone session (Phase 3 E2E).
 * Requires livekit-client UMD (window.LivekitClient) loaded before this script.
 */
(function (global) {
  'use strict';

  var activeRoom = null;
  var activePerformerId = '';

  function sdk() {
    return global.LivekitClient || global.livekit || null;
  }

  function isConnected() {
    return !!(activeRoom && activeRoom.state === 'connected');
  }

  function disconnect() {
    if (!activeRoom) return Promise.resolve();
    var room = activeRoom;
    activeRoom = null;
    activePerformerId = '';
    try {
      return room.disconnect().catch(function (err) {
        if (window.ErrorManager && window.ErrorManager.logJSError) {
          window.ErrorManager.logJSError(err instanceof Error ? err : new Error(String(err)), { source: 'camgirls-livekit-voice.js', context: 'disconnect' });
        }
      });
    } catch (e) {
      if (window.ErrorManager && window.ErrorManager.logJSError) {
        window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'camgirls-livekit-voice.js', context: 'disconnect' });
      }
      return Promise.resolve();
    }
  }

  function connectLive(payload) {
    var url = payload.livekit_url || payload.url;
    var token = payload.token;
    if (!url || !token) {
      return Promise.reject(new Error('livekit_stub'));
    }
    var LK = sdk();
    if (!LK || !LK.Room) {
      return Promise.reject(new Error('livekit_sdk_missing'));
    }
    return disconnect().then(function () {
      var room = new LK.Room({ adaptiveStream: true, dynacast: true });
      activeRoom = room;
      activePerformerId = payload.performer_id || '';
      return room
        .connect(url, token)
        .then(function () {
          return room.localParticipant.setMicrophoneEnabled(true);
        })
        .then(function () {
          return { room: room, mode: 'live' };
        })
        .catch(function (err) {
          activeRoom = null;
          activePerformerId = '';
          if (window.ErrorManager && window.ErrorManager.logJSError) {
            window.ErrorManager.logJSError(err instanceof Error ? err : new Error(String(err)), { source: 'camgirls-livekit-voice.js', context: 'connectLive' });
          }
          throw err;
        });
    });
  }

  function requestToken(apiUrlFn, userId, performerId) {
    var path = '/api/camgirls/livekit/token';
    return fetch(apiUrlFn(path), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, performer_id: performerId }),
    }).then(function (r) {
      return r.json().then(function (body) {
        body._httpStatus = r.status;
        return body;
      });
    });
  }

  function toggleVoice(apiUrlFn, userId, performerId) {
    if (isConnected() && activePerformerId === performerId) {
      return disconnect().then(function () {
        return { success: true, action: 'disconnected' };
      });
    }
    return requestToken(apiUrlFn, userId, performerId).then(function (d) {
      if (!d.success) {
        return d;
      }
      if (d.mode !== 'live' || !d.token) {
        return Object.assign({}, d, { action: 'stub' });
      }
      return connectLive(d).then(function () {
        return Object.assign({}, d, { success: true, action: 'connected' });
      });
    });
  }

  global.CgLiveKitVoice = {
    connectLive: connectLive,
    disconnect: disconnect,
    isConnected: isConnected,
    requestToken: requestToken,
    toggleVoice: toggleVoice,
    activePerformerId: function () {
      return activePerformerId;
    },
  };
})(typeof window !== 'undefined' ? window : this);

;(function () {
  if (typeof window === 'undefined' || !window.ErrorManager || typeof window.ErrorManager.logJSError !== 'function') return;
  var source = 'camgirls-livekit-voice.js';
  window.addEventListener('error', function (event) {
    var file = (event && event.filename) || '';
    if (file.indexOf(source) === -1) return;
    window.ErrorManager.logJSError(event.error || new Error(event.message || 'script error'), { source: source, context: 'window_error' });
  });
})();
