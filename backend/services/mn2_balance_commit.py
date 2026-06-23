"""
Two-phase MN2 balance commits — reserve points before external send, finalize with ledger.

Pending state: data/mn2_pending_commits.json
Recovery: scripts/mn2_recover_pending_commits.py
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PATH = os.path.join(_BASE, "data", "mn2_pending_commits.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load() -> Dict[str, Any]:
    if not os.path.isfile(_PATH):
        return {"commits": {}}
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("commits", {})
            return data
    except Exception:
        pass
    return {"commits": {}}


def _save(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_PATH), exist_ok=True)
    tmp = _PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _PATH)


def pending_amount_for_user(user_id: str) -> float:
    uid = str(user_id or "").strip()
    total = 0.0
    with _LOCK:
        commits = _load().get("commits") or {}
        for c in commits.values():
            if c.get("user_id") == uid and c.get("status") == "reserved":
                total += float(c.get("amount") or 0)
    return round(total, 8)


def begin_withdrawal(user_id: str, amount: float, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Reserve MN2 from balance. Returns commit_id on success."""
    uid = str(user_id or "").strip()
    amt = round(float(amount or 0), 8)
    if not uid or amt <= 0:
        return {"success": False, "error": "invalid user_id or amount"}

    commit_id = "wc_" + uuid.uuid4().hex[:20]
    with _LOCK:
        data = _load()
        commits = data.setdefault("commits", {})
        commits[commit_id] = {
            "commit_id": commit_id,
            "user_id": uid,
            "intent": "withdrawal",
            "amount": amt,
            "status": "reserved",
            "created_at": _iso(),
            "metadata": metadata or {},
        }
        _save(data)

    try:
        from backend.services.unified_points_database import unified_points_db

        r = unified_points_db.add_points(
            uid,
            "mn2_balance",
            -amt,
            source="mn2_withdrawal_reserve",
            metadata={"commit_id": commit_id, **(metadata or {})},
        )
        if not r.get("success"):
            abort(commit_id, reason="reserve_failed")
            return {"success": False, "error": r.get("error", "reserve failed")}
    except Exception as e:
        abort(commit_id, reason=str(e))
        return {"success": False, "error": str(e)}

    return {"success": True, "commit_id": commit_id, "amount": amt}


def finalize_withdrawal(
    commit_id: str,
    *,
    txid: str,
    address: str,
    fee: float,
    amount_sent: float,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Append ledger entry and mark commit finalized."""
    cid = str(commit_id or "").strip()
    with _LOCK:
        data = _load()
        commits = data.get("commits") or {}
        rec = commits.get(cid)
        if not rec or rec.get("status") != "reserved":
            return {"success": False, "error": "commit not found or not reserved", "commit_id": cid}

    uid = rec["user_id"]
    amt = float(rec["amount"])
    try:
        from backend.services.mn2_ledger import append_entry

        append_entry(
            user_id=uid,
            entry_type="withdrawal",
            amount=amt,
            txid=txid,
            address=address,
            metadata={
                "fee": fee,
                "amount_sent": amount_sent,
                "commit_id": cid,
                **(extra_metadata or {}),
            },
        )
    except Exception as e:
        return {"success": False, "error": f"ledger failed: {e}", "commit_id": cid, "critical": True}

    with _LOCK:
        data = _load()
        commits = data.get("commits") or {}
        if cid in commits:
            commits[cid]["status"] = "finalized"
            commits[cid]["finalized_at"] = _iso()
            commits[cid]["txid"] = txid
            _save(data)

    try:
        from backend.services.unified_points_database import unified_points_db

        unified_points_db.add_points(
            uid,
            "mn2_balance",
            0,
            source="mn2_withdrawal_finalized",
            metadata={"commit_id": cid, "txid": txid},
        )
    except Exception:
        pass

    return {"success": True, "commit_id": cid}


def abort(commit_id: str, reason: str = "") -> Dict[str, Any]:
    """Refund reserved amount and mark commit aborted."""
    cid = str(commit_id or "").strip()
    with _LOCK:
        data = _load()
        commits = data.get("commits") or {}
        rec = commits.get(cid)
        if not rec:
            return {"success": False, "error": "commit not found"}
        if rec.get("status") != "reserved":
            return {"success": True, "commit_id": cid, "already": rec.get("status")}

    uid = rec["user_id"]
    amt = float(rec["amount"])
    try:
        from backend.services.unified_points_database import unified_points_db

        unified_points_db.add_points(
            uid,
            "mn2_balance",
            amt,
            source="mn2_withdrawal_abort",
            metadata={"commit_id": cid, "reason": reason},
        )
    except Exception:
        pass

    with _LOCK:
        data = _load()
        commits = data.get("commits") or {}
        if cid in commits:
            commits[cid]["status"] = "aborted"
            commits[cid]["aborted_at"] = _iso()
            commits[cid]["abort_reason"] = reason
            _save(data)

    return {"success": True, "commit_id": cid, "refunded": amt}


def list_pending() -> List[Dict[str, Any]]:
    with _LOCK:
        commits = _load().get("commits") or {}
    return [c for c in commits.values() if c.get("status") == "reserved"]


def recover_stale(max_age_minutes: int = 30) -> Dict[str, Any]:
    """Abort reserved commits older than max_age_minutes (RPC likely failed mid-flight)."""
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max(1, int(max_age_minutes)))
    recovered = []
    for rec in list_pending():
        try:
            created = datetime.fromisoformat(str(rec.get("created_at", "")).replace("Z", "+00:00"))
        except Exception:
            continue
        if created < cutoff:
            abort(rec["commit_id"], reason="stale_recovery")
            recovered.append(rec["commit_id"])
    return {"success": True, "recovered": recovered, "count": len(recovered)}
