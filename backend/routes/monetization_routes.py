"""
Legacy monetization blueprint shim.

Older deployments registered /api/monetization/top-25, recap, and streams here with a
broken @rate_limit() wrapper (missing src.utils on some workers -> view returns None).
New handlers live on cogs_bp under /api/monetization/streams/v1/* — keep this file so
auto-discovery does not resurrect the legacy routes.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

monetization_bp = Blueprint("monetization", __name__)


@monetization_bp.route("/api/monetization/streams/v1/ping", methods=["GET"])
def monetization_streams_ping():
    return jsonify({"success": True, "service": "streams_v1"}), 200


@monetization_bp.route("/api/monetization/streams/v1/hub", methods=["GET"])
@monetization_bp.route("/api/monetization/streams/hub", methods=["GET"])
def monetization_streams_hub():
    try:
        from backend.services.monetization_streams_service import stream_hub

        include_metrics = request.args.get("metrics", "1").strip().lower() not in ("0", "false", "no")
        return jsonify(stream_hub(include_metrics=include_metrics)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@monetization_bp.route("/api/monetization/streams/v1/top-25", methods=["GET"])
@monetization_bp.route("/api/monetization/top-25", methods=["GET"])
def monetization_top_25():
    try:
        from backend.services.monetization_streams_service import build_top_25_streams

        streams = build_top_25_streams()
        return jsonify({"success": True, "count": len(streams), "top_25_streams": streams}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@monetization_bp.route("/api/monetization/streams/v1/recap", methods=["GET"])
@monetization_bp.route("/api/monetization/recap", methods=["GET"])
def monetization_recap():
    from backend.services.monetization_streams_service import build_recap

    return jsonify(build_recap()), 200


@monetization_bp.route("/api/monetization/streams/v1/activity-queue", methods=["GET"])
@monetization_bp.route("/api/monetization/activity-queue", methods=["GET"])
def monetization_activity_queue_list():
    from backend.services.monetization_activity_queue_service import list_queue, queue_stats

    limit = request.args.get("limit", 50, type=int)
    channel = (request.args.get("channel") or "").strip() or None
    return jsonify({
        "success": True,
        "stats": queue_stats(),
        "items": list_queue(limit=limit, channel=channel),
    }), 200
