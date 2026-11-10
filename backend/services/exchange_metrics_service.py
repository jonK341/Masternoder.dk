"""Prometheus metrics for the exchange ladder / profit path.

``start_metrics_server`` binds an HTTP scrape endpoint (default ``:9108``).
``observe_ladder`` / ``observe_feed`` update gauges after each tick. Safe to call
when prometheus_client is missing — then it no-ops.
"""
from __future__ import annotations

import os
import threading
from typing import Any, Dict, Optional

_started = False
_lock = threading.Lock()
_metrics = None


def _init():
    global _metrics
    if _metrics is not None:
        return _metrics
    try:
        from prometheus_client import Counter, Gauge, Info
    except Exception:
        _metrics = False
        return _metrics
    _metrics = {
        "realized": Gauge("masternoder_ladder_realized_usd", "Ladder realized PnL USD", ["venue"]),
        "open_orders": Gauge("masternoder_ladder_open_orders", "Open ladder orders", ["venue", "kind"]),
        "pending_exits": Gauge("masternoder_ladder_pending_exits", "Pending ladder exits", ["venue"]),
        "fills": Counter("masternoder_ladder_fills_total", "Ladder fill events", ["venue", "kind", "side"]),
        "refresh_moves": Counter("masternoder_ladder_refresh_moves_total", "Entry/exit refreshes", ["venue", "kind"]),
        "free_quote": Gauge("masternoder_exchange_free_quote", "Free quote balance", ["venue", "asset"]),
        "feed_age": Gauge("masternoder_market_feed_age_seconds", "Age of cached mid", ["symbol"]),
        "bus": Info("masternoder_exchange_bus", "Exchange bus backend"),
        "fill_prob": Gauge("masternoder_ladder_fill_prob_l0", "Predicted L0 fill probability", ["venue"]),
        "skew": Gauge("masternoder_ladder_inventory_skew", "Inventory skew -1..1", ["venue", "symbol"]),
    }
    return _metrics


def start_metrics_server(port: Optional[int] = None) -> Dict[str, Any]:
    """Start the Prometheus HTTP server once per process."""
    global _started
    port = int(port or os.environ.get("EXCHANGE_METRICS_PORT") or 9108)
    with _lock:
        if _started:
            return {"ok": True, "port": port, "already": True}
        metrics = _init()
        if metrics is False:
            return {"ok": False, "error": "prometheus_client_unavailable"}
        try:
            from prometheus_client import start_http_server
            start_http_server(port)
            _started = True
            return {"ok": True, "port": port}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "port": port}


def observe_ladder(report: Dict[str, Any], *, balances: Optional[Dict[str, float]] = None,
                   quote: str = "USDT", skews: Optional[Dict[str, float]] = None) -> None:
    metrics = _init()
    if not metrics:
        return
    venue = str(report.get("venue") or "nonkyc")
    metrics["realized"].labels(venue=venue).set(float(report.get("realized_usd") or 0))
    metrics["pending_exits"].labels(venue=venue).set(float(report.get("pending_exits") or 0))
    metrics["open_orders"].labels(venue=venue, kind="all").set(float(report.get("open_orders") or 0))
    for fill in report.get("fills") or []:
        metrics["fills"].labels(venue=venue, kind=str(fill.get("kind") or ""), side=str(fill.get("side") or "")).inc()
    if report.get("cancelled"):
        metrics["refresh_moves"].labels(venue=venue, kind="entry").inc(len(report["cancelled"]))
    if report.get("repriced"):
        metrics["refresh_moves"].labels(venue=venue, kind="exit").inc(len(report["repriced"]))
    if balances is not None:
        metrics["free_quote"].labels(venue=venue, asset=quote).set(float(balances.get(quote) or 0))
    if report.get("_fill_prob_l0") is not None:
        metrics["fill_prob"].labels(venue=venue).set(float(report["_fill_prob_l0"]))
    for symbol, skew in (skews or {}).items():
        metrics["skew"].labels(venue=venue, symbol=symbol).set(float(skew))


def observe_feed(status: Dict[str, Any]) -> None:
    metrics = _init()
    if not metrics:
        return
    backend = str(status.get("backend") or "unknown")
    metrics["bus"].info({"backend": backend})
    for symbol, row in (status.get("symbols") or {}).items():
        if row.get("ok"):
            metrics["feed_age"].labels(symbol=symbol).set(float(row.get("age_sec") or 0))
