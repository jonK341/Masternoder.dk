#!/usr/bin/env python3
"""Promote data/camgirls_performers.json into SQLite camgirls_performers (Phase 4)."""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from project_env import load_project_dotenv


def main() -> int:
    load_project_dotenv()
    parser = argparse.ArgumentParser(description="Sync camgirls JSON catalog to SQLite")
    parser.add_argument("--file", help="Override performers JSON path")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from backend.services.camgirls_catalog_sync_service import (
        catalog_db_stats,
        sync_json_catalog_to_db,
    )
    from backend.services.camgirls_catalog_db_service import catalog_source_label

    json_path = args.file
    if json_path and not os.path.isabs(json_path):
        json_path = os.path.join(ROOT, json_path)

    result = sync_json_catalog_to_db(json_path=json_path, dry_run=args.dry_run)
    stats = catalog_db_stats()
    print(result)
    print(f"db_stats: {stats}")
    print(f"catalog_source_label: {catalog_source_label()}")
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
