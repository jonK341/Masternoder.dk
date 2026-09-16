"""Customer aggregator API — admin-gated directory."""
from __future__ import annotations

import os
from flask import Blueprint, jsonify, request

customer_aggregator_bp = Blueprint("customer_aggregator", __name__)


def _admin_ok() -> bool:
    secret = os.environ.get("DISCORD_OPS_SECRET") or os.environ.get("ADMIN_OPS_SECRET", "")
    if not secret:
        return request.environ.get("REMOTE_ADDR") in ("127.0.0.1", "::1")
    return request.headers.get("X-Ops-Secret") == secret


@customer_aggregator_bp.route("/api/customers", methods=["GET"])
def customers_list():
    if not _admin_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.customer_aggregator_service import list_customers
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    search = request.args.get("search")
    source = request.args.get("source")
    return jsonify(list_customers(limit=limit, offset=offset, search=search, source=source)), 200


@customer_aggregator_bp.route("/api/customers/stats", methods=["GET"])
def customers_stats():
    if not _admin_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.customer_aggregator_service import stats
    return jsonify(stats()), 200


@customer_aggregator_bp.route("/api/customers/<user_id>", methods=["GET"])
def customer_detail(user_id: str):
    if not _admin_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.customer_aggregator_service import get_customer
    result = get_customer(user_id)
    code = 200 if result.get("success") else 404
    return jsonify(result), code


@customer_aggregator_bp.route("/api/customers/fulfill/discord", methods=["POST"])
def customers_fulfill_discord():
    if not _admin_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.encoder_customer_fulfillment_service import fulfill_discord_customers_via_encoder

    data = request.get_json(silent=True) or {}
    result = fulfill_discord_customers_via_encoder(
        sync_first=bool(data.get("sync_first", True)),
        include_guild_members=bool(data.get("include_guild_members", False)),
        message_limit=int(data.get("message_limit") or 100),
        limit=int(data.get("limit") or 50),
        force=bool(data.get("force", False)),
    )
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@customer_aggregator_bp.route("/api/customers/fulfill/stats", methods=["GET"])
def customers_fulfill_stats():
    if not _admin_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.encoder_customer_fulfillment_service import fulfillment_stats
    return jsonify(fulfillment_stats()), 200


@customer_aggregator_bp.route("/api/customers/<user_id>/ledger", methods=["GET"])
def customer_ledger(user_id: str):
    if not _admin_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.ledger_customer_control_service import get_ledger_customer
    result = get_ledger_customer(user_id)
    code = 200 if result.get("success") else 404
    return jsonify(result), code


@customer_aggregator_bp.route("/api/customers/<user_id>/control", methods=["GET", "POST", "DELETE"])
def customer_control(user_id: str):
    if not _admin_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.ledger_customer_control_service import (
        assign_controller,
        clear_controller,
        get_assignment,
        get_ledger_customer,
    )

    if request.method == "GET":
        assignment = get_assignment(user_id)
        if not assignment:
            return jsonify({"success": True, "user_id": user_id, "assignment": None}), 200
        return jsonify({"success": True, "user_id": user_id, "assignment": assignment}), 200

    if request.method == "DELETE":
        return jsonify(clear_controller(user_id)), 200

    data = request.get_json(silent=True) or {}
    result = assign_controller(
        user_id,
        data.get("controller_type") or data.get("type") or "ai",
        controller_id=str(data.get("controller_id") or ""),
        performer_id=str(data.get("performer_id") or ""),
        agent_id=str(data.get("agent_id") or ""),
        notes=str(data.get("notes") or ""),
        metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else None,
    )
    if not result.get("success"):
        return jsonify(result), 400
    ledger = get_ledger_customer(user_id)
    result["ledger_preview"] = {
        "control": ledger.get("control"),
        "customer": ledger.get("customer"),
    }
    return jsonify(result), 200


@customer_aggregator_bp.route("/api/customers/<user_id>/control/action", methods=["POST"])
def customer_control_action(user_id: str):
    if not _admin_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.ledger_customer_control_service import execute_control_action

    data = request.get_json(silent=True) or {}
    action = str(data.get("action") or "").strip()
    if not action:
        return jsonify({"success": False, "error": "action_required"}), 400
    result = execute_control_action(
        user_id,
        action,
        approved=bool(data.get("approved")),
        payload=data,
    )
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@customer_aggregator_bp.route("/api/customers/control/stats", methods=["GET"])
def customers_control_stats():
    if not _admin_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.ledger_customer_control_service import control_stats
    return jsonify(control_stats()), 200
