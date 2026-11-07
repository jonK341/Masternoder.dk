"""Aggregator hub v2 — 75-agent catalog, top 25, fulfillment, progress."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ASSIGN_FILE = os.path.join(_ROOT, "data", "aggregator_assignments.json")

_CATEGORIES = [
    "intelligence", "commerce", "social", "gaming", "media", "security",
    "analytics", "automation", "research", "ops",
]

_TECH = [
    "Holodeck grid", "Web Audio", "Base64 encoder", "Intel feeds", "MN2 rewards",
    "Unified points", "5D narrative", "Agent mesh", "LiveKit", "PayPal bridge",
]

_ORCHESTRATOR_AGENT = "analytics_agent"

_CATEGORY_SKILL_SETS: Dict[str, List[str]] = {
    "intelligence": ["intel_gather", "nlp_summarize", "feed_watch"],
    "commerce": ["sku_router", "checkout_nudge", "mn2_treasury"],
    "social": ["community_pulse", "trend_scout", "mention_fanout"],
    "gaming": ["battle_telemetry", "loot_router", "xp_mesh"],
    "media": ["encoder_pipeline", "transcode_queue", "cdn_prefetch"],
    "security": ["audit_trail", "payout_sentinel", "acl_scan"],
    "analytics": ["metrics_rollup", "anomaly_ping", "kpi_stream"],
    "automation": ["cron_mesh", "webhook_fanout", "job_orchestrator"],
    "research": ["paper_digest", "source_verify", "hypothesis_tag"],
    "ops": ["deploy_smoke", "health_ping", "incident_triage"],
}


def _read_assignments() -> dict:
    if not os.path.isfile(_ASSIGN_FILE):
        return {}
    try:
        with open(_ASSIGN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_assignments(data: dict) -> None:
    os.makedirs(os.path.dirname(_ASSIGN_FILE), exist_ok=True)
    with open(_ASSIGN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _skill_set_for_category(category: str) -> List[str]:
    return list(_CATEGORY_SKILL_SETS.get(category, ["aggregator_ops", "mesh_relay"]))


def _catalog_rows() -> List[Dict[str, Any]]:
    rows = []
    for i in range(1, 76):
        aid = f"agg_{i:03d}"
        cat = _CATEGORIES[(i - 1) % len(_CATEGORIES)]
        skill_set = _skill_set_for_category(cat)
        rows.append({
            "id": aid,
            "name": f"Aggregator {i:02d}",
            "category": cat,
            "technologies": [_TECH[(i - 1) % len(_TECH)], _TECH[i % len(_TECH)]],
            "agent_id": f"agent_{cat}_{(i % 12) + 1:02d}",
            "skill_set": skill_set,
            "status": "active",
            "description": f"{cat.title()} pipeline node #{i} for platform intelligence and fulfillment.",
            "rank_score": max(1, 100 - i),
        })
    return rows


def _catalog_row(aggregator_id: str) -> Optional[Dict[str, Any]]:
    for row in _catalog_rows():
        if row.get("id") == aggregator_id:
            return row
    return None


def _activate_assignment_agents(
    user_id: str,
    orchestrator_agent_id: str,
    worker_agent_id: str,
    *,
    aggregator_id: str,
    skill_set: List[str],
) -> Dict[str, Any]:
    """Mark agents active and stamp aggregator skill sets on activity + skills tracker."""
    activated: List[str] = []
    try:
        from backend.services.agent_db_service import agent_db_service
        for aid, role in ((orchestrator_agent_id, "orchestrator"), (worker_agent_id, "worker")):
            agent_db_service.record_agent_activity(
                user_id=user_id,
                agent_id=aid,
                action="aggregator_assign_active",
                skill=skill_set[0] if skill_set else "aggregator_ops",
                xp_gained=5,
                points_gained=0.0,
                metadata={
                    "aggregator_id": aggregator_id,
                    "role": role,
                    "skill_set": skill_set,
                    "status": "active",
                },
            )
            activated.append(aid)
    except Exception:
        pass
    try:
        from backend.services.skills_abilities_tracker import SkillsAbilitiesTracker
        tracker = SkillsAbilitiesTracker()
        cat_row = _catalog_row(aggregator_id) or {}
        category = cat_row.get("category") or "ops"
        for skill in skill_set:
            tracker.update_skill(user_id, category, skill, 1.0, source=f"aggregator:{aggregator_id}")
    except Exception:
        pass
    return {"activated_agents": activated, "skill_set": skill_set}


def list_catalog(limit: int = 75, category: Optional[str] = None, search: Optional[str] = None) -> Dict[str, Any]:
    rows = _catalog_rows()
    if category and category != "all":
        rows = [r for r in rows if r.get("category") == category]
    if search:
        q = search.lower()
        rows = [
            r for r in rows
            if q in (r.get("name") or "").lower()
            or q in (r.get("agent_id") or "").lower()
            or q in " ".join(r.get("technologies") or []).lower()
        ]
    rows = rows[: max(1, int(limit))]
    return {"success": True, "aggregators": rows, "count": len(rows), "categories": _CATEGORIES}


def top25_list() -> Dict[str, Any]:
    ranked = []
    for idx, row in enumerate(
        sorted(_catalog_rows(), key=lambda r: r.get("rank_score", 0), reverse=True)[:25],
        start=1,
    ):
        item = dict(row)
        item["rank"] = idx
        ranked.append(item)
    return {"success": True, "aggregators": ranked, "count": len(ranked)}


def fulfillment_section() -> Dict[str, Any]:
    playbook = [
        {"step": 1, "title": "Discover catalog", "detail": "Browse 75 aggregators and assign agents to your profile."},
        {"step": 2, "title": "Wire intelligence", "detail": "Connect intel feeds and encoder links to customer journeys."},
        {"step": 3, "title": "Track progress", "detail": "Monitor milestones, MN2 rewards, and fulfillment KPIs."},
        {"step": 4, "title": "Close the loop", "detail": "Export Base64 link lists and share deep links to monitor tabs."},
    ]
    return {"success": True, "playbook": playbook}


def assign_agent(
    user_id: str,
    aggregator_id: str,
    agent_id: str,
    *,
    chain_burst: int = 5,
) -> Dict[str, Any]:
    row = _catalog_row(aggregator_id)
    skill_set = row.get("skill_set") if row else _skill_set_for_category("ops")
    orchestrator = _ORCHESTRATOR_AGENT
    worker = agent_id or (row.get("agent_id") if row else "")

    data = _read_assignments()
    user_rows = data.setdefault(user_id, {})
    meta = {
        "agent_id": worker,
        "skill_set": skill_set,
        "status": "active",
        "orchestrator_agent_id": orchestrator,
        "assigned_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    user_rows[aggregator_id] = meta
    _write_assignments(data)

    activation = _activate_assignment_agents(
        user_id,
        orchestrator,
        worker,
        aggregator_id=aggregator_id,
        skill_set=skill_set,
    )

    chain: Dict[str, Any] = {"attempted": 0, "on_chain": 0, "transfers": []}
    try:
        from backend.services.agent_peer_transactions_service import fire_aggregator_assignment_transfers
        chain = fire_aggregator_assignment_transfers(
            user_id,
            orchestrator,
            worker,
            aggregator_id=aggregator_id,
            burst=chain_burst,
        )
    except Exception as exc:
        chain = {"success": False, "error": str(exc)[:200]}

    return {
        "success": True,
        "user_id": user_id,
        "aggregator_id": aggregator_id,
        "agent_id": worker,
        "skill_set": skill_set,
        "agent_status": "active",
        "activation": activation,
        "chain_settlement": chain,
    }


def progress_snapshot(user_id: str) -> Dict[str, Any]:
    data = _read_assignments()
    assigned = data.get(user_id) or {}
    total = len(_catalog_rows())
    done = len(assigned)
    pct = int((done / total) * 100) if total else 0
    return {
        "success": True,
        "assigned_count": len(assigned),
        "total_aggregators": total,
        "percent": pct,
        "milestones": [
            {"id": "m1", "label": "First assignment", "done": len(assigned) >= 1},
            {"id": "m5", "label": "Five agents wired", "done": len(assigned) >= 5},
            {"id": "m25", "label": "Top 25 explored", "done": len(assigned) >= 10},
        ],
    }
