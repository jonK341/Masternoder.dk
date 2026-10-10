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

  var state = {
    recorder: null,
    stream: null,
    active: false,
    bound: false,
    uploadChain: Promise.resolve(),
    chunksSent: 0,
    canvasTimer: null,
  };

  function $(id) {
    return document.getElementById(id);
  }

  function setStatus(msg) {
    var el =
      $("f5-ingest-status") || $("f5-status") || $("yt-stream-status");
    if (el) el.textContent = msg || "";
  }

  function setIngestActive(on) {
    window.__f5IngestActive = !!on;
    if (document.body && document.body.classList) {
      document.body.classList.toggle("f5-ingest-active", !!on);
    }
  }

  function isNoObsClick(target) {
    if (!target || !target.closest) return null;
    return target.closest("#f5-no-obs-stream, #yt-stream-no-obs, [data-no-obs-stream]");
  }

  function stopCapture() {
    setIngestActive(false);
    state.active = false;
    if (state.canvasTimer) {
      clearInterval(state.canvasTimer);
      state.canvasTimer = null;
    }
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
    state.uploadChain = Promise.resolve();
    fetch(API_STOP, { method: "POST", credentials: "same-origin" }).catch(function () {});
  }

  var uploadFails = 0;

  function uploadChunk(blob) {
    if (!blob || !blob.size) return Promise.resolve();
    state.uploadChain = state.uploadChain.then(function () {
      return fetch(API_WEBM, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": blob.type || "application/octet-stream" },
        body: blob,
      })
        .then(function (r) {
          return r.text().then(function (text) {
            var d = {};
            try {
              d = JSON.parse(text);
            } catch (e) {
              d = { success: false, error: "http_" + r.status };
            }
            return { r: r, d: d };
          });
        })
        .then(function (pair) {
          var r = pair.r;
          var d = pair.d;
          if (!r.ok || !d.success) {
            uploadFails += 1;
            if (uploadFails <= 5) {
              setStatus(
                "Upload fejl: " + (d.error || d.hint || r.status) + " — prøv No OBS igen."
              );
            }
            throw new Error(d.error || "upload_failed");
          }
          uploadFails = 0;
          state.chunksSent += 1;
          if (state.chunksSent === 1) {
            setStatus("Første video-chunk sendt — vent 10–30 sek. i Studio (Masternoder2-nøgle).");
          } else if (state.chunksSent % 10 === 0) {
            setStatus("Sender stadig (" + state.chunksSent + " chunks) — tjek Studio forhåndsvisning.");
          }
        });
    });
    return state.uploadChain.catch(function (e) {
      if (e && e.message && e.message !== "upload_failed") {
        uploadFails += 1;
        if (uploadFails <= 5) setStatus("Netværksfejl mod server ingest — " + e.message);
      }
    });
  }

  function pickMimeType() {
    var candidates = [
      "video/webm;codecs=vp8,opus",
      "video/webm;codecs=vp9,opus",
      "video/webm",
    ];
    for (var i = 0; i < candidates.length; i++) {
      if (MediaRecorder.isTypeSupported(candidates[i])) return candidates[i];
    }
    return "video/webm";
  }

  function startCanvasIngest() {
    state.chunksSent = 0;
    state.uploadChain = Promise.resolve();
    return fetch(API_START, { method: "POST", credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (!d.success) {
          setStatus((d.hint || d.error || "Ingest start failed") + "");
          throw new Error(d.error || "start_failed");
        }
        var canvas = $("f5-canvas");
        if (!canvas || !canvas.toBlob) {
          setStatus("Canvas mangler — falder tilbage til fane-deling.");
          return startTabCapture();
        }
        state.active = true;
        setIngestActive(true);
        state.canvasTimer = setInterval(function () {
          if (!state.active) return;
          try {
            canvas.toBlob(
              function (blob) {
                if (blob && blob.size) uploadChunk(blob);
              },
              "image/jpeg",
              0.78
            );
          } catch (e) {
            /* ignore tainted canvas */
          }
        }, 66);
        setStatus(
          "Sender til YouTube — hold denne fane åben 30+ sek. Åbn Studio livestreaming (ikke «Administrer streams»): " +
            "studio.youtube.com/video/-iSYSBSn_8E/livestreaming · nøgle Masternoder2."
        );
        if (document.body && document.body.classList) {
          document.body.classList.add("f5-stream");
        }
        window.scrollTo(0, 0);
      });
  }

  function startTabCapture() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
      setStatus("Browser tab capture not supported — use Chrome/Edge on desktop.");
      return Promise.reject(new Error("no_getDisplayMedia"));
    }
    state.chunksSent = 0;
    state.uploadChain = Promise.resolve();
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
          video: { frameRate: 30, displaySurface: "browser" },
          audio: false,
          preferCurrentTab: true,
        });
      })
      .then(function (mediaStream) {
        state.stream = mediaStream;
        var mime = pickMimeType();
        state.recorder = new MediaRecorder(mediaStream, {
          mimeType: mime,
          videoBitsPerSecond: 2800000,
        });
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
        state.recorder.start(400);
        setStatus(
          "Deler fane → server → YouTube. Vælg DENNE monitor-fane (ikke Studio). Studio: streamnøgle Masternoder2."
        );
      });
  }

  function runNoObs() {
    setStatus("Starter canvas → YouTube…");
    fetch(API_FIX, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "fix_no_obs",
        approved: true,
        go_live: false,
        start_ingest: false,
      }),
    }).catch(function () {});
    return startCanvasIngest();
  }

  function assignAndFixNoObs() {
    return runNoObs();
  }

  function onNoObsClick(btn) {
    if (!btn || btn.disabled) return;
    btn.disabled = true;
    document.querySelectorAll("[data-no-obs-stream]").forEach(function (b) {
      b.disabled = true;
    });
    runNoObs()
      .catch(function (e) {
        setStatus((e && e.message) || "No-OBS start failed");
      })
      .finally(function () {
        document.querySelectorAll("[data-no-obs-stream]").forEach(function (b) {
          b.disabled = false;
        });
      });
  }

  function wireButton(id) {
    var el = $(id);
    if (!el || el.__f5NoObsBound) return;
    el.__f5NoObsBound = true;
    el.addEventListener("click", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      onNoObsClick(el);
    });
  }

  function bindDelegation() {
    if (state.bound) return;
    state.bound = true;
    document.addEventListener(
      "click",
      function (ev) {
        var noObs = isNoObsClick(ev.target);
        if (noObs) {
          ev.preventDefault();
          ev.stopPropagation();
          onNoObsClick(noObs);
          return;
        }
        var stopBtn = ev.target.closest("#f5-ingest-stop, [data-ingest-stop]");
        if (stopBtn) {
          ev.preventDefault();
          stopCapture();
          setStatus("Ingest stopped.");
        }
      },
      true
    );
  }

  function bind() {
    bindDelegation();
    wireButton("f5-no-obs-stream");
    wireButton("f5-no-obs-fixed");
    var stopFixed = $("f5-ingest-stop-fixed");
    if (stopFixed && !stopFixed.__f5StopBound) {
      stopFixed.__f5StopBound = true;
      stopFixed.addEventListener("click", function (ev) {
        ev.preventDefault();
        stopCapture();
        setStatus("Ingest stoppet.");
      });
    }
    fetch(API_STATUS, { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        var ing = d.ingest || {};
        if (!ing.stream_key_configured) {
          setStatus(
            "Kopiér streamnøgle «Masternoder2» fra Studio → YOUTUBE_STREAM_KEY på server — klik derefter No OBS."
          );
        } else if (ing.stream_key_profile && ing.stream_key_profile !== "Masternoder2") {
          setStatus(
            "Server stream-profil: " +
              ing.stream_key_profile +
              " — i Studio skal dropdown matche, ellers Ingen data."
          );
        }
      })
      .catch(function () {});
  }

  window.MNFleetYoutubeIngest = {
    start: runNoObs,
    startTab: startTabCapture,
    stop: stopCapture,
    assignAndFix: runNoObs,
    bind: bindDelegation,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
