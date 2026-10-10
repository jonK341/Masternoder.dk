"""Casino AI hosts — entertainment banter, tips, session monetization."""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "casino_ai_hosts.json")
_SESSION_PATH = os.path.join(_BASE, "logs", "casino_ai_sessions.json")


def _load_config() -> Dict[str, Any]:
    if not os.path.isfile(_CONFIG_PATH):
        return {}
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _casino_level(user_id: str) -> int:
    try:
        from backend.services.casino_progression_service import get_user_progression
        return int((get_user_progression(user_id) or {}).get("level") or 1)
    except Exception:
        return 1


def list_hosts(user_id: str) -> Dict[str, Any]:
    cfg = _load_config()
    level = _casino_level(user_id)
    hosts: List[Dict[str, Any]] = []
    for h in cfg.get("hosts") or []:
        if not isinstance(h, dict):
            continue
        hosts.append({**h, "unlocked": level >= int(h.get("min_level") or 1)})
    return {
        "success": True,
        "user_level": level,
        "hosts": hosts,
        "tip_packs_coins": cfg.get("tip_packs_coins") or [25, 50, 100],
    }


def get_banter(user_id: str, host_id: str, *, context: str = "lobby") -> Dict[str, Any]:
    cfg = _load_config()
    host = next((h for h in (cfg.get("hosts") or []) if h.get("id") == host_id), None)
    if not host:
        return {"success": False, "error": "unknown_host"}
    if _casino_level(user_id) < int(host.get("min_level") or 1):
        return {"success": False, "error": "level_locked"}
    lines = {
        "lobby": host.get("greeting") or "Welcome to the floor.",
        "win": f"{host.get('name')} cheers your win — keep the streak disciplined!",
        "loss": f"{host.get('name')} says: reset, smaller bet, next round.",
        "uber": f"{host.get('name')}: Uber tables favor bold MN2/USD — network bonus active.",
    }
    return {
        "success": True,
        "host_id": host_id,
        "host_name": host.get("name"),
        "line": lines.get(context) or lines["lobby"],
        "persona": host.get("persona"),
    }


def tip_host(user_id: str, host_id: str, coins: int) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    packs = _load_config().get("tip_packs_coins") or [25, 50, 100, 250]
    if coins not in packs:
        return {"success": False, "error": "invalid_tip_amount", "allowed": packs}
    host = next((h for h in (_load_config().get("hosts") or []) if h.get("id") == host_id), None)
    if not host:
        return {"success": False, "error": "unknown_host"}
    try:
        from backend.services import casino_service
        bal = casino_service.get_balance(uid)
        have = float(bal.get("coins") or 0)
        if have < coins:
            return {"success": False, "error": "insufficient_coins"}
        casino_service._apply_balance_delta(uid, -float(coins), "coins", "casino_ai_tip", {"host_id": host_id})
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    banter = get_banter(uid, host_id, context="win")
    return {
        "success": True,
        "host_id": host_id,
        "coins_tipped": coins,
        "banter": banter.get("line"),
        "revenue_event": "mm_ai_tips",
    }
