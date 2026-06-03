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


_CACHE_TTL.update({"getdifficulty": 300, "mncount": 600})


def chainz_difficulty() -> Optional[float]:
    """Chainz network difficulty for MN2. Cached 5 min. Returns None on error."""
    v = _cached_get("getdifficulty")
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def chainz_masternode_count() -> Optional[int]:
    """Chainz masternode count for MN2. Cached 10 min. Returns None on error."""
    v = _cached_get("mncount")
    try:
        return int(float(v)) if v is not None else None
    except (TypeError, ValueError):
        return None


def network_overview() -> Dict[str, Any]:
    """
    Aggregate MN2 network stats: RPC-first (own daemon), Chainz fallback. Best-effort, never raises.
    Returns block_height, mn2_usd_price, staking_weight, masternode_count, difficulty.
    """
    out: Dict[str, Any] = {
        "block_height": None,
        "mn2_usd_price": None,
        "staking_weight": None,
        "expected_stake_time_sec": None,
        "masternode_count": None,
        "difficulty": None,
        "source": {},
    }
    # RPC first
    try:
        from backend.services import mn2_rpc_client as rpc
        r = rpc.getblockcount(timeout_sec=4)
        if not r.get("error") and r.get("result") is not None:
            out["block_height"] = int(r["result"]); out["source"]["block_height"] = "rpc"
        si = rpc.getstakinginfo()
        if not si.get("error") and isinstance(si.get("result"), dict):
            res = si["result"]
            out["staking_weight"] = res.get("netstakeweight") or res.get("weight")
            out["expected_stake_time_sec"] = res.get("expectedtime")
            out["source"]["staking_weight"] = "rpc"
        mc = rpc.getmasternodecount()
        if not mc.get("error") and mc.get("result") is not None:
            res = mc["result"]
            out["masternode_count"] = res.get("total") if isinstance(res, dict) else res
            out["source"]["masternode_count"] = "rpc"
        df = rpc.getdifficulty()
        if not df.get("error") and df.get("result") is not None:
            res = df["result"]
            out["difficulty"] = res.get("proof-of-stake") if isinstance(res, dict) else res
            out["source"]["difficulty"] = "rpc"
    except Exception:
        pass
    # Chainz fallback for anything still missing
    try:
        if out["block_height"] is None:
            bh = chainz_getblockcount()
            if bh is not None:
                out["block_height"] = bh; out["source"]["block_height"] = "chainz"
        if out["mn2_usd_price"] is None:
            px = chainz_ticker_usd()
            if px is not None:
                out["mn2_usd_price"] = round(px, 8); out["source"]["mn2_usd_price"] = "chainz"
        if out["masternode_count"] is None:
            mc = chainz_masternode_count()
            if mc is not None:
                out["masternode_count"] = mc; out["source"]["masternode_count"] = "chainz"
        if out["difficulty"] is None:
            d = chainz_difficulty()
            if d is not None:
                out["difficulty"] = d; out["source"]["difficulty"] = "chainz"
    except Exception:
        pass
    return out


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
