# Lab — handbook & contributor notes

Audience: engineers extending lab progression, co-tech flows, or deployment. Players use **`/lab`**; this doc describes behavior and storage.

## What the Lab is

- **Research grid (Chapters II–IV):** Catalog-driven nodes in `data/lab_progression_catalog.json`. Unlocks use hunter level/XP, unified points, prerequisite nodes, and counts. State lives in **`hunters_profiles.profile_data`** (see keys below).
- **Exploration pulses:** Standard pulse rewards (+activity/game points, hunter XP) with a **3h** cooldown (`lab_exploration`); **deep scan** rewards more with a **12h** cooldown (`lab_deep_scan`).
- **Co-created technologies:** Drafts + optional **agent refine**; **1h** between new drafts per profile, **10h** between refines per draft, lifecycle states `draft` → `agent_suggested` → `user_accepted` / `archived`.
- **Research projects + agent presence:** `/lab` has named tool owners, **6h** cooldown research projects, a round table discussion room for agents/researchers, a 4D monitor with user-triggered sound, and an always-ten activity list.
- **Profile logbook:** `/profile?tab=lab` shows lab tier, research progress, project cooldowns, latest lab events, and active research projects.

## HTTP API (resolved user = `user_id` query/body via account resolution)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/lab/progression` | Catalog rows + `unlock_summary`, `unlocked`, `researched`, `cooldown_remaining_sec`, `interactable`; pulse cooldown summary. |
| GET | `/api/lab/overview` | Unified lab results: tool registry, point systems, research projects, round table, 4D monitor, ten todo points, profile logbook. |
| GET | `/api/lab/research-log` | Compact timeline of research, exploration, deep scans, and co-tech lifecycle events. |
| GET | `/api/lab/share-card` | Text share card for profile/social embeds. |
| GET/POST | `/api/lab/projects` | List/create research projects (POST 429 on 6h project cooldown). |
| POST | `/api/lab/roundtable/messages` | Add researcher/agent discussion message to the Lab round table. |
| POST | `/api/lab/explore` | Run exploration pulse; pass `mode: "deep_scan"` for rare 12h deep scan (429 on cooldown). |
| GET/POST | `/api/lab/chapter2-research` | Read/write researched id list (POST validates unlocks + re-research cooldowns). |
| GET/POST | `/api/lab/technologies` | List/create co-tech drafts (POST 429 on draft cooldown). |
| POST | `/api/lab/technologies/<id>/agent-refine` | LLM/stub refine (429 on per-draft refine cooldown). |
| POST | `/api/lab/technologies/<id>/status` | Set lifecycle status: `draft`, `agent_suggested`, `user_accepted`, `archived`. |

Embed-friendly summary for game/UI: **`GET /api/game/hunters/battle-bridge-snapshot`** (includes lab tier / counts where wired).

## Profile JSON keys (`profile_data`)

| Key | Meaning |
|-----|---------|
| `lab_chapter2_research` | `string[]` — active researched node ids (catalog ids, all chapters). |
| `lab_chapter2_bonus_awarded` | `string[]` — ids that already received first-touch unified points. |
| `lab_chapter2_updated_at` | ISO timestamp of last research write. |
| `lab_research_reenable_after` | `Record<nodeId, iso>` — re-research not allowed until time (after user **clears** a node with `research_cooldown_sec`). |
| `lab_exploration` | `{ last_at, count }` — exploration pulse cooldown + counter. |
| `lab_deep_scan` | `{ last_at, count }` — deep scan cooldown + counter. |
| `lab_research_projects` | Array of research project objects (`id`, `title`, `question`, `track`, `agent_id`, `status`, `progress`, timestamps). |
| `lab_next_research_project_at` | ISO — earliest time another research project can be created. |
| `lab_roundtable` | Array of round table messages (`speaker`, `role`, `topic`, `message`, `created_at`). |
| `lab_technologies` | Array of draft objects (`id`, `name`, `pitch`, `status`, …, optional `next_agent_refine_at`). |
| `lab_next_tech_draft_at` | ISO — earliest time another draft can be created. |

Pruned server-side where helpers drop expired cooldown entries on write/read paths as implemented in `backend/routes/lab_routes.py`.

## Rulebook cross-links (Shop V9)

- **`data/rulebook_v9_shop.json`**: `cross_rulebook_routing.lab_research` ties Shop identity to Lab; `rules` entry **`lab_handbook`** points contributors here and to `/lab`.
- **`docs/RULEBOOK_CANON.md`**: canonical **§ Lab** for humans; Battle **Rulebooks** tab links `/lab` and cites `RULEBOOK_CANON` + this file.

