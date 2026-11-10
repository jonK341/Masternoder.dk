# Star Map 25 — Top 25 Todo (active)

**Purpose:** Actionable Top 25 for finishing Star Map 25. Replaces the old MVP checklist; older upgrade docs marked many items done while several loops are still thin, expired, or unwired.

**Scope:** Monitor UI (`/starmap25/`), `backend/routes/star_map_routes.py`, agent techs (Electric Magnet / Event Tracker), `data/starmap25_*.json`, shop/game/trophies integrations, tests, deploy.

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
| **7** | [x] | Wire shop Level Skip / Daily Reset Bonus / Structure Unlock consume → buildup | Catalog items do not affect gameplay | `POST /api/star-map/25/consume-shop-item` |
| **8** | [x] | Make boosters reliable end-to-end (stable ids + detection + UI multiplier) | Economy core can miss purchased boosters | shop seed + booster matcher |
| **9** | [x] | Special-unit acquisition + invade `special_unit_id` + apply `special_rule` | Design unfinished | units shop SKUs, deploy gate, invade |
| **10** | [x] | LLM invasion blurbs with template fallback | Invade hardcoded one-liner | `_generate_invasion_blurb()` |
| **11** | [x] | Game tab: deploy/invade controls + build deep-link | Secondary surface incomplete | `game/index.html` |
| **12** | [x] | Differentiate trophies: Terra first / full Segmentum / Lore Master ≠ Full Clear | Weak overlapping semantics | `_compute_starmap25_trophies()` |
| **13** | [x] | Show Star Map trophy progress on Trophies page | Link-only before | `trophies/index.html` |
| **14** | [x] | Fail loudly / retry on JSON state write failures | Bare `except: pass` on saves | `_save_json_state()` atomic write + error log |
| **15** | [x] | Real 3D orbit + labels + focus-from-card | HUD claimed drag-rotate | `init3DView()` + `config_3d_monitor.json` enabled |
| **16** | [x] | Clarify walkthrough as progress markers (not hard gates) | Copy overpromised unlocks | `starmap25_walkthrough.json` + Progress tab |
| **17** | [x] | Surface leaderboard + analytics on the monitor | APIs existed; UI absent | Guide tab leaderboard panel |
| **18** | [x] | Complete OpenAPI (planet-intel, sync-profile, ai-*, consume) | Spec incomplete | `_star_map_25_openapi_spec()` |
| **19** | [x] | `GET /api/star-map/25?segmentum=` filter | 50-project backlog | `get_star_map_25()` |
| **20** | [x] | Investigate rate limit (429 + Retry-After) | Abuse / farming gap | `_investigate_rate_limited()` |
| **21** | [ ] | Optional `unlock_requirement` enforcement on investigate | Data project unrealized | map metadata + investigate validation |
| **22** | [ ] | Frontpage/dashboard widget: X/25 + points earned | Canvas visual only today | `static/js/frontpage-home.js` |
| **23** | [~] | Shop AI / agent strategy inject starmap + tech context | Partial: Event Tracker + EM wired into map actions | shop recommend + agent intelligence |
| **24** | [ ] | Persist investigations/buildup/invasions in DB (or file locks) | Multi-worker JSON races | state paths under `data/` |
| **25** | [~] | Keep this Top 25 as source of truth | Prevents false finished signal | this file |

---

## New techs (this push)

1. **Electric Magnet** `view_star_map` now returns Star Map 25 (+ classic 7 stars) and monitor URL.
2. **Event Tracker** receives investigate/build/deploy/collect/invade tasks from Star Map actions.
3. Monitor **Guide** tab: tech panel (status / view / verification / DNA) + leaderboard/analytics.
4. 3D Monitor config enabled; orbit drag, labels, focus-from-card.

## Quick verification

```bash
.venv/bin/python -m pytest tests/unit/test_star_map_25.py -q
curl -s 'http://127.0.0.1:5000/api/star-map/25?segmentum=Solar'
curl -s -X POST http://127.0.0.1:5000/api/agent-tech/agent_electric_magnet/view_star_map -H 'Content-Type: application/json' -d '{"user_id":"default_user"}'
# Open /starmap25/?tab=guide — tech panel + leaderboard
# Open 3D Map — drag to rotate, click system to jump to card
```

## References

- `docs/STARMAP25_UPGRADES_TODO.md`
- `docs/STARMAP25_UNITS_AND_INVASION_DESIGN.md`
- `docs/STARMAP25_AI_IMPROVEMENTS.md`
- `backend/services/agent_techs/agent_electric_magnet.py`
- `backend/services/agent_techs/agent_event_tracker.py`

*Document version: 2026-11-10 (new techs). Star Map 25 — active Top 25.*
