/**
 * Fleet livestream GPS + GPRS — browser GPS, Google Maps + OSM embeds, go-live agent assign.
 */
(function () {
  "use strict";

  var API_GEO = "/api/exchange/fleet-stream/geo/public";
  var API_PING = "/api/exchange/fleet-stream/geo/ping";
  var API_GO_LIVE = "/api/exchange/fleet-stream/go-live";

  var state = {
    snapshot: null,
    markers: [],
    watchId: null,
    timers: [],
    goLiveDone: false,
  };

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function qs(name) {
    var m = new RegExp("[?&]" + name + "=([^&]*)").exec(window.location.search);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function guestKey() {
    try {
      var g = localStorage.getItem("mn_fleet_guest");
      if (!g) {
        g = "g_" + Math.random().toString(36).slice(2, 12);
        localStorage.setItem("mn_fleet_guest", g);
      }
      return g;
    } catch (e) {
      return "g_" + Date.now();
    }
  }

  function isStreamMode() {
    return qs("mode") === "stream" || qs("stream") === "1" || document.body.classList.contains("f5-stream");
  }

  function sendPing(lat, lon, accuracy, kind, source) {
    return fetch(API_PING, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-Fleet-Guest": guestKey(),
      },
      body: JSON.stringify({
        latitude: lat,
        longitude: lon,
        accuracy: accuracy,
        kind: kind || "gps",
        source: source || "browser_gps",
        guest_id: guestKey(),
      }),
    }).catch(function () {});
  }

  function startBrowserGps() {
    if (!navigator.geolocation) return;
    if (state.watchId != null) return;
    state.watchId = navigator.geolocation.watchPosition(
      function (pos) {
        sendPing(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy, "gps", "browser_gps");
      },
      function () {},
      { enableHighAccuracy: true, maximumAge: 12000, timeout: 15000 }
    );
  }

  function renderPanel(snap) {
    var panel = document.getElementById("f5-geo-panel");
    if (!panel || !snap || !snap.success) return;
    var c = snap.counts || {};
    var center = snap.center || {};
    panel.innerHTML =
      '<div class="f5-geo-stats">' +
      '<span class="f5-geo-pill gps">GPS ' + (c.gps || 0) + "</span>" +
      '<span class="f5-geo-pill gprs">GPRS ' + (c.gprs || 0) + "</span>" +
      '<span class="f5-geo-coords">' +
      esc(center.latitude) +
      ", " +
      esc(center.longitude) +
      "</span></div>" +
      '<div class="f5-geo-map-tabs" role="tablist">' +
      '<button type="button" class="f5-geo-map-tab is-active" data-map="google">Google Maps</button>' +
      '<button type="button" class="f5-geo-map-tab" data-map="osm">Direct (OSM)</button>' +
      "</div>" +
      '<div class="f5-geo-map-frame" id="f5-geo-map-frame"></div>' +
      '<ul class="f5-geo-marker-list" id="f5-geo-marker-list"></ul>';

    var maps = snap.maps || {};
    var frame = document.getElementById("f5-geo-map-frame");
    function showMap(which) {
      if (!frame) return;
      var src = which === "osm" ? maps.osm_embed : maps.google_embed;
      if (!src) {
        frame.innerHTML = '<p class="f5-geo-muted">Map unavailable</p>';
        return;
      }
      frame.innerHTML =
        '<iframe title="' +
        (which === "osm" ? "OpenStreetMap" : "Google Maps") +
        '" src="' +
        esc(src) +
        '" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe>';
    }
    showMap("google");
    panel.querySelectorAll(".f5-geo-map-tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        panel.querySelectorAll(".f5-geo-map-tab").forEach(function (b) {
          b.classList.remove("is-active");
        });
        btn.classList.add("is-active");
        showMap(btn.getAttribute("data-map"));
      });
    });

    var list = document.getElementById("f5-geo-marker-list");
    if (list) {
      list.innerHTML = (snap.markers || [])
        .slice(0, 8)
        .map(function (m) {
          return (
            "<li><span class=\"f5-geo-kind " +
            esc(m.kind) +
            '">' +
            esc((m.kind || "").toUpperCase()) +
            "</span> " +
            esc(m.label || m.source || m.id) +
            " · " +
            esc(m.latitude) +
            ", " +
            esc(m.longitude) +
            "</li>"
          );
        })
        .join("");
    }

    var hud = document.getElementById("f5-geo-hud");
    if (hud) {
      hud.textContent =
        "GPS " + (c.gps || 0) + " · GPRS " + (c.gprs || 0) + " · center " + center.latitude + "," + center.longitude;
    }
  }

  function fetchGeo() {
    return fetch(API_GEO, { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (snap) {
        if (!snap || !snap.success) return snap;
        state.snapshot = snap;
        state.markers = snap.markers || [];
        renderPanel(snap);
        if (window.F5MonitorGeoHook) window.F5MonitorGeoHook(snap);
        return snap;
      });
  }

  function goLive() {
    if (state.goLiveDone) return Promise.resolve();
    return fetch(API_GO_LIVE, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        state.goLiveDone = true;
        if (d.geo) {
          state.snapshot = d.geo;
          state.markers = d.geo.markers || [];
          renderPanel(d.geo);
        }
        var status = document.getElementById("f5-status");
        if (status && d.assign && d.assign.success) {
          status.textContent = "YouTube stream agents assigned · GPS/GPRS live";
        }
        if (status && d.discord && d.discord.success) {
          status.textContent += " · Discord main chat updated";
        }
        document.dispatchEvent(new CustomEvent("mn:fleet-go-live", { detail: d }));
        return d;
      })
      .catch(function () {});
  }

  function init() {
    fetchGeo().then(function (snap) {
      if (!snap || !snap.enabled) return;
      startBrowserGps();
      var gpsMs = (snap.poll_ms && snap.poll_ms.gps) || 15000;
      var gprsMs = (snap.poll_ms && snap.poll_ms.gprs) || 20000;
      state.timers.push(setInterval(fetchGeo, gprsMs));
      state.timers.push(
        setInterval(function () {
          if (!navigator.geolocation) return;
          navigator.geolocation.getCurrentPosition(
            function (pos) {
              sendPing(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy, "gps", "browser_gps");
            },
            function () {},
            { maximumAge: gpsMs, timeout: 12000 }
          );
        }, gpsMs)
      );
      if (isStreamMode() && snap.auto_assign_agent_on_stream !== false) {
        goLive();
      }
    });
  }

  window.F5StreamGeo = {
    getMarkers: function () {
      return state.markers || [];
    },
    refresh: fetchGeo,
    goLive: goLive,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
