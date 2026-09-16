#!/usr/bin/env python3
"""Rebuild Discord community fulfillment order list from 3 sources."""
from __future__ import annotations

import argparse
import json
import os
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Discord fulfillment order list (triple-source)")
    parser.add_argument("--local", action="store_true", help="Include local linked users (source A)")
    parser.add_argument("--api", action="store_true", help="Include Discord API guild/channel (source B)")
    parser.add_argument("--buyers", action="store_true", help="Include MN2 purchase intent signals (source C)")
    parser.add_argument("--all", action="store_true", help="All three sources (default when no flags)")
    parser.add_argument("--no-api", action="store_true", help="Deprecated: skip Discord API only")
    parser.add_argument("--json", action="store_true", help="Print full JSON result")
    args = parser.parse_args()

    explicit = args.local or args.api or args.buyers
    if args.all or not explicit:
        use_local = use_api = use_buyers = True
    else:
        use_local = args.local
        use_api = args.api
        use_buyers = args.buyers
    if args.no_api:
        use_api = False

    from backend.services.discord_fulfillment_ledger_service import build_order_list, get_order_list

    result = build_order_list(
        use_local=use_local,
        use_discord_api=use_api,
        use_buyer_signals=use_buyers,
    )
    if args.json:
        print(json.dumps({**result, "orders": get_order_list().get("orders")}, indent=2))
    else:
        src = result.get("sources") or {}
        ov = result.get("overlaps") or {}
        print(
            f"Order list rebuilt: total={result.get('total')} pending={result.get('pending')} "
            f"fulfilled={result.get('fulfilled')} buyer_signals={result.get('buyer_signal_count')}"
        )
        print(
            f"Sources: local={src.get('local_linked', 0)} api={src.get('discord_api', 0)} "
            f"buyers={src.get('purchase_intent', 0)} | overlaps: {ov}"
        )
        print(f"Discord API used: {result.get('discord_api_used')}")
        if result.get("api_notes"):
            print("API notes:", "; ".join(result["api_notes"]))
        if not use_api and not result.get("discord_api_used"):
            print("Note: sources A+C populate ledger without Discord API (set DISCORD_BOT_TOKEN + intent for B).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
