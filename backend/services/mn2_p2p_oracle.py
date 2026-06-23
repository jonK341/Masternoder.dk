"""
P2P listing price corridor anchored to Chainz MN2/USD oracle.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def _oracle_usd() -> Optional[float]:
    try:
        from backend.services.mn2_chainz import chainz_ticker_usd

        p = chainz_ticker_usd()
        if p is not None and float(p) > 0:
            return round(float(p), 8)
    except Exception:
        pass
    return None


def get_corridor(spread_percent: Optional[float] = None) -> Dict[str, Any]:
    """Return oracle mid and min/max allowed listing price (USD per MN2)."""
    try:
        from backend.services.mn2_p2p_service import get_config

        cfg = get_config()
    except Exception:
        cfg = {}
    spread = float(spread_percent if spread_percent is not None else cfg.get("oracle_spread_percent", 25))
    spread = max(0.0, min(spread, 90.0))
    oracle = _oracle_usd()
    if oracle is None:
        return {
            "success": True,
            "oracle_available": False,
            "oracle_usd_per_mn2": None,
            "min_price_usd_per_mn2": None,
            "max_price_usd_per_mn2": None,
            "spread_percent": spread,
        }
    factor = spread / 100.0
    return {
        "success": True,
        "oracle_available": True,
        "oracle_usd_per_mn2": oracle,
        "min_price_usd_per_mn2": round(oracle * (1.0 - factor), 8),
        "max_price_usd_per_mn2": round(oracle * (1.0 + factor), 8),
        "spread_percent": spread,
    }


def validate_listing_price(price_usd_per_mn2: float) -> Dict[str, Any]:
    """Return {allowed: bool, ...} for a seller listing price."""
    try:
        price = round(float(price_usd_per_mn2), 8)
    except (TypeError, ValueError):
        return {"allowed": False, "error": "price_usd_per_mn2 must be a number", "code": "invalid_price"}
    if price <= 0:
        return {"allowed": False, "error": "price must be positive", "code": "invalid_price"}

    corridor = get_corridor()
    if not corridor.get("oracle_available"):
        return {"allowed": True, "oracle_skipped": True, "reason": "oracle unavailable — gate skipped"}

    lo = corridor["min_price_usd_per_mn2"]
    hi = corridor["max_price_usd_per_mn2"]
    if price < lo or price > hi:
        return {
            "allowed": False,
            "code": "price_outside_corridor",
            "error": (
                f"Listing price must be between {lo:.8f} and {hi:.8f} USD/MN2 "
                f"(oracle {corridor['oracle_usd_per_mn2']:.8f}, ±{corridor['spread_percent']:.0f}%)."
            ),
            "oracle_usd_per_mn2": corridor["oracle_usd_per_mn2"],
            "min_price_usd_per_mn2": lo,
            "max_price_usd_per_mn2": hi,
            "submitted_price": price,
            "deviation_pct": round((price / corridor["oracle_usd_per_mn2"] - 1.0) * 100.0, 2),
        }
    return {
        "allowed": True,
        "oracle_usd_per_mn2": corridor["oracle_usd_per_mn2"],
        "deviation_pct": round((price / corridor["oracle_usd_per_mn2"] - 1.0) * 100.0, 2),
    }
