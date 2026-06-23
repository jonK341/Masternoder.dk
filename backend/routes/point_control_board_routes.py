"""Point system control board API."""
from __future__ import annotations

from flask import Blueprint, jsonify

from backend.services.ops_auth_service import ops_ok

point_control_board_bp = Blueprint("point_control_board", __name__)


def _require_ops():
    if not ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    return None


@point_control_board_bp.route("/api/control-board/status", methods=["GET"])
def control_board_status():
    denied = _require_ops()
    if denied:
        return denied
    from backend.services.point_system_control_board import get_board_status
    return jsonify(get_board_status()), 200


@point_control_board_bp.route("/api/control-board/systems", methods=["GET"])
def control_board_systems():
    denied = _require_ops()
    if denied:
        return denied
    from backend.services.point_system_control_board import get_board_status
    return jsonify(get_board_status()), 200
