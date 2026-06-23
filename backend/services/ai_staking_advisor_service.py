"""M7 Staking Yield Advisor — informational forecasts, no auto stake/unstake."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CACHE = os.path.join(_BASE, "data", "ai_staking_advisor_cache.json")
_DECISIONS = os.path.join(_BASE, "data", "ai_monetization_decisions.jsonl")
_DISCLAIMER = (
    "Informational only. This does not move funds. Stake/unstake only via your wallet controls."
)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_cache() -> dict:
    if not os.path.isfile(_CACHE):
        return {}
    try:
        with open(_CACHE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _write_cache(data: dict) -> None:
    os.makedirs(os.path.dirname(_CACHE), exist_ok=True)
    tmp = _CACHE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _CACHE)


def _log_decision(user_id: str, decision: dict) -> None:
    os.makedirs(os.path.dirname(_DECISIONS), exist_ok=True)
    row = {"ts": _iso(), "wave": "M7", "user_id": user_id, **decision}
    with open(_DECISIONS, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")


def refresh_advice(user_id: str) -> Dict[str, Any]:
    from backend.services.mn2_staking_service import get_balances, longevity_tier, get_config

    liquid, staked = get_balances(user_id)
    cfg = get_config()
    base_apr = float(cfg.get("target_apr_percent") or cfg.get("apr_percent") or 12.0) / 100.0
    tier = longevity_tier(0)
    projected_apr = base_apr * float(tier.get("multiplier") or 1.0)

    if staked <= 0 and liquid >= float(cfg.get("min_stake") or 0.1):
        recommendation = "consider_stake"
        rationale = f"You have {liquid:.4f} MN2 liquid. Staking could earn ~{projected_apr*100:.1f}% APR."
    elif staked > 0 and liquid < float(cfg.get("min_stake") or 0.1):
        recommendation = "hold"
        rationale = f"You already stake {staked:.4f} MN2. Keep rig active for longevity bonus."
    else:
        recommendation = "hold"
        rationale = "Maintain current stake; monitor pool APR and longevity tier."

    advice = {
        "recommendation": recommendation,
        "projected_apr": round(projected_apr, 4),
        "longevity_tier": tier,
        "liquid_mn2": liquid,
        "staked_mn2": staked,
        "rationale": rationale,
        "disclaimer": _DISCLAIMER,
        "cached_at": _iso(),
    }
    cache = _read_cache()
    cache[user_id] = advice
    _write_cache(cache)
    _log_decision(user_id, {"recommendation": recommendation, "projected_apr": projected_apr})
    return {"success": True, **advice}


def get_advice(user_id: str) -> Dict[str, Any]:
    cache = _read_cache()
    row = cache.get(user_id)
    if row:
        return {"success": True, **row}
    return refresh_advice(user_id)
