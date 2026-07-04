"""
Platform 100-upgrade roadmap API.
"""
from flask import Blueprint, jsonify, request

from backend.middleware.response_cache_middleware import cached_response
from backend.services.platform_upgrades_service import get_area_summary, get_roadmap

platform_upgrades_bp = Blueprint("platform_upgrades", __name__)


@platform_upgrades_bp.route("/api/platform/upgrades", methods=["GET"])
@cached_response(ttl=60)
def platform_upgrades_roadmap():
    area = request.args.get("area")
    return jsonify(get_roadmap(area)), 200


@platform_upgrades_bp.route("/api/platform/area/<area>/summary", methods=["GET"])
def platform_area_summary(area: str):
    user_id = request.args.get("user_id")
    data = get_area_summary(area, user_id=user_id)
    code = 200 if data.get("success") else 404
    return jsonify(data), code


@platform_upgrades_bp.route("/api/platform/health", methods=["GET"])
@cached_response(ttl=30)
def platform_cross_health():
    areas = ["explorer", "exchange", "command-center"]
    snapshots = {}
    for a in areas:
        snapshots[a] = get_area_summary(a)
    return jsonify({
        "success": True,
        "areas": snapshots,
        "roadmap": get_roadmap(),
    }), 200
