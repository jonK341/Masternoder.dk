"""
Trophy rake rebate — return a slice of house edge to trophy holders on losses.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def _config() -> Dict[str, Any]:
    try:
        from backend.services.casino_service import _load_config
        tr = (_load_config().get("trophy_rake_rebate") or {})
        return tr if isinstance(tr, dict) else {}
    except Exception:
        return {}


def _trophy_count(user_id: str) -> int:
    try:
        from backend.services.unified_points_database import unified_points_db
        pts = unified_points_db.get_all_points(str(user_id))
        systems = pts.get("systems") if isinstance(pts.get("systems"), dict) else {}
        return int(systems.get("trophies_collected") or 0)
    except Exception:
        return 0


def rebate_rate(user_id: str) -> float:
    cfg = _config()
    if not cfg.get("enabled", True):
        return 0.0
    count = _trophy_count(user_id)
    tiers = cfg.get("tiers") or []
    rate = 0.0
    if isinstance(tiers, list):
        for t in tiers:
            if not isinstance(t, dict):
                continue
            if count >= int(t.get("min_trophies") or 0):
                rate = max(rate, float(t.get("rebate_pct") or 0))
    return min(rate, float(cfg.get("max_rebate_pct") or 0.15))


def apply_rebate(user_id: str, bet: float, net: float, currency: str, game: str) -> Optional[Dict[str, Any]]:
    """Credit rebate when user lost (negative net). Returns award dict or None."""
    if float(net or 0) >= 0:
        return None
    rate = rebate_rate(user_id)
    if rate <= 0:
        return None
    loss = abs(float(net))
    rebate = round(loss * rate, 8 if currency == "mn2" else 2)
    if rebate <= 0:
        return None
    try:
        from backend.services.casino_service import _apply_balance_delta
        _apply_balance_delta(
            user_id,
            rebate,
            currency,
            game,
            {"phase": "trophy_rake_rebate", "rebate_pct": rate, "loss": loss},
        )
    except Exception:
        return None
    return {"rebate": rebate, "currency": currency, "rebate_pct": rate, "trophies": _trophy_count(user_id)}
