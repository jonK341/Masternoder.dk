"""Aggregator hub v2 API — catalog, top25, progress, control panel."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

aggregator_hub_bp = Blueprint("aggregator_hub", __name__)


def _uid() -> str:
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(from_body=True, from_query=True)
    except Exception:
        return (request.args.get("user_id") or "default_user").strip()


@aggregator_hub_bp.route("/api/aggregators/catalog", methods=["GET"])
def aggregators_catalog():
    from backend.services.aggregator_catalog_service import list_catalog
    category = request.args.get("category")
    search = request.args.get("search") or request.args.get("q")
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)
    return jsonify(list_catalog(category=category, search=search, limit=limit, offset=offset)), 200


@aggregator_hub_bp.route("/api/aggregators/top25", methods=["GET"])
def aggregators_top25():
    from backend.services.aggregator_catalog_service import top25_list
    return jsonify(top25_list()), 200


@aggregator_hub_bp.route("/api/aggregators/fulfillment", methods=["GET"])
def aggregators_fulfillment():
    from backend.services.aggregator_catalog_service import fulfillment_section
    return jsonify(fulfillment_section()), 200


@aggregator_hub_bp.route("/api/aggregators/progress", methods=["GET"])
def aggregators_progress():
    from backend.services.aggregator_catalog_service import progress_snapshot
    return jsonify(progress_snapshot(_uid())), 200


@aggregator_hub_bp.route("/api/aggregators/control", methods=["GET"])
def aggregators_control_get():
    from backend.services.aggregator_catalog_service import get_control_state
    return jsonify(get_control_state(_uid())), 200


@aggregator_hub_bp.route("/api/aggregators/control/assign", methods=["POST"])
def aggregators_control_assign():
    from backend.services.aggregator_catalog_service import assign_agent
    body = request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or _uid()).strip()
    result = assign_agent(
        user_id,
        body.get("aggregator_id") or "",
        body.get("agent_id") or "",
        auto_run=body.get("auto_run"),
    )
    code = 200 if result.get("success") else 400
    return jsonify(result), code
