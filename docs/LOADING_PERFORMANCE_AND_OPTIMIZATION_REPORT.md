# Loading Performance & Optimization Report

**Date:** 2026-02-27  
**Scope:** API loading time, service worker, database, plugins, full page audit

---

## 1. Executive Summary

| Symptom | Root Cause | Impact |
|---------|------------|--------|
| API 10–12 sec | Worker saturation, DB contention (reduced: 53→14 requests) | 502 Bad Gateway, timeout |
| Tables/plugins slow | Agent behavior: now 1 batch (was 40 requests) | Improved |
| Service worker | Intercepts all fetches; may add latency | Minor; not the main cause |
| Database | SQLite, single connection per worker, repeated `get_all_points` | Lock contention, slow reads |

---

## 2. Service Worker Analysis

### 2.1 Where It Loads

| Page | Loads SW Gatherer? | SW Intercepts |
|------|-------------------|---------------|
| Generator | ✅ Yes | All generator, agent, documentary APIs |
| Unified Dashboard | ❌ No | SW still active if previously installed |
| Profile, Stats, Battle, Shop | ❌ No | SW active if user visited generator |

### 2.2 What the SW Does

- **Scope:** `/vidgenerator/`
- **Intercepts:** All `fetch` under scope
- **Trophies/points/achievements:** `cache: 'no-store'` — network-only
- **Agent API:** Network-first, cache GET on success
- **Generator/documentary:** Network-first, cache GET

### 2.3 SW Impact on Loading

- **Low:** SW passes through most API calls with `cache: 'no-store'`
- **Possible:** Cold SW adds ~50–100 ms on first request
- **Possible:** `controllerchange` → `window.location.reload()` can cause extra reloads
- **Recommendation:** Test with SW disabled to isolate impact

### 2.4 How to Disable SW for Testing

1. **Browser DevTools:** Application → Service Workers → Unregister
2. **Query param:** Add `?sw=0` and check for it before registering
3. **localStorage:** `localStorage.setItem('sw_disabled', '1')` before load

---

## 3. API Request Waterfall

### 3.1 Unified Dashboard

| Phase | Requests | Endpoints |
|-------|----------|-----------|
| 1 | **1** | `aggregator/unified-dashboard/data` — returns all: points, energy, top50, cash, progress, knowledge, agent_behavior |
| 2 | 4 (lazy) | loadAgentAnalytics, loadAgentData, loadPointsAnalytics, unifiedPointCounters — deferred 100ms |

**Total:** 1 API call for initial paint; 4 lazy-loaded for below-the-fold (was ~53).

### 3.2 Unified Dashboard URL — FIXED

- **Dashboard now calls:** `/vidgenerator/api/aggregator/unified-dashboard/data`
- **Response:** `{ success, data: { points, stats, energy, ... } }`

### 3.3 Agent Behavior Widget — FIXED

- **Before:** 20 agents × 2 requests = 40 requests
- **After:** 1 batch request `GET /api/agents/behavior/batch?agent_ids=agent_001,agent_002,...`
- **Fallback:** Individual requests if batch fails

---

## 4. Database & Backend

### 4.1 SQLite Usage

- **Path:** `/var/www/html/vidgenerator/documentaries.db`
- **Workers:** 4 uwsgi processes
- **Connection:** One per worker; SQLite can block on concurrent writes

### 4.2 Repeated `get_all_points` Calls

- **ultra-resource/energy:** `unified_points_db.get_all_points(user_id)`
- **game/achievements:** `unified_points_db.get_all_points(user_id)`
- **game-mechanics/progress:** `unified_points_db.get_all_points(user_id)`
- **aggregator/unified-dashboard:** `get_all_points` called 3+ times in one request

### 4.3 Recommendations

1. **Request-level cache:** Cache `get_all_points(user_id)` per request
2. **Connection pooling:** Use SQLite WAL mode; consider `check_same_thread=False` with care
3. **Indexes:** Ensure `user_id` indexed on player_levels, xp_history, system_point_snapshots

---

## 5. Plugin Loading Order

### 5.1 Dashboard Scripts (defer)

| Order | Script | Purpose |
|-------|--------|---------|
| 1 | load-time-measurement.js | Metrics |
| 2 | error-manager.js | Error handling |
| 3 | Chart.js (CDN) | Charts |
| 4 | navigation-toolbar.js | Nav |
| 5 | comprehensive-auto-save.js | Auto-save |
| 6 | enhanced-frontpage-stats.js | Stats |
| 7 | top50-monetization-frame.js | Top 50 |
| 8 | agent-tracker.js | Agent tracking |
| 9 | agent-dashboard-data.js | Agent data |
| 10 | agent-behavior-widget.js | **40 agent requests** |
| 11 | agent-techs-manager.js | Techs |
| 12+ | energy-regeneration, stats-achievements, image-support, template-effects, template-services, agent-skill-sets, template-engine-core, unified-point-counters, comprehensive-api-integration, sync-status-widget |

