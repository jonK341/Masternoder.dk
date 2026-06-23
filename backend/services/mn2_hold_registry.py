"""
MN2 clearance hold registry — single view of non-withdrawable MN2 per user.

Aggregates on-ramp holds, P2P buyer holds, and optional pending balance commits.
"""
from __future__ import annotations

from typing import Any, Dict, List


def _onramp_held(user_id: str) -> float:
    try:
        from backend.services.mn2_onramp_service import held_amount

        return round(float(held_amount(user_id) or 0), 8)
    except Exception:
        return 0.0


def _p2p_held(user_id: str) -> float:
    try:
        from backend.services.mn2_p2p_service import buyer_held

        return round(float(buyer_held(user_id) or 0), 8)
    except Exception:
        return 0.0


def _pending_commit_held(user_id: str) -> float:
    try:
        from backend.services.mn2_balance_commit import pending_amount_for_user

        return round(float(pending_amount_for_user(user_id) or 0), 8)
    except Exception:
        return 0.0


def get_holds(user_id: str) -> Dict[str, Any]:
    """Return hold breakdown and withdrawable liquid MN2."""
    uid = str(user_id or "").strip()
    onramp = _onramp_held(uid)
    p2p = _p2p_held(uid)
    pending = _pending_commit_held(uid)
    total_held = round(onramp + p2p + pending, 8)

    liquid = 0.0
    try:
        from backend.services.mn2_wallet_service import get_balance

        bal = get_balance(uid)
        if bal.get("success"):
            liquid = round(float(bal.get("mn2_balance") or 0), 8)
    except Exception:
        pass

    staked = 0.0
    try:
        from backend.services.unified_points_database import unified_points_db

        pts = unified_points_db.get_all_points(uid)
        systems = pts.get("systems") if isinstance(pts.get("systems"), dict) else {}
        staked = round(float(systems.get("mn2_staked") or pts.get("points", {}).get("mn2_staked") or 0), 8)
    except Exception:
        pass

    withdrawable = round(max(0.0, liquid - total_held), 8)
    holds: List[Dict[str, Any]] = []
    if onramp > 0:
        holds.append({"reason": "onramp_clearance", "amount_mn2": onramp})
    if p2p > 0:
        holds.append({"reason": "p2p_buyer_hold", "amount_mn2": p2p})
    if pending > 0:
        holds.append({"reason": "pending_balance_commit", "amount_mn2": pending})

    return {
        "user_id": uid,
        "liquid_mn2": liquid,
        "held_mn2": total_held,
        "withdrawable_mn2": withdrawable,
        "staked_mn2": staked,
        "holds": holds,
    }


def assert_withdrawable(user_id: str, amount: float) -> Dict[str, Any]:
    """Return {allowed: bool, error?, code?, ...} for a withdrawal amount."""
    h = get_holds(user_id)
    amt = float(amount or 0)
    if amt <= 0:
        return {"allowed": False, "error": "amount must be positive", "code": "invalid_amount"}
    if amt > h["withdrawable_mn2"]:
        return {
            "allowed": False,
            "error": (
                f"{h['held_mn2']:.4f} MN2 is in clearance hold and cannot be withdrawn yet "
                f"(withdrawable: {h['withdrawable_mn2']:.4f} MN2)."
            ),
            "code": "hold_blocked",
            "held_mn2": h["held_mn2"],
            "withdrawable_mn2": h["withdrawable_mn2"],
            "holds": h["holds"],
        }
    return {"allowed": True, **h}
