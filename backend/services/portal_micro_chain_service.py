"""Portal activity → small on-chain MN2 transactions (activity drip).

Records lightweight events from main site portals (exchange, casino, profile, shop)
and batches them into micro sends when live gates and RPC are available.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_CFG_PATH = os.path.join(ex._DATA_DIR, "portal_micro_chain_config.json")
_QUEUE_PATH = os.path.join(ex._DATA_DIR, "portal_micro_chain_queue.json")
_STATS_PATH = os.path.join(ex._DATA_DIR, "portal_micro_chain_stats.json")

_DEFAULT_CFG = {
    "enabled": True,
    "live": False,
    "mn2_per_tx": 0.001,
    "max_tx_per_day": 48,
    "events_per_tx": 25,
    "min_seconds_between_tx": 300,
    "destination_address": "",
    "portal_sources": ["exchange", "casino", "profile", "shop", "business_control"],
    "note": "Set destination_address + MN2_MICRO_CHAIN_LIVE=1 for real sends. Default is paper/log only.",
}


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_config() -> Dict[str, Any]:
    cfg = dict(_DEFAULT_CFG)
    cfg.update(ex._read_json(_CFG_PATH, {}) or {})
    env_live = os.environ.get("MN2_MICRO_CHAIN_LIVE", "").strip().lower()
    if env_live in ("1", "true", "yes", "on"):
        cfg["live"] = True
    if env_live in ("0", "false", "no", "off"):
        cfg["live"] = False
    addr = (os.environ.get("MN2_MICRO_CHAIN_ADDRESS") or "").strip()
    if addr:
        cfg["destination_address"] = addr
    return cfg


def save_config(patch: Dict[str, Any]) -> Dict[str, Any]:
    cfg = load_config()
    for k in (
        "enabled", "live", "mn2_per_tx", "max_tx_per_day", "events_per_tx",
        "min_seconds_between_tx", "destination_address", "portal_sources",
    ):
        if k in patch:
            cfg[k] = patch[k]
    ex._write_json(_CFG_PATH, cfg)
    return {"success": True, "config": cfg}


def _read_queue() -> Dict[str, Any]:
    data = ex._read_json(_QUEUE_PATH, {"events": []})
    if not isinstance(data.get("events"), list):
        data["events"] = []
    return data


def _write_queue(data: Dict[str, Any]) -> None:
    ex._write_json(_QUEUE_PATH, data)


def _read_stats() -> Dict[str, Any]:
    return ex._read_json(_STATS_PATH, {"day": _today(), "tx_count": 0, "last_tx_at": None})


def _write_stats(st: Dict[str, Any]) -> None:
    ex._write_json(_STATS_PATH, st)


def record_portal_activity(
    portal: str,
    *,
    user_id: str = "",
    action: str = "",
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Queue one portal touch (idempotent best-effort)."""
    cfg = load_config()
    if not cfg.get("enabled"):
        return {"success": True, "queued": False, "reason": "disabled"}
    portal = (portal or "unknown").strip().lower()
    allowed = [str(p).lower() for p in (cfg.get("portal_sources") or [])]
    if allowed and portal not in allowed:
        return {"success": True, "queued": False, "reason": "portal_not_listed"}
    q = _read_queue()
    events = q.get("events") or []
    events.append({
        "ts": _iso(),
        "portal": portal,
        "user_id": (user_id or "")[:64],
        "action": (action or "visit")[:80],
        "meta": meta or {},
    })
    q["events"] = events[-5000:]
    _write_queue(q)
    try:
        from backend.services.activity_events_service import emit
        emit(
            "portal_micro_chain",
            user_id=user_id or None,
            channel=portal,
            text=f"Portal activity · {portal}",
            payload={"action": action, **(meta or {})},
        )
    except Exception:
        pass
    return {"success": True, "queued": True, "queue_size": len(q["events"])}


def ingest_recent_activity_events(*, limit: int = 80) -> int:
    """Pull from logs/activity_events.jsonl into the micro-chain queue (no re-emit)."""
    from backend.services.activity_events_service import recent

    cfg = load_config()
    allowed = {str(p).lower() for p in (cfg.get("portal_sources") or [])}
    q = _read_queue()
    events = q.get("events") or []
    n = 0
    for row in recent(limit=limit):
        ch = str(row.get("channel") or row.get("type") or "").lower()
        if allowed and ch not in allowed and str(row.get("type") or "") not in allowed:
            continue
        events.append({
            "ts": row.get("ts") or _iso(),
            "portal": ch or "activity",
            "user_id": str(row.get("user_id") or "")[:64],
            "action": str(row.get("type") or "event")[:80],
            "meta": {"text": row.get("text"), "from": "activity_log"},
        })
        n += 1
    if n:
        q["events"] = events[-5000:]
        _write_queue(q)
    return n


def process_queue_tick() -> Dict[str, Any]:
    """Batch queued portal events into one micro on-chain tx (paper or live)."""
    cfg = load_config()
    q = _read_queue()
    events: List[Dict[str, Any]] = q.get("events") or []
    if not cfg.get("enabled") or not events:
        return {"success": True, "processed": 0, "reason": "empty_or_disabled"}

    need = int(cfg.get("events_per_tx") or 25)
    if len(events) < need:
        return {"success": True, "processed": 0, "reason": "below_batch", "pending": len(events)}

    st = _read_stats()
    if st.get("day") != _today():
        st = {"day": _today(), "tx_count": 0, "last_tx_at": None}
    if int(st.get("tx_count") or 0) >= int(cfg.get("max_tx_per_day") or 48):
        return {"success": True, "processed": 0, "reason": "daily_cap"}

    batch = events[:need]
    rest = events[need:]
    amount = float(cfg.get("mn2_per_tx") or 0.001)
    addr = (cfg.get("destination_address") or "").strip()
    live = bool(cfg.get("live"))
    portals = sorted({str(e.get("portal") or "") for e in batch if e.get("portal")})

    result: Dict[str, Any] = {
        "success": True,
        "mode": "live" if live else "paper",
        "mn2": amount,
        "address": addr[:16] + "…" if len(addr) > 16 else addr,
        "portals": portals,
        "batch_size": len(batch),
    }

    if not addr:
        result["skipped"] = True
        result["reason"] = "no_destination_address"
    elif not live:
        result["paper"] = True
        result["txid"] = f"paper_{_iso()}"
    else:
        try:
            from backend.services import mn2_rpc_client as rpc
            send = rpc.sendtoaddress(addr, amount)
            result["txid"] = send.get("txid") or send.get("result")
            result["rpc"] = send
        except Exception as exc:
            result["success"] = False
            result["error"] = str(exc)[:200]
            return result

    q["events"] = rest
    _write_queue(q)
    st["tx_count"] = int(st.get("tx_count") or 0) + 1
    st["last_tx_at"] = _iso()
    _write_stats(st)

    try:
        ex._audit(
            "portal_micro_chain_tx",
            amount_usd=0.0,
            mode=result.get("mode"),
            mn2=amount,
            portals=",".join(portals),
            txid=result.get("txid"),
            batch=len(batch),
        )
    except Exception:
        pass

    return result


def status() -> Dict[str, Any]:
    cfg = load_config()
    q = _read_queue()
    st = _read_stats()
    return {
        "success": True,
        "config": {k: cfg.get(k) for k in _DEFAULT_CFG if k != "note"},
        "queue_pending": len(q.get("events") or []),
        "stats": st,
    }
