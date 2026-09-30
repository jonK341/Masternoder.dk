"""Cross-bridge quests — exchange rentals + casino MN2 activity (weekly progress + rewards)."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_CONFIG_PATH = os.path.join(ex._BASE, "data", "exchange_casino_quests.json")
_STATE_DIR = os.path.join(ex._DATA_DIR, "exchange_casino_quests")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _week_key() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"


def load_config() -> Dict[str, Any]:
    cfg = ex._read_json(_CONFIG_PATH, {})
    return cfg if isinstance(cfg, dict) else {}


def _state_path(user_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(user_id))
    return os.path.join(_STATE_DIR, f"{safe}.json")


def _load_user(user_id: str) -> Dict[str, Any]:
    data = ex._read_json(_state_path(user_id), {})
    if not isinstance(data, dict):
        data = {}
    cfg = load_config()
    if cfg.get("week_resets", True) and data.get("week") != _week_key():
        data = {"week": _week_key(), "quests": {}, "completed": {}}
    data.setdefault("week", _week_key())
    data.setdefault("quests", {})
    data.setdefault("completed", {})
    return data


def _save_user(user_id: str, data: Dict[str, Any]) -> None:
    os.makedirs(_STATE_DIR, exist_ok=True)
    ex._write_json(_state_path(user_id), data)


def _quest_defs() -> List[Dict[str, Any]]:
    return [q for q in (load_config().get("quests") or []) if isinstance(q, dict) and q.get("id")]


def _grant_rewards(user_id: str, quest: Dict[str, Any]) -> Dict[str, Any]:
    granted: Dict[str, Any] = {"coins": 0, "xp": 0}
    coins = int(quest.get("reward_coins") or 0)
    xp = int(quest.get("reward_xp") or 0)
    if coins > 0:
        try:
            from backend.services.unified_points_database import unified_points_db

            unified_points_db.add_points(
                user_id, "coins", float(coins),
                source="exchange_casino_quest",
                metadata={"quest_id": quest.get("id")},
            )
            granted["coins"] = coins
        except Exception:
            pass
    if xp > 0:
        try:
            from backend.services import exchange_leveling_service as lvl

            lvl.award_xp(user_id, float(xp), "bridge_quest", quest_id=quest.get("id"))
            granted["xp"] = xp
        except Exception:
            pass
    bp_action = (quest.get("battle_pass_action") or quest.get("action") or "").strip()
    if bp_action:
        try:
            from backend.services.battle_pass_service import record_battle_pass_action

            record_battle_pass_action(user_id, bp_action)
        except Exception:
            pass
    return granted


def record_bridge_action(user_id: str, action: str, *, amount: int = 1) -> Optional[Dict[str, Any]]:
    """Increment cross-bridge quest progress; grant rewards when targets met."""
    user_id = (user_id or "").strip()
    action_key = (action or "").strip()
    cfg = load_config()
    if not cfg.get("enabled", True) or not user_id or user_id == "default_user" or not action_key:
        return None

    matching = [q for q in _quest_defs() if (q.get("action") or "").strip() == action_key]
    if not matching:
        return None

    data = _load_user(user_id)
    completed_now: List[Dict[str, Any]] = []
    inc = max(1, int(amount or 1))

    for quest in matching:
        qid = quest["id"]
        if data["completed"].get(qid):
            continue
        prog = int((data["quests"].get(qid) or {}).get("progress") or 0)
        target = max(1, int(quest.get("target") or 1))
        prog = min(target, prog + inc)
        data["quests"][qid] = {"progress": prog, "target": target, "updated_at": _iso()}
        if prog >= target:
            data["completed"][qid] = _iso()
            granted = _grant_rewards(user_id, quest)
            completed_now.append({"quest_id": qid, "label": quest.get("label"), "granted": granted})

    if not completed_now and inc <= 0:
        return None

    _save_user(user_id, data)
    if completed_now:
        ex._audit("bridge_quest_complete", user_id=user_id, bridge_action=action_key,
                  quests=[c["quest_id"] for c in completed_now])
    return {
        "success": True,
        "action": action_key,
        "completed": completed_now,
        "quests": quest_status(user_id).get("quests") or [],
    }


def quest_status(user_id: str) -> Dict[str, Any]:
    user_id = (user_id or "").strip()
    cfg = load_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "quests_disabled"}
    data = _load_user(user_id)
    rows = []
    for quest in _quest_defs():
        qid = quest["id"]
        target = max(1, int(quest.get("target") or 1))
        prog = int((data["quests"].get(qid) or {}).get("progress") or 0)
        rows.append({
            **quest,
            "progress": prog,
            "target": target,
            "completed": bool(data["completed"].get(qid)),
            "completed_at": data["completed"].get(qid),
        })
    done = sum(1 for r in rows if r["completed"])
    return {
        "success": True,
        "user_id": user_id,
        "season_id": cfg.get("season_id"),
        "week": data.get("week"),
        "quests": rows,
        "completed_count": done,
        "total_count": len(rows),
    }


def emit_bridge_market_event(event_type: str, user_id: str, payload: Dict[str, Any]) -> None:
    """Emit high-signal bridge events for Discord #market fan-out."""
    try:
        from backend.services.activity_events_service import emit

        emit(event_type, channel="market", user_id=user_id, payload=payload)
    except Exception:
        pass
