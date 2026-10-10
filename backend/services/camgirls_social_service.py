"""Camgirls social — favorites, fan club, goals."""
from __future__ import annotations

import json
import os
from typing import Any, Dict

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_FAVORITES_FILE = os.path.join(_ROOT, "data", "camgirls_favorites.json")
_FANCLUB_FILE = os.path.join(_ROOT, "data", "camgirls_fanclub.json")
_OFFLINE_FILE = os.path.join(_ROOT, "data", "camgirls_offline.jsonl")
_PRIVATE_FILE = os.path.join(_ROOT, "data", "camgirls_private.json")
_TIPS_FILE = os.path.join(_ROOT, "data", "camgirls_tips.jsonl")


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


def is_favorite(user_id: str, performer_id: str) -> bool:
    data = _read_json(_FAVORITES_FILE, {})
    return performer_id in (data.get(user_id) or [])


def toggle_favorite(user_id: str, performer_id: str) -> Dict[str, Any]:
    data = _read_json(_FAVORITES_FILE, {})
    favs = set(data.get(user_id) or [])
    if performer_id in favs:
        favs.remove(performer_id)
        on = False
    else:
        favs.add(performer_id)
        on = True
    data[user_id] = sorted(favs)
    _write_json(_FAVORITES_FILE, data)
    return {"success": True, "favorite": on}


def join_fan_club(user_id: str, performer_id: str) -> Dict[str, Any]:
    from backend.services.camgirls_service import _is_unlocked, _is_age_verified
    if not _is_age_verified(user_id):
        return {"success": False, "code": "age_verification_required"}
    if not _is_unlocked(user_id, performer_id):
        return {"success": False, "code": "unlock_required"}
    data = _read_json(_FANCLUB_FILE, {})
    members = set(data.get(performer_id) or [])
    members.add(user_id)
    data[performer_id] = sorted(members)
    _write_json(_FANCLUB_FILE, data)
    return {"success": True}


def get_goal_status(performer_id: str) -> Dict[str, Any]:
    from backend.services.camgirls_service import _get_performer
    p = _get_performer(performer_id) or {}
    goal = float(p.get("goal_mn2") or 100)
    raised = 0.0
    if os.path.isfile(_TIPS_FILE):
        with open(_TIPS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if row.get("performer_id") == performer_id:
                    raised += float(row.get("amount_mn2") or 0)
    percent = min(100, int((raised / goal) * 100)) if goal > 0 else 0
    return {"success": True, "raised_mn2": raised, "goal_mn2": goal, "percent": percent}
