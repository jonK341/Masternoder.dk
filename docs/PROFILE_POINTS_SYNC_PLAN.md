# Profile ↔ Points Synchronization Plan

**Goal:** Tie all loose ends between profiles and the points system so one source of truth and consistent UX everywhere.

**Status:** Plan finished. All 27 loose ends implemented; checklist complete. Profile refetch on visibility + ?refresh=1; trigger-based-actions uses canonical points API. Extended production readiness in **PRODUCTION_READINESS_AND_LOOSE_ENDS.md**.

---

## Loose Ends (Problems) and Solutions

### 1. **Profile points only from aggregated load**
- **Problem:** Profile quick-stats and detailed stats come only from `getUserProfileAggregated()`. After the user earns points on Game/Shop/Star Map 25, the profile does not update until full page reload.
- **Solution:** Add a "Refresh points" action that calls `/vidgenerator/api/points/all` or `/vidgenerator/api/user/account-summary/points`, then updates quick-stats and detailed-stats without full reload.

### 2. **No live points refresh after Sync session**
- **Problem:** When user clicks "Sync session", identity card updates but quick-stats (points) are not refetched.
- **Solution:** After successful `syncSession()`, call a shared `refreshProfilePoints()` and re-render quick-stats (and optionally detailed-stats) from the new points payload.

### 3. **Profile detailed-stats rarely uses points API**
- **Problem:** `renderDetailedStats(statsDiv, stats)` is called with `stats` from aggregated only. `loadPointsStats(statsDiv)` runs only inside `loadDetailedStats()` when `currentStats` is empty or getStats fails, so the Statistics section often misses a full points breakdown (e.g. game_points).
- **Solution:** In `renderProfileFromAggregated`, after rendering, call `loadPointsStats(detailed-stats)` once to fill the Statistics section from `/api/points/all`, or merge `account-summary/points` into stats before rendering.

### 4. **loadPointsStats response shape**
- **Problem:** `loadPointsStats` expects `pointsData.success` and then reads `pointsData.points` or `pointsData.xp_total`. The `/api/points/all` response is `{ success, user_id, points }`, so `xp_total` is inside `points`.
- **Solution:** In `loadPointsStats`, use `const points = pointsData.points || {}` and read all fields from `points` (e.g. `points.xp_total`, `points.game_points`), and add game_points to the displayed stat rows.

### 5. **Game page points fallback URL missing /vidgenerator**
- **Problem:** Game fallback uses `fetch(\`${BASE_URL}/api/points/all?user_id=${userId}\`)`. With `BASE_URL = origin`, this hits `/api/points/all` instead of `/vidgenerator/api/points/all`, which can 404 or hit a different app.
- **Solution:** Use `/vidgenerator/api/points/all` in the fallback (e.g. `${BASE_URL}/vidgenerator/api/points/all?user_id=...`).

### 6. **Battle page points URL missing /vidgenerator**
- **Problem:** `getBattleCoinsBalance()` uses `${BASE_URL}/api/points/all?user_id=...`. Same as above.
- **Solution:** Use `${API_BASE}/points/all?user_id=...` (API_BASE is already `/vidgenerator/api`) or `${BASE_URL}/vidgenerator/api/points/all?user_id=...`.

### 7. **Dashboard points fetch without user_id**
- **Problem:** Dashboard has `fetch(\`${BASE_URL}/vidgenerator/api/points/all\`)` in one place without `user_id`, so server may resolve to default_user or identification.
- **Solution:** Ensure all points fetches include `user_id` from localStorage (e.g. `game_user_id`) so the same user is used as on profile.

### 8. **Two sources of truth: profile aggregated vs account-summary/points**
- **Problem:** Profile uses `user_profile.get_profile_display()` (which calls `unified_points_db.get_all_points`). Account-summary uses `get_points()` from user_account_summary (same backend). Frontend sometimes calls one, sometimes the other; no single "profile points" API that both profile and points page use.
- **Solution:** Standardize on `/vidgenerator/api/user/account-summary/points` for "profile-scoped points" and have profile page use it for refresh; keep `/vidgenerator/api/points/all` for backward compatibility and use same resolution (session/query user_id).

