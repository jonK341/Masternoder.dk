# Star Map 25 — Todo 25: Assignments & Tasks

**Purpose:** A single checklist of **25 tasks** for the Star Map 25 (Imperium Investigation Grid) feature. Use as a roadmap and assignment list.

**References:** `STARMAP_25_WARHAMMER40K_RESEARCH.md`, `HUNTERS_STAR_MAP_IMPLEMENTATION_SUMMARY.md` (sect. 10), `STARMAP_25_TOP10_IDEAS.md`, `data/star_map_25.json`.

---

## Todo 25 — Assignments

| # | Assignment | Owner / Notes |
|---|------------|----------------|
| **1** | **Data** — Verify `data/star_map_25.json` has all 25 points with `id`, `name`, `segmentum`, `point_value`, `lore`, `icon`. | Done. Use as source of truth. |
| **2** | **API** — `GET /api/star-map/25` and `GET /vidgenerator/api/star-map/25` return full 25-point map. | `star_map_routes.py` |
| **3** | **API** — `GET /api/star-map/25/status?user_id=` returns `investigated_ids`, `total_points_earned`. | `star_map_routes.py` |
| **4** | **API** — `POST /api/star-map/25/investigate` body `{ "user_id", "point_id" }`: one-time game_points award, persist investigation. | `star_map_routes.py` |
| **5** | **Persistence** — Investigations stored (e.g. `star_map_25_investigations.json` or DB) and survive app restart. | Backend; avoid in-memory only. |
| **6** | **Monitor page** — `/vidgenerator/starmap25/` loads; shows progress (X/25) and total points earned. | `vidgenerator/starmap25/index.html` |
| **7** | **Monitor page** — Grid of 25 cards: Investigate button, lore, and visual state (e.g. gold when investigated). | UI |
| **8** | **Monitor page** — View toggles: “Grid” and “3D Map” (Three.js) both work. | Optional; 3D can be placeholder. |
| **9** | **Monitor page** — “Live” indicator and periodic status refresh (e.g. 30s). | UX |
| **10** | **Navigation** — Nav toolbar and profile/game links include “Star Map 25” entry to `/vidgenerator/starmap25`. | `navigation-toolbar.js`, profile, points page |
| **11** | **Hunter game** — “Star Map 25” tab exists with progress, points earned, and quick-investigate grid. | `vidgenerator/game/index.html` |
| **12** | **Hunter game** — `loadStarMap25Tab()` fetches status and renders list; “Investigate” from tab calls API and refreshes. | Game tab logic |
| **13** | **Trophies** — Star Map tab has link “Star Map 25 Monitor (25 points)”; optional: show progress (X/25). | `vidgenerator/trophies/index.html` |
| **14** | **Shop** — Category “Star Map 25” with boosters (e.g. 1h/24h), gametime (+30m/+2h), and trophies (Terra, Segmentum Clear, Full Clear, Lore Master). | `shop_routes.py`, shop UI |
| **15** | **Shop** — starmap25 items purchasable; apply effect (e.g. game_points multiplier, time extension). | Backend + shop logic |
| **16** | **Effect clusters** — `starmap25_investigate`, `starmap25_view` present in Hunters effect-clusters API. | `hunters_game.py` (galactic cluster) |
| **17** | **User engagement** — Daily “Star Map Scout” (1 investigation) and weekly “Segmentum Explorer” (5 investigations) quests wired. | `user_engagement.py` |
| **18** | **Deploy** — Add `starmap25` manifest: `vidgenerator/starmap25/index.html`, `backend/routes/star_map_routes.py`, `data/star_map_25.json`. | `scripts/deploy.py` |
| **19** | **Docs** — Keep `STARMAP_25_WARHAMMER40K_RESEARCH.md` and HUNTERS_STAR_MAP sect. 10 in sync with API and UI. | Docs |
| **20** | **Test** — GET `/api/star-map/25`, GET `/api/star-map/25/status?user_id=`, POST `/api/star-map/25/investigate` (manual or script). | QA / script |
| **21** | **Test** — Full flow: open monitor → investigate one point → confirm game_points and lore unlock. | QA |
| **22** | **UX** — Monitor: clear error and loading states (API fail, timeout). | Frontend |
| **23** | **UX** — Optional: group 25 cards by Segmentum (Solar, Obscurus, Tempestus, Pacificus, Ultima) on monitor. | Frontend |
| **24** | **Trophies** — Terra (first), Segmentum Clear, Full Clear, Lore Master: award logic and display on Trophies page. | Backend + trophies UI |
| **25** | **Optional** — 3D map: position 25 points by segmentum/location; orbit controls and labels. | Three.js / future |

---

## Quick reference

- **Data:** `data/star_map_25.json` (25 points), investigations file or DB.
- **API base:** `GET /api/star-map/25`, `GET /api/star-map/25/status`, `POST /api/star-map/25/investigate` (and `/vidgenerator/api/...` prefixes).
- **UI:** `/vidgenerator/starmap25/` (Monitor), Hunter game “Star Map 25” tab, Trophies link, Shop category `starmap25`.
- **Deploy:** `python scripts/deploy.py starmap25` (after manifest is added).

*Document version: 2026-03-04. Star Map 25 — Todo 25 assignments.*
