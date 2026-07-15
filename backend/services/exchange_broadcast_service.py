"""SSE broadcast snapshots for exchange hub — daemon feed, prices, metrics."""
from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional


def broadcast_snapshot(
    user_id: str,
    *,
    feed_limit: int = 20,
    price_venues: Optional[list] = None,
    include_metrics: bool = True,
) -> Dict[str, Any]:
    from backend.services import crypto_exchange_service as ex
    from backend.services.exchange_trading_monitor_service import live_monitor

    venues = price_venues or ["binance", "nonkyc"]
    monitor = live_monitor(user_id or "", feed_limit=feed_limit)
    prices = ex.external_prices_payload(venues=venues)
    out: Dict[str, Any] = {
        "success": True,
        "type": "exchange_broadcast",
        "ts": time.time(),
        "monitor": monitor,
        "prices": prices,
    }
    if include_metrics:
        try:
            from backend.services.profit_daemon_ops_service import daemon_metrics_snapshot
            out["daemon_metrics"] = daemon_metrics_snapshot()
        except Exception as exc:
            out["daemon_metrics"] = {"success": False, "error": str(exc)[:200]}
    return out


def snapshot_signature(payload: Dict[str, Any]) -> str:
    """Stable hash for SSE change detection."""
    slim = {
        "feed_head": (payload.get("monitor") or {}).get("feed", [])[:5],
        "totals": (payload.get("monitor") or {}).get("totals"),
        "scanned_at": (payload.get("prices") or {}).get("scanned_at"),
        "pair_count": len((payload.get("prices") or {}).get("pairs") or []),
        "metrics_loops": len(((payload.get("daemon_metrics") or {}).get("loops") or [])),
    }
    return json.dumps(slim, sort_keys=True, default=str)
