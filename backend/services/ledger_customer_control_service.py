"""Ledger customer control — unified view and agent/camgirl/AI control plane."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONTROLS_FILE = os.path.join(_BASE, "data", "ledger_customer_controls.json")
_LOCK = threading.RLock()

_VALID_CONTROLLERS = frozenset({"agent", "camgirl", "ai"})


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _config() -> Dict[str, Any]:
    try:
        with open(os.path.join(_BASE, "data", "mn2_config.json"), "r", encoding="utf-8") as f:
            root = json.load(f)
        block = root.get("ledger_customer_control") if isinstance(root, dict) else {}
        return block if isinstance(block, dict) else {}
    except Exception:
        return {}


def control_enabled() -> bool:
    return bool(_config().get("enabled", True))


def _load_store() -> Dict[str, Any]:
    if not os.path.isfile(_CONTROLS_FILE):
        return {"version": 1, "assignments": {}}
    try:
        with open(_CONTROLS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("assignments", {})
            return data
    except Exception:
        pass
    return {"version": 1, "assignments": {}}


def _save_store(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_CONTROLS_FILE), exist_ok=True)
    tmp = _CONTROLS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _CONTROLS_FILE)


def get_assignment(user_id: str) -> Optional[Dict[str, Any]]:
    uid = str(user_id or "").strip()
    return (_load_store().get("assignments") or {}).get(uid)


def assign_controller(
    user_id: str,
    controller_type: str,
    *,
    controller_id: str = "",
    performer_id: str = "",
    agent_id: str = "",
    notes: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assign agent, camgirl, or AI control to a ledger customer."""
    if not control_enabled():
        return {"success": False, "error": "control_disabled"}

    uid = str(user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id_required"}

    ctype = str(controller_type or "").strip().lower()
    if ctype not in _VALID_CONTROLLERS:
        return {"success": False, "error": "invalid_controller_type", "valid": sorted(_VALID_CONTROLLERS)}

    cid = str(controller_id or agent_id or performer_id or "").strip()
    if ctype == "camgirl" and not cid:
        cid = str(performer_id or "").strip()
    if ctype == "agent" and not cid:
        cid = str(agent_id or "master_fix").strip()

    row = {
        "user_id": uid,
        "controller_type": ctype,
        "controller_id": cid,
        "notes": str(notes or "")[:500],
        "metadata": dict(metadata or {}),
        "assigned_at": _iso(),
        "updated_at": _iso(),
    }

    with _LOCK:
        store = _load_store()
        prev = (store.get("assignments") or {}).get(uid) or {}
        if prev.get("assigned_at"):
            row["assigned_at"] = prev["assigned_at"]
        store.setdefault("assignments", {})[uid] = row
        _save_store(store)

    return {"success": True, "assignment": row}


def clear_controller(user_id: str) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    with _LOCK:
        store = _load_store()
        assignments = store.get("assignments") or {}
        if uid not in assignments:
            return {"success": False, "error": "not_assigned"}
        removed = assignments.pop(uid)
        store["assignments"] = assignments
        _save_store(store)
    return {"success": True, "removed": removed}


def _customer_base(user_id: str) -> Dict[str, Any]:
    from backend.services.customer_aggregator_service import get_customer, _POINTS_DIR
    import os

    result = get_customer(user_id)
    if result.get("success"):
        return result.get("customer") or {}

    # Discord-only prospect without points file yet
    try:
        from backend.services.discord_customer_ingest_service import list_discord_customers

        for row in (list_discord_customers(limit=5000).get("customers") or []):
            if row.get("user_id") == user_id:
                from backend.services.customer_aggregator_service import _avatar_url, _load_identifiers

                return {
                    "user_id": user_id,
                    "level": 1,
                    "xp_total": 0,
                    "coins": 0,
                    "mn2_balance": 0,
                    "last_active": row.get("last_seen_at"),
                    "avatar_url": _avatar_url(user_id),
                    "identifiers": _load_identifiers(user_id),
                    "source": "discord_channel",
                    "discord": row,
                }
    except Exception:
        pass

    path = os.path.join(_POINTS_DIR, f"{user_id}.json")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f) or {}
        from backend.services.customer_aggregator_service import _customer_row

        return _customer_row(user_id, raw)

    return {}


