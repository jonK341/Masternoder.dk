"""Live price feed for the exchange.

Wraps the multi-venue connector (external_exchange_connector_service) and
exposes a normalised mid-price for every asset in the exchange catalog.
Also writes ``price_cache.json`` drift multipliers so the internal exchange
service (``_price_usd``) uses real market prices automatically.

Refresh cadence:  driven by the master daemon tick (≈every 30–60 s) or
                  lazily on the first request with a 30-second TTL guard.
"""
from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_LIVE_CACHE_PATH = os.path.join(ex._DATA_DIR, "live_price_snapshot.json")
_REFRESH_LOCK = threading.Lock()

_DEFAULT_TTL = 30  # seconds before a cache miss triggers a network refresh


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _cache_age(snapshot: Dict[str, Any]) -> float:
    """Return age of snapshot in seconds, or +inf if unknown."""
    ts = snapshot.get("fetched_at") or ""
    if not ts:
        return float("inf")
    try:
        t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - t).total_seconds()
    except Exception:
        return float("inf")


def _mid(quote: Dict[str, float]) -> float:
    bid = quote.get("bid") or 0.0
    ask = quote.get("ask") or 0.0
    last = quote.get("last") or 0.0
    if bid > 0 and ask > 0:
        return (bid + ask) / 2.0
    return last or bid or ask


def _aggregate_mid(symbol: str, venue_prices: Dict[str, Dict[str, Dict[str, float]]]) -> Optional[float]:
    """Median mid-price across all venues that quote *symbol*."""
    mids = []
    for venue_data in venue_prices.values():
        q = venue_data.get(symbol)
        if q:
            m = _mid(q)
            if m > 0:
                mids.append(m)
    if not mids:
        return None
    mids.sort()
    mid = len(mids) // 2
    return mids[mid] if len(mids) % 2 else (mids[mid - 1] + mids[mid]) / 2.0


def _update_price_drift(symbol_mids: Dict[str, float]) -> None:
    """Write drift multipliers into *price_cache.json* so the internal exchange
    picks up live prices on the next ``_price_usd()`` call."""
    cfg = ex.load_config()
    drift: Dict[str, float] = {}
    for sym, live_mid in symbol_mids.items():
        assets = ex._asset_map(cfg)
        asset = assets.get(sym)
        if not asset:
            continue
        base = float(asset.get("base_price_usd") or 0)
        if base > 0 and live_mid > 0:
            drift[sym] = round(live_mid / base, 8)
    if drift:
        try:
            ex._write_json(ex._PRICE_CACHE_PATH, drift)
        except Exception:
            pass


def refresh(
    *,
    symbols: Optional[List[str]] = None,
    force: bool = False,
    ttl: int = _DEFAULT_TTL,
) -> Dict[str, Any]:
    """Fetch live prices from external venues and update the local snapshot.

    Returns the live price snapshot dict.  Thread-safe: concurrent callers
    share one network round-trip via *_REFRESH_LOCK*.
    """
    cached = ex._read_json(_LIVE_CACHE_PATH, {})
    if not force and _cache_age(cached) < ttl and cached.get("prices"):
        return {**cached, "source": "cache"}

    with _REFRESH_LOCK:
        # Re-check inside lock (another thread may have refreshed while we waited)
        cached = ex._read_json(_LIVE_CACHE_PATH, {})
        if not force and _cache_age(cached) < ttl and cached.get("prices"):
            return {**cached, "source": "cache"}

        try:
            from backend.services.external_exchange_connector_service import fetch_prices
            raw = fetch_prices(symbols=symbols, use_cache=False)
        except Exception as exc:
            return {"success": False, "error": str(exc), "source": "error"}

        venue_prices: Dict[str, Dict[str, Dict[str, float]]] = raw.get("prices") or {}
        all_symbols: List[str] = symbols or sorted(
            {sym for venue_data in venue_prices.values() for sym in venue_data}
        )

        mids: Dict[str, float] = {}
        by_symbol: Dict[str, Any] = {}
        for sym in all_symbols:
            mid = _aggregate_mid(sym, venue_prices)
            if mid:
                mids[sym] = round(mid, 8)
                by_symbol[sym] = {
                    "mid": mids[sym],
                    "venues": {
                        vid: venue_prices[vid][sym]
                        for vid in venue_prices
                        if sym in venue_prices[vid]
                    },
                }

        snapshot = {
            "success": True,
            "fetched_at": _iso(),
            "source": "live",
            "symbol_count": len(mids),
            "mids": mids,
            "by_symbol": by_symbol,
        }
        try:
            ex._write_json(_LIVE_CACHE_PATH, snapshot)
        except Exception:
            pass

        _update_price_drift(mids)
        ex._audit("live_price_refresh", symbol_count=len(mids))
        return snapshot


def get_snapshot(
    *,
    symbols: Optional[List[str]] = None,
    ttl: int = _DEFAULT_TTL,
) -> Dict[str, Any]:
    """Return cached snapshot (or refresh if stale)."""
    cached = ex._read_json(_LIVE_CACHE_PATH, {})
    if _cache_age(cached) < ttl and cached.get("prices") or cached.get("mids"):
        out = {**cached, "source": "cache"}
        if symbols:
            out["mids"] = {s: v for s, v in (cached.get("mids") or {}).items() if s in symbols}
            out["by_symbol"] = {s: v for s, v in (cached.get("by_symbol") or {}).items() if s in symbols}
        return out
    return refresh(symbols=symbols, ttl=ttl)


def price_for(symbol: str) -> Optional[float]:
    """Quick single-symbol mid-price lookup (uses cache, no network call)."""
    snap = ex._read_json(_LIVE_CACHE_PATH, {})
    return (snap.get("mids") or {}).get(symbol.upper())