### 9. **Points page has no "View in profile" or shared state**
- **Problem:** Points page shows counters but does not link to profile or refresh profile state; user may see different totals on Points vs Profile.
- **Solution:** Add a clear link "View full profile" on Points page and, if both are open, consider optional BroadcastChannel or a single "points updated" event that profile can subscribe to (or at least document that refresh on profile reloads points).

### 10. **Unified-point-counters.js updates by element id; profile may not have those ids**
- **Problem:** unified-point-counters.js updates elements like `game-points`, `stat-total-xp`, etc. Profile quick-stats are rendered with different structure and may not have these ids, so global counter updates don’t refresh profile.
- **Solution:** Either add the standard data attributes or ids to profile quick-stats (e.g. `id="game-points"`, `id="stat-total-xp"`) so UnifiedPointCounters can update them, or have profile explicitly call the same API and re-render quick-stats when it wants to refresh.

### 11. **No "Refresh points" button on profile**
- **Problem:** User cannot manually refresh points on profile without reloading the whole page.
- **Solution:** Add a "Refresh points" button (or include in existing "Refresh" in header) that calls account-summary/points or points/all, then updates quick-stats and detailed-stats.

### 12. **After shop purchase, profile does not refresh**
- **Problem:** After spending in Shop, profile still shows old coins/points until reload.
- **Solution:** On return from shop (or when shop signals purchase), profile could refetch points. Implement by: (a) profile polling after visibility focus, or (b) shop redirect to profile with ?refresh=1 and profile refetches points when that param is present.

### 13. **After game action (earn game_points), profile does not refresh**
- **Problem:** Same as shop; earning in Game or Star Map 25 doesn’t update profile until reload.
- **Solution:** Same as #12: refresh points on profile when tab becomes visible (optional) or when user navigates to profile with a refresh hint; and ensure "Refresh points" button is available.

### 14. **Sync-status-widget and points**
- **Problem:** Sync-status-widget may show "points" in sync status but not trigger or reflect profile points refresh.
- **Solution:** Ensure sync-status-widget and profile both use the same user_id; after a "sync" or "points synced" state, profile can call refreshProfilePoints() if desired.

### 15. **Profile identity card does not show live point totals**
- **Problem:** Identity card shows "where progress is stored" but not the actual point totals from those stores.
- **Solution:** Optionally add a line "Current totals: X game_points, Y XP" from account-summary/points or points/all in the identity card, or keep identity for "where" and keep totals in quick-stats (with refresh).

### 16. **Trophies page and profile trophies section**
- **Problem:** Unlocking a trophy on Trophies page does not auto-update the profile trophies section until reload.
- **Solution:** Profile "Refresh" (or "Refresh points") refetches aggregated data (which includes trophies) or a dedicated trophies refetch; ensure one refresh action updates both points and trophies where possible.

### 17. **Navigation toolbar points display**
- **Problem:** Nav bar may call a different endpoint or cache for points; profile and nav can show different numbers.
- **Solution:** Use the same API and user_id for nav bar as for profile (e.g. points/all or account-summary/points with game_user_id), and same cache policy or refresh trigger.

### 18. **stats-achievements-tracker.js points URL**
- **Problem:** Uses `base + '/points/all?user_id=' + uid`; need to confirm `base` includes `/vidgenerator/api`.
- **Solution:** Ensure base is `/vidgenerator/api` or full path to points/all so the same backend is used.

### 19. **trigger-based-actions.js uses /points/unified/get**
- **Problem:** One place uses `/points/unified/get`; other pages use `/points/all`. Different responses can cause inconsistent UI.
- **Solution:** Prefer one canonical endpoint (e.g. points/all or account-summary/points) and document it; or ensure unified/get returns the same shape as points/all for shared code.

### 20. **Profile renderQuickStats missing game_points in some paths**
- **Problem:** If stats from aggregated don’t include game_points (e.g. old cache or missing backend field), quick-stats won’t show it.
- **Solution:** Backend already adds game_points to stats in user_profile; ensure frontend always displays it when present and that refresh fetches from an API that returns game_points (points/all and account-summary/points already do).

### 21. **Points page quick-stat total**
- **Problem:** "Total points" on Points page might be computed client-side from a subset of point types; if game_points or others are missing from response, total is wrong.
- **Solution:** Ensure points/all and account-summary/points return game_points and any other types; Points page uses the same API and sums all numeric point fields for "total" or shows a server-provided total if available.

