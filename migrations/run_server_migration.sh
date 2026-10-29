#!/usr/bin/env bash
# ============================================================================
# masternoder.dk MN2 migration -- SERVER guided self-run.
# Resolves its own folder, so it works whether named migration/ or migrations/.
#
#   STAGE 1 (read-only):  ./run_server_migration.sh probe
#   STAGE 2 (writes)   :  ./run_server_migration.sh apply
#
# NON-DESTRUCTIVE: additive schema + idempotent backfill + page crawl.
# Moves NO funds, never touches wallet.dat or the daemon.
# ============================================================================
set -uo pipefail
cd /var/www/html                      # DATABASE_URL (instance/database.db) resolves from here
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY=python3
if [[ -x /var/www/html/.venv/bin/python ]]; then
  PY=/var/www/html/.venv/bin/python
elif [[ -x .venv/bin/python ]]; then
  PY=.venv/bin/python
fi
DB=instance/database.db
DATA=data                             # real MN2 json live in /var/www/html/data
STAGE="${1:-probe}"

echo "### stage=$STAGE  scripts=$SCRIPT_DIR  db=$DB  data=$DATA"

echo; echo "===== 0. SAFETY: back up the live DB ====="
$PY "$SCRIPT_DIR/000_safety_backup.py" "$DB"
echo ">>> Also snapshot the node wallet (safe, no restart):"
echo ">>>   mn2-cli backupwallet /var/backups/mn2_wallet_$(date +%Y%m%d_%H%M%S).dat"

if [ "$STAGE" = "probe" ]; then
  echo; echo "===== 1. PROBE real sources (writes NOTHING) ====="
  $PY "$SCRIPT_DIR/002_backfill_mn2.py" --db "$DB" --data-dir "$DATA" --probe
  echo; echo ">>> Paste this output back. After review, run:  ./$(basename "${BASH_SOURCE[0]}") apply"
  exit 0
fi

echo; echo "===== 2. Apply schema (idempotent; already applied = no-op) ====="
$PY "$SCRIPT_DIR/001_create_schema.py" --db "$DB"

echo; echo "===== 3. Backfill MN2 from ledger / order_payments / masternodes / treasury ====="
$PY "$SCRIPT_DIR/002_backfill_mn2.py" --db "$DB" --data-dir "$DATA"

echo; echo "===== 3b. Harvest ALL sub-app wallets into canonical identities (DB-only) ====="
$PY "$SCRIPT_DIR/007_consolidate_wallets.py" --db "$DB" --data-dir "$DATA"

echo; echo "===== 3c. Ingest EVERY data store -> catalog + raw conformed layer ====="
$PY "$SCRIPT_DIR/008_ingest_data_stores.py" --db "$DB" --data-dir "$DATA"

echo; echo "===== 3d. Promote camgirls content (performers/payouts/paypal/activity) + smoke ====="
$PY "$SCRIPT_DIR/009_camgirls.py" --db "$DB" --data-dir "$DATA"

echo; echo "===== 3e. Compute MN2 stats + consolidate wallet identities ====="
$PY "$SCRIPT_DIR/005_compute_stats.py" --db "$DB" --data-dir "$DATA"

echo; echo "===== 4. Crawl public pages -> site_pages ====="
$PY "$SCRIPT_DIR/003_crawl_site_pages.py" --db "$DB" --no-html

echo; echo "===== 5. Verify ====="
$PY "$SCRIPT_DIR/004_verify.py" "$DB"
echo; echo ">>> Micro-tx SIMULATION (dry-run, sends nothing) -- run separately when ready:"
echo ">>>   $PY $SCRIPT_DIR/006_micro_tx_sim.py --db $DB --data-dir $DATA --batch --batch-limit 10"
echo ">>> To re-run cleanly after any mapping tweak:"
echo ">>>   $PY $SCRIPT_DIR/002_backfill_mn2.py --db $DB --data-dir $DATA --reset"
echo ">>>   $PY $SCRIPT_DIR/007_consolidate_wallets.py --db $DB --data-dir $DATA"
echo ">>>   $PY $SCRIPT_DIR/008_ingest_data_stores.py --db $DB --data-dir $DATA --reset"
echo ">>>   $PY $SCRIPT_DIR/009_camgirls.py --db $DB --data-dir $DATA --reset"
echo ">>>   $PY $SCRIPT_DIR/005_compute_stats.py --db $DB --data-dir $DATA"
