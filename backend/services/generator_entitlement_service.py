"""
Pre-flight generation entitlement — reserve credits before job start.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_RESERVATIONS = os.path.join(_BASE, "logs", "generator_reservations.jsonl")


def _estimate_credits(duration_sec: int, short_clip: bool) -> float:
    base = 1.0 if short_clip else 3.0
    return round(base + max(0, int(duration_sec) - 60) / 60.0, 2)


def _user_generation_credits(user_id: str) -> float:
    try:
        from backend.services.unified_points_database import unified_points_db
        pts = unified_points_db.get_all_points(str(user_id))
        p = pts.get("points") if isinstance(pts.get("points"), dict) else {}
        systems = pts.get("systems") if isinstance(pts.get("systems"), dict) else {}
        for key in ("generation_credits", "video_credits", "coins"):
            v = p.get(key)
            if v is None:
                v = systems.get(key)
            if v is not None and float(v) > 0:
                return float(v)
    except Exception:
        pass
    return 999999.0  # fail-open for guests / unset quotas


def _credit_point_type(user_id: str) -> str:
    try:
        from backend.services.unified_points_database import unified_points_db
        pts = unified_points_db.get_all_points(str(user_id))
        p = pts.get("points") if isinstance(pts.get("points"), dict) else {}
        systems = pts.get("systems") if isinstance(pts.get("systems"), dict) else {}
        for key in ("generation_credits", "video_credits", "coins"):
            v = p.get(key)
            if v is None:
                v = systems.get(key)
            if v is not None and float(v) > 0:
                return key
    except Exception:
        pass
    return "generation_credits"


def check_and_reserve(user_id: str, duration_sec: int, short_clip: bool = False) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    if not uid or uid == "default_user":
        return {"success": True, "skipped": True, "reason": "guest"}
    required = _estimate_credits(duration_sec, short_clip)
    available = _user_generation_credits(uid)
    if available < required:
        return {
            "success": False,
            "code": "insufficient_generation_credits",
            "required_credits": required,
            "available_credits": round(available, 2),
        }
    rid = "gr_" + uuid.uuid4().hex[:16]
    row = {
        "id": rid,
        "user_id": uid,
        "required": required,
        "point_type": _credit_point_type(uid),
        "status": "reserved",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    try:
        os.makedirs(os.path.dirname(_RESERVATIONS), exist_ok=True)
        with open(_RESERVATIONS, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass
    return {"success": True, "reservation_id": rid, "required_credits": required}


def _find_reservation(reservation_id: str) -> Optional[Dict[str, Any]]:
    if not reservation_id or not os.path.isfile(_RESERVATIONS):
        return None
    found = None
    try:
        with open(_RESERVATIONS, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if row.get("id") == reservation_id:
                    found = row
    except Exception:
        return None
    return found


def settle(reservation_id: Optional[str], actual_credits: Optional[float] = None, *, abort: bool = False) -> Dict[str, Any]:
    if not reservation_id:
        return {"success": True, "skipped": True}
    row = _find_reservation(reservation_id)
    if not row or row.get("status") != "reserved":
        return {"success": True, "skipped": True, "reason": "not_found_or_settled"}

    if abort:
        _append_status(reservation_id, "aborted")
        return {"success": True, "aborted": True}

    debit = float(actual_credits if actual_credits is not None else row.get("required") or 0)
    uid = str(row.get("user_id") or "")
    pt = str(row.get("point_type") or "generation_credits")
    try:
        from backend.services.unified_points_database import unified_points_db
        res = unified_points_db.add_points(
            uid,
            pt,
            -debit,
            source="generator_entitlement",
            metadata={"reservation_id": reservation_id, "phase": "settle"},
        )
        if not res.get("success"):
            return {"success": False, "error": res.get("error") or "debit_failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    _append_status(reservation_id, "settled", debit=debit)
    return {"success": True, "debited": debit, "user_id": uid, "point_type": pt}


def _append_status(reservation_id: str, status: str, debit: float = 0) -> None:
    row = {
        "id": reservation_id,
        "status": status,
        "debited": debit,
        "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    try:
        os.makedirs(os.path.dirname(_RESERVATIONS), exist_ok=True)
        with open(_RESERVATIONS, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass
