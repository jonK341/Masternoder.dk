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
| **21** | [x] | Optional `unlock_requirement` enforcement on investigate | Terra → fortresses → systems; Cadia gates deep traitor worlds | `star_map_25.json` + investigate 403 |
| **22** | [x] | Remove frontpage Star Map 4D monitor; keep full monitor on `/starmap25/` | Frontpage canvas deleted; smart link remains | `index.html`, `frontpage-home.js/.css` |
| **23** | [x] | Shop AI / agent strategy inject starmap + tech context | Recommendations + `develop_strategy` include Star Map 25 + EM/Event Tracker | shop recommend + agent intelligence |
| **24** | [x] | File locks on investigations/buildup/invasions JSON saves | Exclusive `.lock` + atomic replace (multi-worker safer) | `_json_state_lock` / `_save_json_state` |
| **25** | [x] | Keep this Top 25 as source of truth | All 25 closed for this push | this file |

---

## New techs (this push)

1. **Electric Magnet** `view_star_map` now returns Star Map 25 (+ classic 7 stars) and monitor URL.
2. **Event Tracker** receives investigate/build/deploy/collect/invade tasks from Star Map actions.
3. Monitor **Guide** tab: tech panel (status / view / verification / DNA) + leaderboard/analytics.
4. 3D Monitor config enabled; orbit drag, labels, focus-from-card.
5. Frontpage Star Map 4D monitor removed — full monitor lives only on `/starmap25/`.
6. `unlock_requirement` gates on investigate; shop AI + agent strategy get Star Map context; JSON state file locks.

## Quick verification

```bash
.venv/bin/python -m pytest tests/unit/test_star_map_25.py -q
curl -s 'http://127.0.0.1:5000/api/star-map/25?segmentum=Solar'
curl -s -X POST http://127.0.0.1:5000/api/agent-tech/agent_electric_magnet/view_star_map -H 'Content-Type: application/json' -d '{"user_id":"default_user"}'
# Open / — no Star Map 4D canvas; smart link to /starmap25/ still present
# Open /starmap25/ — full Play/Monitor UI
```

## References

- `docs/STARMAP25_UPGRADES_TODO.md`
- `docs/STARMAP25_UNITS_AND_INVASION_DESIGN.md`
- `docs/STARMAP25_AI_IMPROVEMENTS.md`
- `backend/services/agent_techs/agent_electric_magnet.py`
- `backend/services/agent_techs/agent_event_tracker.py`

*Document version: 2026-11-10 (Top 25 complete). Star Map 25 — active Top 25.*
