# Synchronization and Agent Knowledge

**Last updated:** 2026-02-25

## Rulebook V16 — Sync Mechanisms

Rulebook V16 documents all sync domains and mechanisms. See `data/rulebook_v16_sync.json` and `/compendium/rulebook-v16` (or `/compendium/rulebook-v16.html`).

**Sync domains:** unified_points, users, profiles, aggregator, trophies, achievements, battle, shop, quests, leaderboards, analytics, compendium, generator, gallery, stats, social, agent_skillsets, agent_knowledge, game, paypal, login, onboarding.

---

## Unified Points Sync Device

- **Service:** `backend/services/unified_points_sync.py`
- **Singleton:** `unified_points_sync_device`

Single source of truth for the point system. All point reads/writes should flow through this device so DB and file store stay in sync.

- **`get_canonical(user_id)`** — Returns canonical point state (prefer DB, fallback file).
- **`register_award(user_id, point_type, amount, source, metadata)`** — Award points; writes to file + DB and updates sync state.
- **`sync_now(user_id=None)`** — Run a sync pass; optional per-user or global.
- **`get_sync_status()`** — For `/api/sync/status`.

State is stored in the database (`sync_state`, `sync_domain_state` tables) with JSON fallback at `logs/unified_points_sync/sync_state.json`. Audit log: `sync_audit`. Health metrics: `sync_health`.

---

## Agent Skill Sets

- **Battle skill set:** Applied to **all agents** via `ensure_battle_skills_per_agent()`. Export for rulebooks/compendium via **`get_battle_skill_set_for_rulebook()`** (returns agents and their battle skill names; wire to Hunters rulebook and Battle V10).
- **Knowledge skills:** Every agent gets: `sync_compendium`, `update_rulebook_docs`, `maintain_page_info`, `learn_technology`, `write_rulebook_finish`, `agent_knowledge_push`. Applied in **`ensure_knowledge_skills_per_agent()`**, called on skillset load.

See `backend/services/agent_skillset.py`.

---

## Agent Learning → Rulebooks and Compendium

- **Data file:** `data/agent_learning_knowledge.json` — Agent-learned technology entries. Agents with knowledge skills can append via API.
- **GET** `/api/rulebooks/agent-knowledge` — Return agent-learned knowledge for rulebooks and compendium.
- **POST** `/api/rulebooks/agent-knowledge` — Append an entry (body: `id`, `source`, `title`, `text`, `rulebook_ref`).

Rulebooks and compendium pages can load this to show "Agent-learned technology" and keep docs in sync.

---

## Rulebook Documentation and Finish Lines

- **Schema:** In `rulebook_index_v15.json`, `agent_schema` includes **`documentation`** and **`finish_lines`** (closing notes and references).
- **Per-rulebook:** Each rulebook JSON can include **`documentation`** (string) and **`finish_lines`** (array of strings). Example: `data/rulebook_v10_battle.json` — finish lines reference sync device, battle skill set, and agent-knowledge API.

---

## Sync Status API

- **GET** `/api/sync/status` or `/vidgenerator/api/sync/status`

Returns:

- **unified_points** — Last sync time, source, count (from sync device).
- **users** — User count, last sync (from DB or logs/user_profiles).
- **profiles** — Profile count, last sync.
- **domains** — Per-domain last_sync_at and count for all SYNC_DOMAINS.
- **rulebooks** — Index `updated_at` and version.
- **agent_skillsets** — Battle skill set updated time, agents count.
- **agent_knowledge** — Knowledge file `updated_at`, entries count.

- **POST** `/api/sync/now` or `/vidgenerator/api/sync/now` — Trigger sync pass. Optional body: `{user_id}`. Returns updated status.

Important pages and sites can poll or display this to stay synchronized. Dashboard sync widget uses both endpoints.

---

## Summary

| Component | Purpose |
|-----------|---------|
| Unified Points Sync Device | Single source of truth for points; syncs DB and file store. |
| Agent battle skill set | Applied to all agents; exported for rulebooks/compendium. |
| Agent knowledge skills | Every agent can maintain compendium/rulebook and push learned tech. |
| Agent-knowledge API | GET/POST agent-learned entries; wired to rulebooks and compendium. |
| Rulebook documentation / finish_lines | Closing docs and references; synced from agent learning. |
| /api/sync/status | One place to check sync state for points, rulebooks, agents, knowledge. |
