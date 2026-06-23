"""
Account security API — settings, verification, status for real-money accounts.
"""
from flask import Blueprint, jsonify, request

from backend.services.account_resolution_service import resolve_user_id
from backend.services.account_security_service import (
    check_real_money_action,
    get_security_status,
    issue_verification_token,
    update_security_settings,
)

account_security_bp = Blueprint("account_security", __name__)


def _resolve_user() -> str:
    return resolve_user_id(from_body=True, from_query=True)


@account_security_bp.route("/api/user/security/status", methods=["GET"])
def security_status():
    try:
        user_id = _resolve_user()
        return jsonify(get_security_status(user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@account_security_bp.route("/api/user/security/settings", methods=["POST"])
def security_settings_update():
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_user()).strip()
        if not user_id:
            return jsonify({"success": False, "error": "user_id required"}), 400
        result = update_security_settings(user_id, data)
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@account_security_bp.route("/api/user/security/verify", methods=["POST"])
def security_verify():
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_user()).strip()
        password = data.get("password") or ""
        if not user_id or not password:
            return jsonify({"success": False, "error": "user_id and password required"}), 400
        result = issue_verification_token(user_id, password)
        status = 200 if result.get("success") else 401
        return jsonify(result), status
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@account_security_bp.route("/api/user/security/check-real-money", methods=["POST"])
def security_check_real_money():
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_user()).strip()
        token = data.get("verification_token") or data.get("security_token")
        err = check_real_money_action(user_id, verification_token=token)
        if err:
            return jsonify({"success": False, "allowed": False, "error": err}), 403
        return jsonify({"success": True, "allowed": True}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
