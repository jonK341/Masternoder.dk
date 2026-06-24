"""YouTube — status, subscribe MN2 reward."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

youtube_bp = Blueprint("youtube", __name__)


@youtube_bp.route("/api/youtube/status", methods=["GET"])
def youtube_status():
    user_id = (request.args.get("user_id") or "").strip() or None
    from backend.services.youtube_fanout_service import get_youtube_status
    return jsonify(get_youtube_status(user_id=user_id)), 200


@youtube_bp.route("/api/youtube/subscribe-claim", methods=["POST"])
def youtube_subscribe_claim():
    body = request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or request.args.get("user_id") or "").strip()
    if not user_id:
        return jsonify({"success": False, "error": "user_id required"}), 400
    from backend.services.youtube_fanout_service import claim_subscribe_reward
    out = claim_subscribe_reward(user_id)
    return jsonify(out), 200 if out.get("success") else 400
