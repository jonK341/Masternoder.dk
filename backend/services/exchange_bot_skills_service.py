"""Catalog of special trading-bot skills + per-skill edge estimation."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_SKILLS_PATH = os.path.join(ex._BASE, "data", "exchange_bot_skills.json")


def load_skills() -> List[Dict[str, Any]]:
    data = ex._read_json(_SKILLS_PATH, {})
    skills = data.get("skills") if isinstance(data, dict) else None
    return [s for s in (skills or []) if isinstance(s, dict) and s.get("id")]


def _skill_map() -> Dict[str, Dict[str, Any]]:
    return {s["id"]: s for s in load_skills()}


def load_skill_sets() -> List[Dict[str, Any]]:
    data = ex._read_json(_SKILLS_PATH, {})
    return [s for s in (data.get("skill_sets") or []) if isinstance(s, dict) and s.get("id")]


def _skill_set_map() -> Dict[str, Dict[str, Any]]:
    return {s["id"]: s for s in load_skill_sets()}


def skill_details(skill_ids: List[str], *, volatility: float = 0.35) -> List[Dict[str, Any]]:
    smap = _skill_map()
    out: List[Dict[str, Any]] = []
    for sid in skill_ids or []:
        s = smap.get(sid)
        if not s:
            out.append({"id": sid, "name": sid, "category": "unknown", "edge_bps": 0.0})
            continue
        out.append({
            **s,
            "id": sid,
            "edge_bps": estimate_skill_edge(sid, volatility),
        })
    return out


def resolve_skill_set(skill_set_id: Optional[str] = None,
                      skill_ids: Optional[List[str]] = None,
                      *, volatility: float = 0.35) -> Dict[str, Any]:
    smap = _skill_set_map()
    row: Dict[str, Any]
    if skill_set_id and skill_set_id in smap:
        row = smap[skill_set_id]
        ids = list(row.get("skills") or [])
    else:
        ids = list(skill_ids or [])
        row = {"id": skill_set_id or "custom", "name": "Custom skill set", "skills": ids}
    details = skill_details(ids, volatility=volatility)
    blended = blended_edge_bps(ids, volatility)
    return {
        "id": row.get("id", "custom"),
        "name": row.get("name", "Skill set"),
        "tier": row.get("tier"),
        "description": row.get("description", ""),
        "skills": ids,
        "skill_details": details,
        "skill_count": len(details),
        "blended_edge_bps": blended["blended_edge_bps"],
        "skill_breakdown": blended["breakdown"],
    }


def enrich_agent_offer(offer: Dict[str, Any], *, volatility: float = 0.35,
                       skills_key: str = "skills", skill_set_key: str = "skill_set") -> Dict[str, Any]:
    ids = list(offer.get(skills_key) or [])
    ss = resolve_skill_set(offer.get(skill_set_key), ids, volatility=volatility)
    return {
        **offer,
        "skills": ids,
        "skill_details": ss["skill_details"],
        "skill_set": {
            "id": ss["id"],
            "name": ss["name"],
            "tier": ss.get("tier"),
            "description": ss.get("description"),
        },
        "blended_edge_bps": ss["blended_edge_bps"],
        "skill_breakdown": ss["skill_breakdown"],
    }


def list_skills() -> Dict[str, Any]:
    skills = load_skills()
    sets = load_skill_sets()
    return {
        "success": True,
        "skill_count": len(skills),
        "skills": skills,
        "skill_set_count": len(sets),
        "skill_sets": sets,
    }


def get_skill(skill_id: str) -> Optional[Dict[str, Any]]:
    return _skill_map().get((skill_id or "").strip())


def estimate_skill_edge(skill_id: str, volatility: float = 0.35) -> float:
    """Expected edge in bps for a skill at a given market volatility (0..1+)."""
    skill = get_skill(skill_id)
    if not skill:
        return 0.0
    base = float(skill.get("base_edge_bps") or 0)
    sens = float(skill.get("volatility_sensitivity") or 0)
    lo = float(skill.get("min_edge_bps") or 0)
    hi = float(skill.get("max_edge_bps") or base)
    edge = base * (1.0 + sens * (max(0.0, float(volatility)) - 0.35))
    return round(max(lo, min(hi, edge)), 2)


def blended_edge_bps(skill_ids: List[str], volatility: float = 0.35) -> Dict[str, Any]:
    """Combine multiple skills with diminishing returns (sorted desc, decayed)."""
    edges = sorted(
        ((sid, estimate_skill_edge(sid, volatility)) for sid in (skill_ids or []) if get_skill(sid)),
        key=lambda kv: kv[1],
        reverse=True,
    )
    decay = 1.0
    total = 0.0
    breakdown = []
    for sid, edge in edges:
        contrib = edge * decay
        total += contrib
        breakdown.append({"skill_id": sid, "edge_bps": edge, "weight": round(decay, 3), "contribution_bps": round(contrib, 2)})
        decay *= 0.6
    return {"blended_edge_bps": round(total, 2), "breakdown": breakdown}
