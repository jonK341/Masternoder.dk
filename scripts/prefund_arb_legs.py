#!/usr/bin/env python3
"""One-shot ops tool: read top rotation suggestion and execute (dry-run by default).

Usage:
  python scripts/prefund_arb_legs.py              # dry-run top action
  python scripts/prefund_arb_legs.py --live       # live execute (requires EXCHANGE_ROTATION_LIVE=1)
  python scripts/prefund_arb_legs.py --list       # show top 3 suggestions only
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute top arb funding rotation action")
    parser.add_argument("--live", action="store_true", help="Execute live (default: dry-run)")
    parser.add_argument("--list", action="store_true", help="List suggestions only, no execute")
    parser.add_argument("--hours", type=float, default=6, help="PPP lookback hours for suggestions")
    parser.add_argument("--index", type=int, default=0, help="Action index to execute (0=top)")
    parser.add_argument("--json", action="store_true", help="Emit JSON result")
    args = parser.parse_args()

    from scripts.daemon_env import load_dotenv

    load_dotenv()

    from backend.services.exchange_swap_rotation_service import (
        execute_rotation,
        rotation_live_enabled,
        suggest_swap_actions,
    )

    rot = suggest_swap_actions(hours=args.hours, limit=5)
    actions = rot.get("actions") or []
    if not actions:
        out = {"success": False, "error": "no_actions", "funding_skip_count": rot.get("funding_skip_count")}
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            print("No rotation actions suggested (no funding skips in lookback window).")
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
        print(f"Top action [{idx}]:")
        _print_action(idx, action)
        print(f"mode={'live' if args.live else 'dry-run'} rotation_live={rotation_live_enabled()}")

    result = execute_rotation(action, dry_run=dry_run)
    out = {
        "success": bool(result.get("success")),
        "dry_run": dry_run,
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
