#!/usr/bin/env python3
"""Cron worker: genesis block trophy indexing from block #1 at milestone (plan 001 BM-U5)."""
from __future__ import annotations

import argparse
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batches", type=int, default=0, help="Max sync batches (0 = config default)")
    parser.add_argument("--force", action="store_true", help="Force genesis mode below milestone (ops/test)")
    args = parser.parse_args()

    from backend.services.block_mint_service import get_config, run_genesis_backfill_batches

    cfg = get_config()
    batches = args.batches or int(cfg.get("auto_genesis_worker_batches") or 10)
    result = run_genesis_backfill_batches(max_batches=batches, force_milestone=args.force)
    print(json.dumps(result, indent=2))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
