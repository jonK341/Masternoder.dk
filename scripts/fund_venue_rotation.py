#!/usr/bin/env python3
"""Ops CLI for venue funding and agent trade rotation.

Usage:
  python scripts/fund_venue_rotation.py status
  python scripts/fund_venue_rotation.py sell --venue nonkyc --asset USDT --amount 50
  python scripts/fund_venue_rotation.py sell --venue nonkyc --asset USDT --amount 50 --live
  python scripts/fund_venue_rotation.py fund --agent arb_live_dual_farm --symbol DOGE
  python scripts/fund_venue_rotation.py cycle [--live] [--force]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")


def main() -> int:
    parser = argparse.ArgumentParser(description="Venue funding and agent rotation ops")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Show agent rotation status")

    sell_p = sub.add_parser("sell", help="Sell coins on a venue to raise USDT/DOGE/etc.")
    sell_p.add_argument("--venue", required=True)
    sell_p.add_argument("--asset", default="USDT", help="Target quote asset (USDT, DOGE, USDC)")
    sell_p.add_argument("--amount", type=float, required=True, help="Target USD notional")
    sell_p.add_argument("--live", action="store_true")

    fund_p = sub.add_parser("fund", help="Prefund arb legs for agent+symbol")
    fund_p.add_argument("--agent", required=True)
    fund_p.add_argument("--symbol", required=True)
    fund_p.add_argument("--notional", type=float, default=0)
    fund_p.add_argument("--live", action="store_true")

    cycle_p = sub.add_parser("cycle", help="Run one agent rotation cycle")
    cycle_p.add_argument("--live", action="store_true")
    cycle_p.add_argument("--force", action="store_true", help="Run even if EXCHANGE_AGENT_ROTATION is off")

    args = parser.parse_args()

    if args.cmd == "status":
        from backend.services.venue_funding_rotation_service import rotation_status

        print(json.dumps(rotation_status(), indent=2))
        return 0

    dry_run = not getattr(args, "live", False)

    if args.cmd == "sell":
        from backend.services.venue_funding_rotation_service import sell_coins_to_fund_venue

        res = sell_coins_to_fund_venue(args.venue, args.asset, args.amount, dry_run=dry_run)
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("success") else 1

    if args.cmd == "fund":
        from backend.services.venue_funding_rotation_service import fund_venue_legs_for_symbol

        res = fund_venue_legs_for_symbol(args.agent, args.symbol, args.notional, dry_run=dry_run)
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("success") else 1

    if args.cmd == "cycle":
        from backend.services.venue_funding_rotation_service import run_agent_trade_rotation_cycle

        res = run_agent_trade_rotation_cycle(dry_run=dry_run, force=bool(args.force))
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("success") or res.get("skipped") else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
