#!/usr/bin/env python3
"""Step 0 -- SAFETY backup before the migration touches anything.

Copies the live SQLite DB (+ -wal/-shm) to a timestamped backup next to it and
verifies the copy. The MN2 migration is READ-ONLY on the chain and moves NO funds,
but the wallet.dat holds ~2.5M MN2, so snapshot it too via the node RPC:

    mn2-cli backupwallet /var/backups/mn2_wallet_<STAMP>.dat      # safe, no restart

This script does NOT touch wallet.dat or the daemon -- it only backs up the DB.
"""
import os
import shutil
import sqlite3
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module  # noqa: E402

resolver = import_module("001_create_schema")  # reuse resolve_db_url


def main():
    explicit = sys.argv[1] if len(sys.argv) > 1 else None
    db = resolver.resolve_db_url(explicit)
    if not os.path.exists(db):
        sys.exit(f"ERROR: DB not found at {db}")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{db}.bak_{stamp}"
    # checkpoint WAL so the backup is self-contained
    try:
        c = sqlite3.connect(db)
        c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        c.close()
    except sqlite3.Error:
        pass
    shutil.copy2(db, backup)
    # integrity-check the backup itself
    chk = sqlite3.connect(backup).execute("PRAGMA integrity_check").fetchone()[0]
    size = os.path.getsize(backup)
    print(f"[backup] {db}  ->  {backup}")
    print(f"[backup] size={size}B integrity_check={chk}")
    if chk != "ok":
        sys.exit("ERROR: backup failed integrity check -- aborting")
    print("[backup] OK. Remember: also run `backupwallet` on the NODE for wallet.dat.")


if __name__ == "__main__":
    main()
