"""
Optional Chainz CryptoID API for MN2: block height and USD price fallback.
Rate limit: 1 request per 10 seconds (no key). Cache responses to respect limit.
See docs/MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md §1 and §7.
"""
import os
import time
from typing import Any, Dict, Optional

try:
    import requests
except ImportError:
    requests = None

_CHAINZ_BASE = "https://chainz.cryptoid.info/mn2/api.dws"
_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = {"getblockcount": 120, "ticker.usd": 600}  # 2 min, 10 min


def _cached_get(q: str) -> Optional[Any]:
    now = time.time()
    if q in _CACHE and (now - _CACHE[q].get("ts", 0)) < _CACHE_TTL.get(q, 60):
        return _CACHE[q].get("value")
    if not requests:
        return None
    try:
        r = requests.get(f"{_CHAINZ_BASE}?q={q}", timeout=5)
        if r.status_code != 200:
            return None
        text = (r.text or "").strip()
        if q == "getblockcount":
            try:
                value = int(text)
            except ValueError:
                value = None
        else:
            value = text
        _CACHE[q] = {"value": value, "ts": now}
        return value
    except Exception:
        return _CACHE.get(q, {}).get("value")  # stale cache ok


def chainz_getblockcount() -> Optional[int]:
    """Chainz API block height for MN2. Cached 2 min. Returns None on error."""
    return _cached_get("getblockcount")


def chainz_ticker_usd() -> Optional[float]:
    """Chainz API MN2/USD price. Cached 10 min. Returns None on error."""
    out = chainz_ticker_usd_with_updated()
    return out.get("price") if isinstance(out, dict) else None


def chainz_ticker_usd_with_updated() -> Optional[Dict[str, Any]]:
    """Return { price: float, last_updated_iso: str } from cache, or None. Phase 9: live price feed."""
    now = time.time()
    q = "ticker.usd"
    if q in _CACHE and (now - _CACHE[q].get("ts", 0)) < _CACHE_TTL.get(q, 60):
        raw = _CACHE[q].get("value")
        ts = _CACHE[q].get("ts", now)
        try:
            from datetime import datetime, timezone
            price = float(raw) if isinstance(raw, (int, float)) else float(str(raw).strip())
            last_iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")
            return {"price": price, "last_updated_iso": last_iso}
        except (ValueError, TypeError):
            return None
    if not requests:
        return None
    try:
        r = requests.get(f"{_CHAINZ_BASE}?q={q}", timeout=5)
        if r.status_code != 200:
            if q in _CACHE:
                try:
                    return {"price": float(_CACHE[q]["value"]), "last_updated_iso": None}
                except Exception:
                    pass
            return None
        text = (r.text or "").strip()
        try:
            value = float(text)
        except ValueError:
            value = None
        _CACHE[q] = {"value": value, "ts": time.time()}
        if value is None:
            return None
        from datetime import datetime, timezone
        last_iso = datetime.fromtimestamp(_CACHE[q]["ts"], tz=timezone.utc).isoformat().replace("+00:00", "Z")
        return {"price": value, "last_updated_iso": last_iso}
    except Exception:
        if q in _CACHE:
            try:
                v = _CACHE[q]["value"]
                return {"price": float(v), "last_updated_iso": None}
            except Exception:
                pass
        return None
