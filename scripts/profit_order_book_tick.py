#!/usr/bin/env python3
"""Refresh the profit order book (top-5 hitlist + ledger + leg techniques)."""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    ap = argparse.ArgumentParser(description="Profit order book tick")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--apply", action="store_true", help="Apply top technique when enabled gates pass")
    args = ap.parse_args()

    try:
        from scripts.daemon_env import load_dotenv
        load_dotenv()
    except Exception:
        pass

    from backend.services.exchange_profit_order_book_service import (
        profit_order_book_status,
        run_profit_order_book_tick,
    )

    if args.status:
        out = profit_order_book_status()
    else:
        out = run_profit_order_book_tick(force=args.force, apply=True if args.apply else None)

    if args.json or args.status:
        print(json.dumps(out, indent=2, default=str))
    else:
        best = out.get("best") or ((out.get("top5") or [{}])[0] if out.get("top5") else {})
        print(
            f"book deals={out.get('deal_count')} qual={out.get('qualifying_count')} "
            f"best={best.get('net_bps')}bps ${best.get('est_profit_usd')} "
            f"{best.get('symbol')} {best.get('action') or best.get('route')} "
            f"tech={best.get('best_technique')} applied={bool(out.get('applied'))} "
            f"skip={out.get('skip_reason')}"
        )
        for i, row in enumerate(out.get("top5") or [], 1):
            print(
                f"  #{i} {row.get('symbol')} {row.get('net_bps')}bps "
                f"${row.get('est_profit_usd')} {row.get('action')} "
                f"tech={row.get('best_technique')} funded={row.get('funded')}"
            )
    return 0 if out.get("success") or out.get("skipped") else 1


if __name__ == "__main__":
    raise SystemExit(main())
