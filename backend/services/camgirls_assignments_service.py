"""Camgirls platform assignments — agent personas, skill sets, optional MN2 rewards."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ASSIGNMENTS_FILE = os.path.join(_ROOT, "data", "camgirls_assignments.json")
_MODELS_FILE = os.path.join(_ROOT, "data", "camgirls_agent_models.json")

_DEFAULT_SKILL_SET = ["studio_host", "mn2_tips", "fan_club_goal", "gift_router"]
_TASK_KINDS = ("speed", "free", "default", "creative")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _read_assignments() -> Dict[str, Any]:
    data = _read_json(_ASSIGNMENTS_FILE, {"assignments": {}, "updated_at": None})
    if not isinstance(data, dict):
        return {"assignments": {}}
    data.setdefault("assignments", {})
    return data


def _write_assignments(data: Dict[str, Any]) -> None:
    data["updated_at"] = _iso()
    _write_json(_ASSIGNMENTS_FILE, data)


def _slug_token(performer_id: str) -> str:
    base = performer_id.replace("performer_", "", 1) if performer_id.startswith("performer_") else performer_id
    base = re.sub(r"[^a-zA-Z0-9]+", "_", base).strip("_").lower()
    return base or "studio"


def _task_kind_for_index(i: int) -> str:
    return _TASK_KINDS[i % len(_TASK_KINDS)]


def _load_agent_models() -> List[Dict[str, Any]]:
    data = _read_json(_MODELS_FILE, {"agents": []})
    rows = data.get("agents") if isinstance(data, dict) else []
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def _save_agent_models(agents: List[Dict[str, Any]]) -> None:
    _write_json(_MODELS_FILE, {"agents": agents})


def ensure_agent_model(performer_id: str, performer_row: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Register camgirl_agent_* model when wave stubs lack one."""
    from backend.services.camgirls_service import get_performer_row

    row = performer_row or get_performer_row(performer_id) or {}
    display = str(row.get("display_name") or performer_id)
    agents = _load_agent_models()
    for m in agents:
        if m.get("performer_id") == performer_id:
            return {"success": True, "created": False, "agent": m}
    token = _slug_token(performer_id)
    agent_id = f"camgirl_agent_{token}"
    if any(m.get("agent_id") == agent_id for m in agents):
        agent_id = f"{agent_id}_{len(agents)}"
    task = _task_kind_for_index(len(agents))
    model = {
        "agent_id": agent_id,
        "performer_id": performer_id,
        "display_name": f"{display} Agent",
        "task_kind": task,
        "casino_skill_set": list(_DEFAULT_SKILL_SET),
        "description": f"Studio host agent for {display} — MN2 tips, unlocks, and fan-club goals.",
    }
    agents.append(model)
    _save_agent_models(agents)
    return {"success": True, "created": True, "agent": model}


def get_assignment(performer_id: str) -> Optional[Dict[str, Any]]:
    bucket = (_read_assignments().get("assignments") or {})
    row = bucket.get((performer_id or "").strip())
    return row if isinstance(row, dict) else None


def list_assignments() -> Dict[str, Any]:
    data = _read_assignments()
    bucket = data.get("assignments") if isinstance(data.get("assignments"), dict) else {}
    rows = [
        {"performer_id": pid, **(meta if isinstance(meta, dict) else {})}
        for pid, meta in bucket.items()
    ]
    return {"success": True, "count": len(rows), "assignments": rows, "updated_at": data.get("updated_at")}


def _activate_agent(user_id: str, agent_id: str, performer_id: str, skill_set: List[str]) -> None:
    try:
        from backend.services.agent_db_service import agent_db_service

        agent_db_service.record_agent_activity(
            user_id=user_id,
            agent_id=agent_id,
            action="camgirls_assign_active",
            skill=skill_set[0] if skill_set else "studio_host",
            xp_gained=10,
            points_gained=0.0,
            metadata={
                "performer_id": performer_id,
                "skill_set": skill_set,
                "status": "active",
            },
        )
    except Exception:
        pass
    try:
        from backend.services.skills_abilities_tracker import SkillsAbilitiesTracker

        tracker = SkillsAbilitiesTracker()
        for skill in skill_set:
            tracker.update_skill(user_id, "camgirls", skill, 1.0, source=f"camgirls:{performer_id}")
    except Exception:
        pass


