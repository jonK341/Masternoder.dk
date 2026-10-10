"""
AI assist routes — support FAQ, Pro copy assist, admin fraud/risk panel APIs.
"""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, request

ai_assist_bp = Blueprint("ai_assist", __name__)


def _resolve_uid() -> str:
    try:
        from backend.services.account_resolution_service import resolve_user_id

        return resolve_user_id(from_body=True, from_query=True)
    except Exception:
        data = request.get_json(silent=True) or {}
        return (
            (data.get("user_id") or request.args.get("user_id") or "default_user").strip()
        )


def _admin_key_ok():
    expected = (os.environ.get("COGS_ADMIN_REPORT_KEY") or "").strip()
    if not expected:
        return False, expected
    supplied = (request.headers.get("X-Cogs-Admin-Key") or request.args.get("key") or "").strip()
    return supplied == expected, expected


@ai_assist_bp.route("/api/support/faq/topics", methods=["GET"])
def support_faq_topics():
    from backend.services.support_faq_service import list_topics

    return jsonify({"success": True, "topics": list_topics()}), 200


@ai_assist_bp.route("/api/support/faq", methods=["GET"])
def support_faq_get():
    from backend.services.support_faq_service import faq_answer

    q = (request.args.get("q") or request.args.get("question") or "").strip()
    use_llm = (request.args.get("llm") or "1").strip().lower() not in ("0", "false", "no")
    out = faq_answer(q, use_llm=use_llm, channel="web")
    return jsonify(out), 200


@ai_assist_bp.route("/api/support/faq/ask", methods=["POST"])
def support_faq_ask():
    from backend.services.support_faq_service import faq_answer

    data = request.get_json(silent=True) or {}
    q = (data.get("question") or data.get("q") or "").strip()
    use_llm = data.get("use_llm", True)
    channel = (data.get("channel") or "web").strip()
    out = faq_answer(q, use_llm=bool(use_llm), channel=channel)
    return jsonify(out), 200


@ai_assist_bp.route("/api/discord/support/faq", methods=["GET"])
def discord_support_faq():
    """M8 #60 — Discord + cron compatible alias."""
    from backend.services.support_faq_service import faq_answer

    q = (request.args.get("q") or request.args.get("question") or "").strip()
    use_llm = (request.args.get("llm") or "1").strip().lower() not in ("0", "false", "no")
    out = faq_answer(q, use_llm=use_llm, channel="discord")
    return jsonify(out), 200


@ai_assist_bp.route("/api/assist/copy/kinds", methods=["GET"])
def copy_assist_kinds():
    from backend.services.copy_assist_service import list_kinds

    return jsonify(list_kinds()), 200


@ai_assist_bp.route("/api/assist/copy", methods=["POST"])
def copy_assist_generate():
    from backend.services.copy_assist_service import generate_copy

    data = request.get_json(silent=True) or {}
    user_id = (data.get("user_id") or _resolve_uid()).strip()
    kind = (data.get("kind") or "product_description").strip()
    context = data.get("context") if isinstance(data.get("context"), dict) else {
        k: v for k, v in data.items() if k not in ("user_id", "kind", "context")
    }
    out = generate_copy(user_id, kind, context)
    status = int(out.pop("http_status", 200) if isinstance(out.get("http_status"), int) else 200)
    if not out.get("success") and out.get("error") == "pro_required":
        status = 403
    return jsonify(out), status


@ai_assist_bp.route("/api/admin/risk/summary", methods=["GET"])
def admin_risk_summary():
    ok, expected = _admin_key_ok()
    if not expected:
        return jsonify({"success": False, "error": "admin_risk_disabled", "hint": "set COGS_ADMIN_REPORT_KEY"}), 503
    if not ok:
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.mn2_risk_ops_service import risk_summary

    return jsonify(risk_summary()), 200


@ai_assist_bp.route("/api/admin/risk/withdrawals", methods=["GET"])
def admin_risk_withdrawals():
    ok, expected = _admin_key_ok()
    if not expected:
        return jsonify({"success": False, "error": "admin_risk_disabled", "hint": "set COGS_ADMIN_REPORT_KEY"}), 503
    if not ok:
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.mn2_risk_ops_service import read_withdrawal_assessments

    try:
        limit = max(1, min(500, int(request.args.get("limit") or 100)))
    except (TypeError, ValueError):
        limit = 100
    rows = read_withdrawal_assessments(limit=limit)
    return jsonify({"success": True, "count": len(rows), "assessments": rows}), 200


@ai_assist_bp.route("/api/admin/risk/sybil", methods=["GET"])
def admin_risk_sybil():
    ok, expected = _admin_key_ok()
    if not expected:
        return jsonify({"success": False, "error": "admin_risk_disabled", "hint": "set COGS_ADMIN_REPORT_KEY"}), 503
    if not ok:
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.mn2_risk_ops_service import sybil_summary

    try:
        limit = max(1, min(200, int(request.args.get("limit") or 50)))
    except (TypeError, ValueError):
        limit = 50
    try:
        min_score = float(request.args.get("min_score") or 0.35)
    except (TypeError, ValueError):
        min_score = 0.35
    return jsonify(sybil_summary(limit=limit, min_score=min_score)), 200
