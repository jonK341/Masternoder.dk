"""Point system control board API."""
from __future__ import annotations

import os
from flask import Blueprint, jsonify, request

point_control_board_bp = Blueprint("point_control_board", __name__)


def _ops_ok() -> bool:
    secret = os.environ.get("DISCORD_OPS_SECRET") or os.environ.get("ADMIN_OPS_SECRET", "")
    if not secret:
        return request.environ.get("REMOTE_ADDR") in ("127.0.0.1", "::1")
    return request.headers.get("X-Ops-Secret") == secret


@point_control_board_bp.route("/api/control-board/status", methods=["GET"])
def control_board_status():
    from backend.services.point_system_control_board import get_board_status
    return jsonify(get_board_status()), 200


@point_control_board_bp.route("/api/control-board/systems", methods=["GET"])
def control_board_systems():
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.point_system_control_board import get_board_status
    return jsonify(get_board_status()), 200
