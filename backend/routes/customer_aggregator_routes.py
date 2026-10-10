"""Customer aggregator API — admin-gated directory."""
from __future__ import annotations

import os
from flask import Blueprint, jsonify, request

customer_aggregator_bp = Blueprint("customer_aggregator", __name__)


def _admin_ok() -> bool:
    from backend.services.ops_secret_service import ops_auth_ok

    return ops_auth_ok(
        request.headers.get("X-Ops-Secret"),
        remote_addr=request.environ.get("REMOTE_ADDR", ""),
    )


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
    micro = data.get("micro_rewards")
    result = fulfill_discord_customers_via_encoder(
        sync_first=bool(data.get("sync_first", True)),
        include_guild_members=bool(data.get("include_guild_members", False)),
        message_limit=int(data.get("message_limit") or 100),
        limit=int(data.get("limit") or 50),
        force=bool(data.get("force", False)),
        micro_rewards=micro if isinstance(micro, list) else None,
    )
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@customer_aggregator_bp.route("/api/customers/fulfill/micro-rewards", methods=["GET"])
def customers_fulfill_micro_rewards():
    if not _admin_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.encoder_micro_rewards_service import list_attachable_micro_rewards
    return jsonify(list_attachable_micro_rewards()), 200


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


@customer_aggregator_bp.route("/api/customers/sync/ledger", methods=["POST"])
def customers_sync_ledger():
    if not _admin_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.ledger_customer_aggregator_service import sync_ledger_customers_to_aggregator

    data = request.get_json(silent=True) or {}
    result = sync_ledger_customers_to_aggregator(limit=int(data.get("limit") or 500))
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@customer_aggregator_bp.route("/api/customers/agents", methods=["GET"])
def customers_agents():
    if not _admin_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.ledger_customer_aggregator_service import list_available_agents
    return jsonify(list_available_agents()), 200


@customer_aggregator_bp.route("/api/customers/sync/agents", methods=["POST"])
def customers_sync_agents():
    if not _admin_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.ledger_customer_aggregator_service import assign_agents_to_ledger_customers

    data = request.get_json(silent=True) or {}
    result = assign_agents_to_ledger_customers(
        limit=int(data.get("limit") or 200),
        controller_type=str(data.get("controller_type") or "agent"),
        only_unassigned=bool(data.get("only_unassigned", True)),
    )
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@customer_aggregator_bp.route("/api/customers/buy-potential", methods=["GET"])
def customers_buy_potential():
    if not _admin_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.ledger_buy_potential_service import list_buy_opportunities

    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    tier = request.args.get("tier")
    sort = request.args.get("sort", "spendable")
    return jsonify(list_buy_opportunities(limit=limit, offset=offset, tier=tier, sort=sort)), 200


@customer_aggregator_bp.route("/api/customers/buy-potential/stats", methods=["GET"])
def customers_buy_potential_stats():
    if not _admin_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.ledger_buy_potential_service import buy_potential_stats
    return jsonify(buy_potential_stats()), 200


@customer_aggregator_bp.route("/api/customers/<user_id>/buy-potential", methods=["GET"])
def customer_buy_potential(user_id: str):
    if not _admin_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.ledger_buy_potential_service import compute_buy_potential

    live = request.args.get("live", "1") not in ("0", "false", "no")
    result = compute_buy_potential(user_id, live_balance=live)
    code = 200 if result.get("success") else 404
    return jsonify(result), code


@customer_aggregator_bp.route("/api/customers/buy-potential/nudge", methods=["POST"])
def customers_buy_potential_nudge():
    if not _admin_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.ledger_buy_potential_service import nudge_buy_tier

    data = request.get_json(silent=True) or {}
    result = nudge_buy_tier(
        tier=str(data.get("tier") or "funded_never_bought"),
        limit=int(data.get("limit") or 10),
    )
    return jsonify(result), 200


@customer_aggregator_bp.route("/api/customers/sync/ledger-agents", methods=["POST"])
def customers_sync_ledger_agents():
    if not _admin_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.ledger_customer_aggregator_service import sync_ledger_customers_with_agents

    data = request.get_json(silent=True) or {}
    result = sync_ledger_customers_with_agents(limit=int(data.get("limit") or 200))
    code = 200 if result.get("success") else 400
    return jsonify(result), code
