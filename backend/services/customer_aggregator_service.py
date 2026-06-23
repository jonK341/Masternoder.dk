"""Unified customer directory — identity, balances, participation across domains."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_POINTS_DIR = os.path.join(_BASE, "logs", "unified_points")
_IDENT_DIR = os.path.join(_BASE, "logs", "user_identifiers")


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
    listing = list_customers(limit=10000, offset=0)
    customers = listing.get("customers") or []
    now = datetime.now(timezone.utc).date().isoformat()
    active_today = sum(
        1 for c in customers
        if str(c.get("last_active") or "").startswith(now)
    )
    return {
        "success": True,
        "total": listing.get("total", 0),
        "active_today": active_today,
        "with_mn2": sum(1 for c in customers if float(c.get("mn2_balance") or 0) > 0),
    }
