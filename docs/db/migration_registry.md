# Migration Registry (Pass 1)

Status: updated through Phase 6 (run+record and drift checks).
Scope: local workspace and configured DB `sqlite:///instance/database.db`.

## Current state snapshot

- Declared tables in migration scripts: `57`
- Tables present in current DB: `61`
- Missing declared tables in current DB: `0` for Phase 2 required set
- Duplicate table definitions across scripts: `8` table names

## Active migration scripts (canonical candidates)

These are the scripts that should be considered the primary migration set going forward.

| Domain | Script | Creates/updates | Status in current DB |
|---|---|---|---|
| Core feature pack | `scripts/run_all_migrations.py` | orchestrates 7 standalone migrations | partial |
| Battle | `scripts/battle_migration.py` | `battle_matches` | present |
| Trophies | `scripts/trophies_migration.py` | `trophy_definitions`, `user_trophy_unlocks` | present |
| Shop | `scripts/shop_purchase_migration.py` | `shop_items`, `shop_purchases`, `user_inventory` | present |
| Chat | `scripts/chat_migration.py` | `chat_sessions`, `chat_messages` | present |
| Gallery | `scripts/gallery_migration.py` | `gallery_items`, `user_gallery_state`, `gallery_downloads` | present |
| Points daily analytics | `scripts/points_migration.py` | `point_aggregates_daily` | present |
| Generator jobs | `scripts/generator_migration.py` | `video_generation_jobs`, `job_artifacts` | present |
| Unified points core | `scripts/unified_points_database_migration.py` | `player_levels`, `xp_history`, `daily_activities`, `point_transactions`, `point_history`, `point_aggregates`, `point_analytics`, `system_usage_stats`, `system_point_snapshots` | present |
| Missing tables pack | `scripts/missing_tables_migration.py` | `agent_missions`, `agent_quests`, `agent_personality`, `agent_skill_history`, `agent_ai_intelligence`, `agent_errors`, `agent_use_cases`, `video_generation_jobs`, `dna_manipulation` | present |
| Agent technologies | `scripts/agent_technologies_database_migration.py` | `agent_technologies`, `agent_technology_*` tables | present |
| Hunters + rewards | `scripts/migrate_hunters_game_complete.py` | `rewards`, `user_rewards` (+ model-backed game tables) | present |
| Communication psychology | `scripts/communication_psychology_migration.py` | `comm_psych_theory_unlocks`, `comm_psych_activity_log` | present |
| Star map / hunters extras | `scripts/hunters_star_map_migration.py` | `star_map_visits`, `hunters_game_sessions`, `hunters_profiles`, `hunters_spells`, `agent_geo_refs` | present |

## Scripts to mark legacy/overlapping (do not run by default)

These overlap schema ownership and should be treated as legacy unless explicitly needed.

- `scripts/database_migration_standardize_schema.py`
- `scripts/migrate_all_missing_tables.py`
- `scripts/database_diagnostic_and_fix.py`
- `scripts/fix_all_loose_ends_master.py` (contains table creation side effects)

## Proposed registry status labels

Use these labels in future automation:

- `active`: canonical migration script
- `legacy_overlap`: defines tables now owned elsewhere
- `ops_script`: deployment/fix helper, not canonical schema owner
- `blocked`: requires prerequisites or manual review before run

## Phase 3 updates

1. `schema_migrations` ledger table bootstrapped via `scripts/bootstrap_schema_migrations.py`.
2. DB source-of-truth switched to `instance/database.db` in `.env`.
3. Full current inventory captured in `docs/db/instance_table_inventory.md`.

## Phase 4 updates

1. Added reusable recorder: `scripts/record_migration.py`.
2. Added backfill script: `scripts/backfill_phase2_schema_migrations.py`.
3. Backfilled Phase 2 execution history into `schema_migrations` (6 rows).
4. Migration ledger now tracks script name, checksum, status, and notes.

## Phase 5 updates

1. Added wrapper runner: `scripts/run_and_record_migration.py`.
2. Verified wrapper by re-running communication psychology migration and auto-recording outcome.
3. Ledger now includes post-phase rerun entries in addition to backfilled history.

## Phase 6 updates

1. Added drift checker: `scripts/check_migration_drift.py`.
2. Initial drift run found missing core feature tables in `instance/database.db`.
3. Ran `scripts/run_all_migrations.py` against instance DB to close core feature gaps.
4. Re-ran drift check: missing canonical tables = `0`; missing canonical script ledger entries = `0`.

## Phase 7 updates

1. Patched `scripts/battle_migration.py` standalone compatibility (no `Connection.commit` failure path).
2. Re-ran `scripts/run_all_migrations.py` with all modules reporting `ok`.
3. Recorded Phase 7 execution metadata in `schema_migrations`.
