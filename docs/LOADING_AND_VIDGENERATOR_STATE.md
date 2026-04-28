# Loading Time and VidGenerator State of Mind

**Last updated:** 2026-02-25

---

## 1. Page Loading Time — Measurement

### 1.1 Current State

- **No built-in loading-time metrics** — The platform does not currently instrument page load time (e.g. `performance.timing`, `performance.now()`).
- **Loading states** — Pages show loading placeholders (e.g. "Loading profile...", "Loading skills...") in `vidgenerator/profile/index.html`, `vidgenerator/stats/index.html`, etc.
- **Sync status widget** — Uses `document.readyState === 'loading'` to defer fetch until DOM is ready.

### 1.2 Recommended Measurement Approach

To measure loading time on pages:

1. **Client-side (browser):**
   ```javascript
   // At start of page load
   const t0 = performance.now();
   // ... after critical content loaded
   const loadTime = performance.now() - t0;
   ```

2. **Navigation Timing API:**
   ```javascript
   window.addEventListener('load', () => {
     const timing = performance.timing;
     const loadTime = timing.loadEventEnd - timing.navigationStart;
     // Optional: send to analytics
   });
   ```

3. **Sync status widget** — Already defers API fetch until `DOMContentLoaded` or `load` to avoid blocking.

### 1.3 Pages to Monitor

| Page | Path | Notes |
|------|------|-------|
| Unified Dashboard | `/vidgenerator/unified_dashboard/` | Heavy: sync widget, points, stats |
| Profile | `/vidgenerator/profile/` | Multiple async sections (profile, skills, activity, trophies, agents, achievements) |
| Stats | `/vidgenerator/stats/` | Stats, achievements, milestones, referral |
| Generator | `/vidgenerator/generator/` | Video generation UI |
| Battle | `/vidgenerator/battle/` | Battle UI |
| Shop | `/vidgenerator/shop/` | Shop items, points |

---

## 2. VidGenerator "State of Mind" — Generator Status

### 2.1 What "State of Mind" Means

The video generator has an internal state that reflects:
- **Job status:** `pending`, `processing`, `completed`, `failed`
- **Progress:** 0–100%
- **Error message:** When `status=failed`

### 2.2 Where State Lives

- **Service:** `backend/services/video_generator_service.py`
- **Job store:** `backend/services/generator_db_service.py` (DB tables: `video_generation_jobs`, etc.)
- **API:** Job status via generator routes (e.g. `/api/generator/jobs`, job-by-id)

### 2.3 State Values

| State | Meaning |
|-------|---------|
| `pending` | Job queued, not yet started |
| `processing` | Job is running (LLM, clips, assembly) |
| `completed` | Job finished successfully |
| `failed` | Job failed; `error_message` set |

### 2.4 Sync Integration

- **Domain:** `generator`
- **When:** After video generation completes (points awarded, job saved)
- **Source:** `video_generator_service` calls `record_domain_sync('generator')`

### 2.5 Measuring Generator "State of Mind"

To get a snapshot of the generator's state:

1. **Per-job:** `GET /api/generator/jobs/<job_id>` or equivalent — returns `status`, `progress`, `error_message`
2. **List jobs:** `GET /api/generator/jobs` — returns list of jobs with status
3. **Sync status:** `GET /api/sync/status` — includes `domains.generator.last_sync_at` as last sync time for the generator domain

---

## 3. Sync Device Progress Outline

Following the sync device's progress:

1. **State storage:** DB (`sync_state`, `sync_domain_state`) with JSON fallback
2. **Audit:** All sync events → `sync_audit` table
3. **Health:** Success/failure → `sync_health` table
4. **Error logging:** Sync failures → `error_logging` service
5. **Domains:** 30+ domains tracked; add new via `SYNC_DOMAINS` and `record_domain_sync`

---

## 4. Recheck — Root Causes of Slow Loading

### 4.1 Findings (Codebase Analysis)

