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
_BLOCK_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def is_masternode_active(status: str) -> bool:
    """MN2 RPC may report ENABLED or ACTIVE for live masternodes."""
    s = str(status or "").strip().upper()
    return s in ("ENABLED", "ACTIVE")


def classify_search(query: str) -> Dict[str, Any]:
    """Classify a hub search term into tx / address / block routes."""
    q = (query or "").strip()
    if not q:
        return {"type": "invalid", "error": "empty query"}
    if is_valid_txid(q):
        return {"type": "tx", "txid": q, "path": f"/explorer/tx/{q}"}
    if is_valid_address(q):
        return {"type": "address", "address": q, "path": f"/explorer/address/{q}"}
    if q.isdigit():
        return {"type": "block", "height": int(q), "path": f"/explorer/block/{q}"}
    if _BLOCK_HASH_RE.match(q):
        return {"type": "block", "hash": q, "path": f"/explorer/block/{q}"}
    return {"type": "invalid", "error": "unrecognized query"}


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
                if is_masternode_active(status):
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


def _normalize_vins(vins: Any) -> List[Dict[str, Any]]:
    """Normalize vin entries from RPC or eiquidus for detail pages."""
    if not isinstance(vins, list):
        return []
    out: List[Dict[str, Any]] = []
    for v in vins[:50]:
        if not isinstance(v, dict):
            continue
        if v.get("coinbase"):
            out.append({
                "n": v.get("n"),
                "coinbase": True,
                "value": None,
                "addresses": [],
                "prev_txid": None,
                "prev_vout": None,
            })
            continue
        addrs: List[str] = []
        val = v.get("value")
        prevout = v.get("prevout") if isinstance(v.get("prevout"), dict) else {}
        if prevout:
            if val is None:
                val = prevout.get("value")
            pspk = prevout.get("scriptPubKey") or {}
            if isinstance(pspk, dict):
                raw_addrs = pspk.get("addresses")
                if isinstance(raw_addrs, list):
                    addrs = [str(a) for a in raw_addrs if a]
                elif pspk.get("address"):
                    addrs = [str(pspk.get("address"))]
        out.append({
            "n": v.get("n"),
            "coinbase": False,
            "value": val,
            "addresses": addrs,
            "prev_txid": v.get("txid"),
            "prev_vout": v.get("vout"),
        })
    return out


