"""Aggregator catalog v2 — 75 AI/agent aggregators, top-25, progress, control."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CATALOG_FILE = os.path.join(_BASE, "data", "aggregators_catalog.json")
_CONTROL_FILE = os.path.join(_BASE, "data", "aggregator_control.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if data is not None else default
    except Exception:
        return default


def _write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _load_catalog_raw() -> Dict[str, Any]:
    data = _read_json(_CATALOG_FILE, {"aggregators": [], "categories": []})
    if not data.get("aggregators"):
        try:
            from scripts.generate_aggregators_catalog import main as gen  # type: ignore
            gen()
            data = _read_json(_CATALOG_FILE, {"aggregators": []})
        except Exception:
            pass
    return data


def list_catalog(
    *,
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    data = _load_catalog_raw()
    rows: List[Dict[str, Any]] = list(data.get("aggregators") or [])
    cat = (category or "").strip().lower()
    if cat and cat != "all":
        rows = [r for r in rows if (r.get("category") or "").lower() == cat]
    q = (search or "").strip().lower()
    if q:
        rows = [
            r for r in rows
            if q in (r.get("name") or "").lower()
            or q in (r.get("use") or "").lower()
            or q in (r.get("tech") or "").lower()
            or q in (r.get("agent_id") or "").lower()
        ]
    total = len(rows)
    limit = max(1, min(int(limit or 100), 200))
    offset = max(0, int(offset or 0))
    page = rows[offset : offset + limit]
    return {
        "success": True,
        "count": total,
        "offset": offset,
        "limit": limit,
        "categories": data.get("categories") or [],
        "aggregators": page,
    }


def top25_list() -> Dict[str, Any]:
    data = _load_catalog_raw()
    rows = list(data.get("aggregators") or [])
    top_ids = data.get("top25_ids") or []
    if top_ids:
        by_id = {r.get("id"): r for r in rows}
        ordered = [by_id[i] for i in top_ids if i in by_id]
        if len(ordered) >= 10:
            rows = ordered
    ranked = sorted(rows, key=lambda r: -(int(r.get("score") or 0)))
    top = ranked[:25]
    return {
        "success": True,
        "count": len(top),
        "aggregators": [
            {
                **r,
                "rank": i + 1,
                "use_label": r.get("use") or r.get("function") or "",
            }
            for i, r in enumerate(top)
        ],
    }


def fulfillment_section() -> Dict[str, Any]:
    data = _load_catalog_raw()
    rows = [r for r in (data.get("aggregators") or []) if r.get("category") == "customer_fulfillment"]
    if len(rows) < 5:
        rows = [r for r in (data.get("aggregators") or []) if "customer" in (r.get("category") or "")][:12]
    return {
        "success": True,
        "title": "Customer fulfillment aggregators",
        "description": "Attract and convert customers — route leads to shop, profile, and MN2 checkout.",
        "aggregators": rows,
        "playbook": [
            {"step": 1, "action": "Capture lead", "aggregator": "Lead Capture", "reward": "activity_points"},
            {"step": 2, "action": "Onboard user", "aggregator": "Onboarding", "reward": "game_points"},
            {"step": 3, "action": "Shop checkout MN2", "aggregator": "Shop Fulfillment", "reward": "mn2_balance"},
            {"step": 4, "action": "Social proof tip", "aggregator": "Social Tips", "reward": "social_points"},
        ],
    }


def get_control_state(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip() or "default_user"
    with _LOCK:
        store = _read_json(_CONTROL_FILE, {})
        user_block = store.get(uid) if isinstance(store, dict) else {}
        if not isinstance(user_block, dict):
            user_block = {}
    catalog = _load_catalog_raw()
    agents = {}
    for row in catalog.get("aggregators") or []:
        aid = (row.get("agent_id") or "").strip()
        if aid:
            agents.setdefault(aid, {"agent_id": aid, "aggregators": []})
            agents[aid]["aggregators"].append(row.get("id"))
    assignments = user_block.get("assignments") or {}
    return {
        "success": True,
        "user_id": uid,
        "agents_available": list(agents.values()),
        "assignments": assignments,
        "auto_run": bool(user_block.get("auto_run")),
        "updated_at": user_block.get("updated_at"),
    }


def assign_agent(user_id: str, aggregator_id: str, agent_id: str, *, auto_run: Optional[bool] = None) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    agg = (aggregator_id or "").strip()
    agent = (agent_id or "").strip()
    with _LOCK:
        store = _read_json(_CONTROL_FILE, {})
        if not isinstance(store, dict):
            store = {}
        block = store.setdefault(uid, {"assignments": {}, "auto_run": False})
        if agg == "_global" and auto_run is not None:
            block["auto_run"] = bool(auto_run)
            block["updated_at"] = _iso()
            store[uid] = block
            _write_json(_CONTROL_FILE, store)
            return {"success": True, "user_id": uid, "auto_run": block["auto_run"]}
    if not agg or not agent:
        return {"success": False, "error": "aggregator_id and agent_id required"}
    with _LOCK:
        store = _read_json(_CONTROL_FILE, {})
        if not isinstance(store, dict):
            store = {}
        block = store.setdefault(uid, {"assignments": {}, "auto_run": False})
        block.setdefault("assignments", {})[agg] = {
            "agent_id": agent,
            "assigned_at": _iso(),
        }
        if auto_run is not None:
            block["auto_run"] = bool(auto_run)
        block["updated_at"] = _iso()
        store[uid] = block
        _write_json(_CONTROL_FILE, store)
    return {"success": True, "user_id": uid, "aggregator_id": agg, "agent_id": agent, "assignments": block["assignments"]}


def progress_snapshot(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip() or "default_user"
    data = _load_catalog_raw()
    total = len(data.get("aggregators") or [])
    ctrl = get_control_state(uid)
    assigned = len(ctrl.get("assignments") or {})
    pct = round((assigned / total) * 100) if total else 0
    active = sum(1 for r in (data.get("aggregators") or []) if r.get("status") == "active")
    return {
        "success": True,
        "user_id": uid,
        "catalog_total": total,
        "active_aggregators": active,
        "assigned_count": assigned,
        "assignment_pct": pct,
        "auto_run": ctrl.get("auto_run"),
        "milestones": [
            {"label": "Catalog loaded", "pct": 100 if total else 0, "done": total > 0},
            {"label": "Agents assigned", "pct": pct, "done": assigned >= 5},
            {"label": "Fulfillment wired", "pct": min(100, assigned * 4), "done": assigned >= 3},
            {"label": "Top-25 engaged", "pct": min(100, assigned * 3), "done": assigned >= 8},
        ],
        "updated_at": _iso(),
    }
