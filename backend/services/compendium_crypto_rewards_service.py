"""
Compendium / rulebook crypto (MN2) rewards — page reads and theory study.

Credits mn2_balance via game_mn2_rewards.credit_mn2 (idempotent references).
Config: data/mn2_config.json -> compendium
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DAILY_FILE = os.path.join(_BASE, "data", "compendium_crypto_daily.json")
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


def _compendium_cfg() -> Dict[str, Any]:
    raw = _read_json(_MN2_CONFIG).get("compendium") or {}
    defaults: Dict[str, Any] = {
        "enabled": True,
        "earn_on_page_read_mn2": 0.0005,
        "earn_on_theory_study_mn2": 0.001,
        "daily_first_study_mn2": 0.005,
        "daily_cap_mn2": 0.1,
        "staking_bonus_percent_per_1000_mn2": 0.5,
        "staking_bonus_cap_percent": 15.0,
    }
    defaults.update(raw)
    return defaults


def _daily_total(user_id: str) -> float:
    with _LOCK:
        daily = _read_json(_DAILY_FILE)
        key = f"{user_id}:{_today_utc()}"
        return float(daily.get(key, {}).get("total_mn2", 0) or 0)


def _add_daily_total(user_id: str, amount: float) -> None:
    with _LOCK:
        daily = _read_json(_DAILY_FILE)
        key = f"{user_id}:{_today_utc()}"
        rec = daily.get(key) or {"total_mn2": 0.0, "events": []}
        rec["total_mn2"] = round(float(rec.get("total_mn2", 0)) + amount, 8)
        rec["events"] = (rec.get("events") or [])[-50:]
        rec["events"].append({"amount": amount, "at": _iso()})
        daily[key] = rec
        _write_json(_DAILY_FILE, daily)


def _staking_bonus_percent(user_id: str) -> float:
    try:
        from backend.services.mn2_staking_service import get_balances
        _, staked = get_balances(str(user_id))
        staked = float(staked or 0)
    except Exception:
        staked = 0.0
    c = _compendium_cfg()
    per_1k = float(c.get("staking_bonus_percent_per_1000_mn2") or 0.5)
    cap = float(c.get("staking_bonus_cap_percent") or 15.0)
    return round(min(cap, (staked / 1000.0) * per_1k), 4)


def _credit_reward(
    user_id: str,
    amount: float,
    source: str,
    reference: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    cfg = _compendium_cfg()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "compendium_rewards_disabled"}
    amt = float(amount or 0)
    if amt <= 0:
        return {"success": False, "error": "zero_amount"}

    cap = float(cfg.get("daily_cap_mn2") or 0.1)
    if cap > 0 and _daily_total(user_id) + amt > cap:
        return {"success": False, "error": "daily_cap_reached", "daily_cap_mn2": cap}

    stake_pct = _staking_bonus_percent(user_id)
    if stake_pct > 0:
        bonus = round(amt * (stake_pct / 100.0), 8)
        if bonus > 0:
            amt = round(amt + bonus, 8)

    from backend.services.game_mn2_rewards import credit_mn2

    meta = dict(metadata or {})
    meta["staking_bonus_percent"] = stake_pct
    result = credit_mn2(user_id, amt, source=source, reference=reference, metadata=meta)
    if result.get("success") and not result.get("duplicate"):
        _add_daily_total(user_id, amt)
    if result.get("success"):
        result["awarded_mn2"] = amt
    return result


def get_crypto_rewards_info(user_id: str) -> Dict[str, Any]:
    cfg = _compendium_cfg()
    return {
        "success": True,
        "enabled": cfg.get("enabled", True),
        "rates": {
            "page_read_mn2": cfg.get("earn_on_page_read_mn2"),
            "theory_study_mn2": cfg.get("earn_on_theory_study_mn2"),
            "daily_first_study_mn2": cfg.get("daily_first_study_mn2"),
        },
        "daily_cap_mn2": cfg.get("daily_cap_mn2"),
        "daily_earned_mn2": _daily_total(user_id),
        "staking_bonus_percent": _staking_bonus_percent(user_id),
        "note": "Page read MN2 is once per compendium page. Theory study MN2 is once per theory.",
    }


def award_page_read_reward(user_id: str, page_number: int) -> Dict[str, Any]:
    cfg = _compendium_cfg()
    base = float(cfg.get("earn_on_page_read_mn2") or 0.0005)
    amt = base

    with _LOCK:
        daily = _read_json(_DAILY_FILE)
        first_key = f"first_study:{user_id}:{_today_utc()}"
        if not daily.get(first_key):
            extra = float(cfg.get("daily_first_study_mn2") or 0.005)
            if extra > 0:
                amt = round(amt + extra, 8)
            daily[first_key] = {"page_number": page_number, "at": _iso()}
            _write_json(_DAILY_FILE, daily)

    return _credit_reward(
        user_id,
        amt,
        "compendium_page_read",
        f"compendium-page:{user_id}:{page_number}",
        {"page_number": page_number, "action": "page_read"},
    )


def award_theory_study_reward(user_id: str, theory_id: str) -> Dict[str, Any]:
    cfg = _compendium_cfg()
    amt = float(cfg.get("earn_on_theory_study_mn2") or 0.001)
    return _credit_reward(
        user_id,
        amt,
        "compendium_theory_study",
        f"compendium-theory:{user_id}:{theory_id}",
        {"theory_id": theory_id, "action": "theory_study"},
    )
