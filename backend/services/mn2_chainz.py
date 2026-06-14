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


_SUPPLY_CACHE: Dict[str, Any] = {}
_SUPPLY_TTL = 600  # gettxoutsetinfo is a full UTXO scan; cache 10 min


def _cached_circulating_supply() -> Optional[float]:
    """Circulating supply (gettxoutsetinfo.total_amount), cached. None if unsupported/error."""
    now = time.time()
    if "value" in _SUPPLY_CACHE and (now - _SUPPLY_CACHE.get("ts", 0)) < _SUPPLY_TTL:
        return _SUPPLY_CACHE.get("value")
    try:
        from backend.services import mn2_rpc_client as rpc
        r = rpc.gettxoutsetinfo()
        if not r.get("error") and isinstance(r.get("result"), dict):
            ta = r["result"].get("total_amount")
            if ta is not None:
                value = round(float(ta), 8)
                _SUPPLY_CACHE["value"] = value
                _SUPPLY_CACHE["ts"] = now
                return value
    except Exception:
        pass
    return _SUPPLY_CACHE.get("value")  # stale ok


_DAEMON_CACHE: Dict[str, Any] = {}
_DAEMON_TTL = 30  # seconds — bound RPC load from the explorer poll


def daemon_extras() -> Dict[str, Any]:
    """Extra live daemon stats for the explorer (connections, mempool, version, chain).

    RPC-only (no Chainz fallback), cached ~30s. Tolerates forks that don't implement
    a given RPC — each field is independently best-effort and stays None if missing.
    """
    now = time.time()
    cached = _DAEMON_CACHE.get("value")
    if cached is not None and (now - _DAEMON_CACHE.get("ts", 0)) < _DAEMON_TTL:
        return cached

    out: Dict[str, Any] = {
        "connections": None, "version": None, "subversion": None,
        "protocol_version": None, "mempool_tx": None, "mempool_bytes": None,
        "chain": None, "verification_progress": None, "median_time": None,
        "size_on_disk": None, "headers": None, "money_supply": None,
        "reachable": False,
    }
    try:
        from backend.services import mn2_rpc_client as rpc

        cc = rpc.getconnectioncount(timeout_sec=4)
        if not cc.get("error") and cc.get("result") is not None:
            out["connections"] = int(cc["result"]); out["reachable"] = True

        ni = rpc.getnetworkinfo()
        if not ni.get("error") and isinstance(ni.get("result"), dict):
            r = ni["result"]; out["reachable"] = True
            out["version"] = r.get("version")
            out["subversion"] = r.get("subversion")
            out["protocol_version"] = r.get("protocolversion")
            if out["connections"] is None and r.get("connections") is not None:
                out["connections"] = r.get("connections")

        mp = rpc.getmempoolinfo()
        if not mp.get("error") and isinstance(mp.get("result"), dict):
            r = mp["result"]
            out["mempool_tx"] = r.get("size")
            out["mempool_bytes"] = r.get("bytes") or r.get("usage")

        bi = rpc.getblockchaininfo()
        if not bi.get("error") and isinstance(bi.get("result"), dict):
            r = bi["result"]; out["reachable"] = True
            out["chain"] = r.get("chain")
            out["verification_progress"] = r.get("verificationprogress")
            out["median_time"] = r.get("mediantime")
            out["size_on_disk"] = r.get("size_on_disk")
            out["headers"] = r.get("headers")
            if r.get("moneysupply") is not None:
                out["money_supply"] = r.get("moneysupply")

        # PIVX getinfo fills version/connections/moneysupply gaps on older forks.
        if out["money_supply"] is None or out["version"] is None or out["connections"] is None:
            gi = rpc.getinfo()
            if not gi.get("error") and isinstance(gi.get("result"), dict):
                r = gi["result"]; out["reachable"] = True
                if out["money_supply"] is None:
                    out["money_supply"] = r.get("moneysupply")
                if out["version"] is None:
                    out["version"] = r.get("version")
                if out["protocol_version"] is None:
                    out["protocol_version"] = r.get("protocolversion")
                if out["connections"] is None:
                    out["connections"] = r.get("connections")
    except Exception:
        pass

    _DAEMON_CACHE["value"] = out
    _DAEMON_CACHE["ts"] = now
    return out


def network_overview() -> Dict[str, Any]:
    """
    Aggregate MN2 network stats: RPC-first (own daemon), Chainz fallback. Best-effort, never raises.
    Returns block_height, mn2_usd_price, staking_weight, masternode_count, difficulty,
    plus a `daemon` block (connections, mempool, version, chain) and top-level
    `connections`/`mempool_tx` for sparkline history.
    """
    out: Dict[str, Any] = {
        "block_height": None,
        "mn2_usd_price": None,
        "staking_weight": None,
        "network_hashps": None,
        "expected_stake_time_sec": None,
        "masternode_count": None,
        "difficulty": None,
        "circulating_supply": None,
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
        # getmininginfo: networkhashps is the network-weight proxy on PoS forks
        # that don't implement getstakinginfo (MasterNoder2). Also a difficulty fallback.
        mi = rpc.getmininginfo()
        if not mi.get("error") and isinstance(mi.get("result"), dict):
            res = mi["result"]
            nh = res.get("networkhashps")
            if nh is not None:
                out["network_hashps"] = nh
                if out["staking_weight"] is None:
                    out["staking_weight"] = nh
                    out["source"]["staking_weight"] = "rpc"
            if out["difficulty"] is None and res.get("difficulty") is not None:
                out["difficulty"] = res.get("difficulty")
                out["source"]["difficulty"] = "rpc"
        # circulating supply via gettxoutsetinfo (heavy UTXO scan) -> cached ~10 min
        supply = _cached_circulating_supply()
        if supply is not None:
            out["circulating_supply"] = supply
            out["source"]["circulating_supply"] = "rpc"
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

    # Live daemon extras (connections, mempool, version, chain). Top-level mirrors
    # of connections/mempool_tx let the history snapshotter chart them over time.
    try:
        de = daemon_extras()
        out["daemon"] = de
        out["connections"] = de.get("connections")
        out["mempool_tx"] = de.get("mempool_tx")
        if out.get("circulating_supply") is None and de.get("money_supply") is not None:
            out["circulating_supply"] = de.get("money_supply")
            out["source"]["circulating_supply"] = "rpc"
    except Exception:
        out.setdefault("daemon", {})
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
