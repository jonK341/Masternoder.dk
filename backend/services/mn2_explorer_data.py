"""
MN2 explorer data via daemon RPC (explorer Phase E5): latest blocks (#7) and
masternode list (#10). Self-hosted-explorer-independent — uses RPC methods the
MasterNoder2 daemon supports (getblockhash/getblock, listmasternodes).

All functions are best-effort, cached to bound RPC load, and never raise.
"""
import time
import threading
from typing import Any, Dict, List

_LOCK = threading.Lock()
_CACHE: Dict[str, Dict[str, Any]] = {}
_BLOCKS_TTL = 30
_MN_TTL = 60


def _cached(key: str, ttl: int):
    ent = _CACHE.get(key)
    if ent and (time.time() - ent.get("ts", 0)) < ttl:
        return ent.get("value")
    return None


def _store(key: str, value: Any) -> Any:
    _CACHE[key] = {"value": value, "ts": time.time()}
    return value


def _fetch_block(rpc, block_hash: str) -> Dict[str, Any]:
    """getblock with cross-daemon arg handling: PIVX-style wants a boolean `verbose`,
    Bitcoin-style wants an int `verbosity`. Try the common forms until one works."""
    for params in ([block_hash, True], [block_hash, 1], [block_hash]):
        r = rpc._call("getblock", params)
        if not r.get("error") and isinstance(r.get("result"), dict):
            return r
    return {"error": "getblock unsupported", "result": None}


def recent_blocks(limit: int = 10) -> List[Dict[str, Any]]:
    """Latest N blocks (height, time, tx count, size, hash) walked back from the tip via RPC.
    Cached ~30s. Returns [] if the daemon is unreachable."""
    limit = max(1, min(int(limit or 10), 25))
    key = "blocks_%d" % limit
    with _LOCK:
        cached = _cached(key, _BLOCKS_TTL)
        if cached is not None:
            return cached
        out: List[Dict[str, Any]] = []
        try:
            from backend.services import mn2_rpc_client as rpc
            tip = rpc.getblockcount(timeout_sec=5)
            if tip.get("error") or tip.get("result") is None:
                return _store(key, [])
            height = int(tip["result"])
            for h in range(height, max(-1, height - limit), -1):
                hh = rpc.getblockhash(h)
                if hh.get("error") or not hh.get("result"):
                    continue
                b = _fetch_block(rpc, str(hh["result"]))
                if b.get("error") or not isinstance(b.get("result"), dict):
                    continue
                blk = b["result"]
                txs = blk.get("tx")
                out.append({
                    "height": blk.get("height", h),
                    "hash": blk.get("hash"),
                    "time": blk.get("time"),
                    "tx_count": len(txs) if isinstance(txs, list) else None,
                    "size": blk.get("size"),
                })
        except Exception:
            return _store(key, out)
        return _store(key, out)


def masternodes(limit: int = 50) -> Dict[str, Any]:
    """Masternode summary + list via listmasternodes. Cached ~60s.
    Returns {total, enabled, list:[{rank, addr, status, lastpaid, activetime, version}]}."""
    limit = max(1, min(int(limit or 50), 500))
    key = "mn_%d" % limit
    with _LOCK:
        cached = _cached(key, _MN_TTL)
        if cached is not None:
            return cached
        result: Dict[str, Any] = {"total": 0, "enabled": 0, "list": []}
        try:
            from backend.services import mn2_rpc_client as rpc
            r = rpc.listmasternodes()
            rows = r.get("result")
            if r.get("error") or not isinstance(rows, list):
                return _store(key, result)
            enabled = 0
            parsed: List[Dict[str, Any]] = []
            for mn in rows:
                if not isinstance(mn, dict):
                    continue
                status = str(mn.get("status") or "")
                if status.upper() == "ENABLED":
                    enabled += 1
                parsed.append({
                    "rank": mn.get("rank"),
                    "addr": mn.get("addr"),
                    "status": status,
                    "lastpaid": mn.get("lastpaid"),
                    "activetime": mn.get("activetime"),
                    "version": mn.get("version"),
                })
            parsed.sort(key=lambda m: (m.get("rank") is None, m.get("rank") or 0))
            result = {"total": len(parsed), "enabled": enabled, "list": parsed[:limit]}
        except Exception:
            return _store(key, result)
        return _store(key, result)
