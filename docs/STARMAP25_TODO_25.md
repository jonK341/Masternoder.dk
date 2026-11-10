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
| **5** | [x] | Expand deploy manifest with all `starmap25_*.json` gameplay files | Partial deploys shipped broken gameplay | `scripts/deploy.py` |
| **6** | [x] | Unit tests for map/status/health/events/build placement rules | Almost zero coverage | `tests/unit/test_star_map_25.py` |
| **7** | [x] | Wire shop Level Skip / Daily Reset Bonus / Structure Unlock consume → buildup | Catalog items do not affect gameplay | `POST /api/star-map/25/consume-shop-item`, shop seed |
| **8** | [x] | Make boosters reliable end-to-end (stable ids + detection + UI multiplier) | Economy core can miss purchased boosters | `shop_catalog_seed.py`, `_active_starmap25_boosters`, game tab |
| **9** | [x] | Special-unit acquisition + invade `special_unit_id` + apply `special_rule` | Design unfinished; invade ignored specials | units shop SKUs, deploy gate, invade |
| **10** | [x] | LLM invasion blurbs with template fallback | Invade hardcoded one-liner | `_generate_invasion_blurb()` |
| **11** | [x] | Game tab: deploy/invade controls + build deep-link | Secondary surface was investigate/collect only | `game/index.html` |
| **12** | [x] | Differentiate trophies: Terra first / full Segmentum / Lore Master ≠ Full Clear | Weak overlapping semantics | `_compute_starmap25_trophies()` |
| **13** | [x] | Show Star Map trophy progress on Trophies page | Link-only before | `trophies/index.html` |
| **14** | [ ] | Fail loudly / retry on JSON state write failures | Bare `except: pass` on saves | `_save_*` helpers |
| **15** | [ ] | Real 3D orbit + labels + focus-from-card | HUD claims drag-rotate; auto-spin only | `init3DView()` in `starmap25/index.html` |
| **16** | [ ] | Gate walkthrough unlocks (or rewrite copy as progress-only) | Tiers promise 3D/intel gates that are not enforced | `starmap25_walkthrough.json`, UI panels |
| **17** | [ ] | Surface leaderboard + analytics on the monitor | APIs exist; UI absent | leaderboard/analytics + monitor |
| **18** | [ ] | Complete OpenAPI (`planet-intel`, `sync-profile`, `ai-hint`, `ai-guide`, consume) | Spec incomplete | `_star_map_25_openapi_spec()` |
| **19** | [ ] | `GET /api/star-map/25?segmentum=` filter | Listed in 50-project backlog | `get_star_map_25()` |
| **20** | [ ] | Investigate rate limit (429 + Retry-After) | Abuse / farming gap | `investigate_star_map_25_point()` |
| **21** | [ ] | Optional `unlock_requirement` enforcement on investigate | Data project unrealized | map metadata + investigate validation |
| **22** | [ ] | Frontpage/dashboard widget: X/25 + points earned | Canvas visual only today | `static/js/frontpage-home.js` |
| **23** | [ ] | Shop AI / agent strategy inject starmap context | AI Improvements §5–6 | shop recommend + agent intelligence |
| **24** | [ ] | Persist investigations/buildup/invasions in DB (or file locks) | Multi-worker JSON races | state paths under `data/` |
| **25** | [~] | Keep this Top 25 as source of truth; uncheck false “done” in upgrade docs when touching them | Prevents false finished signal | this file, `STARMAP25_UPGRADES_TODO.md` |

---

## This push (continued)

1. Stable Star Map shop SKUs + consumable effects (`starmap25-level-skip`, daily reset, structure unlock, level pack, special units).
2. `POST /api/star-map/25/consume-shop-item` wires inventory → buildup state.
3. Booster detection for stable ids; game tab shows combined multiplier.
4. Special-unit unlock gate on deploy/invade; `special_unit_id` + `special_rule` bonuses; classified lore for Lore Master.
5. LLM invasion blurb with template fallback.
6. Game tab Deploy Guard / Invade / Build deep-link.
7. Differentiated trophy semantics + Trophies page progress panel.
8. Expanded unit tests.

## Quick verification

```bash
.venv/bin/python -m pytest tests/unit/test_star_map_25.py -q
curl -s 'http://127.0.0.1:5000/api/star-map/25/status?user_id=default_user' | head
# Shop: /shop?category=starmap25 — buy skip/reset/specials, then consume via API or monitor
# Game tab: Deploy Guard then Invade on investigated systems
# Trophies → Star Map tab: Star Map 25 trophy cards
```

## References

- `docs/STARMAP25_UPGRADES_TODO.md` (older checklist; many boxes optimistic)
- `docs/STARMAP25_UNITS_AND_INVASION_DESIGN.md`
- `docs/STARMAP25_AI_IMPROVEMENTS.md`
- `docs/STARMAP_25_50_PROJECTS.md`
- `docs/STARMAP25_UPGRADE_FINISH.md`

*Document version: 2026-11-10 (continued). Star Map 25 — active Top 25.*
