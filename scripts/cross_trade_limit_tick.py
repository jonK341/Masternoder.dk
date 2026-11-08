#!/usr/bin/env python3
"""One cross-venue limit-arb pass for cron. Prints a single JSON line."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")
os.environ.setdefault("BINANCE_QUOTE", "USDC")
os.environ.setdefault("EXCHANGE_FORCE_IPV4", "1")

from scripts.daemon_env import load_dotenv

load_dotenv()

from backend.services.exchange_arbitrage_service import live_enabled
from backend.services.exchange_cross_trade_service import (
    cross_trade_live_enabled,
    format_search_block,
    run_once,
    search_fast_books,
    write_search_logs,
)


def main() -> int:
    search = search_fast_books()
    logs = write_search_logs(search)
    print(format_search_block(search), end="")
    result = run_once()
    result["arbitrage_live"] = bool(live_enabled())
    result["cross_trade_live"] = bool(cross_trade_live_enabled())
    result["search"] = {
        "best_symbol": search.get("best_symbol"),
        "best_route": search.get("best_route"),
        "best_net_bps": search.get("best_net_bps"),
        "best_decision": search.get("best_decision"),
        "fee_bps": search.get("fee_bps"),
        "calculations_log": logs.get("calculations"),
        "search_log": logs.get("jsonl"),
    }
    print(json.dumps(result, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
