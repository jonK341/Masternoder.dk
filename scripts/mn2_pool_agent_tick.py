#!/usr/bin/env python3
"""Run one MN2/USDT/USDC pool agent tick (seed MN2, sweep stables, rebalance)."""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")


def main() -> int:
    parser = argparse.ArgumentParser(description="MN2 pool agent tick")
    parser.add_argument("--force", action="store_true", help="Ignore tick cooldown")
    parser.add_argument("--light", action="store_true", help="Light tick: skip heavy agent sweep")
    args = parser.parse_args()

    from backend.services.exchange_mn2_pool_agent_service import tick

    result = tick(force=bool(args.force), light=bool(args.light))
    print(json.dumps(result, default=str))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
