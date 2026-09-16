#!/usr/bin/env python3
"""Rebuild Discord community fulfillment order list from linked users + Discord API."""
from __future__ import annotations

import argparse
import json
import os
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Discord fulfillment order list")
    parser.add_argument("--no-api", action="store_true", help="Skip Discord API (local linked users only)")
    parser.add_argument("--json", action="store_true", help="Print full JSON result")
    args = parser.parse_args()

    from backend.services.discord_fulfillment_ledger_service import build_order_list, get_order_list

    result = build_order_list(use_discord_api=not args.no_api)
    if args.json:
        print(json.dumps({**result, "orders": get_order_list().get("orders")}, indent=2))
    else:
        print(f"Order list rebuilt: total={result.get('total')} pending={result.get('pending')} "
              f"fulfilled={result.get('fulfilled')} discord_api_used={result.get('discord_api_used')}")
        if result.get("api_notes"):
            print("API notes:", "; ".join(result["api_notes"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
