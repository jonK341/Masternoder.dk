"""Camgirls platform API — directory, MN2 unlock/tip (Phase 1)."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, request

camgirls_bp = Blueprint("camgirls", __name__)


def _resolve_user_id(*, from_body: bool = False) -> str:
    """Fast path for catalog polling — avoid user_identification timeouts."""
    uid = (request.args.get("user_id") or request.headers.get("X-User-Id") or "").strip()
    if uid:
        return uid
    if from_body:
        body = request.get_json(silent=True) or {}
        uid = (body.get("user_id") or "").strip()
        if uid:
            return uid
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(
            from_body=from_body,
            from_query=False,
            use_session=True,
            use_identification=False,
        )
    except Exception:
        return "default_user"


def _ops_ok() -> bool:
    secret = (
        os.environ.get("MN2_OPS_SECRET")
        or os.environ.get("MN2_SCAN_SECRET")
        or os.environ.get("DISCORD_OPS_SECRET")
        or os.environ.get("ADMIN_OPS_SECRET")
        or ""
    ).strip()
    if not secret:
        return request.environ.get("REMOTE_ADDR") in ("127.0.0.1", "::1")
    return request.headers.get("X-Ops-Secret") == secret


@camgirls_bp.route("/api/camgirls/performers", methods=["GET"])
def performers_list():
    try:
        from backend.services.camgirls_service import list_performers_catalog
        uid = _resolve_user_id()
        result = list_performers_catalog(user_id=uid)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@camgirls_bp.route("/api/camgirls/performers/<performer_id>", methods=["GET"])
def performer_detail(performer_id: str):
    from backend.services.camgirls_service import get_performer_detail
    uid = _resolve_user_id()
    result = get_performer_detail(performer_id, user_id=uid)
    code = 200 if result.get("success") else 404
    return jsonify(result), code


@camgirls_bp.route("/api/camgirls/performers/<performer_id>/unlock", methods=["POST"])
def performer_unlock(performer_id: str):
    from backend.services.camgirls_service import unlock_performer
    uid = _resolve_user_id()
    result = unlock_performer(uid, performer_id)
    if result.get("code") == "age_verification_required":
        return jsonify(result), 403
    if result.get("error") == "insufficient_mn2":
        return jsonify(result), 402
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@camgirls_bp.route("/api/camgirls/performers/<performer_id>/tip", methods=["POST"])
def performer_tip(performer_id: str):
    from backend.services.camgirls_service import tip_performer
    uid = _resolve_user_id()
    body = request.get_json(silent=True) or {}
    amount = body.get("amount_mn2") or body.get("amount")
    result = tip_performer(uid, performer_id, float(amount or 0))
    if result.get("code") == "age_verification_required":
        return jsonify(result), 403
    if result.get("error") == "insufficient_mn2":
        return jsonify(result), 402
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@camgirls_bp.route("/api/camgirls/age-verify", methods=["POST"])
def age_verify():
    from backend.services.camgirls_service import record_age_verification
    uid = _resolve_user_id()
    body = request.get_json(silent=True) or {}
    if not body.get("confirm"):
        return jsonify({"success": False, "error": "confirm_required"}), 400
    birth_year = body.get("birth_year")
    result = record_age_verification(uid, birth_year=int(birth_year) if birth_year is not None else None)
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@camgirls_bp.route("/api/camgirls/ops/performers", methods=["POST"])
def ops_upsert_performer():
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.camgirls_service import upsert_performer
    body = request.get_json(silent=True) or {}
    result = upsert_performer(body)
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@camgirls_bp.route("/api/camgirls/ops/payout-addresses", methods=["GET", "POST"])
def ops_payout_addresses():
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.camgirls_payout_service import list_payout_addresses, provision_payout_addresses
    if request.method == "GET":
        return jsonify(list_payout_addresses()), 200
    body = request.get_json(silent=True) or {}
    performer_id = (body.get("performer_id") or body.get("id") or "").strip()
    ids = [performer_id] if performer_id else None
    result = provision_payout_addresses(performer_ids=ids)
    code = 200 if result.get("success") else 502
    return jsonify(result), code


@camgirls_bp.route("/api/camgirls/studio/catalog", methods=["GET"])
def camgirls_studio_catalog():
    try:
        from backend.services.camgirls_studio_service import studio_catalog
        return jsonify(studio_catalog()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@camgirls_bp.route("/api/camgirls/performers/<performer_id>/gift", methods=["POST"])
def performer_gift(performer_id: str):
    from backend.services.camgirls_studio_service import tip_with_gift
    uid = _resolve_user_id()
    body = request.get_json(silent=True) or {}
    gift_id = body.get("gift_id") or body.get("gift")
    amount = body.get("amount_mn2") or body.get("amount")
    result = tip_with_gift(
        uid,
        performer_id,
        gift_id=str(gift_id) if gift_id else None,
        amount_mn2=float(amount) if amount is not None else None,
    )
    if result.get("code") == "age_verification_required":
        return jsonify(result), 403
    if result.get("error") == "insufficient_mn2":
        return jsonify(result), 402
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@camgirls_bp.route("/api/camgirls/performers/<performer_id>/dance", methods=["POST"])
def performer_dance(performer_id: str):
    from backend.services.camgirls_studio_service import request_dance
    uid = _resolve_user_id()
    body = request.get_json(silent=True) or {}
    dance_id = body.get("dance_id") or body.get("dance") or ""
    result = request_dance(uid, performer_id, str(dance_id))
    if result.get("code") == "age_verification_required":
        return jsonify(result), 403
    if result.get("code") == "unlock_required":
        return jsonify(result), 403
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@camgirls_bp.route("/api/camgirls/chat", methods=["POST"])
def camgirls_chat():
    from backend.services.camgirls_service import chat_with_performer
    uid = _resolve_user_id(from_body=True)
    body = request.get_json(silent=True) or {}
    performer_id = body.get("performer_id") or body.get("performer")
    message = body.get("message") or body.get("text") or ""
    result = chat_with_performer(uid, str(performer_id or ""), str(message))
    if result.get("code") == "age_verification_required":
        return jsonify(result), 403
    if result.get("code") == "unlock_required":
        return jsonify(result), 403
    if result.get("error") == "insufficient_mn2":
        return jsonify(result), 402
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@camgirls_bp.route("/api/camgirls/agents", methods=["GET"])
def camgirls_agents_roster():
    try:
        from backend.services.camgirls_agents_service import list_agent_models
        agents = list_agent_models()
        if not isinstance(agents, list):
            agents = []
        return jsonify({"success": True, "agents": agents, "count": len(agents)}), 200
    except Exception as exc:
        return jsonify({
            "success": True,
            "agents": [],
            "count": 0,
            "warning": str(exc),
        }), 200


@camgirls_bp.route("/api/camgirls/agent-tools", methods=["GET"])
def camgirls_agent_tools():
    from backend.services.camgirls_agents_service import AGENT_TOOLS
    return jsonify({
        "success": True,
        "tools": AGENT_TOOLS,
        "note": "Mutating actions via /api/camgirls/agent-action require approved=true.",
    }), 200


@camgirls_bp.route("/api/camgirls/agent-action", methods=["POST"])
def camgirls_agent_action():
    """Execute camgirls action as an autonomous agent (agent-native parity)."""
    try:
        body = request.get_json(silent=True) or {}
        action = (body.get("action") or "").strip()
        uid = (body.get("user_id") or _resolve_user_id(from_body=True)).strip()
        from backend.services.camgirls_agents_service import execute_agent_action
        result = execute_agent_action(
            action,
            uid,
            approved=bool(body.get("approved")),
            performer_id=str(body.get("performer_id") or body.get("performer") or ""),
            message=str(body.get("message") or body.get("text") or ""),
            amount_mn2=body.get("amount_mn2"),
        )
        if result.get("error") == "unknown_action":
            return jsonify(result), 400
        if result.get("error") == "mutating_action_requires_approved_true":
            return jsonify(result), 403
        code = 200 if result.get("success", True) else 400
        if result.get("code") == "age_verification_required":
            code = 403
        if result.get("error") == "insufficient_mn2":
            code = 402
        return jsonify(result), code
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
