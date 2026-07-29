"""Unified customer directory — identity, balances, participation across domains."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_POINTS_DIR = os.path.join(_BASE, "logs", "unified_points")
_IDENT_DIR = os.path.join(_BASE, "logs", "user_identifiers")
_ACTIVE_DEBOUNCE_PATH = os.path.join(_BASE, "logs", "customer_active_emit.json")
_ACTIVE_LOCK = threading.Lock()


def _avatar_url(user_id: str) -> str:
    svg = os.path.join(_BASE, "static", "img", "customers", f"{user_id}.svg")
    if os.path.isfile(svg):
        return f"/static/img/customers/{user_id}.svg"
    return f"/static/img/agents/default.svg"


def _load_identifiers(user_id: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not os.path.isdir(_IDENT_DIR):
        return out
    for name in os.listdir(_IDENT_DIR):
        if not name.endswith(".json"):
            continue
        path = os.path.join(_IDENT_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                row = json.load(f)
            if row.get("user_id") == user_id:
                out[name.replace(".json", "")] = row
        except Exception:
            pass
    return out


def _customer_row(user_id: str, raw: dict) -> Dict[str, Any]:
    systems = raw.get("systems") if isinstance(raw.get("systems"), dict) else {}
    return {
        "user_id": user_id,
        "level": int(raw.get("level") or 1),
        "xp_total": float(raw.get("xp_total") or raw.get("xp") or 0),
        "coins": float(raw.get("coins") or systems.get("coins") or 0),
        "mn2_balance": float(raw.get("mn2_balance") or systems.get("mn2_balance") or 0),
        "last_active": raw.get("updated_at") or raw.get("last_source"),
        "avatar_url": _avatar_url(user_id),
        "identifiers": _load_identifiers(user_id),
    }


def list_customers(
    *,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    if not os.path.isdir(_POINTS_DIR):
        return {"success": True, "customers": [], "total": 0}
    rows: List[Dict[str, Any]] = []
    q = (search or "").strip().lower()
    for name in os.listdir(_POINTS_DIR):
        if not name.endswith(".json"):
            continue
        uid = name[:-5]
        if q and q not in uid.lower():
            continue
        path = os.path.join(_POINTS_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f) or {}
            rows.append(_customer_row(uid, raw))
        except Exception:
            continue
    rows.sort(key=lambda r: str(r.get("last_active") or ""), reverse=True)
    total = len(rows)
    page = rows[offset: offset + limit]
    return {"success": True, "customers": page, "total": total, "limit": limit, "offset": offset}


def get_customer(user_id: str) -> Dict[str, Any]:
    path = os.path.join(_POINTS_DIR, f"{user_id}.json")
    if not os.path.isfile(path):
        return {"success": False, "error": "not_found"}
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f) or {}
    return {"success": True, "customer": _customer_row(user_id, raw)}


def stats() -> Dict[str, Any]:
    """Lightweight aggregate counts — avoids per-customer identifier scans."""
    if not os.path.isdir(_POINTS_DIR):
        return {"success": True, "total": 0, "active_today": 0, "with_mn2": 0}
    now = datetime.now(timezone.utc).date().isoformat()
    total = active_today = with_mn2 = 0
    for name in os.listdir(_POINTS_DIR):
        if not name.endswith(".json"):
            continue
        total += 1
        path = os.path.join(_POINTS_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f) or {}
            systems = raw.get("systems") if isinstance(raw.get("systems"), dict) else {}
            if float(raw.get("mn2_balance") or systems.get("mn2_balance") or 0) > 0:
                with_mn2 += 1
            last_active = str(raw.get("updated_at") or raw.get("last_source") or "")
            if last_active.startswith(now):
                active_today += 1
        except Exception:
            continue
    return {
        "success": True,
        "total": total,
        "active_today": active_today,
        "with_mn2": with_mn2,
    }


def _mask_user_id(user_id: str) -> str:
    uid = (user_id or "").strip()
    if len(uid) <= 4:
        return uid
    return f"{uid[:2]}…{uid[-2:]}"


def emit_customer_new(user_id: str) -> None:
    uid = (user_id or "").strip()
    if not uid:
        return
    try:
        from backend.services.customer_avatar_service import ensure_avatar
        ensure_avatar(uid)
    except Exception:
        pass
    try:
        from backend.services.activity_events_service import emit

        emit(
            "customer_new",
            user_id=uid,
            channel="customers",
            text=f"New customer {_mask_user_id(uid)}",
            payload={"avatar_url": _avatar_url(uid), "user_id": uid},
        )
    except Exception:
        pass


def emit_customer_active(user_id: str, *, source: str = "activity") -> None:
    uid = (user_id or "").strip()
    if not uid:
        return
    today = datetime.now(timezone.utc).date().isoformat()
    with _ACTIVE_LOCK:
        state: Dict[str, str] = {}
        if os.path.isfile(_ACTIVE_DEBOUNCE_PATH):
            try:
                with open(_ACTIVE_DEBOUNCE_PATH, "r", encoding="utf-8") as f:
                    state = json.load(f) or {}
            except Exception:
                state = {}
        if state.get(uid) == today:
            return
        state[uid] = today
        if len(state) > 5000:
            keys = sorted(state.keys(), key=lambda k: state[k])[-2500:]
            state = {k: state[k] for k in keys}
        try:
            os.makedirs(os.path.dirname(_ACTIVE_DEBOUNCE_PATH), exist_ok=True)
            with open(_ACTIVE_DEBOUNCE_PATH, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except Exception:
            return
    try:
        from backend.services.activity_events_service import emit

        emit(
            "customer_active",
            user_id=uid,
            channel="customers",
            text=f"Customer {_mask_user_id(uid)} active",
            payload={"avatar_url": _avatar_url(uid), "user_id": uid, "source": source},
        )
    except Exception:
        pass
