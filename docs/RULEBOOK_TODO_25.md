# Rulebooks — Todo 25: Assignments & Tasks

**Purpose:** Checklist of **25 tasks** for the Compendium Rulebook V1–V16 system. Tick as you complete.  
**Reference:** `docs/COMPENDIUM_RULEBOOK_V1_V15.md` · `docs/RULEBOOK_READERS.md`

**Last updated:** 2026-06-17

---

## Todo 25 — Tick list

| # | Assignment | Owner / Notes |
|---|------------|----------------|
| **1** | **V1 Core** — Documented in compendium; `data/rulebook_v1_core.json` exists; API serves it. | Compendium + rulebook_routes |
| **2** | **V2 Hunters** — Trophy Hunters Rulebook (19 spells, 5 sectors); `data/hunters_rulebook_v2.json`; `GET /api/game/hunters/rulebook`. | Compendium + hunters_game |
| **3** | **V3 Comm. Psychology** — 25 theories, 6 categories; `data/communication_psychology_theories.json`; study API. | Compendium + comm_psychology |
| **4** | **V3.2 Systemic Protocols** — 13 protocols; `data/rulebook_v3_2_systemic_protocols.json`; viewer at `/compendium/rulebook-v3-2`. | Compendium + rulebook viewer |
| **5** | **V4 Star Map** — 7 stars, verification, DNA; `data/rulebook_v4_star_map.json`; star-map API. | Compendium + star_map_routes |
| **6** | **V5 Effect Clusters** — 5 clusters; `data/rulebook_v5_effect_clusters.json`; `GET /api/game/hunters/effect-clusters`. | Compendium + hunters_game |
| **7** | **V6 Electric Magnet** — Specials, tech tree; `data/rulebook_v6_electric_magnet.json`. | Compendium |
| **8** | **V7 Unified Points** — Point types and triggers; `data/rulebook_v7_unified_points.json`; add_points, triggers. | Compendium + unified_points |
| **9** | **V8 Agents & Skillsets** — Specials, skillsets.json, debugger; `data/rulebook_v8_agents.json`. | Compendium + agent_skillset |
| **10** | **V9 Shop** — Items, purchases, inventory; `data/rulebook_v9_shop.json`; shop_routes. | Compendium + shop_routes |
| **11** | **V10 Battle** — Profiling, leaderboard, geo_ref, aggregator; `data/rulebook_v10_battle.json`. | Compendium + hunters_game |
| **12** | **V11 DNA** — dna_manipulation_points, dna_cloning_points, run_dna_test; `data/rulebook_v11_dna.json`. | Compendium |
| **13** | **V12 Generator** — Video generator, content categories, user context; `data/rulebook_v12_generator.json`. | Compendium + video_generator_service |
| **14** | **V13 Geo & Session** — geo_reference, checkpoint, extend_session, aggregator_fill; `data/rulebook_v13_geo_session.json`. | Compendium |
| **15** | **V14 Analytics** — Event tracker, analytics, unified dashboard; `data/rulebook_v14_analytics.json`. | Compendium |
| **16** | **V15 Index** — Master index; `data/rulebook_index_v15.json`; catalog V1–V16 in sync with compendium. | Compendium + rulebook_routes |
| **17** | **V16 Sync** — Sync device + domains; `data/rulebook_v16_sync.json`; `/compendium/rulebook-v16`; page 25 in compendium API. | ✓ 2026-06-17 |
| **18** | **API index** — `GET /api/rulebooks/index` returns V1–V16 catalog. | rulebook_routes.py |
| **19** | **API by version** — `GET /api/rulebooks/<version>` (v1..v16, v3.2) returns correct rulebook from data_file. | rulebook_routes.py |
| **20** | **API agent-context** — `GET /api/rulebooks/agent-context` returns aggregated agent_prompt, tech_spec, user_guide, manual. | rulebook_routes.py |
| **21** | **Agent schema** — All rulebooks expose agent_prompt, tech_spec, user_guide, manual (and documentation, finish_lines where used). | COMPENDIUM_RULEBOOK_V1_V15.md |
| **22** | **Data files** — Every version in compendium “Data files reference” has corresponding JSON in `data/`. | data/ |
| **23** | **Compendium UI** — `/compendium/` grid lists V1–V16 + V3.2; Trophies tab links to pages API. | compendium/index.html |
| **24** | **Reader progress** — View tracker maps pages 1–25; aggregator progress reader shows compendium + story; docs in RULEBOOK_READERS.md. | ✓ 2026-06-17 |
| **25** | **Deploy** — `python scripts/deploy.py compendium` uploads routes, data, HTML, tracker JS. | scripts/deploy.py |

---

## Lab companion (outside V1–V16 numbering)

- **`docs/LAB.md`** — Handbook for `/lab`, APIs, catalog, cooldowns; keep aligned with **`data/rulebook_v9_shop.json`** (`cross_rulebook_routing.lab_research`, `rules.lab_handbook`) and **`docs/RULEBOOK_CANON.md`** § Lab.
- **Shop UI** — `/shop` links to `/lab` for players; operators see handbook path in rulebook strip.

---

## Quick reference

- **Master doc:** `docs/COMPENDIUM_RULEBOOK_V1_V15.md`
- **Readers doc:** `docs/RULEBOOK_READERS.md`
- **API:** `GET /api/rulebooks/index` · `GET /api/rulebooks/<version>` · `GET /api/rulebooks/agent-context` · `GET /api/compendium/pages` · `POST /api/compendium/view`
- **Data:** `data/rulebook_index_v15.json`, `data/rulebook_v1_core.json` … `data/rulebook_v16_sync.json`, `data/hunters_rulebook_v2.json`, `data/communication_psychology_theories.json`
- **Backend:** `backend/routes/rulebook_routes.py` · `backend/routes/compendium_routes.py`

*Document version: 2026-06-17. Rulebooks — Todo 25 assignments (V1–V16 catalog).*
