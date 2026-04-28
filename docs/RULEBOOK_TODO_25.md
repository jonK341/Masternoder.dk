# Rulebooks — Todo 25: Assignments & Tasks

**Purpose:** Checklist of **25 tasks** for the Compendium Rulebook V1–V15 system. Tick as you complete.  
**Reference:** `docs/COMPENDIUM_RULEBOOK_V1_V15.md` (master rulebook doc).

---

## Todo 25 — Tick list

| # | Assignment | Owner / Notes |
|---|------------|----------------|
| **1** | **V1 Core** — Documented in compendium; `data/rulebook_v1_core.json` exists; API serves it. | Compendium + rulebook_routes |
| **2** | **V2 Hunters** — Trophy Hunters Rulebook (19 spells, 5 sectors); `data/hunters_rulebook_v2.json`; `GET /api/game/hunters/rulebook`. | Compendium + hunters_game |
| **3** | **V3 Comm. Psychology** — 25 theories, 6 categories; `data/communication_psychology_theories.json`; study API. | Compendium + comm_psychology |
| **4** | **V3.2 Systemic Protocols** — 13 protocols in compendium; pointgiving subversion under V3. | Compendium (no separate data file) |
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
| **16** | **V15 Index** — Master index; `data/rulebook_index_v15.json`; catalog V1–V15 in sync with compendium. | Compendium + rulebook_routes |
| **17** | **API index** — `GET /api/rulebooks/index` and `/vidgenerator/api/rulebooks/index` return V15 index. | rulebook_routes.py |
| **18** | **API by version** — `GET /api/rulebooks/<version>` (v1..v15) returns correct rulebook from data_file. | rulebook_routes.py |
| **19** | **API agent-context** — `GET /api/rulebooks/agent-context` returns aggregated agent_prompt, tech_spec, user_guide, manual. | rulebook_routes.py |
| **20** | **Agent schema** — All rulebooks expose agent_prompt, tech_spec, user_guide, manual (and documentation, finish_lines where used). | COMPENDIUM_RULEBOOK_V1_V15.md |
| **21** | **Data files** — Every version in compendium “Data files reference” has corresponding JSON in `data/`. | data/ |
| **22** | **Compendium UI** — Compendium page loads and lists/links rulebooks (or links to agent-context). | vidgenerator/compendium or similar |
| **23** | **Agent knowledge API** — `POST /api/rulebooks/agent-knowledge` (if present) and GET for compendium display. | See V10 finish lines |
| **24** | **Docs sync** — COMPENDIUM_RULEBOOK_V1_V15.md stays in sync with rulebook_index_v15.json and data files. | Docs |
| **25** | **Deploy** — Rulebook routes and data files included in deploy; compendium doc in docs deploy if needed. | scripts/deploy.py |

---

## Lab companion (outside V1–V15 numbering)

- **`docs/LAB.md`** — Handbook for `/lab`, APIs, catalog, cooldowns; keep aligned with **`data/rulebook_v9_shop.json`** (`cross_rulebook_routing.lab_research`, `rules.lab_handbook`) and **`docs/RULEBOOK_CANON.md`** § Lab.
- **Shop UI** — `/shop` links to `/lab` for players; operators see handbook path in rulebook strip.

---

## Quick reference

- **Master doc:** `docs/COMPENDIUM_RULEBOOK_V1_V15.md`
- **API:** `GET /api/rulebooks/index` · `GET /api/rulebooks/<version>` · `GET /api/rulebooks/agent-context`
- **Data:** `data/rulebook_index_v15.json`, `data/rulebook_v1_core.json` … `data/rulebook_v14_analytics.json`, `data/hunters_rulebook_v2.json`, `data/communication_psychology_theories.json`
- **Backend:** `backend/routes/rulebook_routes.py`

*Document version: 2026-03-05. Rulebooks — Todo 25 assignments.*
