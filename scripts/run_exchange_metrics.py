#!/usr/bin/env python3
"""Prometheus scrape endpoint + periodic ladder/feed metric refresh."""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from typing import Any, Dict, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")

from scripts.daemon_env import load_dotenv

load_dotenv()

from backend.services import crypto_exchange_service as ex
from backend.services.exchange_fill_model_service import train_and_save, tune_ladder_cfg
from backend.services.exchange_inventory_skew import skew_factor
from backend.services.exchange_ladder_service import load_config, load_state, state_path
from backend.services.exchange_market_feed_service import cached_top, feed_status
from backend.services.exchange_metrics_service import observe_feed, observe_ladder, start_metrics_server
from backend.services.exchange_redis_bus import backend_name
from backend.services.exchange_venue_api_service import parse_spot_balances


def _fills_jsonl_path() -> str:
    return os.path.join(ex._BASE, "logs", "cross_trade", "ladder_fills.jsonl")


def _fill_counts(venue: str, path: Optional[str] = None) -> Dict[str, int]:
    counts: Counter[str] = Counter()
    jsonl = path or _fills_jsonl_path()
    if not os.path.isfile(jsonl):
        return {"entry": 0, "exit": 0}
    try:
        with open(jsonl, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(row.get("venue") or "nonkyc") != venue:
                    continue
                kind = str(row.get("kind") or "unknown")
                counts[kind] += 1
    except OSError:
        return {"entry": 0, "exit": 0}
    return {"entry": int(counts.get("entry") or 0), "exit": int(counts.get("exit") or 0)}


def _balances_for(venue: str) -> Dict[str, float]:
    try:
        return parse_spot_balances(venue, dry_run=False) or {}
    except Exception as exc:
        print(f"[metrics] balance {venue}: {exc}", flush=True)
        return {}


def _skews_for(venue: str, cfg: Dict[str, Any], balances: Dict[str, float]) -> Dict[str, float]:
    quote = str(cfg.get("quote") or ("USDC" if venue == "binance" else "USDT"))
    out: Dict[str, float] = {}
    for symbol in cfg.get("symbols") or []:
        top = cached_top(symbol, max_age_sec=30.0)
        if not top:
            out[symbol] = 0.0
            continue
        mid = (float(top["bid"]) + float(top["ask"])) / 2.0
        out[symbol] = round(skew_factor(balances, symbol, mid, quote), 4)
    return out


def _snapshot() -> None:
    observe_feed(feed_status())
    for venue in ("nonkyc", "binance"):
        cfg = load_config(venue)
        if not cfg.get("execute"):
            continue
        quote = str(cfg.get("quote") or ("USDC" if venue == "binance" else "USDT"))
        st = load_state(state_path(None, venue))
        open_n = sum(1 for o in st["orders"].values() if not o.get("cancelled"))
        exits = sum(1 for o in st["orders"].values() if not o.get("cancelled") and o.get("kind") == "exit")
        exits = max(exits, len(st.get("pending") or []))
        balances = _balances_for(venue)
        skews = _skews_for(venue, cfg, balances)
        tuned = tune_ladder_cfg(dict(cfg), venue=venue, min_prob=float(cfg.get("fill_model_min_prob") or 0.18))
        observe_ladder(
            {
                "venue": venue,
                "realized_usd": st.get("realized_usd") or 0,
                "open_orders": open_n,
                "pending_exits": exits,
                "fills": [],
                "cancelled": [],
                "repriced": [],
                "fill_counts": _fill_counts(venue),
                "_fill_prob_l0": tuned.get("_fill_prob_l0"),
            },
            balances=balances,
            quote=quote,
            skews=skews,
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
