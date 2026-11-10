#!/usr/bin/env python3
"""Watch the five fast USDT coins and write a plain-language action line each pass.

Paper by default. This process does not withdraw. A real order still needs
EXCHANGE_ARBITRAGE_LIVE and EXCHANGE_CROSS_TRADE_LIVE, and a book that can fill the clip.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("LITE_APP", "1")
os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("BINANCE_QUOTE", "USDC")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fast USDT watch daemon")
    parser.add_argument("--once", action="store_true", help="One pass, then exit")
    parser.add_argument("--interval", type=int, default=20, help="Seconds between passes")
    args = parser.parse_args()

    from backend.services.fast_desk_service import tick

    if args.once:
        result = tick()
        print(result.get("latest"))
        return 0

    print(f"[fast-desk] interval={args.interval}s quote=USDC")
    while True:
        try:
            result = tick()
            print(f"[fast-desk] {result.get('latest')}")
        except Exception as exc:
            print(f"[fast-desk] error: {exc}")
        time.sleep(max(10, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