def get_ledger_customer(user_id: str) -> Dict[str, Any]:
    """360° ledger customer view — aggregator, ledger, encoder, control assignment."""
    uid = str(user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id_required"}

    customer = _customer_base(uid)
    if not customer:
        return {"success": False, "error": "not_found", "user_id": uid}

    ledger_entries: List[Dict[str, Any]] = []
    try:
        from backend.services.mn2_ledger import get_entries_by_user

        ledger_entries = get_entries_by_user(uid, limit=25)
    except Exception:
        pass

    encoder_orders: List[Dict[str, Any]] = []
    try:
        from backend.services.encoder_order_service import list_orders

        encoder_orders = (list_orders(uid, limit=10).get("orders") or [])
    except Exception:
        pass

    fulfillment = None
    try:
        from backend.services.encoder_customer_fulfillment_service import fulfillment_record

        fulfillment = fulfillment_record(uid)
    except Exception:
        pass

    assignment = get_assignment(uid)
    control_panel: Dict[str, Any] = {}
    try:
        from backend.services.ai_user_controller import ai_control_panel

        control_panel = ai_control_panel(uid)
    except Exception:
        control_panel = {"success": False}

    aggregator_stats: Dict[str, Any] = {}
    try:
        from backend.services.aggregator_mn2_service import get_user_stats

        aggregator_stats = get_user_stats(uid)
    except Exception:
        pass

    return {
        "success": True,
        "user_id": uid,
        "customer": customer,
        "ledger": {
            "entries": ledger_entries,
            "entry_count": len(ledger_entries),
        },
        "encoder_orders": encoder_orders,
        "fulfillment": fulfillment,
        "control": {
            "assignment": assignment,
            "available_controllers": sorted(_VALID_CONTROLLERS),
            "ai_panel": control_panel if control_panel.get("success") else None,
        },
        "aggregator": aggregator_stats,
    }


def list_control_assignments(*, limit: int = 100) -> Dict[str, Any]:
    store = _load_store()
    rows = list((store.get("assignments") or {}).values())
    rows.sort(key=lambda r: str(r.get("updated_at") or ""), reverse=True)
    lim = max(1, min(int(limit or 100), 500))
    return {"success": True, "assignments": rows[:lim], "total": len(rows)}


def execute_control_action(
    user_id: str,
    action: str,
    *,
    approved: bool = False,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run a control action via assigned agent, camgirl, or AI controller."""
    if not control_enabled():
        return {"success": False, "error": "control_disabled"}

    uid = str(user_id or "").strip()
    act = str(action or "").strip().lower()
    if not uid or not act:
        return {"success": False, "error": "user_id_and_action_required"}

    data = dict(payload or {})
    assignment = get_assignment(uid)
    ctype = str((assignment or {}).get("controller_type") or "ai").lower()
    cid = str((assignment or {}).get("controller_id") or "").strip()

    # Explicit override from payload
    if data.get("controller_type"):
        ctype = str(data["controller_type"]).lower()
    if data.get("controller_id"):
        cid = str(data["controller_id"]).strip()

    if ctype == "camgirl":
        from backend.services.camgirls_agents_service import execute_agent_action

        return execute_agent_action(
            act,
            uid,
            approved=approved or bool(data.get("approved")),
            performer_id=data.get("performer_id") or cid,
            message=data.get("message", ""),
            amount=data.get("amount"),
        )

    if ctype == "agent":
        from backend.services.agent_controller import agent_controller as controller

        if act in ("status", "capabilities"):
            if act == "status":
                return {"success": True, "result": controller.get_all_agents_status()}
            return {"success": True, "result": controller.get_agent_capabilities(cid or "master_fix")}
        if act == "skill":
            skill = str(data.get("skill") or data.get("skill_name") or "skill_calculate_with_intelligence")
            return controller.execute_agent_skill(cid or "master_fix", skill, user_id=uid, **data)
        return controller.execute_agent_skill(cid or "master_fix", act, user_id=uid, **data)

    # Default: AI user controller actions
    from backend.services import ai_user_controller as ai

    ai_actions = {
        "onboard": lambda: ai.onboard_new_user(uid, username=data.get("username", "")),
        "analyze": lambda: ai.analyze_user_activity(uid),
        "nudge": lambda: ai.generate_engagement_nudge(uid),
        "next_actions": lambda: ai.suggest_next_actions(uid, count=int(data.get("count") or 3)),
        "profile": lambda: ai.profile_user(uid),
        "health": lambda: ai.account_health_check(uid),
        "build": lambda: ai.ai_build_account(uid, data.get("username", "")),
        "repair": lambda: ai.auto_repair_account(uid),
        "boost": lambda: ai.ai_boost_account(uid, data.get("boost_type", "balanced")),
        "level_up": lambda: ai.ai_level_up(uid),
        "manage_skills": lambda: ai.ai_manage_skills(uid),
        "control_panel": lambda: ai.ai_control_panel(uid),
        "activity": lambda: ai.on_user_activity(uid, data.get("activity_type", "interaction"), metadata=data.get("metadata")),
    }
    if act not in ai_actions:
        return {
            "success": False,
            "error": "unknown_action",
            "controller_type": ctype,
            "available_actions": sorted(ai_actions.keys()),
        }
    result = ai_actions[act]()
    return {"success": True, "controller_type": ctype, "action": act, "result": result}


def control_stats() -> Dict[str, Any]:
    store = _load_store()
    assignments = list((store.get("assignments") or {}).values())
    by_type: Dict[str, int] = {}
    for row in assignments:
        t = str(row.get("controller_type") or "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "success": True,
        "enabled": control_enabled(),
        "total_assigned": len(assignments),
        "by_controller_type": by_type,
    }
