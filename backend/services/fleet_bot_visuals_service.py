"""Public fleet bot avatars and progress tier images for the 5D monitor."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "fleet_bot_visuals.json")
_AGENTS_IMG = os.path.join(_BASE, "static", "img", "agents")


def _load() -> Dict[str, Any]:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def progress_tier_for_level(level: int) -> Dict[str, Any]:
    cfg = _load()
    tiers = cfg.get("progress_tiers") or []
    lv = max(1, int(level or 1))
    for row in tiers:
        if lv >= int(row.get("min_level") or 1):
            return {
                "tier": int(row.get("min_level") or 1),
                "progress_image_url": row.get("image") or cfg.get("default_progress"),
                "progress_label": row.get("label") or "Recruit",
            }
    return {
        "tier": 1,
        "progress_image_url": cfg.get("default_progress") or "/static/img/fleet/progress-tier-1.svg",
        "progress_label": "Recruit",
    }


def avatar_for_bot(fb: Dict[str, Any]) -> str:
    cfg = _load()
    badge = str(fb.get("badge") or "").strip()
    kind = str(fb.get("kind") or "fleet").strip()
    badge_map = cfg.get("badge_avatars") or {}
    kind_map = cfg.get("kind_avatars") or {}
    if badge and badge in badge_map:
        return badge_map[badge]
    if kind in kind_map:
        return kind_map[kind]
    return cfg.get("default_avatar") or "/static/img/fleet/default-bot.svg"


def agent_activity_avatar(agent_id: str) -> str:
    cfg = _load()
    aid = (agent_id or "").strip()
    if not aid:
        return cfg.get("agent_activity_fallback") or "/static/img/agents/ai_intelligence_agent.svg"
    template = cfg.get("agent_activity_avatar") or "/static/img/agents/{agent_id}.svg"
    path = template.replace("{agent_id}", aid)
    rel = path.lstrip("/")
    fs = os.path.join(_BASE, rel.replace("/", os.sep))
    if os.path.isfile(fs):
        return path if path.startswith("/") else "/" + path
    return cfg.get("agent_activity_fallback") or "/static/img/agents/ai_intelligence_agent.svg"


def enrich_bot_visuals(fb: Dict[str, Any]) -> Dict[str, Any]:
    prog = fb.get("progression") if isinstance(fb.get("progression"), dict) else {}
    level = int(prog.get("level") or fb.get("level") or 1)
    tier = progress_tier_for_level(level)
    return {
        "avatar_url": avatar_for_bot(fb),
        "progress_image_url": tier["progress_image_url"],
        "progress_tier": tier["tier"],
        "progress_label": tier["progress_label"],
        "badge": fb.get("badge") or "",
    }
