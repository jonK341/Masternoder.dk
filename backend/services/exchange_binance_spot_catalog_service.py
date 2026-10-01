"""Binance spot market catalog — all TRADING USDC/USDT pairs for daemon coverage."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.services import crypto_exchange_service as ex

_CACHE_PATH = os.path.join(ex._DATA_DIR, "binance_spot_catalog.json")
_STABLE_SKIP = frozenset({"USDC", "USDT", "BUSD", "FDUSD", "TUSD", "DAI", "USD"})
_DEFAULT_QUOTES = ("USDC", "USDT")
_TTL_SEC = int(os.environ.get("BINANCE_SPOT_CATALOG_TTL_SEC", "3600"))


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_cache() -> Dict[str, Any]:
    data = ex._read_json(_CACHE_PATH, {})
    return data if isinstance(data, dict) else {}


def _write_cache(data: Dict[str, Any]) -> None:
    ex._write_json(_CACHE_PATH, data)


def _cache_fresh(cached: Dict[str, Any]) -> bool:
    try:
        fetched = cached.get("fetched_at") or ""
        if not fetched:
            return False
        age = (
            datetime.now(timezone.utc)
            - datetime.fromisoformat(fetched.replace("Z", "+00:00"))
        ).total_seconds()
        return age < _TTL_SEC
    except Exception:
        return False


def refresh_binance_spot_catalog(*, force: bool = False) -> Dict[str, Any]:
    """Pull full Binance spot exchangeInfo and index TRADING bases per quote."""
    cached = _read_cache()
    if not force and _cache_fresh(cached) and cached.get("bases_by_quote"):
        return {
            "success": True,
            "cached": True,
            "fetched_at": cached.get("fetched_at"),
            "bases_by_quote": cached.get("bases_by_quote") or {},
            "all_bases": cached.get("all_bases") or [],
            "count": int(cached.get("count") or 0),
        }

    by_quote: Dict[str, Set[str]] = {q: set() for q in _DEFAULT_QUOTES}
    try:
        import requests
        from backend.services.exchange_http_util import force_ipv4_outbound_if_configured

        force_ipv4_outbound_if_configured()
        resp = requests.get(
            "https://api.binance.com/api/v3/exchangeInfo",
            timeout=12,
            headers={"User-Agent": "masternoder-binance-catalog/1.0"},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"exchangeInfo HTTP {resp.status_code}")
        for sym in (resp.json() or {}).get("symbols") or []:
            if not isinstance(sym, dict):
                continue
            if sym.get("status") != "TRADING":
                continue
            quote = str(sym.get("quoteAsset") or "").upper()
            if quote not in by_quote:
                continue
            base = str(sym.get("baseAsset") or "").upper()
            if not base or base in _STABLE_SKIP:
                continue
            by_quote[quote].add(base)
    except Exception as exc:
        if cached.get("all_bases"):
            return {
                "success": True,
                "cached": True,
                "stale_fallback": True,
                "error": str(exc)[:200],
                "fetched_at": cached.get("fetched_at"),
                "bases_by_quote": cached.get("bases_by_quote") or {},
                "all_bases": cached.get("all_bases") or [],
                "count": int(cached.get("count") or 0),
            }
        from backend.services import external_exchange_connector_service as conn

        fb = {str(s).upper() for s in (conn.load_connectors_config().get("supported_symbols") or [])}
        by_quote["USDC"] = set(fb)
        by_quote["USDT"] = set()

    all_bases = sorted(set().union(*by_quote.values()))
    payload = {
        "fetched_at": _iso(),
        "bases_by_quote": {k: sorted(v) for k, v in by_quote.items()},
        "all_bases": all_bases,
        "count": len(all_bases),
    }
    _write_cache(payload)
    return {"success": True, "cached": False, **payload}


def binance_usdc_bases(*, force_refresh: bool = False) -> Set[str]:
    """Compat with profit pair search — USDC spot bases on Binance."""
    res = refresh_binance_spot_catalog(force=force_refresh)
    bq = res.get("bases_by_quote") or {}
    return {str(b).upper() for b in (bq.get("USDC") or [])}


def bases_for_venue_quote(venue: str, quote: str, *, force_refresh: bool = False) -> List[str]:
    if str(venue).lower() != "binance":
        return []
    res = refresh_binance_spot_catalog(force=force_refresh)
    bq = res.get("bases_by_quote") or {}
    q = str(quote or "USDC").upper()
    if q in bq:
        return list(bq[q])
    return list(res.get("all_bases") or [])


def catalog_batch(
    *,
    batch_size: int = 24,
    offset: int = 0,
    quote: str = "USDC",
    force_refresh: bool = False,
) -> Tuple[List[str], int, int]:
    """Return the next slice of Binance spot bases (rotating window)."""
    bases = bases_for_venue_quote("binance", quote, force_refresh=force_refresh)
    n = len(bases)
    if n == 0 or batch_size <= 0:
        return [], 0, 0
    off = int(offset) % n
    out: List[str] = []
    for i in range(min(batch_size, n)):
        out.append(bases[(off + i) % n])
    next_off = (off + batch_size) % n
    return out, next_off, n


def coverage_snapshot(assets_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Ops view: catalog size vs resting daemon orders on Binance."""
    cat = refresh_binance_spot_catalog()
    assets_state = assets_state or {}
    resting_sell = resting_buy = 0
    tracked = 0
    for key, row in assets_state.items():
        if not str(key).startswith("binance:"):
            continue
        if not isinstance(row, dict):
            continue
        tracked += 1
        if row.get("sell_order_id"):
            resting_sell += 1
        if row.get("buy_order_id"):
            resting_buy += 1
    return {
        "success": True,
        "catalog_count": int(cat.get("count") or 0),
        "usdc_pairs": len((cat.get("bases_by_quote") or {}).get("USDC") or []),
        "usdt_pairs": len((cat.get("bases_by_quote") or {}).get("USDT") or []),
        "fetched_at": cat.get("fetched_at"),
        "tracked_symbols": tracked,
        "resting_sells": resting_sell,
        "resting_buys": resting_buy,
    }
