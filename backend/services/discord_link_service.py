"""Discord account link status (M8 #51) — shared by profile UI and casino VIP."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_IDENT_DIR = os.path.join(_BASE, "logs", "user_identifiers")


def _ident_path(discord_id: str) -> str:
    safe = "".join(c for c in discord_id if c.isalnum() or c in "-_")
    return os.path.join(_IDENT_DIR, f"discord_{safe}.json")


def get_discord_id_for_user(user_id: str) -> Optional[str]:
    if not user_id or not os.path.isdir(_IDENT_DIR):
        return None
    for name in os.listdir(_IDENT_DIR):
        if not name.startswith("discord_") or not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(_IDENT_DIR, name), "r", encoding="utf-8") as f:
                row = json.load(f)
            if row.get("user_id") == user_id and row.get("linked"):
                return row.get("discord_id") or name.replace("discord_", "").replace(".json", "")
        except Exception:
            continue
    return None


def link_user(user_id: str, discord_id: str) -> Dict[str, Any]:
    user_id = (user_id or "").strip()
    discord_id = (discord_id or "").strip()
    if not user_id or not discord_id:
        return {"success": False, "error": "user_id and discord_id required"}
    os.makedirs(_IDENT_DIR, exist_ok=True)
    path = _ident_path(discord_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"user_id": user_id, "discord_id": discord_id, "linked": True}, f, indent=2)
    return {"success": True, "user_id": user_id, "discord_id": discord_id, "linked": True}


def unlink_user(user_id: str) -> Dict[str, Any]:
    user_id = (user_id or "").strip()
    if not user_id:
        return {"success": False, "error": "user_id required"}
    discord_id = get_discord_id_for_user(user_id)
    if not discord_id:
        return {"success": True, "unlinked": False, "message": "not_linked"}
    path = _ident_path(discord_id)
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError as exc:
        return {"success": False, "error": str(exc)}
    return {"success": True, "unlinked": True, "discord_id": discord_id}


def link_status(user_id: str) -> Dict[str, Any]:
    user_id = (user_id or "").strip()
    if not user_id:
        return {"success": False, "error": "user_id required"}
    discord_id = get_discord_id_for_user(user_id)
    mn2_balance = 0.0
    try:
        from backend.services.unified_points_database import unified_points_db
        pts = unified_points_db.get_all_points(user_id)
        mn2_balance = float((pts or {}).get("points", {}).get("mn2_balance") or 0)
    except Exception:
        pass
    min_vip = float(os.environ.get("CASINO_DISCORD_VIP_MIN_MN2", "100"))
    return {
        "success": True,
        "user_id": user_id,
        "linked": bool(discord_id),
        "discord_id": discord_id,
        "mn2_balance": mn2_balance,
        "casino_vip_eligible": bool(discord_id) and mn2_balance >= min_vip,
        "min_mn2_for_vip": min_vip,
    }
