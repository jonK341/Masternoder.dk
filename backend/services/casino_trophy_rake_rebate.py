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


def _trophy_count(user_id: str) -> int:
    try:
        from backend.services.unified_points_database import unified_points_db
        pts = unified_points_db.get_all_points(str(user_id))
        systems = pts.get("systems") if isinstance(pts.get("systems"), dict) else {}
        return int(systems.get("trophies_collected") or 0)
    except Exception:
        return 0


def get_progress(user_id: str) -> Dict[str, Any]:
    """Visible tier progress for rank/compete UI — MN2 rake rebate tiers."""
    cfg = _config()
    count = _trophy_count(user_id)
    tiers = cfg.get("tiers") or []
    sorted_tiers = sorted(
        [t for t in tiers if isinstance(t, dict)],
        key=lambda t: int(t.get("min_trophies") or 0),
    )
    current = None
    nxt = None
    for t in sorted_tiers:
        if count >= int(t.get("min_trophies") or 0):
            current = t
        elif nxt is None:
            nxt = t
    current_pct = float(current.get("rebate_pct") or 0) if current else 0.0
    next_min = int(nxt.get("min_trophies") or 0) if nxt else None
    next_pct = float(nxt.get("rebate_pct") or 0) if nxt else None
    progress_pct = 100.0
    if nxt and next_min:
        prev_min = int(current.get("min_trophies") or 0) if current else 0
        span = max(1, next_min - prev_min)
        progress_pct = round(min(100.0, max(0.0, 100.0 * (count - prev_min) / span)), 1)
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "trophies": count,
        "current_rebate_pct": current_pct,
        "max_rebate_pct": float(cfg.get("max_rebate_pct") or 0.15),
        "current_tier": current,
        "next_tier": nxt,
        "next_tier_min_trophies": next_min,
        "next_tier_rebate_pct": next_pct,
        "progress_pct": progress_pct,
        "at_max_tier": nxt is None,
    }
