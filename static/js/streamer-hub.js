/**
 * Streamer hub — embed latest 5D fleet monitor + Camgirl co-host strip.
 */
(function () {
  "use strict";

  var MONITOR_API = "/api/exchange/fleet-progress-monitor/public?light=1";
  var PERFORMERS_API = "/api/camgirls/performers";
  var EPISODES_API = "/api/podcast/episodes";

  function $(id) {
    return document.getElementById(id);
  }

  function qs(name) {
    var m = new RegExp("[?&]" + name + "=([^&]*)").exec(window.location.search);
    return m ? decodeURIComponent(m[1]) : "";
  }

  var obsMode = qs("obs") === "1" || qs("obs") === "true";

  function absoluteUrl(path) {
    return window.location.origin + path;
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    return Promise.reject(new Error("clipboard unavailable"));
  }

  function setStatus(msg) {
    var el = $("streamer-status");
    if (el) el.textContent = msg || "";
  }

  function loadMonitorSummary() {
    return fetch(MONITOR_API, { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (!d || !d.success) throw new Error("monitor_unavailable");
        var ps = d.progression || {};
        var fl = d.fleet || {};
        setStatus(
          "Cmd Lv " + (ps.commander_level || 1) + " · " + (ps.fleet_total_xp || 0) +
          " XP · " + (fl.bot_count || 0) + " fleet bots · " +
          (d.paper_mode ? "paper" : "live") + " telemetry"
        );
        return d;
      })
      .catch(function () {
        setStatus("5D monitor API slow or offline — iframe may still load.");
      });
  }

  function loadHosts() {
    var wrap = $("streamer-hosts");
    if (!wrap) return;
    fetch(PERFORMERS_API, { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        var rows = (d && d.performers) || [];
        if (!rows.length) {
          wrap.innerHTML = "<span class='streamer-meta'>Camgirl co-hosts load in the stream voice dock.</span>";
          return;
        }
        wrap.innerHTML =
          "<span class='streamer-meta' style='margin-right:8px'>Co-hosts:</span>" +
          rows
            .slice(0, 5)
            .map(function (p) {
              return (
                '<span class="streamer-host">' +
                '<img src="' + (p.avatar_url || "/static/camgirls/avatar-demo.svg") + '" alt="" loading="lazy" />' +
                "<span>" + (p.display_name || "Host") + "</span></span>"
              );
            })
            .join("");
      })
      .catch(function () {
        wrap.innerHTML = "";
      });
  }

  function bindChrome() {
    var obsUrl = absoluteUrl("/streamer/?obs=1");
    var cleanUrl = absoluteUrl("/fleet-stream/");

    $("streamer-copy-obs") &&
      $("streamer-copy-obs").addEventListener("click", function () {
        copyText(obsUrl)
          .then(function () {
            setStatus("Copied OBS URL (chrome hidden).");
          })
          .catch(function () {
            setStatus(obsUrl);
          });
      });

    $("streamer-copy-clean") &&
      $("streamer-copy-clean").addEventListener("click", function () {
        copyText(cleanUrl)
          .then(function () {
            setStatus("Copied clean fleet stream URL.");
          })
          .catch(function () {
            setStatus(cleanUrl);
          });
      });

    var toggle = $("streamer-toggle-chrome");
    if (toggle) {
      toggle.addEventListener("click", function () {
        document.body.classList.toggle("streamer-obs");
        var hidden = document.body.classList.contains("streamer-obs");
        toggle.setAttribute("aria-pressed", hidden ? "true" : "false");
        toggle.textContent = hidden ? "Show bar" : "OBS hide bar";
      });
    }
  }

  function loadPodcast() {
    var meta = $("streamer-podcast-meta");
    var audio = $("streamer-podcast-audio");
    var queueBtn = $("streamer-podcast-queue");
    if (!audio) return;

    fetch(EPISODES_API, { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        var eps = (d && d.episodes) || [];
        if (!eps.length) {
          if (meta) meta.textContent = "No episodes yet — open Podcast to generate.";
          return;
        }
        var ep = eps[0];
        var playUrl = ep.audio_play_url || ep.audio_url || ("/api/podcast/episodes/" + ep.id + "/audio");
        audio.src = playUrl;
        if (meta) {
          meta.textContent =
            (ep.title || "Latest episode") +
            (ep.channel_name ? " · " + ep.channel_name : "") +
            " — verified sound";
        }
        if (queueBtn) {
          queueBtn.hidden = false;
          queueBtn.onclick = function () {
            try {
              audio.play();
            } catch (_) {}
            setStatus("Podcast queued — audio plays alongside the 5D monitor.");
          };
        }
      })
      .catch(function () {
        if (meta) meta.textContent = "Podcast API offline — use /podcast for full hub.";
      });
  }

  function init() {
    if (obsMode) document.body.classList.add("streamer-obs");
    bindChrome();
    loadHosts();
    loadPodcast();
    loadMonitorSummary();
    setInterval(loadMonitorSummary, 60000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
