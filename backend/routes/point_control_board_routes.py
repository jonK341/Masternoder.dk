"""
Point system + System A+ control board routes.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

point_control_board_bp = Blueprint("point_control_board", __name__)


def _resolve_user_id():
    from backend.services.account_resolution_service import resolve_user_id

    return resolve_user_id()


@point_control_board_bp.route("/api/control-board/status", methods=["GET"])
def control_board_status():
    from backend.services.point_system_control_board import get_board_status

    return jsonify(get_board_status()), 200


@point_control_board_bp.route("/api/control-board/a-plus", methods=["GET"])
def control_board_a_plus():
    from backend.services.system_a_plus_board_service import get_a_plus_board

    return jsonify(get_a_plus_board()), 200


@point_control_board_bp.route("/api/control-board/api-integrations", methods=["GET"])
def control_board_api_integrations():
    from backend.services.system_a_plus_board_service import get_api_integration_board

    return jsonify(get_api_integration_board()), 200


@point_control_board_bp.route("/api/control-board/crypto-rewards", methods=["GET"])
def control_board_crypto_rewards():
    from backend.services.system_a_plus_board_service import get_crypto_rewards_board

    return jsonify(get_crypto_rewards_board()), 200
