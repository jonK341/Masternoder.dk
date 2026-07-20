"""
MN2 explorer data via daemon RPC (explorer Phase E5): latest blocks (#7) and
masternode list (#10). Self-hosted-explorer-independent — uses RPC methods the
MasterNoder2 daemon supports (getblockhash/getblock, listmasternodes).

Also proxies read-only tx/address/rich-list data from the local or public
eiquidus API when configured (display-only; never used for crediting).

All functions are best-effort, cached to bound RPC load, and never raise.
"""
import re
import time
import threading
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore

_LOCK = threading.Lock()
_CACHE: Dict[str, Dict[str, Any]] = {}
_BLOCKS_TTL = 30
_MN_TTL = 60
_DETAIL_TTL = 45
_RICH_TTL = 90

_TXID_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_ADDRESS_RE = re.compile(r"^[13mnMNJ][a-km-zA-HJ-NP-Z1-9]{25,62}$")


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


def masternodes(limit: int = 50, *, fresh: bool = False) -> Dict[str, Any]:
    """Masternode summary + list via listmasternodes. Cached ~60s.
    Returns {total, enabled, list:[{rank, addr, status, lastpaid, activetime, version}]}."""
    limit = max(1, min(int(limit or 50), 500))
    key = "mn_%d" % limit
    with _LOCK:
        if not fresh:
            cached = _cached(key, _MN_TTL)
            if cached is not None:
                return cached
        result: Dict[str, Any] = {"total": 0, "enabled": 0, "list": []}
        try:
            from backend.services import mn2_rpc_client as rpc
            r = rpc.listmasternodes(timeout_sec=12)
            rows = r.get("result")
            if r.get("error"):
                result["rpc_error"] = str(r.get("error"))
                if fresh:
                    _CACHE.pop(key, None)
                return result
            if not isinstance(rows, list):
                result["rpc_error"] = "listmasternodes returned non-list"
                if fresh:
                    _CACHE.pop(key, None)
                return result
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
                    "txhash": mn.get("txhash") or mn.get("proTxHash"),
                })
            parsed.sort(key=lambda m: (m.get("rank") is None, m.get("rank") or 0))
            result = {"total": len(parsed), "enabled": enabled, "list": parsed[:limit]}
        except Exception:
            return _store(key, result)
        return _store(key, result)


def is_valid_txid(txid: str) -> bool:
    return bool((txid or "").strip() and _TXID_RE.match(txid.strip()))


def is_valid_address(address: str) -> bool:
    return bool((address or "").strip() and _ADDRESS_RE.match(address.strip()))


def _explorer_api_bases() -> List[str]:
    """Local eiquidus API first, then public explorer /ext base."""
    bases: List[str] = []
    try:
        from backend.services.mn2_explorer_urls import (
            explorer_base_url,
            explorer_kind,
            explorer_local_api_url,
            load_explorer_config,
        )
        cfg = load_explorer_config()
        if explorer_kind(cfg) == "iquidus":
            local = (explorer_local_api_url(cfg) or "").rstrip("/")
            if local:
                bases.append(local)
            public = (explorer_base_url(cfg) or "").rstrip("/")
            if public and public not in bases:
                bases.append(public + "/ext" if not public.endswith("/ext") else public)
    except Exception:
        pass
    return bases


def _explorer_http_get(path: str, *, ttl: int = _DETAIL_TTL) -> Optional[Any]:
    """GET on configured eiquidus API bases. Cached; never raises."""
    if not requests or not path:
        return None
    if not path.startswith("/"):
        path = "/" + path
    key = "http_" + path
    with _LOCK:
        ent = _CACHE.get(key)
        if ent and (time.time() - ent.get("ts", 0)) < ttl:
            return ent.get("value")
    for base in _explorer_api_bases():
        url = base.rstrip("/") + path
        try:
            r = requests.get(url, timeout=5)
            if r.status_code != 200:
                continue
            text = (r.text or "").strip()
            if text.startswith("<"):
                continue
            value: Any = text
            if text.startswith("{") or text.startswith("["):
                try:
                    value = r.json()
                except Exception:
                    value = text
            elif text.replace(".", "", 1).isdigit() or (
                text.startswith("-") and text[1:].replace(".", "", 1).isdigit()
            ):
                try:
                    value = float(text) if "." in text else int(text)
                except ValueError:
                    value = text
            with _LOCK:
                _CACHE[key] = {"value": value, "ts": time.time()}
            return value
        except Exception:
            continue
    return None


def _rpc_tx_detail(txid: str) -> Optional[Dict[str, Any]]:
    try:
        from backend.services import mn2_rpc_client as rpc
        r = rpc.gettransaction(txid)
        if r.get("error") or not isinstance(r.get("result"), dict):
            raw = rpc._call("getrawtransaction", [txid, True])
            if raw.get("error") or not isinstance(raw.get("result"), dict):
                return None
            blk = raw["result"]
        else:
            blk = r["result"]
        vouts = blk.get("vout") if isinstance(blk.get("vout"), list) else []
        return {
            "txid": txid,
            "confirmations": blk.get("confirmations"),
            "time": blk.get("time") or blk.get("blocktime"),
            "blockhash": blk.get("blockhash"),
            "vout_count": len(vouts),
            "vout": [
                {
                    "n": v.get("n"),
                    "value": v.get("value"),
                    "addresses": (
                        (v.get("scriptPubKey") or {}).get("addresses")
                        or ([(v.get("scriptPubKey") or {}).get("address")] if (v.get("scriptPubKey") or {}).get("address") else [])
                    ),
                }
                for v in vouts[:50]
                if isinstance(v, dict)
            ],
            "source": "rpc",
        }
    except Exception:
        return None


