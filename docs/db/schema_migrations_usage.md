# Schema Migrations Usage

Source DB: `sqlite:///instance/database.db`

## Bootstrap ledger table

```bash
python scripts/bootstrap_schema_migrations.py
```

## Record one migration manually

```bash
python scripts/record_migration.py \
  --version phaseX_YYYYMMDD_nn_name \
  --script scripts/your_migration.py \
  --status applied \
  --notes "optional context"
```

## Backfill Phase 2 history

```bash
python scripts/backfill_phase2_schema_migrations.py
```

## Run + record in one command (Phase 5)

```bash
python scripts/run_and_record_migration.py \
  --version phaseX_YYYYMMDD_nn_name \
  --script scripts/your_migration.py \
  --notes "executed via phase5 wrapper"
```

This executes the migration script and writes `applied` or `failed` to `schema_migrations` automatically.

## Check migration drift (Phase 6)

```bash
python scripts/check_migration_drift.py
```

It reports:
- missing canonical tables
- extra tables outside canonical set
- missing canonical script ledger entries

## Inspect ledger entries

```bash
python -c "from sqlalchemy import create_engine, text; eng=create_engine('sqlite:///instance/database.db'); \
with eng.connect() as c: \
 rows=c.execute(text('SELECT version, script_name, status, applied_at FROM schema_migrations ORDER BY applied_at')).fetchall(); \
 [print(r) for r in rows]"
```

## Notes

- `version` must be unique and stable.
- Re-running `record_migration.py` with the same `version` updates that row.
- Prefer one ledger entry per migration script execution.
- `run_and_record_migration.py` passes current `DATABASE_URL` through to the executed script.
- `scripts/battle_migration.py` standalone mode is patched for SQLAlchemy compatibility (Phase 7).
