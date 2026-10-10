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


def main() -> int:
    parser = argparse.ArgumentParser(description="Bring rented MN2 masternodes online")
    parser.add_argument("--start", action="store_true", help="Provision pending hosts and startmasternode")
    parser.add_argument("--limit", type=int, default=20, help="Max hosts to process")
    args = parser.parse_args()
    from backend.services.mn2_masternode_service import (
        bring_rented_masternodes_online,
        rented_masternodes_snapshot,
    )
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