### 5.2 Plugins That May Block

- **agent-behavior-widget:** Now uses 1 batch request (was 40)
- **unified-point-counters:** Calls `updateAllCounters(true)` → multiple API calls
- **comprehensive-api-integration:** May trigger additional fetches
- **sync-status-widget:** Fetches sync status

---

## 6. To-Do List (Prioritized)

### P0 — Critical — DONE ✅

| # | Task | Status |
|---|------|--------|
| 1 | Fix unified dashboard URL | ✅ Done |
| 2 | Add batch agent API | ✅ Done |
| 3 | Use batch in agent-behavior-widget | ✅ Done |

### P1 — High (This Week)

| # | Task | How | Effort |
|---|------|-----|--------|
| 4 | Cache `get_all_points` per request | Use `flask.g` or request-scoped cache | 1 h |
| 5 | Add SW disable flag | `?sw=0` or `localStorage.sw_disabled` | ✅ Done |
| 6 | Lazy-load agent behavior widget | Load below-the-fold only when visible | 30 min |

### P2 — Medium (Next Sprint)

| # | Task | How | Effort |
|---|------|-----|--------|
| 7 | Reduce agent count default | 20 → 5 agents on initial load; "Load more" on demand | 30 min |
| 8 | SQLite WAL mode | `PRAGMA journal_mode=WAL` | 15 min |
| 9 | Increase uwsgi workers | 4 → 6 or 8 (if CPU allows) | 15 min |
| 10 | Profile aggregation | Single `/api/profile/aggregated` for profile page | 2 h |

### P3 — Optional (Investigate)

| # | Task | How | Effort |
|---|------|-----|--------|
| 11 | Drop service worker | Remove SW registration; measure load time | 1 h |
| 12 | API response caching | Short TTL (5–10 s) for points/energy | 2 h |
| 13 | Static asset CDN | Offload CSS/JS to CDN | 2–4 h |

---

## 7. How to Test Loading Time

### 7.1 Browser Console

```javascript
// Load time already logged
// [LoadTime] {full, domReady, page}
// Check sessionStorage.loadTimeHistory
```

### 7.2 Network Tab

1. Open DevTools → Network
2. Reload page
3. Filter: XHR
4. Check: Waterfall, request count, time to first byte

### 7.3 With SW Disabled

1. Application → Service Workers → Unregister
2. Hard Reload (Ctrl+Shift+R)
3. Compare load time

---

## 8. Connection & Database Checklist

| Check | Command / Action |
|-------|------------------|
| DB accessible | `sqlite3 /var/www/html/vidgenerator/documentaries.db "SELECT 1"` |
| Permissions | `ls -la documentaries.db` → www-data:www-data |
| WAL mode | `PRAGMA journal_mode` → WAL |
| Table count | `SELECT COUNT(*) FROM sqlite_master WHERE type='table'` |
| Slow queries | Add timing to `get_all_points` |

---

## 9. Summary

| Area | Status | Action |
|------|--------|--------|
| Service worker | Low impact | Optional: disable for testing (`?sw=0`) |
| API request count | ✅ Fixed | Batch agent API; unified URL corrected |
| Database | Medium | Add request cache; WAL mode |
| Plugins | Medium | Lazy-load agent widget; reduce default agents |
| Unified dashboard URL | ✅ Fixed | Fetch path corrected |

---

## 10. Implementation Notes

### Implemented (2026-02-27)

| Fix | File | Change |
|-----|------|--------|
| P0.1 | `vidgenerator/unified_dashboard/index.html` | Fetch `/aggregator/unified-dashboard/data`; handle `data` wrapper; `updateQuickStatsFromUnified` supports aggregator shape |
| P0.2 | `backend/routes/agent_behavior_routes.py` | Added `GET /api/agents/behavior/batch?agent_ids=agent_001,agent_002,...` |
| P0.3 | `vidgenerator/static/js/agent-behavior-widget.js` | Uses batch endpoint first; falls back to 40 individual requests if batch fails |
| SW disable | `vidgenerator/static/js/service-worker-gatherer.js` | `?sw=0` or `localStorage.sw_disabled=1` skips registration |
| **Single API** | `backend/routes/missing_endpoints_routes.py` | Extended aggregator to return top50, cash, knowledge, agent_behavior, points_comprehensive in one response |
| **Single API** | `vidgenerator/unified_dashboard/index.html` | When unified succeeds: render all from 1 response; lazy-load only agent analytics, agent data, points analytics, unifiedPointCounters |

### Deploy

```bash
# Files to deploy
vidgenerator/unified_dashboard/index.html
vidgenerator/static/js/agent-behavior-widget.js
vidgenerator/static/js/service-worker-gatherer.js
backend/routes/agent_behavior_routes.py
docs/LOADING_PERFORMANCE_AND_OPTIMIZATION_REPORT.md
```
