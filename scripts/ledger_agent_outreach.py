#!/usr/bin/env python3
"""Process top N pending ledger rows — auto-greet and log outreach actions."""
from __future__ import annotations

import argparse
import json
import os
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ledger agent outreach automation stub")
    parser.add_argument("-n", "--limit", type=int, default=10, help="Top N rows to process")
    parser.add_argument("--dry-run", action="store_true", help="List targets without greeting")
    parser.add_argument("--json", action="store_true", help="Print JSON log")
    args = parser.parse_args()

    from backend.services.ledger_coin_sales_service import get_sales_queue
    from backend.services.ledger_agent_service import auto_greet

    queue = get_sales_queue(limit=args.limit).get("queue") or []
    actions = []
    for item in queue:
        lid = item.get("ledger_row_id")
        action = {"ledger_row_id": lid, "ledger_rank": item.get("ledger_rank"), "display_name": item.get("display_name")}
        if args.dry_run:
            action["action"] = "would_greet"
        else:
            greet = auto_greet(lid)
            action["action"] = "greeted" if greet.get("success") and not greet.get("skipped") else greet.get("reason", "skipped")
        actions.append(action)

    if args.json:
        print(json.dumps({"processed": len(actions), "actions": actions}, indent=2))
    else:
        for a in actions:
            print(f"#{a.get('ledger_rank')} {a.get('ledger_row_id')}: {a.get('action')} ({a.get('display_name')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
