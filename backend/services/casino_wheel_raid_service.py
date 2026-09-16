"""Wheel raid boss — community spin counter triggers bonus jackpot seed (Wave 4)."""
from __future__ import annotations

import json
import os
import random
import threading
from typing import Any, Dict, Optional

_LOCK = threading.Lock()


def _cs():
    from backend.services import casino_service
    return casino_service


def _config() -> Dict[str, Any]:
    cfg = _cs()._load_config()
    block = cfg.get("wheel_raid") if isinstance(cfg.get("wheel_raid"), dict) else {}
    return {
        "enabled": bool(block.get("enabled", True)),
        "spin_threshold": int(block.get("spin_threshold") or 500),
        "bonus_seed_coins": float(block.get("bonus_seed_coins") or 2500),
        "bonus_seed_mn2": float(block.get("bonus_seed_mn2") or 0.5),
        "bonus_seed_usd": float(block.get("bonus_seed_usd") or 5.0),
        "award_last_spinner_pct": float(block.get("award_last_spinner_pct") or 0.1),
    }


def _state_path() -> str:
    d = _cs()._log_dir()
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "casino_wheel_raid.json")


def _load_state() -> Dict[str, Any]:
    path = _state_path()
    if not os.path.isfile(path):
        return {"spin_count": 0, "raids_triggered": 0, "last_spinner": None}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"spin_count": 0}
    except Exception:
        return {"spin_count": 0}


def _save_state(state: Dict[str, Any]) -> None:
    try:
        with open(_state_path(), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def get_status() -> Dict[str, Any]:
    conf = _config()
    state = _load_state()
    threshold = conf["spin_threshold"]
    count = int(state.get("spin_count") or 0)
    return {
        "success": True,
        "enabled": conf["enabled"],
        "spin_count": count,
        "spin_threshold": threshold,
        "progress_pct": round(min(100.0, 100.0 * count / threshold), 1) if threshold else 0,
        "raids_triggered": int(state.get("raids_triggered") or 0),
        "last_raid_at": state.get("last_raid_at"),
        "last_spinner": state.get("last_spinner"),
    }


def record_wheel_spin(user_id: str, currency: str = "coins") -> Optional[Dict[str, Any]]:
    """Increment community counter; trigger raid bonus when threshold hit."""
    conf = _config()
    if not conf["enabled"]:
        return None
    currency = _cs()._normalize_currency(currency)
    with _LOCK:
        state = _load_state()
        state["spin_count"] = int(state.get("spin_count") or 0) + 1
        state["last_spinner"] = {"user_id": user_id, "currency": currency}
        threshold = conf["spin_threshold"]
        raid = None
        if state["spin_count"] >= threshold:
            raid = _trigger_raid(state, user_id, currency, conf)
            state["spin_count"] = 0
            state["raids_triggered"] = int(state.get("raids_triggered") or 0) + 1
            state["last_raid_at"] = _cs()._iso()
        _save_state(state)
    return raid


def _trigger_raid(state: Dict[str, Any], user_id: str, currency: str, conf: Dict[str, Any]) -> Dict[str, Any]:
    from backend.services import casino_jackpot

    seeds = {
        "coins": conf["bonus_seed_coins"],
        "mn2": conf["bonus_seed_mn2"],
        "usd": conf["bonus_seed_usd"],
    }
    seeded: Dict[str, float] = {}
    for rail, amount in seeds.items():
        if amount > 0:
            try:
                casino_jackpot.seed_bonus(rail, amount, reason="wheel_raid_boss")
                seeded[rail] = amount
            except Exception:
                pass

    bonus_award = None
    pct = conf["award_last_spinner_pct"]
    if pct > 0 and user_id:
        bonus = seeds.get(currency) or seeds.get("coins") or 0
        award = _cs()._round_payout(bonus * pct, currency)
        if award > 0:
            _cs()._apply_balance_delta(
                user_id, award, currency, "wheel_raid",
                {"phase": "raid_bonus", "pct": pct},
            )
            bonus_award = {"user_id": user_id, "currency": currency, "amount": award}

    return {
        "raid_triggered": True,
        "jackpot_seeded": seeded,
        "last_spinner_bonus": bonus_award,
        "threshold": conf["spin_threshold"],
    }
