# Star Map 25 — Top 25 Todo (active)

**Purpose:** Actionable Top 25 for finishing Star Map 25. Replaces the old MVP checklist; older upgrade docs marked many items done while several loops are still thin, expired, or unwired.

**Scope:** Monitor UI (`/starmap25/`), `backend/routes/star_map_routes.py`, `data/starmap25_*.json`, shop/game/trophies integrations, tests, deploy.

**Started:** 2026-11-10 (Europe/Copenhagen).

---

## Status legend

- `[x]` done in this push or already solid
- `[~]` partially done / next slice
- `[ ]` open

---

## Top 25

| # | Status | Todo | Why | Primary paths |
|---|--------|------|-----|---------------|
| **1** | [x] | Fix Play/Monitor layout so point cards stay visible with filters/buildup | Cards hid on Monitor while filters lived there | `starmap25/index.html` |
| **2** | [x] | Refresh live temporary events (windows had expired 2026-06-01) | Banners/modifiers/analytics idle | `data/starmap25_events.json` |
| **3** | [x] | Always-on action logging for investigate/build/deploy/collect/invade | Analytics only logged when an event matched | `star_map_routes.py` `_log_event_participation` |
| **4** | [x] | Honor `max_per_planet` by building type (allow different buildings on one planet) | Build blocked any second building | `build_star_map_25()`, `starmap25_buildings.json` |
| **5** | [x] | Expand deploy manifest with all `starmap25_*.json` gameplay files | Partial deploys shipped broken loops | `scripts/deploy.py` |
| **6** | [x] | Unit tests for map/status/health/events/build placement rules | Almost zero coverage | `tests/unit/test_star_map_25.py` |
| **7** | [ ] | Wire shop Level Skip / Daily Reset Bonus / Structure Unlock consume → buildup | Catalog items do not affect gameplay | `shop_catalog_seed.py`, `shop_routes.py`, `star_map_routes.py` |
| **8** | [ ] | Make boosters reliable end-to-end (purchase → active → multipliers) | Economy core can miss purchased boosters | `_active_starmap25_boosters()`, shop purchase path |
| **9** | [ ] | Special-unit acquisition + invade `special_unit_id` + apply `special_rule` | Design unfinished; invade ignores specials | `starmap25_units.json`, `invade_star_map_25()` |
| **10** | [ ] | LLM invasion blurbs with template fallback | Invade still hardcodes one-liner | `invade_star_map_25()`, `llm_service` |
| **11** | [ ] | Game tab: build/deploy/invade controls (or deep-link with prefilled system) | Secondary surface is investigate/collect only | `game/index.html` `loadStarMap25Tab()` |
| **12** | [ ] | Differentiate trophies: Segmentum Clear = full segmentum; Lore Master ≠ Full Clear; Terra = first investigate | Current semantics are weak/overlapping | `_compute_starmap25_trophies()`, trophies UI |
| **13** | [ ] | Show Star Map trophy progress on Trophies page | Link-only today | `trophies/index.html` |
| **14** | [ ] | Fail loudly / retry on JSON state write failures | Bare `except: pass` on saves | `_save_*` helpers |
| **15** | [ ] | Real 3D orbit + labels + focus-from-card | HUD claims drag-rotate; auto-spin only | `init3DView()` in `starmap25/index.html` |
| **16** | [ ] | Gate walkthrough unlocks (or rewrite copy as progress-only) | Tiers promise 3D/intel gates that are not enforced | `starmap25_walkthrough.json`, UI panels |
| **17** | [ ] | Surface leaderboard + analytics on the monitor | APIs exist; UI absent | `star_map_25_leaderboard`, `star_map_25_analytics`, monitor |
| **18** | [ ] | Complete OpenAPI (`planet-intel`, `sync-profile`, `ai-hint`, `ai-guide`) | Spec incomplete | `_star_map_25_openapi_spec()`, `docs/STARMAP25_API_OPENAPI.md` |
| **19** | [ ] | `GET /api/star-map/25?segmentum=` filter | Listed in 50-project backlog | `get_star_map_25()` |
| **20** | [ ] | Investigate rate limit (429 + Retry-After) | Abuse / farming gap | `investigate_star_map_25_point()` |
| **21** | [ ] | Optional `unlock_requirement` enforcement on investigate | Data project unrealized | map metadata + investigate validation |
| **22** | [ ] | Frontpage/dashboard widget: X/25 + points earned | Canvas visual only today | `static/js/frontpage-home.js` |
| **23** | [ ] | Shop AI / agent strategy inject starmap context | AI Improvements §5–6 | shop recommend + agent intelligence |
| **24** | [ ] | Persist investigations/buildup/invasions in DB (or file locks) | Multi-worker JSON races | state paths under `data/` |
| **25** | [~] | Keep this Top 25 as source of truth; uncheck false “done” in upgrade docs when touching them | Prevents false finished signal | this file, `STARMAP25_UPGRADES_TODO.md` |

---

## This push (started work)

1. New Top 25 checklist (this document).
2. Play/Monitor cards visibility fix.
3. Fresh event windows (active + upcoming).
4. Always-on action analytics log.
5. `max_per_planet` placement rules.
6. Full `starmap25` deploy manifest.
7. Focused unit tests for health/map/events/build rules.

## Quick verification

```bash
.venv/bin/python -m pytest tests/unit/test_star_map_25.py -q
curl -s http://127.0.0.1:5000/api/star-map/25/health
curl -s http://127.0.0.1:5000/api/star-map/25/events
# Open /starmap25/ — Play shows cards; Monitor shows cards + filters + buildup
```

## References

- `docs/STARMAP25_UPGRADES_TODO.md` (older checklist; many boxes optimistic)
- `docs/STARMAP25_UNITS_AND_INVASION_DESIGN.md`
- `docs/STARMAP25_AI_IMPROVEMENTS.md`
- `docs/STARMAP_25_50_PROJECTS.md`
- `docs/STARMAP25_UPGRADE_FINISH.md`

*Document version: 2026-11-10. Star Map 25 — active Top 25.*
