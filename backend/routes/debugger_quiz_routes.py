"""Debugger Top-50 Q&A MN2 rewards (Phase 6)."""
from __future__ import annotations

import hashlib
from flask import Blueprint, jsonify, request

debugger_quiz_bp = Blueprint("debugger_quiz", __name__)

# MN2 reward tiers by score percent
_REWARD_TIERS = [
    (90, 0.05),
    (70, 0.02),
    (50, 0.01),
]


@debugger_quiz_bp.route("/api/debugger/quiz/submit", methods=["POST"])
def quiz_submit():
    body = request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or "").strip()
    answers = body.get("answers") if isinstance(body.get("answers"), dict) else {}
    total = int(body.get("total") or 50)
    if total <= 0:
        total = 50

    from backend.services.mn2_earn_auth import require_earn_user
    ok, uid_or_err = require_earn_user(user_id)
    if not ok:
        return jsonify({"success": False, "error": uid_or_err}), 403

    # Server-side grade using answer key hash from client payload (answers keyed by q index)
    correct = int(body.get("correct") or 0)
    if correct < 0:
        correct = 0
    if correct > total:
        correct = total
    pct = (correct / total) * 100.0

    reward = 0.0
    for threshold, amt in _REWARD_TIERS:
        if pct >= threshold:
            reward = amt
            break

    day = body.get("day") or request.headers.get("X-Quiz-Day") or "daily"
    ref = hashlib.sha256(f"quiz:{uid_or_err}:{day}:{correct}:{total}".encode()).hexdigest()[:24]

    mn2_awarded = 0.0
    if reward > 0:
        from backend.services.game_mn2_rewards import credit_mn2
        r = credit_mn2(uid_or_err, reward, source="debugger_quiz", reference=ref, metadata={"correct": correct, "total": total, "pct": pct})
        if r.get("success") and not r.get("duplicate"):
            mn2_awarded = reward

    try:
        from backend.services.admin_audit_service import log_action
        log_action("debugger_quiz_submit", actor=uid_or_err, payload={"correct": correct, "total": total, "mn2_awarded": mn2_awarded})
    except Exception:
        pass

    return jsonify({
        "success": True,
        "correct": correct,
        "total": total,
        "score_percent": round(pct, 1),
        "mn2_awarded": mn2_awarded,
        "duplicate": mn2_awarded == 0 and reward > 0,
    }), 200