def assign_performer(
    performer_id: str,
    *,
    assigner_user_id: str = "platform_camgirls",
    aggregator_category: str = "media",
    reward_on_chain: bool = False,
    reward_amount_mn2: float = 0.0001,
    dry_run: bool = False,
) -> Dict[str, Any]:
    from backend.services.camgirls_service import get_performer_row

    pid = (performer_id or "").strip()
    if not pid:
        return {"success": False, "error": "performer_id_required"}
    perf = get_performer_row(pid)
    if not perf:
        return {"success": False, "error": "performer_not_found"}

    agent_res = ensure_agent_model(pid, perf)
    agent = agent_res.get("agent") or {}
    agent_id = str(agent.get("agent_id") or "")
    skill_set = list(agent.get("casino_skill_set") or _DEFAULT_SKILL_SET)

    from backend.services.camgirls_payout_service import get_payout_address

    wallet = get_payout_address(pid)
    payout_address = (wallet.get("address") or "").strip() or None

    data = _read_assignments()
    bucket = data.setdefault("assignments", {})
    ref = f"camgirl-assign:{pid}"
    meta = {
        "agent_id": agent_id,
        "aggregator_category": aggregator_category,
        "skill_set": skill_set,
        "payout_address": payout_address,
        "assigned_at": _iso(),
        "assigner_user_id": assigner_user_id,
        "status": "active",
        "reward_reference": ref,
    }
    bucket[pid] = meta
    _write_assignments(data)

    _activate_agent(assigner_user_id, agent_id, pid, skill_set)

    chain: Dict[str, Any] = {"attempted": False}
    if reward_on_chain and payout_address:
        from backend.services.camgirls_payout_service import payout_performer_reward_on_chain

        chain = payout_performer_reward_on_chain(
            pid,
            reward_amount_mn2,
            source="camgirls_assignment",
            reference=ref,
            dry_run=dry_run,
        )
        chain["attempted"] = True
        if chain.get("txid"):
            meta["last_reward_txid"] = chain.get("txid")
            bucket[pid] = meta
            _write_assignments(data)
    elif reward_on_chain and not payout_address:
        chain = {"attempted": True, "success": False, "error": "no_payout_address"}

    return {
        "success": True,
        "performer_id": pid,
        "agent_id": agent_id,
        "payout_address": payout_address,
        "assignment": meta,
        "agent_created": bool(agent_res.get("created")),
        "chain_reward": chain,
    }


def assign_all_performers(
    *,
    assigner_user_id: str = "platform_camgirls",
    provision_missing_addresses: bool = True,
    reward_on_chain: bool = False,
    reward_amount_mn2: float = 0.0001,
    dry_run: bool = False,
) -> Dict[str, Any]:
    from backend.services.camgirls_service import list_active_performer_ids

    ids = list_active_performer_ids()
    if provision_missing_addresses and ids:
        from backend.services.camgirls_payout_service import provision_payout_addresses

        provision_payout_addresses(performer_ids=ids)

    results: List[Dict[str, Any]] = []
    on_chain = 0
    for pid in ids:
        row = assign_performer(
            pid,
            assigner_user_id=assigner_user_id,
            reward_on_chain=reward_on_chain,
            reward_amount_mn2=reward_amount_mn2,
            dry_run=dry_run,
        )
        results.append(row)
        cr = row.get("chain_reward") or {}
        if cr.get("txid") or cr.get("dry_run"):
            on_chain += 1

    with_wallet = sum(1 for r in results if r.get("payout_address"))
    return {
        "success": True,
        "total": len(ids),
        "assigned": len(results),
        "with_payout_address": with_wallet,
        "chain_rewards": on_chain,
        "results": results,
    }
