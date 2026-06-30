#!/usr/bin/env python3
"""Run crypto exchange cross-trading agents in a local/server daemon loop."""
from __future__ import annotations

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Crypto exchange agent daemon")
    parser.add_argument("--once", action="store_true", help="Run one tick and exit")
    parser.add_argument("--interval", type=int, default=0, help="Override interval seconds")
    args = parser.parse_args()

    from backend.services.crypto_exchange_agent_service import list_agents, tick

    interval = args.interval or int(list_agents().get("daemon_interval_sec") or 300)
    if args.once:
        print(tick(force=True))
        return 0

    print(f"[crypto-exchange-agent-daemon] interval={interval}s")
    while True:
        result = tick()
        print(f"[crypto-exchange-agent-daemon] tick={result.get('tick_count')} success={result.get('success')}")
        time.sleep(max(5, interval))


if __name__ == "__main__":
    raise SystemExit(main())
