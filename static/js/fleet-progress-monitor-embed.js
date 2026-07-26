/**
 * Homepage embed — lazy-loads 5D fleet monitor iframe (same-origin, no sensitive query params).
 */
(function () {
  "use strict";

  function init() {
    var root = document.getElementById("fp-fleet-5d-embed");
    if (!root) return;

    var open = document.getElementById("fp-fleet-5d-open");
    if (open) {
      open.href = "/fleet-progress-monitor/?mode=stream";
    }

    var iframe = document.createElement("iframe");
    iframe.title = "5D Fleet Progress Monitor";
    iframe.loading = "lazy";
    iframe.referrerPolicy = "same-origin";
    iframe.sandbox = "allow-scripts allow-same-origin";
    iframe.src = "/fleet-progress-monitor/?mode=stream&embed=1";

    root.appendChild(iframe);

    fetch("/api/exchange/fleet-progress-monitor/public?light=1")
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (!d.success) return;
        var pill = document.getElementById("fp-fleet-5d-pill");
        if (pill && d.progression) {
          pill.textContent =
            "Cmd Lv " + d.progression.commander_level + " · " + d.progression.fleet_total_xp + " XP · audience-safe";
        }
      })
      .catch(function () {});
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
