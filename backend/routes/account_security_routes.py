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
from backend.services.profile_auth_service import check_profile_write_access

account_security_bp = Blueprint("account_security", __name__)


def _resolve_user() -> str:
    return resolve_user_id(from_body=True, from_query=True)


def _deny(user_id: str, *, guest_ok: bool = False):
    if guest_ok and (user_id or "").strip().lower() == "default_user":
        return None
    msg = check_profile_write_access(user_id)
    if msg:
        return jsonify({"success": False, "error": msg}), 403
    return None


@account_security_bp.route("/api/user/security/status", methods=["GET"])
def security_status():
    try:
        user_id = _resolve_user()
        denied = _deny(user_id, guest_ok=True)
        if denied:
            return denied
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
        denied = _deny(user_id)
        if denied:
            return denied
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
        denied = _deny(user_id)
        if denied:
            return denied
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
        denied = _deny(user_id)
        if denied:
            return denied
        token = data.get("verification_token") or data.get("security_token")
        err = check_real_money_action(user_id, verification_token=token)
        if err:
            return jsonify({"success": False, "allowed": False, "error": err}), 403
        return jsonify({"success": True, "allowed": True}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
