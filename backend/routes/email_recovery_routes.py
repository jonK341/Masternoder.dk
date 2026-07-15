"""
Email verification and recovery routes.
"""
from flask import Blueprint, jsonify, request

from backend.services.account_resolution_service import resolve_user_id
from backend.services.email_recovery_service import (
    confirm_email_change,
    confirm_email_verification,
    confirm_recovery_email,
    get_email_status,
    request_email_change,
    request_email_verification,
    request_recovery_email,
)
from backend.services.profile_auth_service import check_profile_write_access

email_recovery_bp = Blueprint("email_recovery", __name__)


def _user_id() -> str:
    data = request.get_json(silent=True) or {}
    return (data.get("user_id") or request.args.get("user_id") or resolve_user_id()).strip()


@email_recovery_bp.route("/api/auth/email/status", methods=["GET"])
def email_status():
    try:
        user_id = _user_id()
        return jsonify({"success": True, "user_id": user_id, **get_email_status(user_id)}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@email_recovery_bp.route("/api/auth/email/verify/request", methods=["POST"])
def email_verify_request():
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or resolve_user_id()).strip()
        denied = check_profile_write_access(user_id)
        if denied:
            return jsonify({"success": False, "error": denied}), 403
        result = request_email_verification(user_id, data.get("email") or "")
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@email_recovery_bp.route("/api/auth/email/verify/confirm", methods=["POST"])
def email_verify_confirm():
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or resolve_user_id()).strip()
        result = confirm_email_verification(user_id, data.get("token") or "")
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@email_recovery_bp.route("/api/auth/email/change/request", methods=["POST"])
def email_change_request():
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or resolve_user_id()).strip()
        denied = check_profile_write_access(user_id)
        if denied:
            return jsonify({"success": False, "error": denied}), 403
        result = request_email_change(user_id, data.get("new_email") or data.get("email") or "", data.get("current_password"))
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@email_recovery_bp.route("/api/auth/email/change/confirm", methods=["POST"])
def email_change_confirm():
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or resolve_user_id()).strip()
        result = confirm_email_change(user_id, data.get("token") or "")
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@email_recovery_bp.route("/api/auth/email/recovery/request", methods=["POST"])
def recovery_email_request():
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or resolve_user_id()).strip()
        denied = check_profile_write_access(user_id)
        if denied:
            return jsonify({"success": False, "error": denied}), 403
        result = request_recovery_email(user_id, data.get("recovery_email") or data.get("email") or "")
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@email_recovery_bp.route("/api/auth/email/recovery/confirm", methods=["POST"])
def recovery_email_confirm():
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or resolve_user_id()).strip()
        result = confirm_recovery_email(user_id, data.get("token") or "")
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
