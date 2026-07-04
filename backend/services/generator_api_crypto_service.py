"""
Generator API crypto profile — MN2 rewards for metered API usage and external integrations.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DAILY_FILE = os.path.join(_BASE, "data", "generator_api_crypto_daily.json")

DEFAULT_REWARDS = {
    "per_job_mn2": 0.002,
    "daily_cap_mn2": 0.05,
    "integration_bonus_mn2": 0.001,
    "external_link_reward_mn2": 0.0005,
}


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _read_daily() -> Dict[str, Any]:
    if not os.path.isfile(_DAILY_FILE):
        return {}
    try:
        with open(_DAILY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_daily(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_DAILY_FILE), exist_ok=True)
    tmp = _DAILY_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _DAILY_FILE)


def _rewards_cfg() -> Dict[str, Any]:
    cfg = dict(DEFAULT_REWARDS)
    try:
        from backend.services.monetization_config_service import reload_monetization_config

        raw = reload_monetization_config()
        block = raw.get("generator_api_crypto_rewards")
        if isinstance(block, dict):
            cfg.update(block)
    except Exception:
        pass
    return cfg


def list_external_integrations() -> List[Dict[str, Any]]:
    """Programs that can call the Generator API and earn MN2 for linked usage."""
    try:
        from backend.services.monetization_config_service import reload_monetization_config

        raw = reload_monetization_config()
        rows = raw.get("generator_api_integrations")
        if isinstance(rows, list) and rows:
            return [dict(r) for r in rows if isinstance(r, dict)]
    except Exception:
        pass
    return [
        {
            "id": "discord-bot",
            "name": "Discord bot bridge",
            "docs_url": "/docs/API_DOCUMENTATION.md",
            "reward_mn2_per_call": 0.0005,
            "status": "beta",
        },
        {
            "id": "mobile-twa",
            "name": "Google Play TWA shell",
            "docs_url": "/docs/PODCAST.md",
            "reward_mn2_per_call": 0.0005,
            "status": "planned",
        },
        {
            "id": "studio-webhook",
            "name": "Studio Cash Rail webhook",
            "docs_url": "/docs/MONETIZATION_PAYPAL.md",
            "reward_mn2_per_call": 0.001,
            "status": "live",
        },
    ]


def get_crypto_rewards_info(user_id: Optional[str] = None) -> Dict[str, Any]:
    cfg = _rewards_cfg()
    uid = (user_id or "").strip()
    earned_today = 0.0
    if uid:
        with _LOCK:
            earned_today = float((_read_daily().get(uid) or {}).get(_today()) or 0)
    return {
        "success": True,
        "user_id": uid or None,
        "per_job_mn2": float(cfg.get("per_job_mn2") or 0),
        "daily_cap_mn2": float(cfg.get("daily_cap_mn2") or 0),
        "integration_bonus_mn2": float(cfg.get("integration_bonus_mn2") or 0),
        "external_link_reward_mn2": float(cfg.get("external_link_reward_mn2") or 0),
        "earned_today_mn2": round(earned_today, 6),
        "integrations": list_external_integrations(),
    }


def get_api_crypto_profile(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id_required"}
    try:
        from backend.services.generator_api_key_service import get_user_api_status, list_public_tiers

        api_status = get_user_api_status(uid)
        tiers = list_public_tiers()
    except Exception as exc:
        return {"success": False, "error": str(exc)[:200]}
    mn2_balance = 0.0
    mn2_staked = 0.0
    try:
        from backend.services.mn2_staking_service import get_balances

        mn2_balance, mn2_staked = get_balances(uid)
    except Exception:
        pass
    rewards = get_crypto_rewards_info(uid)
    return {
        "success": True,
        "user_id": uid,
        "api": api_status,
        "tiers_catalog": tiers.get("tiers") or [],
        "mn2_balance": round(float(mn2_balance or 0), 6),
        "mn2_staked": round(float(mn2_staked or 0), 6),
        "crypto_rewards": rewards,
        "payment_rails": ["coins", "mn2", "paypal", "mn2_onchain"],
        "profile_url": "/profile#generator-api",
    }


def credit_api_job_reward(
    user_id: str,
    *,
    job_id: Optional[str] = None,
    integration_id: Optional[str] = None,
) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id_required"}
    cfg = _rewards_cfg()
    amount = float(cfg.get("per_job_mn2") or 0)
    if integration_id:
        amount += float(cfg.get("integration_bonus_mn2") or 0)
    cap = float(cfg.get("daily_cap_mn2") or 0)
    if amount <= 0:
        return {"success": False, "error": "rewards_disabled"}
    with _LOCK:
        daily = _read_daily()
        user_day = daily.setdefault(uid, {})
        today_key = _today()
        earned = float(user_day.get(today_key) or 0)
        if cap > 0 and earned >= cap:
            return {
                "success": False,
                "error": "daily_cap_reached",
                "daily_cap_mn2": cap,
                "earned_today_mn2": earned,
            }
        grant = min(amount, cap - earned) if cap > 0 else amount
        if grant <= 0:
            return {"success": False, "error": "daily_cap_reached"}
        user_day[today_key] = round(earned + grant, 6)
        daily[uid] = user_day
        _write_daily(daily)
    try:
        from backend.services.unified_points_database import unified_points_db

        unified_points_db.add_points(
            user_id=uid,
            point_type="mn2_balance",
            amount=grant,
            source="generator_api_crypto",
            metadata={"job_id": job_id, "integration_id": integration_id},
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)[:200]}
    return {
        "success": True,
        "mn2_granted": round(grant, 6),
        "job_id": job_id,
        "integration_id": integration_id,
    }
