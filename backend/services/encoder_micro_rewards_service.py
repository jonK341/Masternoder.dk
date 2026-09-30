"""Attach configurable micro MN2 rewards during encoder customer fulfillment."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Union

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MN2_CFG = os.path.join(_BASE, "data", "mn2_config.json")

_ENCODER_ACTIONS = {
    "encoder_fulfillment": 0.0005,
    "customer_onboard": 0.0003,
}


def _fulfillment_cfg() -> Dict[str, Any]:
    try:
        with open(_MN2_CFG, "r", encoding="utf-8") as f:
            root = json.load(f)
        block = root.get("encoder_customer_fulfillment") if isinstance(root, dict) else {}
        return block if isinstance(block, dict) else {}
    except Exception:
        return {}


def _normalize_reward_item(item: Union[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if isinstance(item, str):
        action = item.strip()
        if not action:
            return None
        return {"action": action}
    if isinstance(item, dict):
        action = str(item.get("action") or "").strip()
        if not action:
            return None
        row = {"action": action}
        if item.get("mn2") is not None:
            row["mn2"] = float(item.get("mn2") or 0)
        if item.get("enabled") is False:
            return None
        return row
    return None


def default_micro_reward_actions() -> List[str]:
    """Configured micro-reward actions for encoder fulfillment."""
    cfg = _fulfillment_cfg()
    raw = cfg.get("micro_rewards")
    if isinstance(raw, list) and raw:
        actions: List[str] = []
        for item in raw:
            row = _normalize_reward_item(item)
            if row:
                actions.append(row["action"])
        if actions:
            return actions
    legacy = str(cfg.get("aggregator_action") or "discord_welcome").strip()
    return [legacy] if legacy else ["discord_welcome"]


def list_attachable_micro_rewards() -> Dict[str, Any]:
    """Catalog of micro rewards ops can attach during encoder fulfillment."""
    from backend.services.aggregator_mn2_service import get_config

    agg = get_config()
    rewards = dict(agg.get("action_rewards_mn2") or {})
    rewards.update(_ENCODER_ACTIONS)
    default_reward = float(agg.get("default_reward_mn2") or 0.00005)
    daily_cap = float(agg.get("daily_cap_mn2") or 0.25)

    cfg = _fulfillment_cfg()
    bonus_mn2 = float(cfg.get("bonus_mn2") or 0)
    selected = default_micro_reward_actions()

    catalog: List[Dict[str, Any]] = []
    for action, amount in sorted(rewards.items(), key=lambda kv: kv[0]):
        catalog.append({
            "action": action,
            "mn2": round(float(amount or 0), 8),
            "selected_default": action in selected,
        })

    if bonus_mn2 > 0:
        catalog.append({
            "action": "encoder_bonus",
            "mn2": round(bonus_mn2, 8),
            "selected_default": bool(cfg.get("attach_bonus_mn2", True)),
            "kind": "direct_bonus",
        })

    return {
        "success": True,
        "default_actions": selected,
        "daily_cap_mn2": daily_cap,
        "default_reward_mn2": default_reward,
        "bonus_mn2": bonus_mn2,
        "rewards": catalog,
    }


def _reward_amount(action: str, override: Optional[float], agg_cfg: Dict[str, Any]) -> float:
    if override is not None and override > 0:
        return float(override)
    if action in _ENCODER_ACTIONS:
        return float(_ENCODER_ACTIONS[action])
    rewards = agg_cfg.get("action_rewards_mn2") or {}
    if action in rewards:
        return float(rewards[action] or 0)
    return float(agg_cfg.get("default_reward_mn2") or 0)


def _attach_bonus_mn2(user_id: str, amount: float, meta: Dict[str, Any]) -> Dict[str, Any]:
    amt = round(float(amount or 0), 8)
    if amt <= 0:
        return {"success": True, "skipped": "zero_bonus", "mn2_awarded": 0.0}

    from backend.services.aggregator_mn2_service import _credit

    full_meta = {
        "action": "encoder_bonus",
        "source": "encoder_micro_rewards",
        **meta,
    }
    if not _credit(user_id, amt, full_meta):
        return {"success": False, "error": "bonus_credit_failed", "mn2_awarded": 0.0}
    return {"success": True, "action": "encoder_bonus", "mn2_awarded": amt, "kind": "direct_bonus"}


def attach_micro_rewards(
    user_id: str,
    *,
    actions: Optional[List[Union[str, Dict[str, Any]]]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Award a bundle of micro MN2 rewards to a customer (aggregator-capped per action)."""
    uid = str(user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id_required"}

    from backend.services.aggregator_mn2_service import award_for_action, get_config

    agg_cfg = get_config()
    if not agg_cfg.get("enabled", True):
        return {"success": True, "skipped": "aggregator_disabled", "results": [], "total_mn2_awarded": 0.0}

    raw_actions = actions if actions is not None else default_micro_reward_actions()
    parsed: List[Dict[str, Any]] = []
    for item in raw_actions:
        row = _normalize_reward_item(item)
        if row:
            parsed.append(row)

    cfg = _fulfillment_cfg()
    if cfg.get("attach_bonus_mn2", True) and float(cfg.get("bonus_mn2") or 0) > 0:
        if not any(r.get("action") == "encoder_bonus" for r in parsed):
            parsed.append({"action": "encoder_bonus", "mn2": float(cfg.get("bonus_mn2") or 0)})

    base_meta = dict(meta or {})
    base_meta.setdefault("source", "encoder_micro_rewards")

    results: List[Dict[str, Any]] = []
    total = 0.0

    for row in parsed:
        action = row["action"]
        if action == "encoder_bonus":
            res = _attach_bonus_mn2(uid, float(row.get("mn2") or cfg.get("bonus_mn2") or 0), base_meta)
        else:
            res = award_for_action(
                uid,
                action,
                meta={**base_meta, "micro_reward": True, "encoder_action": action},
            )
        results.append(res)
        if res.get("success") and float(res.get("mn2_awarded") or 0) > 0:
            total += float(res["mn2_awarded"])

    return {
        "success": True,
        "user_id": uid,
        "actions": [r.get("action") for r in parsed],
        "results": results,
        "total_mn2_awarded": round(total, 8),
        "awarded_count": sum(1 for r in results if float(r.get("mn2_awarded") or 0) > 0),
    }
