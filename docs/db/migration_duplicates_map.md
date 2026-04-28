# Migration Duplicate Table Map (Pass 1)

This map lists table names that are created in more than one migration script.
Goal: assign one canonical owner per table and mark others as legacy overlap.

## Detected duplicates

| Table | Scripts defining it | Canonical owner (proposed) | Notes |
|---|---|---|---|
| `video_generation_jobs` | `scripts/generator_migration.py`, `scripts/missing_tables_migration.py` | `scripts/generator_migration.py` | Generator service/tests already align with generator migration. |
| `player_levels` | `scripts/unified_points_database_migration.py`, `scripts/database_migration_standardize_schema.py`, `scripts/migrate_all_missing_tables.py`, `scripts/database_diagnostic_and_fix.py` | `scripts/unified_points_database_migration.py` | Unified points has the most complete progression schema. |
| `xp_history` | `scripts/unified_points_database_migration.py`, `scripts/database_migration_standardize_schema.py`, `scripts/migrate_all_missing_tables.py` | `scripts/unified_points_database_migration.py` | Keep one ownership path for XP/event history. |
| `daily_activities` | `scripts/unified_points_database_migration.py`, `scripts/database_migration_standardize_schema.py`, `scripts/migrate_all_missing_tables.py` | `scripts/unified_points_database_migration.py` | Column sets differ; unified should win. |
| `system_point_snapshots` | `scripts/unified_points_database_migration.py`, `scripts/database_migration_standardize_schema.py`, `scripts/migrate_all_missing_tables.py` | `scripts/unified_points_database_migration.py` | Prevent schema drift in analytics pipeline. |
| `user_profiles` | `scripts/database_migration_standardize_schema.py`, `scripts/migrate_all_missing_tables.py` | `scripts/migrate_all_missing_tables.py` (temporary) | Pick one now; revisit once profile domain migration is split. |
| `rewards` | `scripts/migrate_hunters_game_complete.py`, `scripts/fix_all_loose_ends_master.py` | `scripts/migrate_hunters_game_complete.py` | Keep reward creation out of omnibus fix scripts. |
| `user_rewards` | `scripts/migrate_hunters_game_complete.py`, `scripts/fix_all_loose_ends_master.py` | `scripts/migrate_hunters_game_complete.py` | Same as above. |

## Conflict risk summary

- High risk: progression/points tables (`player_levels`, `xp_history`, `daily_activities`, `system_point_snapshots`)
- Medium risk: generator jobs table (`video_generation_jobs`)
- Medium risk: profile/rewards tables with mixed ownership

## Immediate governance rule

- A table must have exactly one canonical migration owner.
- Any non-owner script that creates the same table must be marked `legacy_overlap`.
- New migrations must not redefine an existing table outside its owner domain.
