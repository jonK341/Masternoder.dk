"""
MN2 + coins rewards for agent and AI-assisted user actions.

Config: data/mn2_config.json -> agent_rewards (rates, daily cap).
Credits via game_mn2_rewards.credit_mn2 + unified_points_database (idempotent references).
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DAILY_FILE = os.path.join(_BASE, "data", "agent_crypto_daily.json")
_MN2_CONFIG = os.path.join(_BASE, "data", "mn2_config.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _read_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _agent_rewards_cfg() -> Dict[str, Any]:
    raw = _read_json(_MN2_CONFIG).get("agent_rewards") or {}
    defaults: Dict[str, Any] = {
        "enabled": True,
        "daily_cap_mn2": 0.5,
        "action_rewards_mn2": {
            "routed_chat": 0.002,
            "llm_insight": 0.003,
            "debugger_task_complete": 0.0005,
            "debugger_task_ai": 0.001,
            "feedback_outcome": 0.0003,
            "agent_orchestrator": 0.001,
            "research_rotation_insight": 0.002,
            "cron_ai_summary": 0.001,
            "evaluate_output": 0.0004,
            "first_post": 0.001,
            "post_created": 0.0003,
            "like_received": 0.0002,
        },
        "action_rewards_coins": {
            "routed_chat": 5,
            "llm_insight": 8,
            "debugger_task_complete": 2,
            "debugger_task_ai": 4,
            "feedback_outcome": 2,
            "agent_orchestrator": 3,
            "research_rotation_insight": 5,
            "cron_ai_summary": 3,
            "evaluate_output": 2,
            "first_post": 3,
            "post_created": 1,
            "like_received": 1,
        },
    }
    if isinstance(raw.get("action_rewards_mn2"), dict):
        defaults["action_rewards_mn2"].update(raw["action_rewards_mn2"])
    if isinstance(raw.get("action_rewards_coins"), dict):
        defaults["action_rewards_coins"].update(raw["action_rewards_coins"])
    for k in ("enabled", "daily_cap_mn2"):
        if k in raw:
            defaults[k] = raw[k]
    return defaults


def _daily_mn2_used(user_id: str) -> float:
    with _LOCK:
        daily = _read_json(_DAILY_FILE)
        row = daily.get(f"{user_id}:{_today_utc()}") or {}
        return float(row.get("mn2") or 0)


def _record_daily_mn2(user_id: str, amount: float) -> None:
    with _LOCK:
        daily = _read_json(_DAILY_FILE)
        key = f"{user_id}:{_today_utc()}"
        row = daily.get(key) or {"mn2": 0.0, "events": []}
        row["mn2"] = round(float(row.get("mn2") or 0) + amount, 8)
        events = list(row.get("events") or [])
        events.append({"at": _iso(), "amount": amount})
        row["events"] = events[-50:]
        daily[key] = row
        _write_json(_DAILY_FILE, daily)


def get_reward_amount(action: str) -> Dict[str, float]:
    cfg = _agent_rewards_cfg()
    mn2 = float((cfg.get("action_rewards_mn2") or {}).get(action) or 0)
    coins = float((cfg.get("action_rewards_coins") or {}).get(action) or 0)
    return {"mn2": mn2, "coins": coins}


def award_agent_action(
    user_id: str,
    action: str,
    *,
    reference: str,
    metadata: Optional[Dict[str, Any]] = None,
    require_success: bool = True,
    success: bool = True,
) -> Dict[str, Any]:
    """
    Idempotent MN2/coins grant for an agent or AI-assisted action.
    reference must be unique per award (e.g. trace_id, task_id+day).
    """
    if require_success and not success:
        return {"success": False, "skipped": "action_not_successful"}

    cfg = _agent_rewards_cfg()
    if not cfg.get("enabled", True):
        return {"success": False, "skipped": "agent_rewards_disabled"}

    rates = get_reward_amount(action)
    mn2_amt = rates["mn2"]
    coins_amt = int(rates["coins"])
    if mn2_amt <= 0 and coins_amt <= 0:
        return {"success": False, "skipped": "no_reward_configured", "action": action}

    cap = float(cfg.get("daily_cap_mn2") or 0)
    if mn2_amt > 0 and cap > 0:
        used = _daily_mn2_used(str(user_id))
        if used >= cap:
            mn2_amt = 0.0
        elif used + mn2_amt > cap:
            mn2_amt = round(max(0.0, cap - used), 8)

    out: Dict[str, Any] = {
        "success": True,
        "action": action,
        "reference": reference,
        "mn2_awarded": 0.0,
        "coins_awarded": 0,
    }

    meta = dict(metadata or {})
    meta["action"] = action

    if mn2_amt > 0:
        from backend.services.game_mn2_rewards import credit_mn2

        src = f"agent_ai_{action}"
        cr = credit_mn2(
            user_id,
            mn2_amt,
            source=src,
            reference=reference,
            metadata=meta,
        )
        if cr.get("success") and not cr.get("duplicate"):
            _record_daily_mn2(str(user_id), mn2_amt)
            out["mn2_awarded"] = mn2_amt
        elif cr.get("duplicate"):
            out["duplicate"] = True
            out["mn2_awarded"] = 0.0
        else:
            out["success"] = False
            out["error"] = cr.get("error", "mn2_credit_failed")
            return out

    if coins_amt > 0:
        try:
            from backend.services.mn2_earn_auth import require_earn_user
            from backend.services.unified_points_database import unified_points_db

            ok, uid_or_err = require_earn_user(user_id)
            if ok:
                coin_ref = f"coins:{reference}"
                coin_meta = {**meta, "reference": coin_ref, "source": f"agent_ai_{action}"}
                cr_coins = unified_points_db.add_points(
                    uid_or_err,
                    "coins",
                    coins_amt,
                    source=f"agent_ai_{action}",
                    metadata=coin_meta,
                )
                if cr_coins.get("success") and not cr_coins.get("duplicate"):
                    out["coins_awarded"] = coins_amt
                elif cr_coins.get("duplicate"):
                    out.setdefault("duplicate", True)
        except Exception as e:
            out["coins_error"] = str(e)[:120]

    if out.get("mn2_awarded", 0) > 0 or out.get("coins_awarded", 0) > 0:
        try:
            from backend.services.activity_events_service import emit

            emit(
                "agent_ai_reward",
                user_id=str(user_id),
                channel="agents",
                text=f"+{out.get('mn2_awarded', 0)} MN2, +{out.get('coins_awarded', 0)} coins ({action})",
                payload={
                    "action": action,
                    "mn2": out.get("mn2_awarded", 0),
                    "coins": out.get("coins_awarded", 0),
                    "reference": reference,
                },
            )
        except Exception:
            pass

    return out


def public_rewards_info() -> Dict[str, Any]:
    cfg = _agent_rewards_cfg()
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "daily_cap_mn2": cfg.get("daily_cap_mn2"),
        "actions_mn2": cfg.get("action_rewards_mn2") or {},
        "actions_coins": cfg.get("action_rewards_coins") or {},
        "currency": "MN2",
    }
