#!/usr/bin/env python3
"""Run cross-venue arbitrage paper agents in a daemon loop.

Phase 1: fetches live public prices, scans spreads, and credits per-agent paper
profit accounts. No real funds move (see docs/EXCHANGE_CROSS_VENUE_ARBITRAGE.md).
"""
from __future__ import annotations

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.daemon_env import load_dotenv, daemon_mode_label


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-venue arbitrage daemon")
    parser.add_argument("--once", action="store_true", help="Run one tick and exit")
    parser.add_argument("--interval", type=int, default=120, help="Interval seconds between ticks")
    args = parser.parse_args()

    from backend.services.exchange_arbitrage_service import run_paper_tick, live_enabled

    load_dotenv()
    if args.once:
        print(run_paper_tick())
        return 0

    print(f"[arbitrage-daemon] mode={daemon_mode_label()} interval={args.interval}s live={live_enabled()}")
    while True:
        try:
            result = run_paper_tick()
            print(f"[arbitrage-daemon] executed={result.get('executed_count')}/"
                  f"{result.get('agent_count')} source={result.get('source')}")
        except Exception as exc:  # never crash the loop
            print(f"[arbitrage-daemon] error: {exc}")
        time.sleep(max(15, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