| Page | API Calls on Load | Pattern | Bottleneck |
|------|-------------------|---------|------------|
| **Profile** | 1 + 8 | Sequential then parallel | `getUserProfileDisplay` blocks; user sees "Loading profile..." until it completes. Then 8 parallel fetches (points, activity, agents, achievements, trophies, stats, geo, PayPal). |
| **Unified Dashboard** | 6+ | Partially parallel | 4 parallel (points, energy, top50, cash), then 2 sequential (trophies, knowledge). `loadQuickStats` could run trophies + knowledge in parallel. |
| **Stats** | 8 | Parallel | All parallel — good. But 8 separate HTTP round-trips; no aggregator. |
| **Generator** | varies | — | Video job status fetches. |
| **Battle, Shop** | multiple | — | Similar multi-fetch patterns. |

### 4.2 Root Causes

1. **No measurement** — No `performance.timing` or `performance.now()` instrumentation, so bottlenecks are unknown.
2. **Waterfall dependencies** — Profile: first API blocks; Dashboard: trophies and knowledge run after the first 4.
3. **Scattered API calls** — Heavy pages (Profile, Stats, Dashboard) make 6–9 separate requests instead of using aggregators.
4. **Script loading** — Many scripts; some without `defer` can block parsing.
5. **No above-the-fold prioritization** — Critical content is not loaded first.

---

## 5. Conclusion and Solution

### 5.1 Recommended Fixes (Priority Order)

| Priority | Fix | Impact | Effort |
|----------|-----|--------|--------|
| **P1** | Add loading-time measurement | Diagnose bottlenecks; baseline for improvements | Low |
| **P2** | Use aggregator for Profile and Stats | Reduce 8–9 requests to 1–2 | Medium |
| **P3** | Parallelize remaining sequential fetches | Dashboard: run trophies + knowledge in parallel | Low |
| **P4** | Add `defer` to non-critical scripts | Faster initial parse | Low |
| **P5** | Skeleton loaders for above-the-fold | Perceived speed; show structure immediately | Medium |

### 5.2 Implementation: Loading-Time Measurement (P1)

Add a small script to key pages (unified_dashboard, profile, stats) to measure and optionally log load time:

```javascript
// At top of <head> or first script
window._pageLoadStart = performance.now();
window.addEventListener('load', function() {
  const timing = performance.timing;
  const fullLoad = timing.loadEventEnd - timing.navigationStart;
  const domReady = timing.domContentLoadedEventEnd - timing.navigationStart;
  const apiReady = performance.now() - window._pageLoadStart;
  console.log('[LoadTime]', {
    full: fullLoad + 'ms',
    domReady: domReady + 'ms',
    page: window.location.pathname
  });
  // Optional: send to /api/analytics/load-time
});
```

### 5.3 Implementation: Use Aggregator (P2)

- **Profile:** Extend `getUserProfileDisplay` or add `/api/profile/aggregated` to return profile + skills + points + activity + achievements + trophies in one response.
- **Stats:** Add `/api/stats/aggregated?user_id=X` that returns achievements, milestones, categories, profile, xp-scores, statistics in one call.
- **Dashboard:** `loadQuickStats` already uses `Promise.allSettled` for 4 calls; add trophies and knowledge to that batch.

### 5.4 Implementation Notes (2026-02-27)

**P1 DONE:** `vidgenerator/static/js/load-time-measurement.js` — logs `[LoadTime] {full, domReady, page}` to console. Inline `window._pageLoadStart` in head of unified_dashboard, profile, stats, generator, battle, shop. History in `sessionStorage.loadTimeHistory` (last 5).

**P2 DONE:** `/api/stats/aggregated?user_id=X&days=30` — single response with achievements, milestones, categories, statistics, stats_points, points_analytics, profile. Stats page tries aggregated first, falls back to 8 individual fetches.

**P3 DONE:** Dashboard `loadQuickStats` — trophies + knowledge now in `Promise.allSettled` (was sequential).

**P4 DONE:** `defer` added to image-support, template-effects, template-services, agent-skill-sets, template-engine-core, unified-point-counters, comprehensive-api-integration, toast-notifications, theme-toggle on profile/stats.

**P5 DONE:** Dashboard quick-stats use `.skeleton-loader` with shimmer until `loadQuickStats` completes.

### 5.5 Summary

| Topic | Status |
|-------|--------|
| Page loading time | P1: Instrumented; console + sessionStorage |
| Root cause | Waterfall + scattered API calls |
| Solution | P1–P5 implemented |
| VidGenerator state | Job status: pending/processing/completed/failed; progress 0–100 |
| Sync device state | DB + JSON; audit + health in DB |
