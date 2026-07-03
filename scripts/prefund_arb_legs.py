#!/usr/bin/env python3
"""One-shot ops tool: read top rotation suggestion and execute (dry-run by default).

Usage:
  python scripts/prefund_arb_legs.py              # dry-run top action
  python scripts/prefund_arb_legs.py --live       # live buy-leg prefund only (default --leg buy)
  python scripts/prefund_arb_legs.py --list       # show top 3 suggestions only
  python scripts/prefund_arb_legs.py --live --symbol DOGE --leg buy   # NonKYC DOGE sell-leg prefund
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")


def _print_action(idx: int, action: dict) -> None:
    label = str(action.get("label") or "").replace("\u2192", "->")
    print(
        f"  [{idx}] {label} "
        f"type={action.get('type')} "
        f"priority={action.get('priority')} "
        f"usd={action.get('amount_usd') or action.get('suggested_notional_usd')}"
    )
    if action.get("venue_id"):
        print(f"       venue={action.get('venue_id')} symbol={action.get('symbol')} side={action.get('side')}")
    if action.get("top25_items"):
        print(f"       top25={action.get('top25_items')}")


def filter_prefund_actions(
    actions: List[Dict[str, Any]],
    *,
    symbol: str = "",
    leg: str = "",
    buy_sell_leg: bool = False,
    venue: str = "nonkyc",
) -> List[Dict[str, Any]]:
    """Keep only safe prefund actions (buy on sell venue; never sell base inventory)."""
    sym = str(symbol or "").strip().upper()
    leg_l = str(leg or "").strip().lower()
    prefund = buy_sell_leg or bool(sym)

    if prefund and not leg_l:
        leg_l = "buy"

    out = list(actions)
    if sym:
        out = [
            a for a in out
            if sym == str(a.get("symbol") or "").upper()
            or sym in str(a.get("label") or "").upper()
        ]

    if prefund or leg_l == "buy":
        out = [a for a in out if str(a.get("type") or "") != "external_market_sell"]

    if leg_l == "buy":
        out = [
            a for a in out
            if str(a.get("type") or "") == "external_market_buy"
            and str(a.get("side") or "").lower() == "buy"
        ]
    elif leg_l == "sell":
        out = [
            a for a in out
            if str(a.get("type") or "") == "external_market_sell"
            or str(a.get("side") or "").lower() == "sell"
        ]

    if sym or buy_sell_leg:
        venue_id = str(venue or "nonkyc").lower()
        out = [
            a for a in out
            if str(a.get("venue_id") or "").lower() == venue_id
        ]
        if sym:
            out = [a for a in out if sym == str(a.get("symbol") or "").upper()]

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute top arb funding rotation action")
    parser.add_argument("--live", action="store_true", help="Execute live (default: dry-run)")
    parser.add_argument("--list", action="store_true", help="List suggestions only, no execute")
    parser.add_argument("--hours", type=float, default=6, help="PPP lookback hours for suggestions")
    parser.add_argument("--index", type=int, default=0, help="Action index to execute (0=top)")
    parser.add_argument("--symbol", type=str, default="", help="Filter to actions matching symbol (e.g. DOGE)")
    parser.add_argument(
        "--leg",
        type=str,
        default="",
        choices=["", "buy", "sell"],
        help="Leg filter: buy=sell-leg prefund (default buy on --live); use --leg sell explicitly to sell",
    )
    parser.add_argument(
        "--buy-sell-leg",
        action="store_true",
        help="Prefund sell-leg inventory: external_market_buy on nonkyc only (skips sells)",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON result")
    args = parser.parse_args()
    if args.live and not args.leg:
        args.leg = "buy"

    from scripts.daemon_env import load_dotenv

    load_dotenv()

    from backend.services.exchange_swap_rotation_service import (
        execute_rotation,
        rotation_live_enabled,
        suggest_swap_actions,
    )

    rot = suggest_swap_actions(hours=args.hours, limit=12)
    all_actions = rot.get("actions") or []
    actions = filter_prefund_actions(
        all_actions,
        symbol=args.symbol,
        leg=args.leg,
        buy_sell_leg=args.buy_sell_leg,
    )
    if not actions:
        out = {
            "success": False,
            "error": "no_actions",
            "funding_skip_count": rot.get("funding_skip_count"),
            "filtered_from": len(all_actions),
        }
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            sym_hint = f" (symbol={args.symbol.upper()}, leg={args.leg or 'buy'})" if args.symbol or args.buy_sell_leg else ""
            print(f"No rotation actions after prefund filter{sym_hint}.")
            if all_actions and (args.symbol or args.buy_sell_leg or args.leg):
                print(f"  ({len(all_actions)} unfiltered actions — use --list without filters to inspect)")
        return 1

    if args.list:
        print(f"Rotation suggestions (lookback={args.hours}h, funding_skips={rot.get('funding_skip_count')}):")
        for i, act in enumerate(actions):
            _print_action(i, act)
        return 0

    idx = max(0, min(args.index, len(actions) - 1))
    action = actions[idx]
    dry_run = not args.live

    if args.live and not rotation_live_enabled():
        print("ERROR: --live requires rotation_live_enabled or EXCHANGE_ROTATION_LIVE=1 in .env")
        return 2

    if not args.json:
        print(f"Will execute action [{idx}] of {len(actions)} (filtered from {len(all_actions)}):")
        _print_action(idx, action)
        print(
            f"  -> type={action.get('type')} venue={action.get('venue_id')} "
            f"symbol={action.get('symbol')} side={action.get('side')}"
        )
        print(f"mode={'live' if args.live else 'dry-run'} rotation_live={rotation_live_enabled()}")

    result = execute_rotation(action, dry_run=dry_run)
    out = {
        "success": bool(result.get("success")),
        "dry_run": dry_run,
        "action_index": idx,
        "action": action.get("label"),
        "type": action.get("type"),
        "mode": result.get("mode"),
        "baseline_id": result.get("baseline_id"),
        "already_applied": result.get("already_applied"),
        "error": result.get("error") or result.get("reason"),
        "venue_id": action.get("venue_id"),
        "symbol": action.get("symbol"),
        "market": action.get("market"),
    }

    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        print(f"result: success={out['success']} mode={out.get('mode')} baseline={out.get('baseline_id')}")
        if out.get("error"):
            print(f"  error: {out['error']}")
        if out.get("already_applied"):
            print("  (already applied — no duplicate config write)")

    return 0 if out["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
