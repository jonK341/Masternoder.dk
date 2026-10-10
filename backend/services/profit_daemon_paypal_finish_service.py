"""Profit daemon — auto-capture APPROVED PayPal checkouts (shop, onramp, hosting, …)."""
from __future__ import annotations

import os
from typing import Any, Dict

_DEFAULT_INTERVAL_SEC = 600
_DEFAULT_LIMIT = 50


def paypal_finish_enabled() -> bool:
    """When true, profit daemon periodically runs finish_pending_paypal_orders."""
    raw = os.environ.get("PROFIT_DAEMON_PAYPAL_FINISH", "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def paypal_finish_interval_sec() -> int:
    try:
        iv = int(os.environ.get("PROFIT_DAEMON_PAYPAL_FINISH_INTERVAL", str(_DEFAULT_INTERVAL_SEC)))
    except (TypeError, ValueError):
        iv = _DEFAULT_INTERVAL_SEC
    return max(120, iv)


def paypal_finish_limit() -> int:
    try:
        limit = int(os.environ.get("PROFIT_DAEMON_PAYPAL_FINISH_LIMIT", str(_DEFAULT_LIMIT)))
    except (TypeError, ValueError):
        limit = _DEFAULT_LIMIT
    return max(1, min(limit, 400))


def paypal_prune_enabled() -> bool:
    raw = os.environ.get("PROFIT_DAEMON_PAYPAL_PRUNE", "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _summarize_prune(result: Dict[str, Any]) -> str:
    counts = result.get("counts") if isinstance(result.get("counts"), dict) else {}
    return (
        f"scanned={int(counts.get('scanned') or 0)} pruned={int(counts.get('pruned') or 0)} "
        f"kept={int(counts.get('kept') or 0)}"
    )


def _summarize_finish(result: Dict[str, Any]) -> str:
    counts = result.get("counts") if isinstance(result.get("counts"), dict) else {}
    pending = int(counts.get("pending_found") or 0)
    captured = int(counts.get("captured") or 0)
    awaiting = int(counts.get("awaiting_payer") or 0)
    expired = int(counts.get("expired") or 0)
    failed = int(counts.get("failed") or 0)
    skipped = int(counts.get("skipped") or 0)
    return (
        f"pending={pending} captured={captured} awaiting_payer={awaiting} "
        f"expired={expired} failed={failed} skipped={skipped}"
    )


def run_paypal_finish_tick() -> Dict[str, Any]:
    """
    Capture APPROVED PayPal Orders v2 checkouts and fulfill the matching rail.

    Without this, buyers who approve in PayPal but never hit /capture leave money
    uncaptured and local pending rows stuck open.
    """
    if not paypal_finish_enabled():
        return {"success": True, "skipped": True, "reason": "disabled"}
    from backend.services.paypal_order_events import finish_pending_paypal_orders

    from backend.services.paypal_order_events import (
        finish_pending_paypal_orders,
        prune_stale_paypal_pending_orders,
    )

    result = finish_pending_paypal_orders(limit=paypal_finish_limit())
    prune: Dict[str, Any] = {"skipped": True, "reason": "disabled"}
    if paypal_prune_enabled():
        prune = prune_stale_paypal_pending_orders(limit=paypal_finish_limit())
    if isinstance(result, dict):
        result["summary"] = _summarize_finish(result)
        result["prune"] = prune
        if prune.get("counts"):
            result["summary"] = f"{result['summary']} | prune {_summarize_prune(prune)}"
        try:
            from backend.services.profit_daemon_news_service import maybe_publish_paypal_finish_news
            from backend.services.profit_daemon_ops_service import maybe_alert_paypal_capture_batch

            maybe_publish_paypal_finish_news(result)
            maybe_alert_paypal_capture_batch(result)
        except Exception:
            pass
    return result
