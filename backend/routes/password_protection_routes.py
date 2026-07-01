"""
Password protection routes — encrypted password as reward for completing and earning points.
Unlock by reaching min game_points or Star Map investigations; set password and get a small points reward.
"""
from flask import Blueprint, jsonify, request

from backend.services.password_protection_service import (
    get_password_status,
    get_recovery_status,
    request_password_recovery,
    reset_password_with_recovery,
    unlock_password_protection,
    set_password,
    verify_password,
)

password_protection_bp = Blueprint("password_protection", __name__)


def _user_id() -> str:
    data = request.get_json(silent=True) or {}
    return (data.get("user_id") or request.args.get("user_id") or "default_user").strip()


@password_protection_bp.route("/api/auth/password/status", methods=["GET"])
def password_status():
    """GET ?user_id= — has_unlocked, has_password, can_unlock, unlock_rule, reward_on_set."""
    try:
        user_id = _user_id()
        result = get_password_status(user_id)
        return jsonify({"success": True, **result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@password_protection_bp.route("/api/auth/password/unlock", methods=["POST"])
def password_unlock():
    """POST { user_id } — Mark password protection as unlocked if user meets rule (earn points / investigations)."""
    try:
        user_id = _user_id()
        result = unlock_password_protection(user_id)
        status = 200 if result.get("success") else 400
        return jsonify(result), status
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@password_protection_bp.route("/api/auth/password/set", methods=["POST"])
def password_set():
    """POST { user_id, password, current_password? } — Set or change password. Unlocks automatically if eligible. Awards game_points reward on first set."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or "default_user").strip()
        password = data.get("password") or data.get("new_password") or ""
        current_password = data.get("current_password")
        result = set_password(user_id, password, current_password=current_password)
        status = 200 if result.get("success") else 400
        return jsonify(result), status
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@password_protection_bp.route("/api/auth/password/verify", methods=["POST"])
def password_verify():
    """POST { user_id, password } — Verify password for sensitive actions."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or "default_user").strip()
        password = data.get("password") or ""
        result = verify_password(user_id, password)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@password_protection_bp.route("/api/auth/password/recovery/status", methods=["GET"])
def password_recovery_status():
    """GET ?user_id= — report email/provider-backed recovery availability."""
    try:
        user_id = _user_id()
        return jsonify({"success": True, "user_id": user_id, **get_recovery_status(user_id)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@password_protection_bp.route("/api/auth/password/recovery/request", methods=["POST"])
def password_recovery_request():
    """POST { user_id, email? } — create a short-lived reset request."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or "default_user").strip()
        result = request_password_recovery(user_id, data.get("email"))
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@password_protection_bp.route("/api/auth/password/recovery/reset", methods=["POST"])
def password_recovery_reset():
    """POST { user_id, token, password } — reset password with a valid recovery token."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or "default_user").strip()
        result = reset_password_with_recovery(user_id, data.get("token") or "", data.get("password") or "")
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
