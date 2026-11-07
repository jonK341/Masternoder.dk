#!/usr/bin/env python3
"""Fund 5k MN2 collateral pool and register platform fleet on-chain (run on server)."""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.daemon_env import load_dotenv

load_dotenv()

from backend.services.mn2_fleet_inventory_ops import bootstrap_platform_fleet  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=int, default=500, help="Target free 5k collateral UTXOs")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fund-only", action="store_true", help="Only create collateral UTXOs")
    parser.add_argument("--provision-only", action="store_true", help="Skip funding; seed + provision")
    parser.add_argument("--provision-batch", type=int, default=50)
    parser.add_argument("--max-rounds", type=int, default=400)
    parser.add_argument(
        "--progress",
        default="",
        help="Write JSON progress snapshot (default: data/mn2_fleet_bootstrap_progress.json)",
    )
    args = parser.parse_args()

    progress = args.progress.strip() or os.path.join(ROOT, "data", "mn2_fleet_bootstrap_progress.json")

    def hook(payload: dict) -> None:
        line = json.dumps({"ts": payload.get("phase"), **payload}, default=str)
        print(line, flush=True)

    result = bootstrap_platform_fleet(
        args.target,
        dry_run=args.dry_run,
        fund_only=args.fund_only,
        provision_only=args.provision_only,
        provision_batch=args.provision_batch,
        max_provision_rounds=args.max_rounds,
        progress_hook=hook,
        progress_path=progress,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
