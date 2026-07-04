"""
Platform upgrade roadmap API — batch 1 (100) and batch 2 (200).
"""
from flask import Blueprint, jsonify, request

from backend.middleware.response_cache_middleware import cached_response
from backend.services.platform_upgrades_batch2_service import get_batch2_roadmap, get_batch2_widgets
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
        "batch2": get_batch2_roadmap(),
    }), 200


@platform_upgrades_bp.route("/api/platform/upgrades/batch2", methods=["GET"])
@cached_response(ttl=60)
def platform_upgrades_batch2_roadmap():
    area = request.args.get("area")
    return jsonify(get_batch2_roadmap(area)), 200


@platform_upgrades_bp.route("/api/platform/batch2/<area>/widgets", methods=["GET"])
def platform_batch2_widgets(area: str):
    user_id = request.args.get("user_id")
    data = get_batch2_widgets(area, user_id=user_id)
    code = 200 if data.get("success") else 404
    return jsonify(data), code


@platform_upgrades_bp.route("/api/platform/upgrades/combined", methods=["GET"])
@cached_response(ttl=60)
def platform_upgrades_combined():
    b1 = get_roadmap()
    b2 = get_batch2_roadmap()
    return jsonify({
        "success": True,
        "batch1": {"total": b1.get("total"), "done": b1.get("done"), "planned": b1.get("planned")},
        "batch2": {"total": b2.get("total"), "done": b2.get("done"), "planned": b2.get("planned")},
        "combined_total": (b1.get("total") or 0) + (b2.get("total") or 0),
        "combined_done": (b1.get("done") or 0) + (b2.get("done") or 0),
    }), 200
