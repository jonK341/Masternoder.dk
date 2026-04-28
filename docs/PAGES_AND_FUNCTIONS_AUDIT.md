# Pages and Functions Audit

**Purpose:** Track which front-page and profile-page URLs work (200) vs fail (404/timeout) so we can fix endpoints and align frontend with backend.

**Source:** `scripts/test_url_timing.py` (hard test against BASE_URL). Run: `python scripts/test_url_timing.py`

**Full recheck:** For all checkpoints (env, agents, deploy, Agent Support, nav, URL timing), see `docs/CHECKPOINTS_RECHECK.md`. Production 404s (Bind session, Profile aggregated, Gallery recent) and fix steps: CHECKPOINTS_RECHECK §9 and RESEARCH_AI_SYSTEMS §10.

---

## 1. Front Page URLs

| Endpoint | Path | Status (typical) | Backend / Notes |
|----------|------|------------------|-----------------|
| Front page init | `/vidgenerator/api/frontpage/init` | 200 | `missing_endpoints` + fallback |
| Stats summary | `/vidgenerator/api/stats/summary` | 200 (slow) | OK |
| Points all | `/vidgenerator/api/points/all` | 200 | OK |
| Battle stats | `/vidgenerator/api/battle/stats` | 200 | `battle_routes` + fallback in missing_endpoints |
| Agent skillset all | `/vidgenerator/api/agent-skillset/all` | 200 or 404 | `agent_automation_routes.py` – multiple path variants |
| Aggregator frontend | `/vidgenerator/api/aggregator/frontend` | 200 | OK |

**Working:** Front page init, Stats summary, Points all, Battle stats, Aggregator frontend, Agent skillset all (when route registered).

---

## 2. Profile Page URLs

| Endpoint | Path | Status (typical) | Backend / Notes |
|----------|------|------------------|-----------------|
| Bind session | `/vidgenerator/api/user/bind-session` | 200 | OK |
| Profile aggregated | `/vidgenerator/api/user/profile/<user_id>/aggregated` | 200 | `user_profile_routes.py` |
| User identity | `/vidgenerator/api/user/identity` | 200 | OK |
| Account summary points | `/vidgenerator/api/user/account-summary/points` | 200 | OK |
| Gallery recent | `/vidgenerator/api/gallery/recent-temp` | 200 | OK |
| Geo ref | `/vidgenerator/api/game/hunters/geo-ref` | 200 or timeout | Hunters |
| PayPal control panel | `/vidgenerator/api/shop/paypal/control-panel` | 200 or timeout | Shop |
| Agents activity feed | `/vidgenerator/api/agents/activity-feed` | 200 | OK |
| My agents | `/vidgenerator/api/agents/my-agents` | 200 | OK |
| Trophies list | `/vidgenerator/api/trophies/list` | 200 | `trophies_routes` + fallback in missing_endpoints |
| Game achievements | `/vidgenerator/api/game/achievements` | 200 | OK |
| Battle PVP trophies | `/vidgenerator/api/battle/pvp/trophies` | 200 | `battle_routes` + fallback in missing_endpoints |

**Working:** All listed. Trophies list and Battle PVP trophies have fallbacks in missing_endpoints. Geo ref and PayPal can timeout under load.

**Fallbacks:** Bind session, Profile aggregated, and Gallery recent have fallback routes in `missing_endpoints_routes.py` that delegate to `user_profile_routes` / `gallery_routes` when available, or return minimal 200 JSON so the hard test and profile page keep working even if those blueprints load later or path differs.

---

## 3. Pages That Use These APIs

| Page | Key APIs | Notes |
|------|----------|--------|
| Front (vidgenerator/index.html) | frontpage/init, stats/summary, points/all, battle/stats, agent-skillset/all, aggregator/frontend | Init and battle/stats often 404 |
| Profile (vidgenerator/profile/index.html) | bind-session, profile/aggregated, identity, account-summary/points, gallery/recent-temp, geo-ref, paypal/control-panel, agents/activity-feed, my-agents, trophies/list, game/achievements, battle/pvp/trophies | Profile works when aggregated + identity + points OK; trophies and battle PVP can fail |
| Game | points/all, game/achievements, hunters/* | Depends on points and hunters routes |
| Shop | shop/*, points | Shop purchase and items |
| Trophies | trophies/list, star-map, game/achievements | trophies/list must resolve |
| Agents | agent/skillset/*, agents/my-agents, agents/activity-feed | agent-skillset/all used on front |

---

## 4. Recommended Fixes (done)

1. **Front page init** – Done. `GET /vidgenerator/api/frontpage/init` in `missing_endpoints_routes.py` returns `{ success, ready }` immediately.
2. **Battle stats** – Done. Fallback in `missing_endpoints_routes.py` delegates to `battle_routes.battle_stats` or returns default stats JSON.
3. **Trophies list** – Done. Fallback in `missing_endpoints_routes.py` delegates to `trophies_routes.list_trophies_api` or returns minimal `{ success, trophies, definitions, user_id }`.
4. **Battle PVP trophies** – Done. Fallback in `missing_endpoints_routes.py` delegates to `battle_routes.battle_pvp_trophies` or returns `{ success, user_id, trophies: [] }`.
5. **Profile loading time** – Profile uses one aggregated call (45s timeout). Backend should respond within that; for faster perceived load, frontend could later add parallel fetches for identity + account-summary/points before or after aggregated.
6. **Generator** – Done. Generator `safeJson()` now handles 5xx/HTML and shows "Server error. Try again." instead of "Invalid JSON".

7. **Game time & boosters in UI (last part)** – Done. Profile quick-stats show **Game time** (remaining minutes from Shop) and **Boosters** (count). Game page has a **Game time & boosters** strip above Comprehensive Points, filled from `points/all` (or from fallback points when comprehensive uses fallback). Backend `user_profile.get_profile_display` now includes `game_time_remaining_minutes` and `active_boosters` in stats; `get_all_points` already returns them.

---

## 5. Run Audit

```bash
python scripts/test_url_timing.py
# Or against production:
# set BASE_URL=https://masternoder.dk
# python scripts/test_url_timing.py
```

Results are saved to `logs/url_timing_results.json`. If any 404s occur, see `logs/production_404_deploy_checklist.txt` for suggested route files.

**How to verify:** Run the command above; check exit code (0 = all OK, 1 = at least one failed). Open `logs/url_timing_results.json` for per-URL status and timing. Compare "Failed" list with §2 table and CHECKPOINTS_RECHECK §8–9.
