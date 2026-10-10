# Performance improvement ideas

**Purpose:** Rethink options to improve performance beyond the existing [Port 5000 bottleneck](PORT_5000_BOTTLENECK_AND_SOLUTIONS.md) (second backend, LITE_APP, caching). These are **new or complementary** ideas: frontend, backend, and infra.

---

## 1. Frontend

### 1.1 Reduce API waterfall on page load

- **Issue:** Generator, Game, and Profile trigger many sequential or parallel GETs (points, stats, battle, leaderboard, starmap, etc.). One slow request delays rendering or blocks the main thread.
- **Ideas:**
  - **Single “bootstrap” endpoint** — e.g. `GET /api/bootstrap?user_id=` that returns a JSON blob with points summary, level, battle stats, starmap count, and optionally leaderboard top 5. Frontend calls it once and then hydrates the page. Fewer round-trips and one place to cache (e.g. 30–60s TTL).
  - **Defer non-critical requests** — Load leaderboard, activity feed, or “AI tips” after first paint (e.g. `requestIdleCallback` or setTimeout). Show placeholders until data arrives.
  - **Inline critical data** — For Game or Profile, server-render a `<script type="application/json" id="bootstrap">...</script>` with the minimal data needed for above-the-fold content so the page doesn’t need an extra API call for the first paint.

### 1.2 Lazy-load heavy UI and scripts

- **Issue:** Large single-page surfaces (e.g. Game with many tabs) load all JS and render all tabs up front.
- **Ideas:**
  - **Dynamic import for tab content** — Load the code for “Star Map 25”, “Social”, “Timeline” only when the user switches to that tab. Reduces initial parse/compile and memory.
  - **Lazy-load images and iframes** — Use `loading="lazy"` and/or Intersection Observer for gallery thumbnails and embedded content so they don’t block or compete for bandwidth on load.

### 1.3 Cache API responses in the browser

- **Issue:** Every navigation or refresh re-fetches the same data (e.g. leaderboard, starmap definition).
- **Ideas:**
  - **Cache-Control and ETag** — Set `Cache-Control: public, max-age=60` (or 30) for GETs that are safe to reuse (e.g. `/api/star-map/25`, `/api/leaderboard/top10`, `/api/social/networks`). Use ETag for validation so clients can revalidate without re-downloading when unchanged.
  - **In-memory or sessionStorage** — For the same tab/session, keep a short-lived cache (e.g. 30s) for repeated calls to the same endpoint (e.g. points summary) so rapid tab switches don’t hammer the server.

---

## 2. Backend

### 2.1 Expand response caching

- **Current:** Some heavy GETs use `@cached_response(ttl=60)` (e.g. points/all, stats/summary, frontpage/init).
- **Ideas:**
  - **Cache more read-heavy GETs** — e.g. `/api/star-map/25`, `/api/leaderboard`, `/api/social/crews`, `/api/social/networks`, `/api/star-map/25/buildings`, `/api/star-map/25/units`. Short TTL (30–60s) is usually enough and cuts DB/file reads.
  - **User-agnostic vs user-specific** — Cache starmap definition and networks globally; cache leaderboard with a short TTL; avoid caching user-specific points in a shared cache unless keyed by `user_id` and you’re OK with staleness.
  - **Redis (optional)** — If you add Redis, move cache there so all workers share the same cache and TTL is consistent across restarts.

### 2.2 Lightweight “bootstrap” endpoint

- **Idea:** One endpoint that aggregates the minimal data needed for the first paint of Game or Profile: `user_id`, `level`, `xp_total`, `game_points`, `battle_wins`, `starmap25_investigated_count`, optional `leaderboard_top5`. Implement by calling existing services or DB once and returning a single JSON. Frontend calls only this on load, then optionally refreshes or fetches details (e.g. full leaderboard) in the background.
- **Benefit:** Fewer round-trips, one place to cache, faster perceived load.

### 2.3 Defer or background heavy work

- **Ideas:**
  - **AI tips / LLM calls** — The Star Map 25 “AI hint” and Game AI coach call the LLM on demand. Consider caching the last hint per user (e.g. 5–10 min TTL) or returning a cached/rule-based hint immediately and refreshing asynchronously.
  - **Activity feed** — If the feed is large, paginate and only compute the first page; avoid loading the full feed into memory.
  - **Leaderboard** — Precompute top N on a schedule (e.g. every 1–5 min) and serve the cached list; recompute in background.

### 2.4 Connection pooling and DB

- **If DB is used:** Use connection pooling so each worker doesn’t open too many connections. Tune pool size to the number of workers and DB `max_connections`.
- **File I/O:** JSON files (social_structure, starmap25, etc.) are read on every request in some routes. Caching (in-process or Redis) reduces disk reads; ensure writes don’t hold the cache lock too long.

---

## 3. Infra and deployment

### 3.1 CDN and static assets

- **Ideas:**
  - Serve static assets (CSS, JS, images) from a CDN or with long `Cache-Control` so repeat visits don’t hit the app server for them.
  - If the app serves HTML that includes many script/style tags, consider bundling and minifying to reduce requests and parse time.

### 3.2 Compression

- **Idea:** Enable gzip (or Brotli) for JSON and HTML in nginx or in the app so responses are smaller and faster over the network. Many clients send `Accept-Encoding: gzip`; nginx can compress proxy responses.

### 3.3 Split by path (already in bottleneck doc)

- **Reminder:** Sending heavy or slow APIs (e.g. `/api/points/all`, `/api/generator/...`) to a second backend (5001) keeps them from blocking the main app on 5000. Combine with LITE_APP on both so each instance uses less RAM.

### 3.4 Health and timeouts

- **Ideas:**
  - **Harakiri / request timeouts** — Ensure uWSGI harakiri and nginx timeouts are aligned so stuck requests don’t hold workers forever. Optimize or cache the slowest endpoints so they stay under the timeout.
  - **Health check** — A lightweight `/health` or `/ping` that doesn’t load the full app (or uses a minimal route) lets load balancers and monitoring detect availability without stressing the server.

---

## 4. Quick wins (prioritized)

| Action | Effort | Impact |
|--------|--------|--------|
| Bootstrap endpoint + single call on Game/Profile load | Medium | High (fewer requests, faster first paint) |
| Cache more GETs (starmap, leaderboard, social/networks) | Low | Medium (fewer file/DB reads) |
| Defer non-critical API calls (leaderboard, activity, AI hint) after first paint | Low | Medium (faster TTI) |
| Cache AI hint / coach response per user (short TTL) | Low | Medium (fewer LLM calls) |
| `Cache-Control` + ETag for static and cacheable GETs | Low | Medium (repeat visits) |
| Lazy-load tab content (dynamic import) | Medium | Medium (initial JS and memory) |
| gzip in nginx for API/HTML | Low | Low–medium (smaller payloads) |

---

## 5. References

- **Bottleneck and existing fixes:** [PORT_5000_BOTTLENECK_AND_SOLUTIONS.md](PORT_5000_BOTTLENECK_AND_SOLUTIONS.md) — second backend, LITE_APP, `@cached_response` for some endpoints.
- **Server operations:** [SERVER_QUICK_REFERENCE.md](SERVER_QUICK_REFERENCE.md).
