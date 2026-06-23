"""Hunter level milestone MN2 rewards — one-time claim per level reached."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE_DIR, "data", "game_level_crypto.json")
_STATE_PATH = os.path.join(_BASE_DIR, "data", "game_level_crypto_state.json")

_CONFIG_CACHE: Optional[Dict[str, Any]] = None


def _data_dir() -> str:
    return os.path.join(_BASE_DIR, "data")


def _load_config() -> Dict[str, Any]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            _CONFIG_CACHE = json.load(f)
    except Exception:
        _CONFIG_CACHE = {"levels": [], "currency": "MN2"}
    return _CONFIG_CACHE


def _load_state() -> dict:
    if os.path.exists(_STATE_PATH):
        try:
            with open(_STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"users": {}}


def _save_state(data: dict) -> None:
    os.makedirs(_data_dir(), exist_ok=True)
    tmp = _STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _STATE_PATH)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_hunter_level(user_id: str) -> int:
    level = 1
    try:
        from backend.routes.hunters_game import get_user_level_info

        info = get_user_level_info(user_id) or {}
        level = int(info.get("current_level") or 1)
    except Exception:
        pass
    if level <= 1:
        try:
            from backend.services.unified_points_database import unified_points_db

            res = unified_points_db.get_all_points(user_id) if unified_points_db else {}
            pts = res.get("points", {}) if isinstance(res, dict) else {}
            level = max(level, int(pts.get("level") or 1))
        except Exception:
            pass
    return max(1, level)


def _mn2_balance(user_id: str) -> float:
    try:
        from backend.services.unified_points_database import unified_points_db

        res = unified_points_db.get_all_points(user_id) if unified_points_db else {}
        pts = res.get("points", {}) if isinstance(res, dict) else {}
        return float(pts.get("mn2_balance", 0) or 0)
    except Exception:
        return 0.0


def level_rewards_status(user_id: str) -> Dict[str, Any]:
    cfg = _load_config()
    state = _load_state()
    user_state = state.setdefault("users", {}).setdefault(user_id, {"claimed_levels": [], "claims": []})
    claimed_set = {int(x) for x in (user_state.get("claimed_levels") or [])}
    current_level = _resolve_hunter_level(user_id)
    levels: List[Dict[str, Any]] = []
    claimable_count = 0
    for row in cfg.get("levels") or []:
        lvl = int(row.get("level") or 0)
        if lvl <= 0:
            continue
        claimed = lvl in claimed_set
        unlocked = current_level >= lvl
        ready = unlocked and not claimed
        if ready:
            claimable_count += 1
        levels.append({
            "level": lvl,
            "label": row.get("label") or f"Level {lvl}",
            "reward_mn2": round(float(row.get("mn2", 0) or 0), 8),
            "unlocked": unlocked,
            "claimed": claimed,
            "ready": ready,
        })
    total_earned = round(
        sum(float(c.get("amount_mn2", 0) or 0) for c in (user_state.get("claims") or [])),
        8,
    )
    return {
        "user_id": user_id,
        "currency": cfg.get("currency", "MN2"),
        "current_level": current_level,
        "mn2_balance": _mn2_balance(user_id),
        "total_mn2_earned": total_earned,
        "claimable_count": claimable_count,
        "levels": levels,
        "claims": list(user_state.get("claims") or [])[-20:],
        "implementation_status": "one_time_level_milestone_claims",
    }


def claim_level_reward(user_id: str, level: int) -> tuple:
    cfg = _load_config()
    row = next((r for r in (cfg.get("levels") or []) if int(r.get("level") or 0) == level), None)
    if not row:
        return {"success": False, "error": "Unknown level reward"}, 404

    current_level = _resolve_hunter_level(user_id)
    if current_level < level:
        return {
            "success": False,
            "error": "Level not reached yet",
            "current_level": current_level,
            "required_level": level,
        }, 400

    state = _load_state()
    user_state = state.setdefault("users", {}).setdefault(user_id, {"claimed_levels": [], "claims": []})
    claimed_levels = [int(x) for x in (user_state.get("claimed_levels") or [])]
    if level in claimed_levels:
        return {"success": False, "error": "Already claimed", "duplicate": True}, 409

    amount = round(float(row.get("mn2", 0) or 0), 8)
    if amount <= 0:
        return {"success": False, "error": "Invalid reward amount"}, 400

    reference = f"game-level-{level}"
    from backend.services.game_mn2_rewards import credit_mn2

    credit = credit_mn2(
        user_id,
        amount,
        source="game_level_crypto_claim",
        reference=reference,
        metadata={"level": level, "label": row.get("label")},
    )
    if not credit.get("success") and not credit.get("duplicate"):
        return {"success": False, "error": credit.get("error", "MN2 award failed")}, 500

    now = _utc_now().isoformat()
    if not credit.get("duplicate"):
        claimed_levels.append(level)
        user_state["claimed_levels"] = sorted(set(claimed_levels))
        claim = {
            "level": level,
            "label": row.get("label"),
            "amount_mn2": amount,
            "claimed_at": now,
        }
        user_state.setdefault("claims", []).append(claim)
        user_state["updated_at"] = now
        _save_state(state)
        try:
            from backend.routes.social_routes import push_activity

            push_activity(
                user_id,
                "game_level_crypto_claim",
                f"Claimed {amount:.8f} MN2 for reaching level {level}",
                {"level": level},
            )
        except Exception:
            pass

    return {
        "success": True,
        "claim": {
            "level": level,
            "amount_mn2": amount,
            "claimed_at": now,
        },
        "level_rewards": level_rewards_status(user_id),
    }, 200
