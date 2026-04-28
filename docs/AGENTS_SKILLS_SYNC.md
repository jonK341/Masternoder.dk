# Agent Skills ↔ Skill Sets Sync

**Purpose:** Clarify how user-facing agent skills connect to the global agent skill sets and how to keep them in sync.

---

## 1. Two Layers

| Layer | Service | Role |
|-------|---------|------|
| **Global skill sets** | `backend.services.agent_skillset` | Defines all agents and their skills (battle, sales, PayPal, top25, shared growth, etc.). Stored in `logs/agent_skillsets/skillsets.json`. |
| **Per-user assignments** | `backend.services.user_agent_skills` | Which agents and skills are assigned to each user. Stored in `logs/user_agent_skills/<user_id>.json`. |

Profile, game, and shop use both: **agent_skillset** for available skills and power totals; **user_agent_skills** for “my agents” and which skills the user has.

---

## 2. How They Connect

- **Onboarding:** `user_onboarding` calls `user_agent_skills.assign_initial_skills(user_id, scraped_info)` and can set `profile.agent_skillset_id` (e.g. `balanced`, `creator`, `battle`).
- **Lazy seed (no JSON yet):** `user_agent_skills.get_user_skills(user_id)` calls `assign_initial_skills(user_id, {})` when `logs/user_agent_skills/<user_id>.json` is missing, so new users immediately get a **balanced path** assignment (see below) and `agent_db_service` has agents to merge.
- **Profile / My Agents:** Profile aggregated and “My agents” APIs merge data from `agent_db_service` (activity, progress) with `user_agent_skills.get_user_skills(user_id)` and `agent_skillset.get_all_skillsets()` so the UI shows the user’s assigned agents and their skills.
- **Shop:** Shop uses `agent_skillset.get_all_skillsets()` for agent offers and “Skills” category; purchases don’t change skill sets but can add inventory; user progress is still from user_agent_skills + agent_skillset.

---

## 2a. Balanced path (default seed)

When behavior is neutral / unknown, **`skill_path: balanced`** assigns four agents and **10 skills**:

| Agent | Skills (level 1) |
|--------|------------------|
| `content_generator_agent` | `generate_video`, `ai_assist_task` |
| `analytics_agent` | `track_metrics`, `analyze_user_behavior`, `ai_suggest_next` |
| `learning_agent` | `ai_follow_user_action`, `ai_win_with_user`, `ai_nice_and_easy` |
| **`reporter_agent`** | **`broadcast`**, **`news_report_ingredients`** |

`reporter_agent` supports **broadcast** and **knowledge-sharing “news report” ingredients** (structured snippets from `data/agent_learning_knowledge.json`, platform hints, optional activity log). Other paths (creator, battle, social, analytics, ai) keep their existing two–three agent mixes unless extended separately.

---

## 2b. Stale skills files (inactivity maintenance)

Long-idle users can accumulate orphaned JSON under `logs/user_agent_skills/`. **`UserAgentSkills.maintenance_inactive_user_skills()`** (and **`POST /api/agents/user-skills/maintenance-inactive`**) reevaluates files against:

- `updated_at` in the JSON, per-skill `last_used_at`, file mtime, and **`agent_db_service.get_user_last_activity_at(user_id)`** (DB `agent_activity` / `agent_progress`, with file fallback).

If the **newest** of those timestamps is still older than **`USER_SKILLS_INACTIVE_DAYS`** (default **120**), the JSON file is **removed** (next `get_user_skills` re-seeds balanced). Each run processes at most **`max_batch`** files (**default 10**). Use **`dry_run=1`** to list candidates without deleting.

- **Auth:** Set **`USER_SKILLS_MAINTENANCE_SECRET`** and pass **`X-Maintenance-Token`** or **`?token=`**. If the secret is unset, the endpoint is **rejected in production** (`FLASK_ENV=production` or `PRODUCTION=true`).

---

## 2c. Reporter agent — knowledge ingredients & cron

| Piece | Role |
|--------|------|
| **`GET` / `POST` `/api/agents/reporter/knowledge-ingredients`** | Returns `report` with ingredients for compendium / broadcast. Optional **`append_log`**: appends one JSON line to `logs/knowledge_sharing/ingredients.jsonl`. Optional **`record_activity=1`**: records `reporter_agent` activity (`news_report_ingredients` / `broadcast`). |
| **Auth (production):** | Set **`KNOWLEDGE_REPORT_SECRET`**; send **`X-Reporter-Token`** or **`?token=`**. If unset, the route stays open (set the secret on public servers). |
| **Cron** | `cron/knowledge_sharing_report.sh` + `cron/masternoder-knowledge-report.cron.d` (daily example). Reads the secret from `.env` like other platform crons. Deploy: `python scripts/deploy.py knowledge_cron_env` (uploads + installs `/etc/cron.d/masternoder-knowledge-report`). |
| **Agent platform crons** | `POST /api/agents/cron/run` with `AGENT_CRON_SECRET` — daily/weekly/monthly presets (skillsets ensure, inactive user-skills cleanup, automation maintenance, LLM snapshot, research rotation, monthly rebalance). Scripts: `cron/agents_cron_*.sh` — deploy `python scripts/deploy.py agents_cron_env`. See **`docs/RESEARCH_AI_SYSTEMS.md`** (Agent cron). |

