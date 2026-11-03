#!/usr/bin/env python3
"""Check whether rented MN2 masternodes can be brought online, then attempt it.

Usage:
  python scripts/mn2_bring_rented_online.py           # snapshot only
  python scripts/mn2_bring_rented_online.py --start   # restore paid hosts + startmasternode
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)


def _load_env() -> None:
    from scripts.daemon_env import load_dotenv
    load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(description="Bring rented MN2 masternodes online")
    parser.add_argument("--start", action="store_true", help="Provision pending hosts and startmasternode")
    parser.add_argument("--snapshot", action="store_true", help="Print rented_masternodes_snapshot only (fast)")
    parser.add_argument(
        "--provision-only",
        action="store_true",
        help="Only process_pending_hosts (no bring_online order sync / fleet start)",
    )
    parser.add_argument("--limit", type=int, default=20, help="Max hosts to process")
    args = parser.parse_args()
    _load_env()
    from backend.services.mn2_masternode_service import (
        bring_rented_masternodes_online,
        process_pending_hosts,
        rented_masternodes_snapshot,
    )
    if args.snapshot:
        result = rented_masternodes_snapshot()
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("daemon_healthy") else 1
    if args.provision_only:
        snap = rented_masternodes_snapshot()
        print(json.dumps({"snapshot": snap}, indent=2, default=str)[:8000])
        if not snap.get("daemon_healthy"):
            return 1
        result = process_pending_hosts(limit=args.limit, skip_explorer=True)
        print(json.dumps(result, indent=2, default=str)[:120000])
        return 0 if result.get("success") else 1
    if args.start:
        result = bring_rented_masternodes_online(limit=args.limit)
    else:
        result = rented_masternodes_snapshot()
    print(json.dumps(result, indent=2, default=str))
    if args.start:
        return 0 if result.get("success") else 1
    return 0 if result.get("can_bring_online") or result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
