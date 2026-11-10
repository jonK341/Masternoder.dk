#!/usr/bin/env python3
"""Prometheus scrape endpoint + periodic ladder/feed metric refresh."""
from __future__ import annotations

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")

from scripts.daemon_env import load_dotenv

load_dotenv()

from backend.services.exchange_fill_model_service import train_and_save
from backend.services.exchange_ladder_service import load_config, load_state, state_path
from backend.services.exchange_market_feed_service import feed_status
from backend.services.exchange_metrics_service import observe_feed, observe_ladder, start_metrics_server
from backend.services.exchange_redis_bus import backend_name


def _snapshot() -> None:
    observe_feed(feed_status())
    for venue in ("nonkyc", "binance"):
        cfg = load_config(venue)
        if not cfg.get("execute"):
            continue
        st = load_state(state_path(None, venue))
        open_n = sum(1 for o in st["orders"].values() if not o.get("cancelled"))
        exits = sum(1 for o in st["orders"].values() if not o.get("cancelled") and o.get("kind") == "exit")
        observe_ladder(
            {
                "venue": venue,
                "realized_usd": st.get("realized_usd") or 0,
                "open_orders": open_n,
                "pending_exits": exits,
                "fills": [],
                "cancelled": [],
                "repriced": [],
            },
            quote=cfg.get("quote") or ("USDC" if venue == "binance" else "USDT"),
        )


def main() -> int:
    port = int(os.environ.get("EXCHANGE_METRICS_PORT") or 9108)
    started = start_metrics_server(port)
    print(f"[metrics] {started} bus={backend_name()}", flush=True)
    print(f"[metrics] fill-model {train_and_save()}", flush=True)
    while True:
        try:
            _snapshot()
        except Exception as exc:
            print(f"[metrics] snapshot error: {exc}", flush=True)
        time.sleep(float(os.environ.get("EXCHANGE_METRICS_INTERVAL") or 30))


if __name__ == "__main__":
    raise SystemExit(main())