## Catalog (`data/lab_progression_catalog.json`)

- Top-level `description` documents policy.
- Each **upgrade** object: `id`, `chapter`, `icon`, `name`, `desc`, `tier`, `unlock` (object, stripped from public API output), public `unlock_summary` (derived), `first_research_points` (optional), **`research_cooldown_sec`** (optional; re-research gate after clear).
- **Unlock** supports: `min_hunter_level`, `min_total_xp`, `min_unified_xp_total`, `min_game_points`, `min_battle_points`, `requires_researched` (array of ids), `min_researched_total`.

After editing the JSON, restart workers or rely on **mtime-based catalog reload** in `lab_routes` (cache invalidates when the file changes).

## Frontend

- **`lab/index.html`** — ideas workbench, agent tool registry, research project cooldowns, round table, 4D monitor + sound, ten todo points, grid, exploration/deep scan, co-tech lifecycle, cooldown UI ticker, policy `<details>`, catalog cache + offline POST queue.
- **`profile/index.html`** — Lab research logbook tab via aggregated profile payload (`lab_logbook`).
- **`static/js/game-battle-bridge.js`** — surfaces lab summary in game bridge card when API provides it.

## Deploy checklist

Ensure **`deploy.py`** includes at least: `lab/index.html`, `shop/index.html`, `battle/index.html`, `backend/routes/lab_routes.py`, `data/lab_progression_catalog.json`, `service-worker.js`, `static/js/service-worker-gatherer.js`, **`backend/routes/rulebook_routes.py`**, the full **`data/rulebook_*.json`** bundle (index + `hunters_rulebook_v2.json` + `communication_psychology_theories.json` + V1/V3.2/V4–V14/V16 + **`rulebook_v9_shop.json`**), `backend/register_blueprints.py`, `static/js/game-battle-bridge.js`, `backend/routes/api_monitor_routes.py` (monitor fallbacks), **`docs/RULEBOOK_CANON.md`**, **`docs/RULEBOOK_AGENT_CONTEXT.md`**, **`docs/RULEBOOK_TODO_25.md`**, and this file: **`docs/LAB.md`**.

## Troubleshooting

- **400 `unlock_failed`:** Progression requirements not met; check `/api/lab/progression` `points` + hunter level vs catalog `unlock`.
- **429 `research_cooldown`:** Cleared a node that has `research_cooldown_sec`; wait or inspect `lab_research_reenable_after`.
- **429 explore / deep scan / project / draft / refine cooldowns:** Expected; timers are profile-backed.
- **Empty catalog in UI:** GET progression failed or DB unavailable; static fallback list in `lab/index.html` still renders tiles without server unlock flags.

---

## Ideas backlog (started on `/lab`)

1. **In-lab “research log”** — Implemented as `GET /api/lab/research-log` and the workbench log panel.
2. **Per-node tooltips** — Implemented via derived `unlock_summary` on progression rows and tile hover/focus labels.
3. **“Recommended next”** — Implemented as a highlighted next interactable node in the research grid.
4. **Shareable lab card** — Implemented as `GET /api/lab/share-card` + copy action (text card; image can follow later).
5. **Webhook or agent hook** — Started as an opt-in Event Tracker task from the workbench.
6. **Chapter IV stub** — Started with three `chapter: 4` catalog rows behind `c3_foundry_core`.
7. **Exploration variants** — Implemented as `mode: "deep_scan"` on `/api/lab/explore` with a 12h cooldown.
8. **Co-tech lifecycle** — Implemented with `user_accepted` / `archived` controls and status API.
9. **Localization** — Started with workbench English/Danish copy switching; full catalog i18n remains future work.
10. **Offline-first lab** — Started with catalog local cache and localStorage POST replay queue; server validation remains authoritative.
11. **Agent presence / more tools** — Implemented as `/api/lab/overview` tool registry with named owner agents and UI cards.
12. **Research project cooldowns** — Implemented as `GET/POST /api/lab/projects` with a 6h creation cooldown.
13. **Profile logbook** — Implemented in the profile aggregated payload and `/profile?tab=lab`.
14. **Unified point systems in Lab results** — Implemented in `/api/lab/overview` `point_systems` and rendered in the workbench output.
15. **Round table discussion room** — Implemented with researcher/agent messages and tech progression topic.
16. **4D monitor + sound + ten todos** — Implemented in the lab overview panel; sound is user-triggered and todos always return ten rows.

---

*Last aligned with lab routes + catalog structure in-repo; adjust dates/keys if schema migrations rename columns.*
