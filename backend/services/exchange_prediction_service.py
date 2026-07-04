"""Profit Prediction Engine — an explainable heuristic forecast for agents.

This is NOT a guaranteed signal. It blends transparent market signals (cross-venue
price gap vs the internal price, venue dispersion, and coverage) into a directional
view, a confidence score, and an "edge uplift" that premium agents can capture on top
of their base skill edge. By default it reads the last cached external prices and does
NOT hit the network, so it is safe to call inside agent ticks.
"""
from __future__ import annotations

from statistics import median
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services import external_exchange_connector_service as conn

_DISCLAIMER = "Heuristic forecast from public price signals. Not financial advice; no profit is guaranteed."


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _cached_prices() -> Dict[str, Dict[str, Dict[str, float]]]:
    cached = ex._read_json(conn._PRICE_CACHE_PATH, {})
    if isinstance(cached, dict) and isinstance(cached.get("prices"), dict):
        return cached["prices"]
    return {}


def _venue_mids(prices: Dict[str, Dict[str, Dict[str, float]]], symbol: str) -> List[float]:
    mids: List[float] = []
    for _vid, syms in (prices or {}).items():
        t = (syms or {}).get(symbol)
        if not t:
            continue
        bid, ask, last = float(t.get("bid") or 0), float(t.get("ask") or 0), float(t.get("last") or 0)
        mid = last if last > 0 else ((bid + ask) / 2 if bid > 0 and ask > 0 else (bid or ask))
        if mid > 0:
            mids.append(mid)
    return mids


def predict_symbol(symbol: str, prices: Optional[Dict[str, Dict[str, Dict[str, float]]]] = None) -> Dict[str, Any]:
    symbol = str(symbol).upper()
    if prices is None:
        prices = _cached_prices()
    mids = _venue_mids(prices, symbol)
    internal = ex._price_usd(symbol)

    if not mids:
        return {
            "symbol": symbol, "direction": "flat", "confidence_pct": 5.0,
            "expected_move_bps": 0.0, "arb_edge_bps": 0.0, "edge_uplift_bps": 0.0,
            "venue_count": 0, "internal_price_usd": round(internal, 8), "external_mid_usd": 0.0,
            "signals": [{"name": "coverage", "value": 0, "note": "No external prices cached yet."}],
            "disclaimer": _DISCLAIMER,
        }

    ext_mid = median(mids)
    dispersion_bps = ((max(mids) - min(mids)) / ext_mid * 10000.0) if ext_mid > 0 else 0.0
    gap_bps = ((ext_mid - internal) / internal * 10000.0) if internal > 0 else 0.0

    if gap_bps > 5:
        direction = "up"
    elif gap_bps < -5:
        direction = "down"
    else:
        direction = "flat"

    expected_move_bps = round(min(abs(gap_bps), 500.0), 2)
    venue_count = len(mids)
    confidence = 40.0 + min(venue_count, 6) * 8.0 - min(dispersion_bps / 20.0, 20.0)
    confidence = round(_clamp(confidence, 5.0, 92.0), 1)
    arb_edge_bps = round(max(0.0, dispersion_bps - 40.0), 2)
    edge_uplift_bps = round(arb_edge_bps * 0.5 + expected_move_bps * 0.25, 2)

    signals = [
        {"name": "price_gap", "value": round(gap_bps, 2),
         "note": "Internal price vs external mid (mean-reversion pull)."},
        {"name": "venue_dispersion", "value": round(dispersion_bps, 2),
         "note": "Spread across venues (arbitrage potential)."},
        {"name": "coverage", "value": venue_count,
         "note": "Number of venues quoting this symbol."},
    ]
    return {
        "symbol": symbol,
        "direction": direction,
        "confidence_pct": confidence,
        "expected_move_bps": expected_move_bps,
        "arb_edge_bps": arb_edge_bps,
        "edge_uplift_bps": edge_uplift_bps,
        "venue_count": venue_count,
        "internal_price_usd": round(internal, 8),
        "external_mid_usd": round(ext_mid, 8),
        "signals": signals,
        "disclaimer": _DISCLAIMER,
    }


def predict_batch(symbols: Optional[List[str]] = None,
                  prices: Optional[Dict[str, Dict[str, Dict[str, float]]]] = None) -> Dict[str, Any]:
    if prices is None:
        prices = _cached_prices()
    symbols = [str(s).upper() for s in (symbols or conn.load_connectors_config().get("supported_symbols") or [])]
    rows = [predict_symbol(s, prices) for s in symbols]
    rows.sort(key=lambda r: r["edge_uplift_bps"], reverse=True)
    return {"success": True, "count": len(rows), "predictions": rows, "disclaimer": _DISCLAIMER}


def market_uplift_bps(prices: Optional[Dict[str, Dict[str, Dict[str, float]]]] = None,
                      symbols: Optional[List[str]] = None) -> float:
    """Average predicted edge uplift across symbols — used to boost premium agents."""
    batch = predict_batch(symbols, prices)
    rows = batch.get("predictions") or []
    if not rows:
        return 0.0
    return round(sum(r["edge_uplift_bps"] for r in rows) / len(rows), 2)
