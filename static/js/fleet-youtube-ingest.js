/**
 * No-OBS YouTube ingest — share monitor tab → server ffmpeg → RTMP.
 */
(function () {
  "use strict";

  var API_START = "/api/exchange/fleet-stream/ingest/start";
  var API_STOP = "/api/exchange/fleet-stream/ingest/stop";
  var API_WEBM = "/api/exchange/fleet-stream/ingest/webm";
  var API_FIX = "/api/exchange/youtube-stream/agent-action";
  var API_STATUS = "/api/exchange/fleet-stream/ingest/status";

  var state = { recorder: null, stream: null, active: false };

  function $(id) {
    return document.getElementById(id);
  }

  function setStatus(msg) {
    var el = $("f5-ingest-status") || $("yt-stream-status");
    if (el) el.textContent = msg || "";
  }

  function stopCapture() {
    state.active = false;
    if (state.recorder && state.recorder.state !== "inactive") {
      try {
        state.recorder.stop();
      } catch (e) {
        /* ignore */
      }
    }
    if (state.stream) {
      state.stream.getTracks().forEach(function (t) {
        t.stop();
      });
    }
    state.recorder = null;
    state.stream = null;
    fetch(API_STOP, { method: "POST", credentials: "same-origin" }).catch(function () {});
  }

  function uploadChunk(blob) {
    if (!blob || !blob.size) return Promise.resolve();
    return fetch(API_WEBM, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "video/webm" },
      body: blob,
    }).catch(function () {});
  }

  function startTabCapture() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
      setStatus("Browser tab capture not supported — use Chrome/Edge on desktop.");
      return Promise.reject(new Error("no_getDisplayMedia"));
    }
    return fetch(API_START, { method: "POST", credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (!d.success) {
          setStatus((d.hint || d.error || "Ingest start failed") + "");
          throw new Error(d.error || "start_failed");
        }
        return navigator.mediaDevices.getDisplayMedia({
          video: { frameRate: 30 },
          audio: true,
        });
      })
      .then(function (mediaStream) {
        state.stream = mediaStream;
        var mime = MediaRecorder.isTypeSupported("video/webm;codecs=vp9,opus")
          ? "video/webm;codecs=vp9,opus"
          : "video/webm";
        state.recorder = new MediaRecorder(mediaStream, { mimeType: mime, videoBitsPerSecond: 4500000 });
        state.recorder.ondataavailable = function (ev) {
          if (ev.data && ev.data.size && state.active) uploadChunk(ev.data);
        };
        state.recorder.onstop = function () {
          stopCapture();
        };
        mediaStream.getVideoTracks()[0].addEventListener("ended", function () {
          stopCapture();
        });
        state.active = true;
        state.recorder.start(1000);
        setStatus("Sending tab to YouTube — when Studio shows video, click Go live.");
      });
  }

  function assignAndFixNoObs() {
    return fetch(API_FIX, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "fix_no_obs",
        approved: true,
        go_live: true,
        start_ingest: false,
      }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (d.assign && d.assign.success) {
          setStatus("YouTube agent assigned — starting tab capture…");
        }
        return startTabCapture();
      })
      .catch(function (e) {
        setStatus(e.message || "No-OBS fix failed");
      });
  }

  function bind() {
    var btn = $("f5-no-obs-stream") || $("yt-stream-no-obs");
    if (btn) {
      btn.addEventListener("click", function () {
        btn.disabled = true;
        assignAndFixNoObs().finally(function () {
          btn.disabled = false;
        });
      });
    }
    var stopBtn = $("f5-ingest-stop");
    if (stopBtn) {
      stopBtn.addEventListener("click", function () {
        stopCapture();
        setStatus("Ingest stopped.");
      });
    }
    fetch(API_STATUS, { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        var ing = d.ingest || {};
        if (!ing.stream_key_configured) {
          setStatus("Add YOUTUBE_STREAM_KEY on server (.env) from Studio streamnøgle — then click No OBS stream.");
        }
      })
      .catch(function () {});
  }

  window.MNFleetYoutubeIngest = {
    start: startTabCapture,
    stop: stopCapture,
    assignAndFix: assignAndFixNoObs,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
