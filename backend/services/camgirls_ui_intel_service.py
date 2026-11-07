"""Camgirls UI intelligence — Top 10 ranking and tech labels for the studio front-end."""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

_INTEL_TECH = [
    "Agent mesh",
    "SSE chat",
    "LiveKit voice",
    "MN2 wallet",
    "PayPal bridge",
    "eBPF telemetry",
    "RAG persona",
    "Skill sets",
    "On-chain tips",
    "Studio floor NFT",
]


def _vibe(performer_id: str, display_name: str) -> str:
    pid = (performer_id or "").lower()
    name = (display_name or "").lower()
    if "wave3" in pid or any(t in pid for t in ("nebula", "cosmic", "stellar", "galaxy", "void", "pulsar")):
        return "cosmic"
    if "studio_host" in pid or "studio-host" in name:
        return "studio"
    if "signal" in pid or "vox" in pid or "neon" in pid:
        return "signal"
    if "wave2" in pid:
        return "wave2"
    return "legacy"


def _score_row(row: Dict[str, Any], *, rank_seed: str) -> float:
    score = 40.0
    tech = row.get("tech") if isinstance(row.get("tech"), dict) else {}
    if tech.get("agent_id"):
        score += 22
    if tech.get("ai_enabled", True):
        score += 8
    if tech.get("voice_mode") == "live":
        score += 12
    elif tech.get("voice_mode"):
        score += 4
    feats = tech.get("features") or []
    score += min(15, len(feats) * 0.8)
    media = row.get("media") if isinstance(row.get("media"), dict) else {}
    if media.get("preview_video_url") or media.get("preview_video_mp4_url"):
        score += 14
    if row.get("picture_url") or media.get("picture_url"):
        score += 10
    upgrades = row.get("studio_upgrades") or []
    score += min(8, len(upgrades) * 2)
    vibe = _vibe(str(row.get("id") or ""), str(row.get("display_name") or ""))
    if vibe == "cosmic":
        score += 9
    elif vibe == "studio":
        score += 6
    elif vibe == "signal":
        score += 5
    digest = hashlib.sha256(rank_seed.encode("utf-8")).hexdigest()
    score += (int(digest[:4], 16) % 100) / 100.0
    return round(score, 2)


def _tech_labels(row: Dict[str, Any], platform: Dict[str, Any]) -> List[str]:
    tech = row.get("tech") if isinstance(row.get("tech"), dict) else {}
    out: List[str] = []
    if tech.get("agent_id"):
        out.append("Agent mesh")
    if tech.get("voice_mode") == "live":
        out.append("LiveKit voice")
    else:
        out.append("Voice AI")
    out.append("SSE chat")
    pays = tech.get("payments") or ["mn2"]
    if "paypal" in pays:
        out.append("PayPal bridge")
    out.append("MN2 wallet")
    if platform.get("voice_live"):
        out.append("eBPF telemetry")
    out.append("RAG persona")
    if tech.get("casino_skill_set"):
        out.append("Skill sets")
    out.append("Studio floor NFT")
    seen = set()
    ordered: List[str] = []
    for label in out + _INTEL_TECH:
        if label not in seen:
            seen.add(label)
            ordered.append(label)
        if len(ordered) >= 6:
            break
    return ordered


def top10_performers(user_id: str = "default_user") -> Dict[str, Any]:
    from backend.services.camgirls_agents_service import agent_for_performer
    from backend.services.camgirls_service import list_performers_catalog
    from backend.services.camgirls_status_service import (
        _read_ops_state_file,
        _roster_scale_snapshot,
        paypal_configured,
        studio_tech_for_performer,
    )
    from backend.services.camgirls_livekit_service import public_status as livekit_status

    cat = list_performers_catalog(user_id=user_id, lite=True)
    rows = cat.get("performers") if isinstance(cat.get("performers"), list) else []
    livekit = livekit_status()
    paypal_on = paypal_configured()
    platform = {
        "voice_live": bool(livekit.get("configured")),
        "agents_linked": 0,
    }
    scored: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        pid = str(row["id"])
        enriched = dict(row)
        enriched["tech"] = studio_tech_for_performer(row, livekit=livekit, paypal_on=paypal_on)
        agent = agent_for_performer(pid) or {}
        if agent.get("casino_skill_set"):
            enriched["tech"]["casino_skill_set"] = agent.get("casino_skill_set")
        pic = row.get("avatar_url") or row.get("picture_url")
        if pic:
            enriched["picture_url"] = pic
        sc = _score_row(enriched, rank_seed=pid)
        scored.append(
            {
                "performer_id": pid,
                "display_name": row.get("display_name") or pid,
                "score": sc,
                "vibe": _vibe(pid, str(row.get("display_name") or "")),
                "picture_url": enriched.get("picture_url") or row.get("avatar_url"),
                "agent_id": enriched.get("tech", {}).get("agent_id"),
                "task_kind": enriched.get("tech", {}).get("task_kind"),
                "technologies": _tech_labels(enriched, platform),
                "intel_summary": (
                    f"{(enriched.get('tech') or {}).get('task_kind') or 'default'} agent · "
                    f"{_vibe(pid, str(row.get('display_name') or ''))} tier"
                ),
            }
        )
    scored.sort(key=lambda r: r["score"], reverse=True)
    top = scored[:10]
    for i, item in enumerate(top, start=1):
        item["rank"] = i
    agents_linked = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        if studio_tech_for_performer(row, livekit=livekit, paypal_on=paypal_on).get("agent_id"):
            agents_linked += 1
    scale = _roster_scale_snapshot(len(rows))
    ops = _read_ops_state_file()
    return {
        "success": True,
        "count": len(top),
        "performers_count": len(rows),
        "agents_linked": agents_linked,
        "scale": {
            "current": scale.get("current"),
            "target": scale.get("target"),
            "progress_pct": scale.get("progress_pct"),
            "scale_paused": bool(ops.get("scale_paused")),
        },
        "intel_stack": _INTEL_TECH,
        "top10": top,
    }
