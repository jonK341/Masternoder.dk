#!/usr/bin/env python3
"""Idempotent, resumable backfill of per-user MN2 deposit addresses.

Dry-run (default) lists the next batch and does not call the daemon.
Apply creates addresses for users who do not already have one and advances
logs/mn2_address_backfill_state.json after each user so a crash can resume.

Examples:
  python scripts/mn2_backfill_user_addresses.py --dry-run --batch-size 100
  python scripts/mn2_backfill_user_addresses.py --apply --batch-size 100
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill MN2 deposit addresses for existing users")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Show the next batch without creating addresses (default)")
    mode.add_argument("--apply", action="store_true", help="Create addresses for the next batch and advance the cursor")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--state", default="", help="Override resumable state JSON path")
    args = parser.parse_args()

    from backend.services.mn2_onchain_wallet import apply_address_backfill, plan_address_backfill

    state = args.state.strip() or None
    if args.apply:
        result = apply_address_backfill(batch_size=args.batch_size, state_path=state)
    else:
        result = plan_address_backfill(batch_size=args.batch_size, state_path=state)
    print(json.dumps(result, indent=2))
    return 0 if result.get("success", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
