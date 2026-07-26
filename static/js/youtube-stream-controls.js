/**
 * YouTube stream agent controls — fleet 5D monitor + OBS playbook.
 */
(function () {
  "use strict";

  var API_CONTROLS = "/api/exchange/youtube-stream/controls";
  var API_ASSIGN = "/api/exchange/youtube-stream/assign-agent";
  var API_ACTION = "/api/exchange/youtube-stream/agent-action";
  var API_START = "/api/exchange/fleet-stream/start-youtube";

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function qs(name) {
    var m = new RegExp("[?&]" + name + "=([^&]*)").exec(window.location.search);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    return Promise.reject(new Error("clipboard unavailable"));
  }

  function mountTarget() {
    return (
      $("youtube-stream-panel") ||
      $("f5-youtube-stream") ||
      document.querySelector("[data-youtube-stream-mount]")
    );
  }

  function renderPanel(el, data) {
    if (!el || !data || !data.success) return;
    var mon = data.monitor || {};
    var scenes = data.obs_scenes || [];
    var checklist = data.checklist || [];
    var skills = data.skill_set || [];

    var enc = data.encoder || {};
    var encSteps = (enc.studio_edit_da || []).concat(enc.youtube_live_setup || []).slice(0, 8);

    el.innerHTML =
      '<div class="yt-stream-panel">' +
      '<div class="yt-stream-encoder-warn">' +
      "<strong>Ingen data i Studio?</strong> " +
      esc(
        "Rediger (titel) går ikke live alene — start OBS med streamnøgle + RTMP nedenfor."
      ) +
      "</div>" +
      '<div class="yt-stream-head">' +
      '<span class="yt-stream-kicker">▶️ YouTube agent</span>' +
      '<strong>' + esc(data.primary_agent || "youtube_stream_agent") + '</strong>' +
      '<p class="yt-stream-meta">OBS browser capture · 5D monitor · podcast co-host</p>' +
      (data.live_broadcast && data.live_broadcast.title
        ? '<p class="yt-stream-live-title"><span class="yt-stream-live-dot">LIVE</span> ' +
          esc(data.live_broadcast.title) +
          (data.live_broadcast.video_id ? ' · <code>' + esc(data.live_broadcast.video_id) + "</code>" : "") +
          "</p>"
        : "") +
      "</div>" +
      '<div class="yt-stream-urls">' +
      (data.live_broadcast && data.live_broadcast.watch_url
        ? '<a class="yt-stream-btn primary" href="' +
          esc(data.live_broadcast.watch_url) +
          '" target="_blank" rel="noopener">Open live watch</a>' +
          '<button type="button" class="yt-stream-btn" data-copy-url="' +
          esc(data.live_broadcast.watch_url) +
          '">Copy watch URL</button>'
        : "") +
      '<button type="button" class="yt-stream-btn primary" data-copy-url="' +
      esc(mon.stream_layout || "") +
      '">Copy YouTube layout URL</button>' +
      '<button type="button" class="yt-stream-btn" data-copy-url="' +
      esc(mon.obs_browser || "") +
      '">Copy OBS browser URL</button>' +
      '<a class="yt-stream-btn" href="' +
      esc(
        (data.live_broadcast && data.live_broadcast.studio_url) ||
          (data.youtube && data.youtube.studio_live_url) ||
          "https://studio.youtube.com/"
      ) +
      '" target="_blank" rel="noopener">YouTube Studio</a>' +
      '<a class="yt-stream-btn" href="' +
      esc((data.youtube && data.youtube.channel_url) || "https://youtube.com/@MasterNoder") +
      '" target="_blank" rel="noopener">Channel</a>' +
      "</div>" +
      '<div class="yt-stream-encoder">' +
      '<p class="yt-stream-label">OBS / RTMP (fix “Ingen data”)</p>' +
      '<button type="button" class="yt-stream-btn primary" data-copy-url="' +
      esc(enc.rtmp_server || "rtmp://a.rtmp.youtube.com/live2") +
      '">Copy RTMP server</button>' +
      '<button type="button" class="yt-stream-btn" data-copy-url="' +
      esc(enc.obs_browser_url || mon.stream_layout || "") +
      '">Copy browser source URL</button>' +
      "<p class=\"yt-stream-meta\">" +
      esc(enc.stream_key_note || "") +
      " · " +
      esc(enc.resolution || "1920x1080") +
      " · " +
      esc(String(enc.fps || 30)) +
      "fps · ~" +
      esc(String(enc.bitrate_kbps || 4500)) +
      " kbps</p>" +
      '<ul class="yt-stream-checklist yt-stream-encoder-steps">' +
      encSteps
        .map(function (line) {
          return "<li>" + esc(line) + "</li>";
        })
        .join("") +
      "</ul></div>" +
      '<ul class="yt-stream-checklist">' +
      checklist.map(function (line) {
        return "<li>" + esc(line) + "</li>";
      }).join("") +
      "</ul>" +
      (scenes.length
        ? '<div class="yt-stream-scenes"><p class="yt-stream-label">OBS scenes</p><ul>' +
          scenes
            .map(function (s) {
              return (
                "<li><strong>" +
                esc(s.label) +
                "</strong> · " +
                esc(s.source) +
                " · <code>" +
                esc(s.url_hint) +
                "</code></li>"
              );
            })
            .join("") +
          "</ul></div>"
        : "") +
      '<div class="yt-stream-skills"><p class="yt-stream-label">Agent skill set</p>' +
      skills
        .map(function (row) {
          var sk = (row.skills || []).join(", ");
          return '<span class="yt-stream-skill-chip">' + esc(row.agent_id) + ": " + esc(sk) + "</span>";
        })
        .join("") +
      "</div>" +
      '<div class="yt-stream-actions">' +
      '<button type="button" class="yt-stream-btn primary" id="yt-stream-start">Start stream (agent)</button>' +
      '<button type="button" class="yt-stream-btn primary" id="yt-stream-assign">Assign stream agents</button>' +
      '<button type="button" class="yt-stream-btn" id="yt-stream-preflight">Preflight URLs</button>' +
      '<button type="button" class="yt-stream-btn" id="yt-stream-narration">Narration line</button>' +
      "</div>" +
      '<p class="yt-stream-status" id="yt-stream-status"></p>' +
      '<p class="yt-stream-narration" id="yt-stream-narration-line" hidden></p>' +
      "</div>";

    el.querySelectorAll("[data-copy-url]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var url = btn.getAttribute("data-copy-url") || "";
        copyText(url)
          .then(function () {
            setStatus(el, "Copied: " + url);
          })
          .catch(function () {
            setStatus(el, url);
          });
      });
    });

    var assignBtn = el.querySelector("#yt-stream-assign");
    var startBtn = el.querySelector("#yt-stream-start");
    if (startBtn) {
      startBtn.addEventListener("click", function () {
        startBtn.disabled = true;
        fetch(API_START, {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (d) {
            var ok = d.success && (d.session || d).assign;
            var aok = (d.session && d.session.assign && d.session.assign.success) || d.assign;
            setStatus(
              el,
              aok || d.success
                ? "Agent started — now Start streaming in OBS, then Go live in Studio."
                : d.error || "Start failed"
            );
          })
          .catch(function () {
            setStatus(el, "Start stream request failed.");
          })
          .finally(function () {
            startBtn.disabled = false;
          });
      });
    }
    if (assignBtn) {
      assignBtn.addEventListener("click", function () {
        assignBtn.disabled = true;
        fetch(API_ASSIGN, {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (d) {
            setStatus(el, d.success ? "Agents assigned to your profile." : d.error || "Assign failed");
          })
          .catch(function () {
            setStatus(el, "Assign request failed.");
          })
          .finally(function () {
            assignBtn.disabled = false;
          });
      });
    }

    var preBtn = el.querySelector("#yt-stream-preflight");
    if (preBtn) {
      preBtn.addEventListener("click", function () {
        preBtn.disabled = true;
        fetch(API_ACTION, {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "preflight_urls", approved: true }),
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (d) {
            var checks = d.checks || [];
            var ok = checks.filter(function (c) {
              return c.ok;
            }).length;
            setStatus(el, "Preflight: " + ok + "/" + checks.length + " URLs OK");
          })
          .catch(function () {
            setStatus(el, "Preflight failed.");
          })
          .finally(function () {
            preBtn.disabled = false;
          });
      });
    }

    var narBtn = el.querySelector("#yt-stream-narration");
    if (narBtn) {
      narBtn.addEventListener("click", function () {
        fetch(API_ACTION, {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "narration_line" }),
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (d) {
            var lineEl = el.querySelector("#yt-stream-narration-line");
            if (lineEl && d.line) {
              lineEl.hidden = false;
              lineEl.textContent = d.line;
            }
            setStatus(el, "Narration loaded — use with Camgirl voice on monitor.");
          })
          .catch(function () {
            setStatus(el, "Narration unavailable.");
          });
      });
    }
  }

  function setStatus(root, msg) {
    var st = root.querySelector("#yt-stream-status");
    if (st) st.textContent = msg || "";
  }

  function init() {
    var target = mountTarget();
    if (!target) return;
    var streamOnly = target.getAttribute("data-stream-only") === "1";
    var streamMode = qs("mode") === "stream" || qs("stream") === "1";
    if (streamOnly && !streamMode) {
      target.hidden = true;
      return;
    }
    target.hidden = false;
    fetch(API_CONTROLS, { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        renderPanel(target, d);
      })
      .catch(function () {
        target.innerHTML = '<p class="yt-stream-meta">YouTube stream controls offline.</p>';
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
