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
from backend.services.exchange_fill_model_service import train_and_save
from backend.services.exchange_ladder_service import (
    VENUES as LADDER_VENUES,
    format_ladder_block,
    run_ladder,
    write_ladder_log,
)
from backend.services.exchange_market_feed_service import feed_status
from backend.services.exchange_metrics_service import observe_feed
from backend.services.exchange_redis_bus import backend_name
from backend.services.exchange_maker_quote_service import (
    format_maker_block,
    run_maker_quotes,
    write_maker_log,
)
from backend.services.exchange_strategy_service import (
    dispatch_strategy_orders,
    format_strategy_block,
    search_strategies,
    write_strategy_logs,
)


def main() -> int:
    try:
        status = feed_status()
        observe_feed(status)
        print(f"feed bus={backend_name()} ok={sum(1 for r in status['symbols'].values() if r.get('ok'))}/{len(status['symbols'])}")
    except Exception as exc:
        print(f"feed status failed: {exc}")
    try:
        model = train_and_save()
        print(f"fill_model status={model.get('status')} n={model.get('n')}")
    except Exception as exc:
        print(f"fill_model failed: {exc}")
    search = search_fast_books()
    logs = write_search_logs(search)
    print(format_search_block(search), end="")
    try:
        strategies = search_strategies(book_report=search)
        strategies["sent"] = dispatch_strategy_orders(strategies, search)
        strategy_logs = write_strategy_logs(strategies)
        print(format_strategy_block(strategies), end="")
    except Exception as exc:
        strategies = {"actionable": 0, "execute": False, "error": str(exc)}
        strategy_logs = {}
        print(f"strategies failed: {exc}")
    try:
        maker = run_maker_quotes()
        write_maker_log(maker)
        print(format_maker_block(maker), end="")
    except Exception as exc:
        maker = {"execute": False, "error": str(exc)}
        print(f"maker failed: {exc}")
    ladders = {}
    for venue in LADDER_VENUES:
        try:
            ladder = run_ladder(venue=venue)
            write_ladder_log(ladder)
            print(format_ladder_block(ladder), end="")
        except Exception as exc:
            ladder = {"execute": False, "error": str(exc)}
            print(f"ladder {venue} failed: {exc}")
        ladders[venue] = ladder
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
    result["strategies"] = {
        "actionable": strategies.get("actionable"),
        "execute": strategies.get("execute"),
        "best": strategies.get("best"),
        "skipped_minus": strategies.get("skipped_minus"),
        "orders": [
            {"strategy": row.get("strategy"), "symbol": row.get("symbol"), "signal": row.get("signal")}
            for row in (strategies.get("orders") or [])
        ],
        "sent": [
            {"strategy": row.get("strategy"), "symbol": row.get("symbol"), "venue": row.get("venue"), "success": row.get("success"), "order_id": row.get("order_id"), "error": row.get("error"), "skipped": row.get("skipped")}
            for row in (strategies.get("sent") or [])
        ],
        "log": strategy_logs.get("calculations"),
    }
    result["maker"] = {
        "execute": maker.get("execute"),
        "quotes": maker.get("quotes"),
        "fills": maker.get("fills"),
        "error": maker.get("error"),
    }
    result["ladder"] = {
        venue: {
            key: ladder.get(key)
            for key in ("execute", "open_orders", "pending_exits", "realized_usd", "placed", "fills", "errors", "error")
        }
        for venue, ladder in ladders.items()
    }
    print(json.dumps(result, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
