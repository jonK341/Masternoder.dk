"""Sync MN2 ledger customers into the aggregator and wire agent control."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_POINTS_DIR = os.path.join(_BASE, "logs", "unified_points")


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


def list_ledger_customers(*, limit: int = 500, offset: int = 0) -> Dict[str, Any]:
    from backend.services.mn2_ledger import list_ledger_user_summaries

    rows = list_ledger_user_summaries(limit=max(limit + offset, 500))
    page = rows[offset: offset + limit]
    return {"success": True, "customers": page, "total": len(rows), "limit": limit, "offset": offset}


def _ensure_points_stub(user_id: str, ledger_row: Dict[str, Any]) -> bool:
    try:
        os.makedirs(_POINTS_DIR, exist_ok=True)
        path = os.path.join(_POINTS_DIR, f"{user_id}.json")
        created = False
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f) or {}
        else:
            raw = {
                "user_id": user_id,
                "level": 1,
                "xp_total": 0,
                "coins": 0,
                "mn2_balance": 0,
                "systems": {"mn2_balance": 0, "coins": 0},
                "source": "ledger",
                "updated_at": _iso(),
            }
            created = True
        raw["source"] = raw.get("source") or "ledger"
        raw["ledger"] = {
            "entry_count": ledger_row.get("entry_count"),
            "last_activity": ledger_row.get("last_activity"),
            "ledger_in_mn2": ledger_row.get("ledger_in_mn2"),
            "ledger_out_mn2": ledger_row.get("ledger_out_mn2"),
            "ledger_net_mn2": ledger_row.get("ledger_net_mn2"),
            "entry_types": ledger_row.get("entry_types"),
        }
        raw["updated_at"] = ledger_row.get("last_activity") or raw.get("updated_at") or _iso()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2)
        return created
    except OSError as exc:
        raise RuntimeError(f"points_stub_write_failed:{user_id}:{exc}") from exc


def sync_ledger_customers_to_aggregator(*, limit: int = 500) -> Dict[str, Any]:
    """Import ledger user IDs into unified points / customer aggregator."""
    from backend.services.mn2_ledger import list_ledger_user_summaries

    cfg = _config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "ledger_customer_control_disabled"}

    rows = list_ledger_user_summaries(limit=limit)
    created = 0
    updated = 0
    errors: List[Dict[str, Any]] = []
    for row in rows:
        uid = str(row.get("user_id") or "").strip()
        if not uid:
            continue
        try:
            if _ensure_points_stub(uid, row):
                created += 1
            else:
                updated += 1
        except RuntimeError as exc:
            errors.append({"user_id": uid, "error": str(exc)})
            if len(errors) >= 5:
                break

    if errors and created == 0 and updated == 0:
        return {
            "success": False,
            "error": "points_stub_write_failed",
            "errors": errors,
            "ledger_total": len(rows),
        }

    return {
        "success": True,
        "ledger_total": len(rows),
        "stubs_created": created,
        "stubs_updated": updated,
        "errors": errors,
        "preview": rows[:15],
    }


def list_available_agents() -> Dict[str, Any]:
    """Platform agents available for ledger customer control."""
    agents: List[Dict[str, Any]] = []
    try:
        from backend.services.agent_controller import agent_controller

        status = agent_controller.get_all_agents_status()
        for agent_id, info in (status.get("agents") or {}).items():
            agents.append({
                "agent_id": agent_id,
                "status": info.get("status"),
                "label": agent_id.replace("_", " ").title(),
            })
    except Exception:
        pass

    cfg = _config()
    default_agent = str(cfg.get("default_agent_id") or "master_fix")
    if default_agent and not any(a["agent_id"] == default_agent for a in agents):
        agents.insert(0, {"agent_id": default_agent, "status": "configured", "label": default_agent})

    return {
        "success": True,
        "agents": agents,
        "default_agent_id": default_agent,
        "auto_assign_agent": bool(cfg.get("auto_assign_agent", True)),
    }


def assign_agents_to_ledger_customers(
    *,
    limit: int = 200,
    controller_type: str = "agent",
    only_unassigned: bool = True,
) -> Dict[str, Any]:
    """Assign platform agents to ledger customers (round-robin over available agents)."""
    from backend.services.ledger_customer_control_service import assign_controller, get_assignment
    from backend.services.mn2_ledger import list_ledger_user_summaries

    cfg = _config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "ledger_customer_control_disabled"}

    agent_info = list_available_agents()
    agents = [a["agent_id"] for a in (agent_info.get("agents") or []) if a.get("agent_id")]
    if not agents:
        agents = [str(cfg.get("default_agent_id") or "master_fix")]

    rows = list_ledger_user_summaries(limit=limit)
    assigned: List[Dict[str, Any]] = []
    skipped = 0
    idx = 0

    for row in rows:
        uid = str(row.get("user_id") or "").strip()
        if not uid:
            continue
        if only_unassigned and get_assignment(uid):
            skipped += 1
            continue
        agent_id = agents[idx % len(agents)]
        idx += 1
        res = assign_controller(
            uid,
            controller_type,
            agent_id=agent_id,
            notes="auto-assigned from ledger sync",
            metadata={"source": "ledger_customer_aggregator", "ledger_entries": row.get("entry_count")},
        )
        if res.get("success"):
            assigned.append({"user_id": uid, "agent_id": agent_id, "assignment": res.get("assignment")})

    return {
        "success": True,
        "assigned_count": len(assigned),
        "skipped_count": skipped,
        "agents_used": agents,
        "assignments_preview": assigned[:20],
    }


def sync_ledger_customers_with_agents(*, limit: int = 200) -> Dict[str, Any]:
    """Full pipeline: ledger → aggregator stubs → agent assignment."""
    sync = sync_ledger_customers_to_aggregator(limit=limit)
    if not sync.get("success"):
        return sync
    assign = assign_agents_to_ledger_customers(limit=limit, only_unassigned=True)
    return {
        "success": True,
        "ledger_sync": sync,
        "agent_assign": assign,
    }