def _tx_fee_from_raw(raw: Dict[str, Any]) -> Optional[float]:
    """Extract fee from RPC/eiquidus tx payload when available."""
    fee = raw.get("fee")
    if fee is not None:
        try:
            return abs(float(fee))
        except (TypeError, ValueError):
            pass
    vins = raw.get("vin") if isinstance(raw.get("vin"), list) else []
    vouts = raw.get("vout") if isinstance(raw.get("vout"), list) else []
    if not vins or not vouts:
        return None
    if any(isinstance(v, dict) and v.get("coinbase") for v in vins):
        return None
    vin_sum = 0.0
    vout_sum = 0.0
    has_vin_val = False
    for v in vins:
        if not isinstance(v, dict):
            continue
        val = v.get("value")
        if val is None and isinstance(v.get("prevout"), dict):
            val = v["prevout"].get("value")
        if val is not None:
            try:
                vin_sum += float(val)
                has_vin_val = True
            except (TypeError, ValueError):
                pass
    for v in vouts:
        if isinstance(v, dict) and v.get("value") is not None:
            try:
                vout_sum += float(v["value"])
            except (TypeError, ValueError):
                pass
    if has_vin_val and vout_sum > 0:
        diff = vin_sum - vout_sum
        return round(diff, 8) if diff >= 0 else None
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
        vins = blk.get("vin") if isinstance(blk.get("vin"), list) else []
        return {
            "txid": txid,
            "confirmations": blk.get("confirmations"),
            "time": blk.get("time") or blk.get("blocktime"),
            "blockhash": blk.get("blockhash"),
            "vout_count": len(vouts),
            "vin_count": len(vins),
            "fee": _tx_fee_from_raw(blk),
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
            "vin": _normalize_vins(vins),
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
            vins = raw.get("vin") if isinstance(raw.get("vin"), list) else []
            out = {
                "txid": txid,
                "confirmations": raw.get("confirmations"),
                "time": raw.get("time") or raw.get("blocktime"),
                "blockhash": raw.get("blockhash"),
                "vout_count": len(vouts),
                "vin_count": len(vins),
                "fee": _tx_fee_from_raw(raw),
                "vout": vouts[:50] if vouts else None,
                "vin": _normalize_vins(vins) if vins else None,
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


def block_detail(ref: str) -> Optional[Dict[str, Any]]:
    """Read-only block summary via daemon RPC (height or hash)."""
    ref = (ref or "").strip()
    if not ref:
        return None
    key = "blk_" + ref
    with _LOCK:
        ent = _CACHE.get(key)
        if ent and (time.time() - ent.get("ts", 0)) < _BLOCKS_TTL:
            return ent.get("value")
    out: Optional[Dict[str, Any]] = None
    try:
        from backend.services import mn2_rpc_client as rpc
        block_hash = ref
        if ref.isdigit():
            hh = rpc.getblockhash(int(ref))
            if hh.get("error") or not hh.get("result"):
                return None
            block_hash = str(hh["result"])
        b = _fetch_block(rpc, block_hash)
        if b.get("error") or not isinstance(b.get("result"), dict):
            return None
        blk = b["result"]
        txs = blk.get("tx") if isinstance(blk.get("tx"), list) else []
        txids = [str(t) for t in txs[:50] if t]
        out = {
            "height": blk.get("height"),
            "hash": blk.get("hash") or block_hash,
            "time": blk.get("time"),
            "tx_count": len(txs),
            "txids": txids,
            "size": blk.get("size"),
            "difficulty": blk.get("difficulty"),
            "merkleroot": blk.get("merkleroot"),
            "previousblockhash": blk.get("previousblockhash"),
            "confirmations": blk.get("confirmations"),
            "source": "rpc",
        }
    except Exception:
        return None
    if out is not None:
        with _LOCK:
            _CACHE[key] = {"value": out, "ts": time.time()}
    return out


def mempool_stats() -> Dict[str, Any]:
    """Pending mempool summary from daemon RPC."""
    key = "mempool"
    with _LOCK:
        ent = _CACHE.get(key)
        if ent and (time.time() - ent.get("ts", 0)) < 15:
            return ent.get("value") or {}
    out: Dict[str, Any] = {"size": None, "bytes": None, "usage": None, "source": "rpc"}
    try:
        from backend.services import mn2_rpc_client as rpc
        r = rpc.getmempoolinfo()
        if not r.get("error") and isinstance(r.get("result"), dict):
            res = r["result"]
            out["size"] = res.get("size")
            out["bytes"] = res.get("bytes")
            out["usage"] = res.get("usage")
    except Exception:
        pass
    with _LOCK:
        _CACHE[key] = {"value": out, "ts": time.time()}
    return out


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


def _parse_tx_ids(raw: Any) -> List[str]:
    if not isinstance(raw, list):
        return []
    out: List[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        elif isinstance(item, dict):
            txid = item.get("txid") or item.get("hash")
            if txid:
                out.append(str(txid).strip())
    return out


def address_transactions(address: str, limit: int = 25, offset: int = 0) -> Dict[str, Any]:
    """Paginated address transaction ids from eiquidus ext API."""
    address = (address or "").strip()
    limit = max(1, min(int(limit or 25), 100))
    offset = max(0, int(offset or 0))
    empty = {"address": address, "transactions": [], "count": 0, "limit": limit, "offset": offset, "source": "unavailable"}
    if not is_valid_address(address):
        return empty
    key = f"addr_txs_{address}_{limit}_{offset}"
    with _LOCK:
        ent = _CACHE.get(key)
        if ent and (time.time() - ent.get("ts", 0)) < _DETAIL_TTL:
            return ent.get("value") or empty
    rows: List[Dict[str, Any]] = []
    total = 0
    source = "unavailable"
    for path in (
        f"/getaddresstxs?address={address}&limit={limit}&offset={offset}",
        f"/getaddresstxs?address={address}&limit={limit}&skip={offset}",
        f"/getaddress/{address}?limit={limit}&offset={offset}",
    ):
        raw = _explorer_http_get(path, ttl=_DETAIL_TTL)
        if raw is None:
            continue
        if isinstance(raw, dict):
            txs = raw.get("transactions") or raw.get("txs") or raw.get("txids")
            total = int(raw.get("txcount") or raw.get("tx_count") or raw.get("total") or 0)
            ids = _parse_tx_ids(txs)
            if ids or total:
                source = "iquidus"
                for txid in ids[:limit]:
                    rows.append({"txid": txid})
                break
        elif isinstance(raw, list):
            ids = _parse_tx_ids(raw)
            if ids:
                source = "iquidus"
                total = len(ids)
                for txid in ids[offset:offset + limit]:
                    rows.append({"txid": txid})
                break
    out = {
        "address": address,
        "transactions": rows,
        "count": total or len(rows),
        "limit": limit,
        "offset": offset,
        "source": source,
    }
    with _LOCK:
        _CACHE[key] = {"value": out, "ts": time.time()}
    return out


def explorer_status() -> Dict[str, Any]:
    """Aggregate explorer health: RPC tip, eiquidus supply, rich-list, mempool."""
    from backend.services.mn2_explorer_urls import (
        explorer_base_url,
        explorer_kind,
        explorer_local_api_url,
        load_explorer_config,
    )
    cfg = load_explorer_config()
    kind = explorer_kind(cfg)
    checks: Dict[str, Any] = {}
    overall = "healthy"

    try:
        from backend.services import mn2_rpc_client as rpc
        r = rpc.getblockcount(timeout_sec=4)
        if r.get("error") or r.get("result") is None:
            checks["rpc"] = {"ok": False, "error": str(r.get("error") or "unreachable")}
            overall = "degraded"
        else:
            checks["rpc"] = {"ok": True, "block_height": int(r["result"])}
    except Exception as exc:
        checks["rpc"] = {"ok": False, "error": str(exc)}
        overall = "degraded"

    iquidus: Dict[str, Any] = {
        "kind": kind,
        "base_url": explorer_base_url(cfg),
        "local_api_url": explorer_local_api_url(cfg) or None,
    }
    if kind == "iquidus":
        sup = _explorer_http_get("/getmoneysupply", ttl=60)
        iquidus["supply_ok"] = sup is not None
        if sup is None:
            overall = "degraded"

    rich = rich_list(limit=1)
    rich_ok = bool(rich)
    checks["rich_list"] = {
        "ok": rich_ok,
        "sample_count": len(rich),
        "index_synced": rich_ok,
        "note": None if rich_ok else "Rich list empty — eiquidus index may still be syncing",
    }
    if not rich_ok and kind == "iquidus":
        overall = "degraded"
    checks["mempool"] = mempool_stats()

    return {
        "status": overall,
        "explorer_kind": kind,
        "explorer_base_url": explorer_base_url(cfg),
        "checks": checks,
        "iquidus": iquidus,
    }


EXPLORER_OPENAPI: Dict[str, Any] = {
    "openapi": "3.0.3",
    "info": {"title": "MN2 Explorer API", "version": "1.0.0"},
    "paths": {
        "/api/mn2/network-overview": {"get": {"summary": "Live network tiles"}},
        "/api/mn2/network-history": {"get": {"summary": "Historical snapshots", "parameters": [
            {"name": "hours", "in": "query", "schema": {"type": "number"}},
            {"name": "limit", "in": "query", "schema": {"type": "integer"}},
        ]}},
        "/api/mn2/recent-blocks": {"get": {"summary": "Latest blocks via RPC"}},
        "/api/mn2/masternodes": {"get": {"summary": "Masternode list"}},
        "/api/mn2/rich-list": {"get": {"summary": "Top addresses by balance"}},
        "/api/mn2/supply-stats": {"get": {"summary": "Circulating supply"}},
        "/api/mn2/mempool": {"get": {"summary": "Mempool summary"}},
        "/api/mn2/explorer/search": {"get": {"summary": "Classify search query", "parameters": [
            {"name": "q", "in": "query", "required": True, "schema": {"type": "string"}},
        ]}},
        "/api/mn2/explorer/status": {"get": {"summary": "Explorer health aggregate"}},
        "/api/mn2/explorer/openapi.json": {"get": {"summary": "This OpenAPI document"}},
        "/api/mn2/explorer/tx/{txid}": {"get": {"summary": "Transaction detail"}},
        "/api/mn2/explorer/address/{address}": {"get": {"summary": "Address detail"}},
        "/api/mn2/explorer/address/{address}/txs": {"get": {"summary": "Paginated address txs"}},
        "/api/mn2/explorer/block/{ref}": {"get": {"summary": "Block detail"}},
        "/api/mn2/explorer/stream": {"get": {"summary": "SSE network overview"}},
    },
}
