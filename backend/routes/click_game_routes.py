"""Click-through game routes — progress, save, and instant MN2 click rewards."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from flask import Blueprint, jsonify, request

click_game_bp = Blueprint("click_game", __name__)

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROGRESS_DIR = os.path.join(_BASE, "data", "click_game")


def _uid() -> str:
    body = request.get_json(silent=True) or {}
    return (
        request.args.get("user_id")
        or body.get("user_id")
        or request.headers.get("X-User-Id")
        or "default_user"
    )


def _progress_path(user_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (user_id or "default"))
    return os.path.join(_PROGRESS_DIR, f"{safe}.json")


def _read_progress(user_id: str) -> Dict[str, Any]:
    path = _progress_path(user_id)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_progress(user_id: str, data: Dict[str, Any]) -> bool:
    os.makedirs(_PROGRESS_DIR, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        with open(_progress_path(user_id), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


@click_game_bp.route("/api/game/click-game/progress", methods=["GET"])
def click_game_progress():
    user_id = _uid()
    prog = _read_progress(user_id)
    return jsonify({
        "success": True,
        "user_id": user_id,
        "progress": prog.get("progress") or {},
        "mn2_earned_total": prog.get("mn2_earned_total", 0),
    }), 200


@click_game_bp.route("/api/game/click-game/save-progress", methods=["POST"])
def click_game_save_progress():
    user_id = _uid()
    body = request.get_json(silent=True) or {}
    progress = body.get("progress") or {}
    if not isinstance(progress, dict):
        return jsonify({"success": False, "error": "invalid_progress"}), 400
    existing = _read_progress(user_id)
    existing["progress"] = progress
    existing["user_id"] = user_id
    if not _write_progress(user_id, existing):
        return jsonify({"success": False, "error": "save_failed"}), 500
    return jsonify({"success": True, "user_id": user_id}), 200


@click_game_bp.route("/api/game/click-game/instant-reward", methods=["POST"])
def click_game_instant_reward():
    """Instant MN2 credit when user wins a click reward."""
    body = request.get_json(silent=True) or {}
    user_id = _uid()
    action = str(body.get("action") or "click").strip().lower()
    click_id = str(body.get("click_id") or body.get("tx_id") or "").strip() or None
    metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}

    if not click_id:
        click_id = f"click:{user_id}:{action}:{uuid.uuid4().hex}"

    from backend.services.click_mn2_rewards_service import credit_instant_click_reward

    result = credit_instant_click_reward(
        user_id,
        action=action,
        click_id=click_id,
        metadata=metadata,
    )
    code = 200 if result.get("success") else 400

    if result.get("success"):
        store = _read_progress(user_id)
        total = float(store.get("mn2_earned_total") or 0) + float(result.get("amount_mn2") or 0)
        store["mn2_earned_total"] = total
        store["last_instant_tx"] = result.get("tx_id")
        _write_progress(user_id, store)

    return jsonify(result), code


@click_game_bp.route("/api/game/click-game/reward-quote", methods=["GET"])
def click_game_reward_quote():
    from backend.services.click_mn2_rewards_service import click_reward_quote

    action = request.args.get("action") or "click"
    return jsonify(click_reward_quote(action)), 200
