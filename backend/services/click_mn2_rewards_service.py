"""Instant MN2 (MasterNoder2) rewards for click-game wins."""
from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "mn2_config.json")

_DEFAULT_CLICK_CFG = {
    "enabled": True,
    "base_per_click_mn2": 0.0001,
    "critical_multiplier": 3.0,
    "combo_bonus_per_level_mn2": 0.00002,
    "mission_win_mn2": 0.002,
    "quest_win_mn2": 0.003,
    "achievement_win_mn2": 0.005,
    "level_up_mn2": 0.01,
    "daily_cap_mn2": 0.5,
    "instant": True,
}


def _load_click_cfg() -> Dict[str, Any]:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            root = json.load(f)
        cfg = root.get("click_rewards") or {}
        out = dict(_DEFAULT_CLICK_CFG)
        out.update(cfg)
        return out
    except Exception:
        return dict(_DEFAULT_CLICK_CFG)


def _calc_amount(action: str, metadata: Dict[str, Any], cfg: Dict[str, Any]) -> float:
    action = (action or "click").strip().lower()
    base = float(cfg.get("base_per_click_mn2") or 0.0001)

    if action == "click":
        amt = base
        if metadata.get("critical"):
            amt *= float(cfg.get("critical_multiplier") or 3.0)
        combo = int(metadata.get("combo") or 0)
        if combo > 1:
            amt += float(cfg.get("combo_bonus_per_level_mn2") or 0.00002) * (combo - 1)
        level = int(metadata.get("level") or 1)
        amt *= 1.0 + (max(0, level - 1) * 0.02)
        return round(amt, 8)

    table = {
        "mission_complete": float(cfg.get("mission_win_mn2") or 0.002),
        "quest_complete": float(cfg.get("quest_win_mn2") or 0.003),
        "achievement_unlock": float(cfg.get("achievement_win_mn2") or 0.005),
        "achievement_bonus": float(cfg.get("achievement_win_mn2") or 0.005) * 0.5,
        "level_up": float(cfg.get("level_up_mn2") or 0.01),
        "level_milestone": float(cfg.get("level_up_mn2") or 0.01) * 2,
        "story_chapter": 0.001,
        "clip_story_view": 0.0005,
    }
    return round(table.get(action, base), 8)


def credit_instant_click_reward(
    user_id: str,
    *,
    action: str = "click",
    click_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Credit MN2 instantly when the user wins a click reward.
    Returns new balance and transaction id for UI toast.
    """
    cfg = _load_click_cfg()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "click_rewards_disabled"}

    meta = dict(metadata or {})
    amount = _calc_amount(action, meta, cfg)
    if amount <= 0:
        return {"success": False, "error": "zero_reward"}

    ref = click_id or f"click-mn2:{user_id}:{action}:{uuid.uuid4().hex[:16]}"
    source = "click_reward_mn2" if action == "click" else f"click_{action}_mn2"

    from backend.services.game_mn2_rewards import credit_mn2

    result = credit_mn2(
        user_id,
        amount,
        source=source,
        reference=ref,
        metadata={
            "action": action,
            "instant": True,
            "click_id": click_id,
            **meta,
        },
    )
    if not result.get("success") and not result.get("duplicate"):
        return result

    balance_mn2 = None
    try:
        from backend.services.unified_points_database import unified_points_db
        pts = unified_points_db.get_all_points(user_id)
        if isinstance(pts, dict) and pts.get("success"):
            balance_mn2 = float((pts.get("points") or {}).get("mn2_balance") or 0)
    except Exception:
        pass

    try:
        from backend.services.activity_events_service import emit
        emit(
            "click_mn2_instant",
            user_id=user_id,
            channel="game",
            text=f"+{amount} MN2 instant ({action})",
            payload={"amount_mn2": amount, "action": action, "instant": True, "reference": ref},
        )
    except Exception:
        pass

    return {
        "success": True,
        "instant": True,
        "amount_mn2": amount,
        "balance_mn2": balance_mn2,
        "tx_id": ref,
        "action": action,
        "duplicate": bool(result.get("duplicate")),
        "currency": "MN2",
    }


def click_reward_quote(action: str = "click", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = _load_click_cfg()
    amt = _calc_amount(action, metadata or {}, cfg)
    return {
        "success": True,
        "action": action,
        "amount_mn2": amt,
        "instant": bool(cfg.get("instant", True)),
        "currency": "MN2",
        "config": {k: cfg[k] for k in ("base_per_click_mn2", "critical_multiplier", "daily_cap_mn2") if k in cfg},
    }
