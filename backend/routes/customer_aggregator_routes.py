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
    return jsonify(list_customers(limit=limit, offset=offset, search=search)), 200


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
