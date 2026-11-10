#!/usr/bin/env python3
"""Binance bookTicker websocket → Redis/file bus for the ladder tick."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")

from scripts.daemon_env import load_dotenv

load_dotenv()

from backend.services.exchange_market_feed_service import DEFAULT_SYMBOLS, run_feed_forever
from backend.services.exchange_redis_bus import backend_name


def main() -> int:
    symbols = [s.strip().upper() for s in (os.environ.get("EXCHANGE_FEED_SYMBOLS") or "").split(",") if s.strip()]
    symbols = symbols or list(DEFAULT_SYMBOLS)
    print(f"[market-feed] bus={backend_name()} symbols={','.join(symbols)}", flush=True)
    run_feed_forever(symbols)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
