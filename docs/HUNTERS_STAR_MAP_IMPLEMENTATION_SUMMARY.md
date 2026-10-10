# Hunters Game + Star Map — Implementation Summary

**Date:** 2026-01-27  
**Status:** Implemented (pre-upload verification)

---

## 1. Star Map

- **`data/star_map.json`**  
  - 7 nearest stars (Sun, Proxima Centauri, Alpha Centauri, Barnard’s Star, Lalande 21185, Sirius, Epsilon Eridani, Ross 128).
  - For each: `planets`, `life_bearing`, `life_label` (host → b), `info`, `flyers`, `specials`.
- **`view_star_map`** added to Electric Magnet specials and to agent specials in skillsets.

**APIs:**

- `GET /api/star-map`, `GET /vidgenerator/api/star-map`
- `GET /api/game/hunters/star-map`
- `GET /api/star-map/stars`
- `GET/POST /api/agent-tech/agent_electric_magnet/view_star_map`

**Blueprint:** `star_map_bp` registered in `register_blueprints.py`.

---

## 2. Electric Magnet Specials

- **Specials:** `run_verification`, `run_dna_test`, `view_star_map`.
- **`view_star_map`** implemented in `agent_electric_magnet.py`; loads `data/star_map.json`, tracks usage, returns `star_map` in response.
- Routes: `run_verification`, `run_dna_test`, `view_star_map` (plus execute/download).

---

## 3. Trophy Hunters Game

**New endpoints:**

- `GET /api/game/hunters/specials` — returns specials list.
- `GET /api/game/hunters/rulebook` — Rulebook V.2 (19 spells, sectors).
- `GET /api/game/hunters/effect-clusters` — effect clusters (galactic, verification, combat, support, utility).
- `GET /api/game/hunters/profiling` — profiling (agent_tech, specials, level_info, geo_ref placeholder).
- `POST /api/game/hunters/award-game-points` — awards `game_points` via unified points.

**Rulebook V.2:** `data/hunters_rulebook_v2.json` — 19 theme-based spells in 5 sectors (Galactic, Verification, Combat, Support, Utility).

**Unified points:** `game_points` added; default user JSON and `add_points` support it.

---

## 4. Database

**Migration:** `scripts/hunters_star_map_migration.py` creates:

- `star_map_visits`
- `hunters_game_sessions`
- `hunters_profiles`
- `hunters_spells`
- `agent_geo_refs`

Run: `python scripts/hunters_star_map_migration.py`.

---

## 5. UI

- **Trophies page:** “Star Map” tab; fetches `/api/star-map`, renders 7 stars (name, life_label, distance, info).
- **Profile page:** “Trophy Hunters Game” card with links to Game, Trophies, Star Map API; mentions specials.

---

## 6. Agents & Skillsets

- **Specials** in `logs/agent_skillsets/skillsets.json`: `["run_verification", "run_dna_test", "view_star_map"]` for agents that have specials.
- **Galactic tech tree:** `electric_magnet_tech` updated with `view_star_map` and `star_map` path.

---

## 7. Verification Checklist (before upload/deploy)

- [ ] Run `python scripts/hunters_star_map_migration.py`.
- [ ] `GET /api/star-map` returns `star_map` with `stars` array.
- [ ] `GET /api/game/hunters/specials` returns `specials` array.
- [ ] `GET /api/game/hunters/rulebook` returns rulebook with sectors and `all_spell_ids`.
- [ ] `GET /api/game/hunters/effect-clusters` returns `effect_clusters`.
- [ ] `GET /api/game/hunters/profiling?user_id=default_user` returns profiling object.
- [ ] `POST /api/game/hunters/award-game-points` with `{ "user_id": "default_user", "amount": 10 }` updates `game_points`.
- [ ] Trophies page “Star Map” tab loads and shows stars.
- [ ] Profile page shows “Trophy Hunters Game” block with links.
- [ ] **Do not restart** services until all checks pass.

---

## 8. Optional / Placeholders

- **Checkpoint on/off:** Referenced in rulebook (spell `checkpoint`); no generator toggle implemented yet.
- **3D monitor:** Placeholder for future vidgenerator 3D visuals.
- **Aggregator / fulfill API:** Rulebook spell `aggregator_fill`; aggregator logic to “fill” missing Hunters data not implemented.
- **GPS / geo-ref:** `agent_geo_refs` table and `geo_ref` in profiling; schema ready, wiring TBD.
- **Event tracker for agents:** New task placeholder; not implemented in this pass.
- **Debugger agent skills:** Skillsets and specials are exposed; debugger UI wiring TBD.

---

## 9. Summary

Star map (7 stars, life-bearing b), Electric Magnet specials (including `view_star_map`), Hunters game (specials, rulebook V.2, effect clusters, profiling, game points), new DB tables, and UI (trophies Star Map tab, profile game section) are in place. Verify via the checklist above before upload and deployment; do not restart services until verification is complete.

---

## 10. Star Map 25 (Imperium Investigation Grid) — 2026-03-04

- **Purpose:** 25 investigation points across the Segmentae Majoris (Warhammer 40,000 themed). Each point is a star system (host + planets); users investigate to earn `game_points` and unlock lore.
- **Data:** `data/star_map_25.json` — 25 points (Terra, Mars, Cypra Mundi, Hydraphur, Bakka, Kar Duniash, Macragge, Fenris, Cadia, Baal, Nocturne, Medusa, Olympia, Caliban, Chogoris, Barbarus, Chemos, Colchis, Nostramo, Prospero, Cthonia, Deliverance, Nuceria, Inwit, Ryza). Each has `id`, `name`, `host_star`, `segmentum`, `planets`, `life_bearing`, `info`, `point_value`, `lore`, `icon`.
- **Research:** `docs/STARMAP_25_WARHAMMER40K_RESEARCH.md` — WH40K galaxy summary, 25-point table (host star, planets, lore), brainstorm, tech spec.
- **API:**
  - `GET /api/star-map/25`, `GET /vidgenerator/api/star-map/25` — full 25-point map.
  - `GET /api/star-map/25/status?user_id=` — investigated_ids, total_points_earned.
  - `POST /api/star-map/25/investigate` — body `{ "user_id", "point_id" }` — one-time game_points award per point per user; investigations stored in `data/star_map_25_investigations.json`.
- **UI:**
  - **Star Map 25 Monitor:** `/vidgenerator/starmap25/` — dashboard: progress (X/25), points earned, grid of 25 cards with Investigate button and lore.
  - **Trophies:** Star Map tab has link “Star Map 25 Monitor (25 points)” to the monitor.
- **Blueprint:** Same `star_map_bp`; page `starmap25` added to `all_page_routes` PAGES list.

**Live, 3D, coordinated monitoring (2026-03):**
- Monitor page: live status (30s refresh), "Last updated" and "Live" indicator; view toggles Grid / 3D Map.
- 3D map: Three.js scene with 25 points as spheres in galactic layout; orbit/rotate.
- Coordinated monitoring panel: 25-cell grid (1–25) showing investigated (gold) vs not.

**Shop:** Boosters and gametime (Star Map 25 Booster 1h/24h, Game Time +30m/+2h) and trophies (Terra, Segmentum Clear, Full Clear, Lore Master) in category `starmap25`. Shop UI has category button "Star Map 25".

**Hunter game:** New tab "Star Map 25" with progress, points earned, specials (View Star Map, Run Verification, Run DNA Test), quick-investigate grid, link to full monitor. Effect clusters extended with `starmap25_investigate`, `starmap25_view`.