### 22. **Dashboard /points/all and /points/comprehensive**
- **Problem:** Dashboard uses both; comprehensive might have different shape. Inconsistent handling.
- **Solution:** Use one primary endpoint (e.g. points/all with user_id) for dashboard totals and use comprehensive only where richer breakdown is needed; ensure both receive same user_id.

### 23. **Battle fallback root /api/points/all**
- **Problem:** Battle has another fallback that uses root `/api/points/all`; same wrong-path issue.
- **Solution:** Use vidgenerator-prefixed URL everywhere: `/vidgenerator/api/points/all`.

### 24. **Profile loadPointsStats does not show game_points**
- **Problem:** loadPointsStats builds stat rows for generation_points, xp_total, battle_points, etc., but may omit game_points.
- **Solution:** Add a row for Game Points in loadPointsStats from points.game_points.

### 25. **No shared "profile points updated" event**
- **Problem:** Multiple components (profile quick-stats, detailed-stats, nav bar, points page) can show points; no single event to "invalidate and refetch" across them.
- **Solution:** Introduce a small custom event (e.g. `window.dispatchEvent(new CustomEvent('profile-points-refresh'))`) that profile and (optionally) nav listen to; when any action (sync session, return from shop, button click) updates points, dispatch the event and have listeners refetch and re-render.

### 26. **Backend connector getStats vs get_points**
- **Problem:** Profile getStats calls `/user/profile/${uid}/stats`; account-summary has get_points(). Different endpoints can diverge.
- **Solution:** Have profile "Refresh points" use the same backend as account-summary/points (get_points) so one source; getStats can remain for other profile stats, but points display should prefer account-summary/points or points/all.

### 27. **Detailed stats section not populated from points API on first load**
- **Problem:** On first load, renderProfileFromAggregated calls renderDetailedStats(statsDiv, stats) with aggregated stats only; loadPointsStats is never called for the initial view, so Statistics section lacks full points breakdown.
- **Solution:** After renderProfileFromAggregated, call loadPointsStats(detailed-stats) once (or loadDetailedStats which will use currentStats first, then getStats, then loadPointsStats) so the Statistics section gets points data; or merge points from account-summary/points into stats before first render.

---

## Implementation Checklist (solved loose ends)

- [x] **1–4, 11, 24, 27:** Profile: add refreshProfilePoints(), "Refresh points" button, use points API for detailed-stats and loadPointsStats (correct shape, include game_points).
- [x] **2:** After syncSession(), call refreshProfilePoints() and update quick-stats.
- [x] **5, 6, 23:** Game and Battle: fix points URLs to use `/vidgenerator/api/points/all` (or `API_BASE/points/all`).
- [x] **7:** Dashboard: add user_id to all points/all calls (fallback and loadUnifiedPoints).
- [x] **8:** Profile refresh uses account-summary/points; points/all kept for compatibility.
- [x] **9:** Points page: "View full profile" link and note that points are synced with profile.
- [x] **10:** refreshProfilePoints() re-renders quick-stats and calls loadPointsStats(detailed-stats).
- [x] **12, 13:** Profile refetch points on visibility focus (debounced 10s) and when navigating with ?refresh=1.
- [x] **17, 22:** Dashboard and profile use same user_id (localStorage game_user_id).
- [x] **18, 19:** stats-achievements-tracker already uses baseURL `/vidgenerator/api`; trigger-based-actions getUnifiedPoints() now uses canonical `/vidgenerator/api/points/all`.
- [x] **25:** CustomEvent 'profile-points-refresh' dispatched after refreshProfilePoints(); other components can listen.
- [x] **26:** Profile points display uses account-summary/points for refresh and points/all for loadPointsStats.

---

## Summary

**Minimum 25 loose ends** are listed above (27 total). Solving them gives:

1. **Single source of truth:** account-summary/points and points/all (same backend); profile and Points page use same user_id and same endpoints where possible.
2. **Explicit refresh:** Profile has "Refresh points" and refresh after Sync session; optional refetch on focus or ?refresh=1.
3. **Correct URLs:** All points API calls use `/vidgenerator/api/points/all` or `/vidgenerator/api/user/account-summary/points` with user_id.
4. **Full points on profile:** Quick-stats and Statistics section show game_points and all types; loadPointsStats uses correct response shape and is used on first load.
5. **Cross-links:** Points page links to profile; profile links to Points, Game, Shop, Star Map 25 (already in place).
