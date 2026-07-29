"""MN2 + coins rewards for AI-routed agent actions (chat, debugger, feedback)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DAILY_FILE = os.path.join(_BASE, "data", "agent_crypto_daily.json")


def _iso_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_rewards_config() -> Dict[str, Any]:
    try:
        from backend.services.monetization_config_service import _load_raw

        raw = _load_raw() or {}
        block = raw.get("agent_ai_rewards") or {}
        return block if isinstance(block, dict) else {}
    except Exception:
        return {}


def _action_rates(action: str) -> Dict[str, float]:
    cfg = _load_rewards_config()
    actions = cfg.get("actions") if isinstance(cfg.get("actions"), dict) else {}
    row = actions.get(action) if isinstance(actions.get(action), dict) else {}
    return {
        "mn2": float(row.get("mn2") or 0),
        "coins": float(row.get("coins") or 0),
    }


def _load_daily() -> Dict[str, Any]:
    if not os.path.isfile(_DAILY_FILE):
        return {"days": {}}
    try:
        with open(_DAILY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"days": {}}
    except Exception:
        return {"days": {}}


def _save_daily(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_DAILY_FILE), exist_ok=True)
    tmp = _DAILY_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _DAILY_FILE)


def public_rewards_info() -> Dict[str, Any]:
    cfg = _load_rewards_config()
    actions = cfg.get("actions") if isinstance(cfg.get("actions"), dict) else {}
    actions_mn2 = {
        k: float((v or {}).get("mn2") or 0)
        for k, v in actions.items()
        if isinstance(v, dict)
    }
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "daily_cap_mn2": float(cfg.get("daily_cap_mn2") or 0),
        "actions_mn2": actions_mn2,
        "actions": actions,
    }


def award_agent_action(
    user_id: str,
    action: str,
    *,
    reference: Optional[str] = None,
    success: bool = True,
) -> Dict[str, Any]:
    from backend.services.mn2_earn_auth import require_earn_user

    if not success:
        return {"success": False, "error": "action_not_successful"}
    ok, uid_or_err = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid_or_err}

    user_id = uid_or_err
    cfg = _load_rewards_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "rewards_disabled"}

    rates = _action_rates(action)
    mn2_amt = float(rates.get("mn2") or 0)
    coins_amt = float(rates.get("coins") or 0)
    if mn2_amt <= 0 and coins_amt <= 0:
        return {"success": False, "error": "unknown_action"}

    ref = (reference or f"{action}:{user_id}:{_iso_day()}").strip()
    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry

    meta = {"reference": ref, "action": action}
    if mn2_amt > 0:
        result = unified_points_db.add_points(
            user_id, "mn2_balance", mn2_amt, source=f"agent_{action}", metadata=meta,
        )
        if not result.get("success"):
            return result
        if result.get("duplicate"):
            return {"success": True, "duplicate": True, "mn2_awarded": 0.0, "coins_awarded": 0}
        append_entry(
            user_id=user_id,
            entry_type=f"agent_{action}",
            amount=mn2_amt,
            txid=ref,
            metadata=meta,
        )

    if coins_amt > 0:
        unified_points_db.add_points(
            user_id, "coins", coins_amt, source=f"agent_{action}", metadata=meta,
        )

    day = _iso_day()
    daily = _load_daily()
    days = daily.setdefault("days", {})
    user_day = days.setdefault(day, {}).setdefault(user_id, {"mn2": 0.0, "actions": []})
    user_day["mn2"] = round(float(user_day.get("mn2") or 0) + mn2_amt, 8)
    user_day.setdefault("actions", []).append({"action": action, "reference": ref, "mn2": mn2_amt})
    _save_daily(daily)

    return {
        "success": True,
        "mn2_awarded": mn2_amt,
        "coins_awarded": coins_amt,
        "action": action,
        "reference": ref,
    }
