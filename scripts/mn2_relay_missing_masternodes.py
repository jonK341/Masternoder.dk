#!/usr/bin/env python3
"""
Relay P2P masternode broadcasts for aliases still MISSING from the network list.

Run on the server (root or user with wallet RPC):
  python3 scripts/mn2_relay_missing_masternodes.py
  python3 scripts/mn2_relay_missing_masternodes.py --limit 80

Cron: invoked from cron/mn2_masternode_provision.sh before provision-pending.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def main() -> int:
    p = argparse.ArgumentParser(description="Relay missing masternode network broadcasts")
    p.add_argument("--limit", type=int, default=50, help="Max aliases to relay (default 50)")
    p.add_argument("--json", action="store_true", help="Print JSON only")
    args = p.parse_args()

    from backend.services.mn2_masternode_service import relay_missing_masternode_broadcasts

    out = relay_missing_masternode_broadcasts(limit=args.limit)
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(
            f"relay_missing: candidates={out.get('candidates')} "
            f"relayed={len(out.get('relayed') or [])} failed={len(out.get('failed') or [])}"
        )
        for alias in out.get("relayed") or []:
            print(f"  OK {alias}")
        for row in out.get("failed") or []:
            print(f"  FAIL {row.get('alias')}: {row.get('error')}")
    ok = bool(out.get("success")) or not out.get("failed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
