# Performance improvements — rethought ideas

**Purpose:** Central list of ways to improve performance (backend, frontend, and UX). Builds on `PORT_5000_BOTTLENECK_AND_SOLUTIONS.md` and adds new, actionable ideas.

---

## 1. Current state (already in place)

| Measure | Where | Effect |
|--------|--------|--------|
| **Two backends (5000 + 5001)** | Nginx upstream, systemd units | More workers, less queueing |
| **LITE_APP=1** | uWSGI env | Fewer blueprints, less RAM, room for more workers |
| **Response caching** | `response_cache_middleware.py` | `@cached_response(ttl)` on points/all, stats/summary, frontpage/init (30–60s) |
| **Cacheable patterns** | Same middleware | stats, battle/stats, points/comprehensive, points/all, frontpage/init, aggregator |

---

## 2. Backend — new ideas

### 2.1 Extend caching to more GETs

- **Social:** `GET /api/social/summary`, `GET /api/social/friends`, `GET /api/social/crews`, `GET /api/social/activity` — cache 30–60s per `user_id` so repeated tab switches don’t hit disk every time.
- **Leaderboard:** Already in cacheable patterns; ensure TTL is sane (e.g. 2 min).
- **Star Map 25 (read-only):** `GET /api/star-map/25`, `GET /api/star-map/25/buildings`, `GET /api/star-map/25/units` — cache 60–300s (data changes rarely).
- **Rulebook / static data:** Any GET that reads only from JSON files and doesn’t depend on `user_id` — cache 5–15 min.

**Implementation:** Add paths to `_is_cacheable()` in `response_cache_middleware.py` and use `@cached_response(ttl=…)` on those routes. For user-scoped endpoints, include `user_id` in the cache key (already done via `request.args`).

### 2.2 Batch / composite endpoint for page load

- **Idea:** One endpoint e.g. `GET /api/page/init?page=game&user_id=` that returns a single JSON with: points summary, battle stats, leaderboard top 10, social summary, starmap25 status. Frontend calls it once and distributes data to state.
- **Pros:** Fewer round-trips, one TCP connection, less queueing on the server.
- **Cons:** More backend work to maintain; cache key is coarse (invalidate or short TTL when user acts).

**Implementation:** New route that calls existing helpers (no duplicate logic), merges results, returns one JSON. Frontend replaces 4–6 parallel GETs with 1 GET for above-the-fold data.

### 2.3 Lighter payloads

- **Field selection:** e.g. `GET /api/points/all?fields=game_points,xp_total,level` so profile/game can ask only for what they need.
- **Trim large lists:** Leaderboard: cap at 50 or 100; activity feed: cap at 25 server-side (already done). Avoid returning full history when only “last N” is needed.

### 2.4 DB and disk

- **Indexes:** If any endpoint runs SQL (e.g. user_points, battle history), ensure indexes on `user_id`, `created_at` (or equivalent) so “last N for user” is fast.
- **JSON file reads:** Keep using `_load_*()` helpers; avoid loading the same file multiple times per request (memoize within request if needed). For very hot paths, consider loading once at startup and invalidating on write (if writes are rare).

### 2.5 Timeouts and harakiri

- Ensure long-running endpoints (e.g. AI clips generation, documentary) run in background jobs and don’t hold a worker. Only quick reads/writes should run in request handlers.
- Keep harakiri (uWSGI) at a value that allows slow-but-necessary GETs (e.g. 30–60s) without killing normal requests.

---

## 3. Frontend — new ideas

### 3.1 Lazy-load tab content

- **Idea:** Don’t call Social, Star Map 25, Leaderboard, etc. until the user opens that tab. Today many tabs trigger `load*()` on first show; that’s good. Ensure no tab preloads all others on page load.
- **Check:** Game page: only load data for the active tab; when switching tab, call the corresponding `load*()` once. Avoid calling every tab’s loader on initial load.

### 3.2 Defer non-critical JS

- **Idea:** Scripts that are not needed for first paint (e.g. timeline, epic journey, analytics) should be `defer` or loaded after `DOMContentLoaded`. Critical path: tabs, stats, one feed.
- **Preconnect:** `<link rel="preconnect" href="https://api-origin">` if API is on another origin; otherwise not needed.

### 3.3 Static assets

- **Cache-Control:** For `/static/*` (CSS, JS), set long cache (e.g. 1 year) with a versioned query string (e.g. `?v=20260304`). Already in use in many places; ensure all static refs use a version.
- **CDN:** If static assets are heavy, serve them from a CDN or a separate subdomain to reduce load on the app server.

### 3.4 Fewer requests on profile/game load

- Use the **batch endpoint** (above) so the first paint has data with one request. Alternatively, keep parallel requests but ensure they’re only for the visible section (e.g. don’t load Social API until Social tab is opened).

---

## 4. UX / perceived performance

- **Skeleton loaders:** Already present in some tabs; use them everywhere data is loading so the user sees structure immediately.
- **Optimistic updates:** For actions like “Add friend” or “Collect”, update the UI immediately and revert on error, instead of waiting for the response.
- **Service worker:** If the app is a PWA or has a service worker, cache static assets and optionally cache GET responses for offline or repeat visits.

---

## 5. Prioritized summary

| Priority | Idea | Effort | Impact |
|----------|------|--------|--------|
| High | Extend caching to social + starmap25 read-only GETs | Low | Fewer disk reads, faster tab switches |
| High | Lazy-load tab data (only load when tab is opened) | Low | Faster first load, less server load |
| Medium | Batch endpoint for game/profile init | Medium | Fewer round-trips, simpler frontend state |
| Medium | Field selection for points/all | Low | Smaller payloads |
| Low | Defer non-critical JS | Low | Faster first paint |
| Low | Cache-Control + versioning for all static assets | Low | Fewer repeat requests for CSS/JS |
| Later | Redis for cache (shared across workers) | Medium | Better hit rate with multiple backends |

---

## 6. Quick wins to implement next

1. **Cache social and starmap25 GETs:** In `response_cache_middleware.py`, add `/api/social/`, `/api/star-map/25` (GET only, with `user_id` in key). Add `@cached_response(ttl=45)` to the relevant routes (or use a per-route TTL).
2. **Ensure game page doesn’t preload all tabs:** In `game/index.html`, confirm that `loadSocialTab`, `loadStarMap25Tab`, etc. are only called when the tab is selected (already the case if they’re triggered by tab click). If any loader is called on page load for a hidden tab, remove it.
3. **Static versioning:** Audit `<script>` and `<link>` tags; ensure they use `?v=...` and that the version is updated on deploy so caches refresh.

Implementing (1) and (2) gives the best cost/benefit with minimal code change.
