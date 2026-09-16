"""
Generator crypto (MN2) rewards — finish bonus + multi-AI, daily-first, staking bonuses.

Credits mn2_balance via unified_points_database + mn2_ledger (same path as generator_mn2_service).
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DAILY_FILE = os.path.join(_BASE, "data", "generator_crypto_daily.json")


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


def _crypto_cfg() -> Dict[str, Any]:
    try:
        from backend.services.generator_mn2_service import get_generator_config
        cfg = get_generator_config()
    except Exception:
        cfg = {}
    defaults = {
        "multi_ai_per_provider_mn2": 0.001,
        "multi_ai_cap_mn2": 0.005,
        "daily_first_video_mn2": 0.01,
        "staking_bonus_percent_per_1000_mn2": 0.5,
        "staking_bonus_cap_percent": 15.0,
    }
    extra = cfg.get("crypto_rewards") if isinstance(cfg.get("crypto_rewards"), dict) else {}
    defaults.update(extra)
    return defaults


def _staking_bonus_percent(user_id: str) -> float:
    """Extra MN2 earn % based on staked balance."""
    try:
        from backend.services.mn2_staking_service import get_balances
        _, staked = get_balances(str(user_id))
        staked = float(staked or 0)
    except Exception:
        staked = 0.0
    c = _crypto_cfg()
    per_1k = float(c.get("staking_bonus_percent_per_1000_mn2") or 0.5)
    cap = float(c.get("staking_bonus_cap_percent") or 15.0)
    pct = min(cap, (staked / 1000.0) * per_1k)
    return round(pct, 4)


def _daily_first_available(user_id: str) -> bool:
    with _LOCK:
        daily = _read_json(_DAILY_FILE)
        key = f"{user_id}:{_today_utc()}"
        return not bool(daily.get(key))


def _mark_daily_first(user_id: str, doc_id: str) -> None:
    with _LOCK:
        daily = _read_json(_DAILY_FILE)
        key = f"{user_id}:{_today_utc()}"
        daily[key] = {"doc_id": doc_id, "at": _iso()}
        _write_json(_DAILY_FILE, daily)


def _compute_breakdown(user_id: str, doc_id: str, config: Optional[Dict[str, Any]]) -> Dict[str, float]:
    cfg = config or {}
    c = _crypto_cfg()
    breakdown: Dict[str, float] = {}

    providers: List[str] = list(cfg.get("_providers_used") or [])
    if len(providers) >= 2:
        per = float(c.get("multi_ai_per_provider_mn2") or 0.001)
        cap = float(c.get("multi_ai_cap_mn2") or 0.005)
        bonus = min(cap, per * (len(providers) - 1))
        if bonus > 0:
            breakdown["multi_ai"] = round(bonus, 8)

    daily_amt = float(c.get("daily_first_video_mn2") or 0.01)
    if daily_amt > 0 and _daily_first_available(str(user_id)):
        breakdown["daily_first"] = round(daily_amt, 8)

    return breakdown


def award_generator_crypto_rewards(
    user_id: str,
    doc_id: str,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Award MN2 on video completion: base finish bonus + crypto extras.
    Returns {success, total_mn2, breakdown, base_mn2, extra_mn2}.
    """
    from backend.services.generator_mn2_service import award_finish_bonus

    cfg = config or {}
    breakdown: Dict[str, float] = {}

    base_result = award_finish_bonus(user_id, doc_id, cfg)
    base_mn2 = float(base_result.get("awarded") or 0.0)
    if base_mn2 > 0:
        breakdown["base_finish"] = base_mn2

    if not base_result.get("success", True) and base_result.get("error"):
        return {
            "success": False,
            "error": base_result.get("error"),
            "total_mn2": base_mn2,
            "breakdown": breakdown,
            "base_mn2": base_mn2,
            "extra_mn2": 0.0,
        }

    extra_breakdown = _compute_breakdown(user_id, doc_id, cfg)
    breakdown.update(extra_breakdown)

    subtotal_for_stake = base_mn2 + sum(
        v for k, v in extra_breakdown.items() if k in ("multi_ai", "daily_first")
    )
    stake_pct = _staking_bonus_percent(user_id)
    if stake_pct > 0 and subtotal_for_stake > 0:
        staking_bonus = round(subtotal_for_stake * (stake_pct / 100.0), 8)
        if staking_bonus > 0:
            breakdown["staking"] = staking_bonus

    extra_to_credit = round(
        sum(v for k, v in breakdown.items() if k != "base_finish"),
        8,
    )

    if extra_to_credit > 0:
        try:
            from backend.services.generator_mn2_service import _credit, _load_charges, _save_charges
            meta = {
                "doc_id": doc_id,
                "breakdown": {k: v for k, v in breakdown.items() if k != "base_finish"},
                "source": "generator_crypto_bonus",
                "reference": f"gen-crypto:{doc_id}",
            }
            if not _credit(str(user_id), extra_to_credit, "generator_crypto_bonus", meta):
                extra_to_credit = 0.0
                for k in ("multi_ai", "daily_first", "staking"):
                    breakdown.pop(k, None)
            else:
                if "daily_first" in breakdown:
                    _mark_daily_first(str(user_id), doc_id)
                charges = _load_charges()
                rec = charges.get(doc_id) or {"user_id": user_id}
                rec["crypto_extra"] = extra_to_credit
                rec["crypto_breakdown"] = breakdown
                charges[doc_id] = rec
                _save_charges(charges)
        except Exception:
            extra_to_credit = 0.0

    total = round(base_mn2 + extra_to_credit, 8)
    return {
        "success": True,
        "total_mn2": total,
        "base_mn2": base_mn2,
        "extra_mn2": extra_to_credit,
        "breakdown": breakdown,
        "staking_bonus_percent": stake_pct,
        "doc_id": doc_id,
    }


def public_crypto_rewards_info() -> Dict[str, Any]:
    """Public rates for generator UI."""
    c = _crypto_cfg()
    try:
        from backend.services.generator_mn2_service import get_generator_config
        gen = get_generator_config()
        base = float(gen.get("earn_on_finish_mn2") or 0.005)
    except Exception:
        base = 0.005
    return {
        "success": True,
        "currency": "MN2",
        "base_finish_mn2": base,
        "multi_ai_per_provider_mn2": c.get("multi_ai_per_provider_mn2"),
        "multi_ai_cap_mn2": c.get("multi_ai_cap_mn2"),
        "daily_first_video_mn2": c.get("daily_first_video_mn2"),
        "staking_bonus_note": "+0.5% earn per 1000 MN2 staked (cap 15%)",
    }