Env vars (see `.env.example`): **`KNOWLEDGE_REPORT_SECRET`**, **`USER_SKILLS_MAINTENANCE_SECRET`**, **`USER_SKILLS_INACTIVE_DAYS`**.

---

## 3. Syncing “Skills to Agent Skill Sets”

To keep global skill sets in sync and aligned with what agents need:

1. **Ensure battle/sales/PayPal/top25/shared-growth skills exist per agent**  
   Already done on load in `AgentSkillset.load_skillsets()`:
   - `ensure_battle_skills_per_agent(count=30)`
   - `ensure_sales_skillsets_per_agent(count=50)`
   - `ensure_paypal_skillsets_per_agent(count=15)`
   - `ensure_top25_skill_upgrades_per_agent(count=25)`
   - `ensure_shared_growth_skills(count=100)`
   - `ensure_knowledge_skills_per_agent()`
   - `ensure_ai_skills_per_agent()`
   - `ensure_criticism_skills_per_agent(count=20)` — review, feedback, quality assessment (code, content, decisions).
   - `ensure_blueprint_route_fixer_skills_per_agent()` — blueprint/route parity & Register Intelligence workflows.
   - `ensure_api_service_skills_per_agent()` — REST/API surface & contract awareness.

2. **Call the same from an endpoint or script**  
   Use existing routes, e.g.:
   - `POST /api/agents/skillsets/battle/ensure`
   - `POST /api/agents/skillsets/sales/ensure`
   - `POST /api/agents/skillsets/paypal/ensure`
   - `POST /api/agents/skillsets/top25/ensure`
   - `POST /api/agents/skillsets/shared-growth/ensure`
   - `POST /api/agents/skillsets/blueprint-route-fixer/ensure`
   - `POST /api/agents/skillsets/api-service/ensure`

   Account control / debug UI already links to these (see `user_account_routes` account-control).

3. **User ↔ profile**  
   - Profile page uses `user_id` from `game_user_id` (localStorage) and calls bind-session, profile/aggregated, account-summary/points.  
   - “My agents” and agent activity come from APIs that use both `user_agent_skills.get_user_skills(user_id)` and `agent_skillset.get_all_skillsets()`.  
   So “connect users with profile” is already in place; ensure the same `user_id` is used everywhere (bind-session, points, profile, agents).

---

## 4. Cursor / Agent “Skills” (rules and skills)

- **Cursor rules** (e.g. in `.cursor/rules/`) guide the IDE agent; they are not the same as the in-app “agent skill sets” above.
- **Agent skills** in this doc mean the in-app game/UX skills (battle, sales, PayPal, top25, criticism, etc.) stored in `agent_skillset` and assigned per user in `user_agent_skills`.
- To “sync skills to the agents’ skill sets”: run the ensure endpoints above or trigger `agent_skillset.load_skillsets()` (e.g. on deploy or via a cron) so all agents have the required skill counts.

---

## 5. Quick Checklist

- [ ] All points/APIs use the same `user_id` (e.g. from session or `game_user_id`).
- [ ] Profile and “My agents” call both user_agent_skills and agent_skillset.
- [ ] After deploy or schema change, run ensure endpoints (or load_skillsets) so agent skill sets are populated.
- [ ] Shop “Skills” category and agent offers use `agent_skillset.get_all_skillsets()`.

---

## 6. Conclusions

- **Single source of truth:** Global skill sets live in `agent_skillset`; user assignments in `user_agent_skills`. Profile, shop, and game must use the same `user_id` and the same APIs so “my agents” and power totals stay consistent.
- **Criticism as a skill:** Agents now have **criticism skills** (e.g. code_review, logic_gaps, security_audit, copy_review, bias_detection, ux_critique). These are generated per agent via `ensure_criticism_skills_per_agent()` and contribute to `criticism_skill_power_total`. Use them for review tasks, quality gates, and constructive feedback flows.
- **Sync on load:** `AgentSkillset.load_skillsets()` runs all ensure methods (battle, sales, PayPal, top25, shared growth, knowledge, AI, criticism). After deploy or when adding a new skill type, ensure the corresponding `ensure_*` is called so every agent gets the new profiles and power totals.
- **Outcome:** Keeping these two layers in sync and including criticism gives agents a full set of capabilities (monetization, battle, growth, knowledge, AI, and criticism) that the UI and shop can surface consistently.
- **Balanced default + reporter:** New users without a skills file get **content_generator_agent**, **analytics_agent**, **learning_agent**, and **reporter_agent** (10 skills). **Maintenance** and **reporter/cron** keep storage and knowledge-sharing flows aligned with production ops.
