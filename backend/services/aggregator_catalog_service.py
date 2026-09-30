"""Aggregator hub v2 — 75-agent catalog, top 25, fulfillment, progress."""
from __future__ import annotations

import json
import os
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


def _catalog_rows() -> List[Dict[str, Any]]:
    rows = []
    for i in range(1, 76):
        aid = f"agg_{i:03d}"
        cat = _CATEGORIES[(i - 1) % len(_CATEGORIES)]
        rows.append({
            "id": aid,
            "name": f"Aggregator {i:02d}",
            "category": cat,
            "technologies": [_TECH[(i - 1) % len(_TECH)], _TECH[i % len(_TECH)]],
            "agent_id": f"agent_{cat}_{(i % 12) + 1:02d}",
            "description": f"{cat.title()} pipeline node #{i} for platform intelligence and fulfillment.",
            "rank_score": max(1, 100 - i),
        })
    return rows


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


def assign_agent(user_id: str, aggregator_id: str, agent_id: str) -> Dict[str, Any]:
    data = _read_assignments()
    user_rows = data.setdefault(user_id, {})
    user_rows[aggregator_id] = agent_id
    _write_assignments(data)
    return {"success": True, "user_id": user_id, "aggregator_id": aggregator_id, "agent_id": agent_id}


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
