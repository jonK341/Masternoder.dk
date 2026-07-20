"""Debugger Top-50 Q&A quiz — server-side MN2 rewards."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from flask import Blueprint, jsonify, request

debugger_quiz_bp = Blueprint("debugger_quiz", __name__)

_MIN_CORRECT = 30
_MAX_DAILY_MN2 = 0.05


def _iso_day(day: Optional[str] = None) -> str:
    if day and str(day).strip():
        return str(day).strip()[:10]
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _score_reward(correct: int, total: int) -> float:
    total = max(int(total or 0), 1)
    correct = max(0, min(int(correct or 0), total))
    ratio = correct / total
    if correct < _MIN_CORRECT or ratio < 0.6:
        return 0.0
    return round(min(_MAX_DAILY_MN2, 0.01 + ratio * 0.04), 8)


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
    amount = _score_reward(correct, total)
    if amount <= 0:
        return {
            "success": False,
            "error": "score_too_low",
            "correct": correct,
            "total": total,
        }, 400

    reference = f"debugger_quiz:{user_id}:{quiz_day}"
    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry
    from backend.services.activity_events_service import emit

    result = unified_points_db.add_points(
        user_id,
        "mn2_balance",
        amount,
        source="debugger_quiz",
        metadata={"reference": reference, "correct": correct, "total": total, "day": quiz_day},
    )
    if not result.get("success"):
        return result, 500
    if result.get("duplicate"):
        return {
            "success": False,
            "error": "already_rewarded_today",
            "day": quiz_day,
        }, 429

    append_entry(
        user_id=user_id,
        entry_type="debugger_quiz",
        amount=amount,
        txid=reference,
        metadata={"correct": correct, "total": total, "day": quiz_day},
    )
    emit(
        "debugger_quiz_reward",
        user_id=user_id,
        channel="debugger",
        text=f"+{amount} MN2 (quiz {correct}/{total})",
        payload={"amount": amount, "correct": correct, "total": total, "day": quiz_day},
    )
    return {
        "success": True,
        "mn2_awarded": amount,
        "amount_mn2": amount,
        "reward_mn2": amount,
        "correct": correct,
        "total": total,
        "day": quiz_day,
    }, 200


@debugger_quiz_bp.route("/api/debugger/quiz/submit", methods=["POST"])
def quiz_submit():
    data = request.get_json(silent=True) or {}
    body, status = submit_quiz(
        str(data.get("user_id") or ""),
        correct=int(data.get("correct") or 0),
        total=int(data.get("total") or 0),
        day=data.get("day"),
    )
    return jsonify(body), status