def tx_detail(txid: str) -> Optional[Dict[str, Any]]:
    """Read-only tx summary from eiquidus ext API with RPC fallback."""
    txid = (txid or "").strip()
    if not is_valid_txid(txid):
        return None
    key = "tx_" + txid
    with _LOCK:
        ent = _CACHE.get(key)
        if ent and (time.time() - ent.get("ts", 0)) < _DETAIL_TTL:
            return ent.get("value")
    out: Optional[Dict[str, Any]] = None
    for path in (f"/gettransaction?txid={txid}", f"/getrawtransaction?txid={txid}"):
        raw = _explorer_http_get(path, ttl=_DETAIL_TTL)
        if isinstance(raw, dict):
            vouts = raw.get("vout") if isinstance(raw.get("vout"), list) else []
            out = {
                "txid": txid,
                "confirmations": raw.get("confirmations"),
                "time": raw.get("time") or raw.get("blocktime"),
                "blockhash": raw.get("blockhash"),
                "vout_count": len(vouts),
                "vout": vouts[:50] if vouts else None,
                "source": "iquidus",
            }
            break
    if out is None:
        out = _rpc_tx_detail(txid)
    if out is not None:
        with _LOCK:
            _CACHE[key] = {"value": out, "ts": time.time()}
    return out


def address_detail(address: str) -> Optional[Dict[str, Any]]:
    """Read-only address summary from eiquidus ext API."""
    address = (address or "").strip()
    if not is_valid_address(address):
        return None
    key = "addr_" + address
    with _LOCK:
        ent = _CACHE.get(key)
        if ent and (time.time() - ent.get("ts", 0)) < _DETAIL_TTL:
            return ent.get("value")
    out: Optional[Dict[str, Any]] = None
    for path in (
        f"/getaddressbalance?address={address}",
        f"/getaddress/{address}",
        f"/getaddresstxs?address={address}&limit=10",
    ):
        raw = _explorer_http_get(path, ttl=_DETAIL_TTL)
        if raw is None:
            continue
        if isinstance(raw, (int, float)):
            out = {"address": address, "balance": float(raw), "source": "iquidus"}
            break
        if isinstance(raw, dict):
            bal = raw.get("balance") if raw.get("balance") is not None else raw.get("final_balance")
            if bal is not None or raw.get("address"):
                out = {
                    "address": address,
                    "balance": bal,
                    "received": raw.get("received"),
                    "sent": raw.get("sent"),
                    "tx_count": raw.get("txcount") or raw.get("tx_count"),
                    "transactions": raw.get("transactions") or raw.get("txs"),
                    "source": "iquidus",
                }
                break
    if out is not None:
        with _LOCK:
            _CACHE[key] = {"value": out, "ts": time.time()}
        return out
    return {"address": address, "balance": None, "source": "unavailable"}


def rich_list(limit: int = 100) -> List[Dict[str, Any]]:
    """Top addresses by balance from eiquidus rich list (cached)."""
    limit = max(1, min(int(limit or 100), 500))
    key = "rich_%d" % limit
    with _LOCK:
        ent = _CACHE.get(key)
        if ent and (time.time() - ent.get("ts", 0)) < _RICH_TTL:
            return ent.get("value") or []
    rows: List[Dict[str, Any]] = []
    raw = _explorer_http_get(f"/getrichlist?limit={limit}", ttl=_RICH_TTL)
    if isinstance(raw, list):
        for i, item in enumerate(raw[:limit], start=1):
            if isinstance(item, dict):
                rows.append({
                    "rank": item.get("rank", i),
                    "address": item.get("address") or item.get("addr"),
                    "balance": item.get("balance") or item.get("amount"),
                })
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                rows.append({"rank": i, "address": item[0], "balance": item[1]})
    with _LOCK:
        _CACHE[key] = {"value": rows, "ts": time.time()}
    return rows


def supply_stats() -> Dict[str, Any]:
    """Circulating/max supply from eiquidus with RPC fallback."""
    out: Dict[str, Any] = {"source": {}}
    sup = _explorer_http_get("/getmoneysupply", ttl=_RICH_TTL)
    if isinstance(sup, dict):
        sup = sup.get("result") or sup.get("supply") or sup.get("moneysupply")
    if sup is not None:
        try:
            out["circulating_supply"] = round(float(sup), 8)
            out["source"]["circulating_supply"] = "iquidus"
        except (TypeError, ValueError):
            pass
    try:
        from backend.services import mn2_chainz
        circ = mn2_chainz._cached_circulating_supply()
        if circ is not None and out.get("circulating_supply") is None:
            out["circulating_supply"] = circ
            out["source"]["circulating_supply"] = "rpc"
    except Exception:
        pass
    return out
