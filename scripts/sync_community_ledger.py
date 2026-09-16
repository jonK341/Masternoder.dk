#!/usr/bin/env python3
"""Rebuild community fulfillment ledger from 25 population sources."""
from __future__ import annotations

import argparse
import json
import os
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync community fulfillment ledger (25 sources)")
    parser.add_argument("--no-api", action="store_true", help="Skip Discord API guild/channel scans")
    parser.add_argument("--legacy", action="store_true", help="Use legacy 3-source mode only")
    parser.add_argument("--json", action="store_true", help="Print full JSON result")
    args = parser.parse_args()

    from backend.services.discord_fulfillment_ledger_service import build_order_list, get_order_list
    from backend.services.community_ledger_population import list_population_source_ids

    if args.legacy:
        result = build_order_list(
            use_local=True,
            use_discord_api=not args.no_api,
            use_buyer_signals=True,
            use_all_sources=False,
        )
    else:
        result = build_order_list(
            use_local=True,
            use_discord_api=not args.no_api,
            use_buyer_signals=True,
            use_all_sources=True,
        )

    if args.json:
        print(json.dumps({**result, "orders": get_order_list().get("orders"), "source_ids": list_population_source_ids()}, indent=2))
    else:
        src = result.get("sources") or {}
        print(
            f"Community ledger rebuilt: total={result.get('total')} pending={result.get('pending')} "
            f"fulfilled={result.get('fulfilled')} buyer_signals={result.get('buyer_signal_count')}"
        )
        print(f"Population sources ({len(src)}): {src}")
        print(f"Discord API used: {result.get('discord_api_used')}")
        if result.get("api_notes"):
            print("Notes:", "; ".join(result["api_notes"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
