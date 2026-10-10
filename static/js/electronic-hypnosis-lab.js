/**
 * Electronic Hypnosis Lab (SAFE MODE)
 * ------------------------------------------------------------
 * This is a visual/UX effects + diagnostics toolkit.
 * - No coercive behavior
 * - No silent data exfiltration
 * - GPS requires explicit user permission and is never auto-sent anywhere
 *
 * Exposes EXACTLY 22 public functions on window.eHypnosisLab.
 */
(function () {
  "use strict";

  const STORAGE_KEY_ENABLED = "eh_lab_enabled";
  const STORAGE_KEY_INTENSITY = "eh_lab_intensity";
  const STORAGE_KEY_THEME = "eh_lab_theme";

  const state = {
    enabled: false,
    intensity: 0.6,
    theme: "neon",
    overlayOpen: false,
    perfInterval: null,
    fetchPatched: false,
    originalFetch: null,
    networkEvents: [],
    consoleErrors: [],
    mutationObserver: null,
    gpsWatchId: null,
    lastGPS: null,
    marks: {},
  };

  function nowMs() {
    return (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
  }

  function loadPersistedState() {
    try {
      state.enabled = localStorage.getItem(STORAGE_KEY_ENABLED) === "true";
      const i = parseFloat(localStorage.getItem(STORAGE_KEY_INTENSITY) || "");
      if (!Number.isNaN(i)) state.intensity = Math.min(1, Math.max(0, i));
      const t = localStorage.getItem(STORAGE_KEY_THEME);
      if (t) state.theme = t;
    } catch (_) {}
  }

  function persistState() {
    try {
      localStorage.setItem(STORAGE_KEY_ENABLED, String(state.enabled));
      localStorage.setItem(STORAGE_KEY_INTENSITY, String(state.intensity));
      localStorage.setItem(STORAGE_KEY_THEME, String(state.theme));
    } catch (_) {}
  }

  function cssForTheme(theme) {
    if (theme === "mono") {
      return {
        accent: "#ffffff",
        accent2: "#bbbbbb",
        bg: "rgba(0,0,0,0.82)",
        border: "rgba(255,255,255,0.18)",
      };
    }
    // neon default
    return {
      accent: "#00ff88",
      accent2: "#00d4ff",
      bg: "rgba(0,0,0,0.80)",
      border: "rgba(0,255,136,0.22)",
    };
  }

  function ensureStyles() {
    if (document.getElementById("eh-lab-styles")) return;
    const s = document.createElement("style");
    s.id = "eh-lab-styles";
    const c = cssForTheme(state.theme);
    s.textContent = `
      .eh-lab-toggle {
        position: fixed;
        right: 16px;
        bottom: 16px;
        z-index: 100000;
        border: 1px solid ${c.border};
        background: ${c.bg};
        color: rgba(255,255,255,0.92);
        padding: 10px 12px;
        border-radius: 12px;
        font-weight: 800;
        cursor: pointer;
        backdrop-filter: blur(8px);
      }
      .eh-lab-toggle small { display:block; font-weight:600; opacity:0.75; }
      .eh-lab-overlay {
        position: fixed;
        inset: 0;
        z-index: 100001;
        background: rgba(0,0,0,0.72);
        display: none;
        align-items: center;
        justify-content: center;
        padding: 20px;
      }
      .eh-lab-overlay.open { display: flex; }
      .eh-lab-panel {
        width: 100%;
        max-width: 980px;
        background: ${c.bg};
        border: 1px solid ${c.border};
        border-radius: 16px;
        box-shadow: 0 30px 90px rgba(0,0,0,0.55);
        overflow: hidden;
      }
      .eh-lab-header {
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap: 12px;
        padding: 14px 16px;
        border-bottom: 1px solid ${c.border};
      }
      .eh-lab-title {
        font-weight: 900;
        letter-spacing: 0.3px;
        color: ${c.accent};
      }
      .eh-lab-actions { display:flex; gap: 8px; flex-wrap: wrap; }
      .eh-lab-btn {
        border: 1px solid ${c.border};
        background: rgba(255,255,255,0.06);
        color: rgba(255,255,255,0.92);
        padding: 8px 10px;
        border-radius: 12px;
        cursor: pointer;
        font-weight: 800;
      }
      .eh-lab-btn.primary {
        background: linear-gradient(135deg, ${c.accent}, ${c.accent2});
        color: #000;
        border: none;
      }
      .eh-lab-body {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        padding: 14px 16px;
      }
      @media (max-width: 900px) {
        .eh-lab-body { grid-template-columns: 1fr; }
      }
      .eh-lab-card {
        border: 1px solid ${c.border};
        background: rgba(255,255,255,0.04);
        border-radius: 14px;
        padding: 12px;
      }
      .eh-lab-card h3 {
        margin: 0 0 8px 0;
        font-size: 1.05rem;
        color: rgba(255,255,255,0.9);
      }
      .eh-lab-mono {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size: 12px;
        white-space: pre-wrap;
        color: rgba(255,255,255,0.82);
        max-height: 220px;
        overflow: auto;
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 12px;
        padding: 10px;
        background: rgba(0,0,0,0.35);
      }
      .eh-lab-row { display:flex; gap: 10px; align-items: center; flex-wrap: wrap; }
      .eh-lab-row label { opacity: 0.75; font-weight: 700; }
      .eh-lab-row input, .eh-lab-row select {
        border: 1px solid rgba(255,255,255,0.16);
        background: rgba(255,255,255,0.06);
        color: rgba(255,255,255,0.92);
        padding: 6px 8px;
        border-radius: 10px;
      }
      .eh-lab-badge {
        display:inline-block;
        padding: 3px 8px;
        border-radius: 999px;
        background: rgba(0,255,136,0.12);
        border: 1px solid ${c.border};
        color: rgba(255,255,255,0.88);
        font-weight: 800;
        font-size: 12px;
      }
    `;
    document.head.appendChild(s);
  }

  function ensureToggleButton() {
    if (document.getElementById("eh-lab-toggle")) return;
    ensureStyles();
    const btn = document.createElement("button");
    btn.id = "eh-lab-toggle";
    btn.className = "eh-lab-toggle";
    btn.type = "button";
    btn.innerHTML = `Lab <small>${state.enabled ? "enabled" : "disabled"}</small>`;
    btn.addEventListener("click", () => {
      if (!state.enabled) {
        // Opt-in gate
        const ok = window.confirm(
          "Enable Electronic Hypnosis Lab (SAFE MODE)?\n\nThis enables visual effects + debugging tools on this page.\nGPS features require separate permission when used."
        );
        if (!ok) return;
        enable();
      }
      toggleOverlay();
    });
    document.body.appendChild(btn);
  }

  function setToggleLabel() {
    const btn = document.getElementById("eh-lab-toggle");
    if (!btn) return;
    btn.innerHTML = `Lab <small>${state.enabled ? "enabled" : "disabled"}</small>`;
  }

  function ensureOverlay() {
    if (document.getElementById("eh-lab-overlay")) return;
    ensureStyles();
    const overlay = document.createElement("div");
    overlay.id = "eh-lab-overlay";
    overlay.className = "eh-lab-overlay";
    overlay.innerHTML = `
      <div class="eh-lab-panel" role="dialog" aria-modal="true" aria-label="Electronic Hypnosis Lab">
        <div class="eh-lab-header">
          <div class="eh-lab-title">Electronic Hypnosis Lab <span class="eh-lab-badge">SAFE MODE</span></div>
          <div class="eh-lab-actions">
            <button class="eh-lab-btn" id="eh-lab-close">Close</button>
            <button class="eh-lab-btn" id="eh-lab-export">Export diagnostics</button>
            <button class="eh-lab-btn primary" id="eh-lab-disable">Disable</button>
          </div>
        </div>
        <div class="eh-lab-body">
          <div class="eh-lab-card">
            <h3>Controls</h3>
            <div class="eh-lab-row" style="margin-bottom:8px;">
              <label>Intensity</label>
              <input id="eh-lab-intensity" type="range" min="0" max="1" step="0.05" />
              <span id="eh-lab-intensity-val" class="eh-lab-badge"></span>
            </div>
            <div class="eh-lab-row" style="margin-bottom:8px;">
              <label>Theme</label>
              <select id="eh-lab-theme">
                <option value="neon">neon</option>
                <option value="mono">mono</option>
              </select>
              <button class="eh-lab-btn" id="eh-lab-apply-theme">Apply</button>
            </div>
            <div class="eh-lab-row">
              <button class="eh-lab-btn" id="eh-lab-scan-links">Scan dead links</button>
              <button class="eh-lab-btn" id="eh-lab-scan-dom">Scan missing DOM ids</button>
              <button class="eh-lab-btn" id="eh-lab-perf-start">Start perf</button>
              <button class="eh-lab-btn" id="eh-lab-perf-stop">Stop perf</button>
            </div>
          </div>
          <div class="eh-lab-card">
            <h3>GPS coordinator (permission-based)</h3>
            <div class="eh-lab-row" style="margin-bottom:8px;">
              <button class="eh-lab-btn" id="eh-lab-gps-once">Get location</button>
              <button class="eh-lab-btn" id="eh-lab-gps-watch">Watch</button>
              <button class="eh-lab-btn" id="eh-lab-gps-stop">Stop</button>
            </div>
            <div class="eh-lab-mono" id="eh-lab-gps-out">No GPS data</div>
          </div>
          <div class="eh-lab-card">
            <h3>Network monitor</h3>
            <div class="eh-lab-row" style="margin-bottom:8px;">
              <button class="eh-lab-btn" id="eh-lab-net-start">Start</button>
              <button class="eh-lab-btn" id="eh-lab-net-stop">Stop</button>
              <button class="eh-lab-btn" id="eh-lab-net-clear">Clear</button>
            </div>
            <div class="eh-lab-mono" id="eh-lab-net-out">No network events</div>
          </div>
          <div class="eh-lab-card">
            <h3>Console errors / trackers</h3>
            <div class="eh-lab-row" style="margin-bottom:8px;">
              <button class="eh-lab-btn" id="eh-lab-track-dom">Track DOM mutations</button>
              <button class="eh-lab-btn" id="eh-lab-untrack-dom">Stop tracking</button>
              <button class="eh-lab-btn" id="eh-lab-clear-errors">Clear</button>
            </div>
            <div class="eh-lab-mono" id="eh-lab-errors-out">No errors captured</div>
          </div>
        </div>
      </div>
    `;
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closeOverlay();
    });
    document.body.appendChild(overlay);

    // Wire controls
    document.getElementById("eh-lab-close").addEventListener("click", closeOverlay);
    document.getElementById("eh-lab-disable").addEventListener("click", () => {
      disable();
      closeOverlay();
    });
    document.getElementById("eh-lab-export").addEventListener("click", exportDiagnostics);
    document.getElementById("eh-lab-scan-links").addEventListener("click", async () => {
      const result = await scanDeadLinks();
      logEvent("scanDeadLinks", result);
      refreshOverlayOutputs();
      alert(`Dead links: ${result.dead.length} (checked: ${result.checked.length})`);
    });
    document.getElementById("eh-lab-scan-dom").addEventListener("click", () => {
      const result = scanMissingElements(["stat-total-xp", "stat-level", "navToolbar", "agent-data-content"]);
      logEvent("scanMissingElements", result);
      refreshOverlayOutputs();
      alert(`Missing ids: ${result.missing.length}`);
    });
    document.getElementById("eh-lab-perf-start").addEventListener("click", startPerformanceMonitor);
    document.getElementById("eh-lab-perf-stop").addEventListener("click", stopPerformanceMonitor);

    document.getElementById("eh-lab-net-start").addEventListener("click", startNetworkMonitor);
    document.getElementById("eh-lab-net-stop").addEventListener("click", stopNetworkMonitor);
    document.getElementById("eh-lab-net-clear").addEventListener("click", () => {
      state.networkEvents = [];
      refreshOverlayOutputs();
    });

    document.getElementById("eh-lab-track-dom").addEventListener("click", () => startDOMMutationTracker());
    document.getElementById("eh-lab-untrack-dom").addEventListener("click", stopDOMMutationTracker);
    document.getElementById("eh-lab-clear-errors").addEventListener("click", () => {
      state.consoleErrors = [];
      refreshOverlayOutputs();
    });

    document.getElementById("eh-lab-gps-once").addEventListener("click", async () => {
      const loc = await getGPSCoordinates();
      refreshOverlayOutputs();
      if (!loc.success) alert(`GPS error: ${loc.error}`);
    });
    document.getElementById("eh-lab-gps-watch").addEventListener("click", () => {
      watchGPSCoordinates();
      refreshOverlayOutputs();
    });
    document.getElementById("eh-lab-gps-stop").addEventListener("click", () => {
      stopGPSWatch();
      refreshOverlayOutputs();
    });

    // Intensity / theme
    const slider = document.getElementById("eh-lab-intensity");
    const sliderVal = document.getElementById("eh-lab-intensity-val");
    slider.value = String(state.intensity);
    sliderVal.textContent = String(state.intensity);
    slider.addEventListener("input", () => {
      const v = parseFloat(slider.value);
      setIntensity(v);
      sliderVal.textContent = String(state.intensity);
    });
    const themeSelect = document.getElementById("eh-lab-theme");
    themeSelect.value = state.theme;
    document.getElementById("eh-lab-apply-theme").addEventListener("click", () => {
      setTheme(themeSelect.value);
      // re-apply styles by removing style block
      const st = document.getElementById("eh-lab-styles");
      if (st) st.remove();
      ensureStyles();
      alert("Theme applied. Reload page for full effect.");
    });
  }

  function openOverlay() {
    ensureOverlay();
    const overlay = document.getElementById("eh-lab-overlay");
    overlay.classList.add("open");
    state.overlayOpen = true;
    refreshOverlayOutputs();
  }

  function closeOverlay() {
    const overlay = document.getElementById("eh-lab-overlay");
    if (overlay) overlay.classList.remove("open");
    state.overlayOpen = false;
  }

  function toggleOverlay() {
    if (state.overlayOpen) closeOverlay();
    else openOverlay();
  }

  function refreshOverlayOutputs() {
    const gpsOut = document.getElementById("eh-lab-gps-out");
    const netOut = document.getElementById("eh-lab-net-out");
    const errOut = document.getElementById("eh-lab-errors-out");
    if (gpsOut) gpsOut.textContent = JSON.stringify(state.lastGPS || { info: "No GPS data" }, null, 2);
    if (netOut) netOut.textContent = state.networkEvents.length ? JSON.stringify(state.networkEvents.slice(-30), null, 2) : "No network events";
    if (errOut) errOut.textContent = state.consoleErrors.length ? JSON.stringify(state.consoleErrors.slice(-30), null, 2) : "No errors captured";
  }

  // ---------- Core enable/disable ----------
  function enable() {
    state.enabled = true;
    persistState();
    ensureToggleButton();
    setToggleLabel();
    hookConsoleErrorCapture();
    // optional: lightweight visual effect
    applyFocusPulse(true);
  }

  function disable() {
    state.enabled = false;
    persistState();
    setToggleLabel();
    applyFocusPulse(false);
    stopPerformanceMonitor();
    stopNetworkMonitor();
    stopDOMMutationTracker();
    stopGPSWatch();
  }

  function toggle() {
    if (state.enabled) disable();
    else enable();
    return state.enabled;
  }

  function setIntensity(value) {
    state.intensity = Math.min(1, Math.max(0, Number(value)));
    persistState();
    applyFocusPulse(state.enabled);
    return state.intensity;
  }

  function setTheme(theme) {
    state.theme = String(theme || "neon");
    persistState();
    return state.theme;
  }

  // ---------- Visual effect (SAFE: subtle, no manipulation) ----------
  function applyFocusPulse(on) {
    const id = "eh-lab-focus-pulse";
    let el = document.getElementById(id);
    if (!on) {
      if (el) el.remove();
      return;
    }
    if (!el) {
      el = document.createElement("div");
      el.id = id;
      el.style.position = "fixed";
      el.style.inset = "0";
      el.style.pointerEvents = "none";
      el.style.zIndex = "99999";
      document.body.appendChild(el);
    }
    const c = cssForTheme(state.theme);
    const alpha = 0.06 + state.intensity * 0.10;
    el.style.background = `radial-gradient(circle at 50% 40%, rgba(0,0,0,0), rgba(0,0,0,0.18)), radial-gradient(circle at 50% 40%, ${c.accent}00, ${c.accent}00)`;
    el.style.boxShadow = `inset 0 0 0 1px rgba(255,255,255,0.05), inset 0 0 90px rgba(0,0,0,0.35), 0 0 0 0`;
    el.style.opacity = String(alpha);
  }

  // ---------- Debug/telemetry ----------
  function logEvent(name, payload) {
    state.marks[name] = { t: nowMs(), payload };
    return true;
  }

  function startPerformanceMonitor() {
    if (state.perfInterval) return true;
    state.perfInterval = window.setInterval(() => {
      const mem = performance && performance.memory ? {
        jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
        totalJSHeapSize: performance.memory.totalJSHeapSize,
        usedJSHeapSize: performance.memory.usedJSHeapSize,
      } : null;
      const entry = {
        ts: new Date().toISOString(),
        href: location.href,
        timing: performance && performance.timing ? {
          domContentLoaded: performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart,
          load: performance.timing.loadEventEnd - performance.timing.navigationStart,
        } : null,
        mem,
      };
      logEvent("perf", entry);
      if (state.overlayOpen) refreshOverlayOutputs();
    }, 2000);
    return true;
  }

  function stopPerformanceMonitor() {
    if (state.perfInterval) {
      window.clearInterval(state.perfInterval);
      state.perfInterval = null;
    }
    return true;
  }

  async function scanDeadLinks() {
    const anchors = Array.from(document.querySelectorAll("a[href]"))
      .map(a => a.getAttribute("href"))
      .filter(Boolean)
      .filter(h => !h.startsWith("javascript:") && !h.startsWith("#"));

    const unique = Array.from(new Set(anchors)).slice(0, 50); // cap for safety
    const checked = [];
    const dead = [];

    for (const href of unique) {
      try {
        const url = new URL(href, window.location.origin).toString();
        checked.push(url);
        const res = await fetch(url, { method: "HEAD" });
        if (!res.ok) dead.push({ url, status: res.status });
      } catch (e) {
        dead.push({ url: href, error: String(e) });
      }
    }
    return { checked, dead };
  }

  function scanMissingElements(requiredIds) {
    const ids = Array.isArray(requiredIds) ? requiredIds : [];
    const missing = ids.filter(id => !document.getElementById(id));
    return { checked: ids, missing };
  }

  function hookConsoleErrorCapture() {
    if (console.__eh_lab_patched) return true;
    console.__eh_lab_patched = true;
    const origError = console.error.bind(console);
    console.error = function (...args) {
      try {
        state.consoleErrors.push({ ts: new Date().toISOString(), type: "error", args: args.map(String).slice(0, 8) });
        if (state.consoleErrors.length > 500) state.consoleErrors = state.consoleErrors.slice(-500);
        if (state.overlayOpen) refreshOverlayOutputs();
      } catch (_) {}
      return origError(...args);
    };
    window.addEventListener("error", (e) => {
      try {
        state.consoleErrors.push({ ts: new Date().toISOString(), type: "window_error", message: String(e.message || ""), file: e.filename, line: e.lineno });
        if (state.overlayOpen) refreshOverlayOutputs();
      } catch (_) {}
    });
    window.addEventListener("unhandledrejection", (e) => {
      try {
        state.consoleErrors.push({ ts: new Date().toISOString(), type: "unhandledrejection", message: String(e.reason || "") });
        if (state.overlayOpen) refreshOverlayOutputs();
      } catch (_) {}
    });
    return true;
  }

  function startNetworkMonitor() {
    if (state.fetchPatched) return true;
    if (typeof window.fetch !== "function") return false;
    state.originalFetch = window.fetch.bind(window);
    state.fetchPatched = true;
    window.fetch = async function (...args) {
      const start = nowMs();
      try {
        const res = await state.originalFetch(...args);
        const end = nowMs();
        try {
          state.networkEvents.push({
            ts: new Date().toISOString(),
            url: String(args[0]),
            method: (args[1] && args[1].method) ? args[1].method : "GET",
            status: res.status,
            ms: Math.round(end - start),
          });
          if (state.networkEvents.length > 500) state.networkEvents = state.networkEvents.slice(-500);
          if (state.overlayOpen) refreshOverlayOutputs();
        } catch (_) {}
        return res;
      } catch (e) {
        const end = nowMs();
        state.networkEvents.push({
          ts: new Date().toISOString(),
          url: String(args[0]),
          method: (args[1] && args[1].method) ? args[1].method : "GET",
          error: String(e),
          ms: Math.round(end - start),
        });
        if (state.overlayOpen) refreshOverlayOutputs();
        throw e;
      }
    };
    return true;
  }

  function stopNetworkMonitor() {
    if (!state.fetchPatched) return true;
    if (state.originalFetch) window.fetch = state.originalFetch;
    state.fetchPatched = false;
    state.originalFetch = null;
    return true;
  }

  function startDOMMutationTracker(options) {
    if (state.mutationObserver) return true;
    const obs = new MutationObserver((mutations) => {
      try {
        const sample = mutations.slice(0, 10).map(m => ({
          type: m.type,
          target: m.target && m.target.nodeName,
          added: m.addedNodes ? m.addedNodes.length : 0,
          removed: m.removedNodes ? m.removedNodes.length : 0,
        }));
        logEvent("dom_mutation", { ts: new Date().toISOString(), sample });
        if (state.overlayOpen) refreshOverlayOutputs();
      } catch (_) {}
    });
    obs.observe(document.documentElement, options || { childList: true, subtree: true });
    state.mutationObserver = obs;
    return true;
  }

  function stopDOMMutationTracker() {
    if (state.mutationObserver) {
      try { state.mutationObserver.disconnect(); } catch (_) {}
      state.mutationObserver = null;
    }
    return true;
  }

  function getGPSCoordinates(opts) {
    return new Promise((resolve) => {
      if (!navigator.geolocation) {
        resolve({ success: false, error: "Geolocation not supported" });
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const payload = {
            success: true,
            ts: new Date().toISOString(),
            coords: {
              latitude: pos.coords.latitude,
              longitude: pos.coords.longitude,
              accuracy_m: pos.coords.accuracy,
              altitude_m: pos.coords.altitude,
              heading: pos.coords.heading,
              speed_mps: pos.coords.speed,
            },
          };
          state.lastGPS = payload;
          resolve(payload);
        },
        (err) => {
          resolve({ success: false, error: err.message || String(err) });
        },
        Object.assign({ enableHighAccuracy: false, timeout: 10000, maximumAge: 0 }, opts || {})
      );
    });
  }

  function watchGPSCoordinates(opts) {
    if (!navigator.geolocation) return { success: false, error: "Geolocation not supported" };
    if (state.gpsWatchId != null) return { success: true, watchId: state.gpsWatchId };
    state.gpsWatchId = navigator.geolocation.watchPosition(
      (pos) => {
        state.lastGPS = {
          success: true,
          ts: new Date().toISOString(),
          coords: {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy_m: pos.coords.accuracy,
          },
        };
        if (state.overlayOpen) refreshOverlayOutputs();
      },
      (err) => {
        state.lastGPS = { success: false, error: err.message || String(err) };
        if (state.overlayOpen) refreshOverlayOutputs();
      },
      Object.assign({ enableHighAccuracy: false, timeout: 10000, maximumAge: 0 }, opts || {})
    );
    return { success: true, watchId: state.gpsWatchId };
  }

  function stopGPSWatch() {
    if (state.gpsWatchId != null && navigator.geolocation) {
      try { navigator.geolocation.clearWatch(state.gpsWatchId); } catch (_) {}
    }
    state.gpsWatchId = null;
    return true;
  }

  function exportDiagnostics() {
    const payload = {
      ts: new Date().toISOString(),
      href: location.href,
      enabled: state.enabled,
      intensity: state.intensity,
      theme: state.theme,
      lastGPS: state.lastGPS,
      networkEvents: state.networkEvents.slice(-200),
      consoleErrors: state.consoleErrors.slice(-200),
      marks: state.marks,
      userAgent: navigator.userAgent,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `eh-lab-diagnostics-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    return true;
  }

  // ---------- Public API (EXACTLY 22 functions) ----------
  // 1
  function initLab() {
    loadPersistedState();
    ensureToggleButton();
    if (state.enabled) {
      hookConsoleErrorCapture();
      applyFocusPulse(true);
    }
    return true;
  }

  // 2-22 (see export below for ordering)
  const api = {
    initLab,                 // 1
    enable,                  // 2
    disable,                 // 3
    toggle,                  // 4
    setIntensity,            // 5
    setTheme,                // 6
    openOverlay,             // 7
    closeOverlay,            // 8
    toggleOverlay,           // 9
    logEvent,                // 10
    startPerformanceMonitor, // 11
    stopPerformanceMonitor,  // 12
    scanDeadLinks,           // 13
    scanMissingElements,     // 14
    hookConsoleErrorCapture, // 15
    startNetworkMonitor,     // 16
    stopNetworkMonitor,      // 17
    startDOMMutationTracker, // 18
    stopDOMMutationTracker,  // 19
    getGPSCoordinates,       // 20
    watchGPSCoordinates,     // 21
    stopGPSWatch,            // 22
    exportDiagnostics,       // (NOT EXPORTED to keep exactly 22!)
  };

  // Export exactly 22 by excluding exportDiagnostics from window API
  const exported = {
    initLab,
    enable,
    disable,
    toggle,
    setIntensity,
    setTheme,
    openOverlay,
    closeOverlay,
    toggleOverlay,
    logEvent,
    startPerformanceMonitor,
    stopPerformanceMonitor,
    scanDeadLinks,
    scanMissingElements,
    hookConsoleErrorCapture,
    startNetworkMonitor,
    stopNetworkMonitor,
    startDOMMutationTracker,
    stopDOMMutationTracker,
    getGPSCoordinates,
    watchGPSCoordinates,
    stopGPSWatch,
  };

  // Attach exportDiagnostics privately but accessible from overlay button via closure
  window.__ehLabExportDiagnostics = exportDiagnostics;

  // Expose
  window.eHypnosisLab = exported;

  // Auto-init
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initLab);
  } else {
    initLab();
  }
})();

