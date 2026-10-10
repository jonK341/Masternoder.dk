"""Debugger Top-50 Q&A quiz — server-side MN2 rewards."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from flask import Blueprint, jsonify, request

debugger_quiz_bp = Blueprint("debugger_quiz", __name__)

_MIN_CORRECT = 30
_MAX_DAILY_MN2 = 0.05
_REWARD_TIERS = (
    (90, 0.05),
    (70, 0.02),
    (50, 0.01),
)


def _iso_day(day: Optional[str] = None) -> str:
    if day and str(day).strip():
        return str(day).strip()[:10]
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _tier_reward(pct: float) -> float:
    for threshold, amt in _REWARD_TIERS:
        if pct >= threshold:
            return amt
    return 0.0


def _score_reward(correct: int, total: int) -> float:
    total = max(int(total or 0), 1)
    correct = max(0, min(int(correct or 0), total))
    ratio = correct / total
    if correct < _MIN_CORRECT or ratio < 0.6:
        return 0.0
    formula = round(min(_MAX_DAILY_MN2, 0.01 + ratio * 0.04), 8)
    tier = _tier_reward(ratio * 100.0)
    return round(min(_MAX_DAILY_MN2, max(formula, tier)), 8)


def submit_quiz(
    user_id: str,
    *,
    correct: int,
    total: int,
    day: Optional[str] = None,
) -> Tuple[Dict[str, Any], int]:
    from backend.services.mn2_earn_auth import require_earn_user

    ok, uid_or_err = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid_or_err}, 403

    user_id = uid_or_err
    quiz_day = _iso_day(day)
    total_n = max(int(total or 0), 1)
    correct_n = max(0, min(int(correct or 0), total_n))
    pct = round((correct_n / total_n) * 100.0, 1)
    amount = _score_reward(correct_n, total_n)
    if amount <= 0:
        return {
            "success": False,
            "error": "score_too_low",
            "correct": correct_n,
            "total": total_n,
            "score_percent": pct,
        }, 400

    reference = f"debugger_quiz:{user_id}:{quiz_day}"
    from backend.services.game_mn2_rewards import credit_mn2

    result = credit_mn2(
        user_id,
        amount,
        source="debugger_quiz",
        reference=reference,
        metadata={"correct": correct_n, "total": total_n, "day": quiz_day, "pct": pct},
    )
    if result.get("duplicate"):
        return {
            "success": False,
            "error": "already_rewarded_today",
            "day": quiz_day,
            "score_percent": pct,
        }, 429
    if not result.get("success"):
        return result, 500

    try:
        from backend.services.admin_audit_service import log_action

        log_action(
            "debugger_quiz_submit",
            actor=user_id,
            payload={"correct": correct_n, "total": total_n, "mn2_awarded": amount, "day": quiz_day},
        )
    except Exception:
        pass

    return {
        "success": True,
        "mn2_awarded": amount,
        "amount_mn2": amount,
        "reward_mn2": amount,
        "correct": correct_n,
        "total": total_n,
        "score_percent": pct,
        "day": quiz_day,
    }, 200


@debugger_quiz_bp.route("/api/debugger/quiz/submit", methods=["POST"])
def quiz_submit():
    data = request.get_json(silent=True) or {}
    total = int(data.get("total") or 50)
    if total <= 0:
        total = 50
    body, status = submit_quiz(
        str(data.get("user_id") or ""),
        correct=int(data.get("correct") or 0),
        total=total,
        day=data.get("day"),
    )
    return jsonify(body), status
