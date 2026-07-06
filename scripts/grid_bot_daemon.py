#!/usr/bin/env python3
"""Grid/market-maker bot daemon: ticks every configured asset on a loop.

Paper unless EXCHANGE_GRID_LIVE=1 + EXCHANGE_ARBITRAGE_LIVE=1 and venue credentials are set.
Enforces per-asset inventory cap + hard loss cap (auto-halt) from the grid bot config.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")


def main() -> int:
    parser = argparse.ArgumentParser(description="Grid/market-maker bot daemon")
    parser.add_argument("--once", action="store_true", help="Run one tick cycle and exit")
    parser.add_argument("--interval", type=int, default=30, help="Seconds between tick cycles")
    parser.add_argument("--paper", action="store_true", help="Force paper mode (no real orders)")
    args = parser.parse_args()

    try:
        from scripts.daemon_env import load_dotenv
        load_dotenv()
    except Exception:
        pass

    from backend.services.exchange_grid_bot_service import run_all, grid_live_enabled

    dry = True if args.paper else None
    mode = "paper" if (args.paper or not grid_live_enabled()) else "LIVE"

    if args.once:
        print(run_all(dry_run=dry))
        return 0

    print(f"[grid-daemon] mode={mode} interval={args.interval}s")
    while True:
        try:
            res = run_all(dry_run=dry)
            if not res.get("skipped"):
                print(f"[grid-daemon] realized_pnl_usd={res.get('realized_pnl_usd')} "
                      f"ticks={len(res.get('ticks') or [])}")
        except Exception as exc:
            print(f"[grid-daemon] loop error: {exc}")
        time.sleep(max(10, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
