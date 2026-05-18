"""
Virtual-coins casino API (cosmetic betting only).
"""
from flask import Blueprint, jsonify, request

from backend.services.account_resolution_service import resolve_user_id
import backend.services.casino_service as casino_service


casino_bp = Blueprint("virtual_casino", __name__)


def _casino_settings_payload():
    payload = casino_service.get_public_config()
    payload["success"] = True
    return payload


@casino_bp.route("/api/casino/settings", methods=["GET"])
def casino_settings():
    try:
        return jsonify(_casino_settings_payload()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/config", methods=["GET"])
def casino_config_compat():
    """Backward-compatible alias for older clients."""
    return casino_settings()


@casino_bp.route("/api/casino/balance", methods=["GET"])
def casino_balance():
    try:
        user_id = resolve_user_id(from_body=False, from_query=True)
        return jsonify(casino_service.get_balance(user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/history", methods=["GET"])
def casino_history():
    try:
        user_id = resolve_user_id(from_body=False, from_query=True)
        limit = request.args.get("limit", 25)
        return jsonify(casino_service.get_history(user_id, limit=limit)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/coin-flip", methods=["POST"])
def casino_coin_flip():
    try:
        data = request.get_json(silent=True) or {}
        user_id = resolve_user_id(from_body=True, from_query=True)
        result = casino_service.play_coin_flip(
            user_id=user_id,
            bet=data.get("bet"),
            choice=(data.get("choice") or "").strip(),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/dice", methods=["POST"])
def casino_dice():
    try:
        data = request.get_json(silent=True) or {}
        user_id = resolve_user_id(from_body=True, from_query=True)
        result = casino_service.play_dice(
            user_id=user_id,
            bet=data.get("bet"),
            guess=data.get("guess"),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/rps-bet", methods=["POST"])
def casino_rps_bet():
    try:
        data = request.get_json(silent=True) or {}
        user_id = resolve_user_id(from_body=True, from_query=True)
        result = casino_service.play_rps_bet(
            user_id=user_id,
            bet=data.get("bet"),
            choice=(data.get("choice") or "").strip(),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
