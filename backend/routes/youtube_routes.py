"""YouTube — status, subscribe MN2 reward, trade-stream interest votes."""
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


@youtube_bp.route("/api/youtube/trade-stream-interest", methods=["GET"])
def youtube_trade_stream_interest_status():
    """Public tally: local votes + YouTube subscriber votes for trade livestream."""
    from backend.services.profit_trade_stream_service import interest_status, snapshot

    if str(request.args.get("with_trades") or "").strip() in ("1", "true", "yes"):
        return jsonify(snapshot(limit=20)), 200
    return jsonify(interest_status()), 200


@youtube_bp.route("/api/youtube/trade-stream-interest", methods=["POST"])
def youtube_trade_stream_interest_vote():
    """Public vote endpoint for YouTube description/chat links (subscribers + local)."""
    from backend.services.profit_trade_stream_service import register_interest

    body = request.get_json(silent=True) or {}
    audience = str(body.get("audience") or request.args.get("audience") or "youtube_subscriber")
    voter = str(body.get("voter") or request.remote_addr or "anon")
    user_id = str(body.get("user_id") or request.args.get("user_id") or "").strip()
    # Default: YouTube link votes are subscriber-audience with self-attest.
    self_attest = bool(
        body.get("self_attest_subscriber")
        if "self_attest_subscriber" in body
        else (audience in ("youtube_subscriber", "subscriber", "youtube"))
    )
    out = register_interest(
        voter=voter,
        audience=audience,
        user_id=user_id,
        self_attest_subscriber=self_attest,
    )
    return jsonify(out), 200
