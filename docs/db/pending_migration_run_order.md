# Pending Migration Run Order (Pass 1)

Purpose: safe, deterministic order for pending schema work based on current DB state.
Status: **executed for Phase 2** on `instance/database.db`.

## Current DB now has (post Phase 2)

- feature core tables from run_all_migrations
- unified points/progression tables
- agent mission/intelligence/error/use-case tables
- agent technologies tables
- rewards/user_rewards tables
- communication psychology tables
- hunters/star-map supplemental tables

## Execution policy

1. Back up DB.
2. Run one migration script at a time.
3. Verify created tables after each script.
4. Stop on error and inspect before continuing.
5. Do not run legacy overlap scripts in this sequence.

## Ordered plan (completed)

### Phase A: foundational domain tables

1. `scripts/unified_points_database_migration.py` ✅

2. `scripts/missing_tables_migration.py` ✅

3. `scripts/agent_technologies_database_migration.py` ✅

### Phase B: specialized feature tables

4. `scripts/migrate_hunters_game_complete.py` ⚠️
   - Non-zero exit due to Windows console emoji encoding.
   - Table verification confirms `rewards` and `user_rewards` exist.

5. `scripts/communication_psychology_migration.py` ✅

6. `scripts/hunters_star_map_migration.py` ✅

### Phase C: validation and reconciliation

7. Re-ran verification checks ✅
   - required Phase 2 table set: 0 missing
   - final table count observed: 50

## Explicitly excluded from this run order

- `scripts/database_migration_standardize_schema.py` (overlaps unified points and profile schemas)
- `scripts/migrate_all_missing_tables.py` (overlaps several domains and broad side effects)
- `scripts/database_diagnostic_and_fix.py` (diagnostic/fix style, not canonical migration owner)
- `scripts/fix_all_loose_ends_master.py` (omnibus script; not suitable as canonical schema step)

## Post-Pass 2 requirement

Before further migration work, implement `schema_migrations` ledger tracking and register each script execution with version + checksum.
