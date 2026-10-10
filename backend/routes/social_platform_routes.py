"""Social platform hub — Discord / Facebook / YouTube fan-out cron + status."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, request

social_platform_bp = Blueprint("social_platform", __name__)


def _ops_ok() -> bool:
    secret = (os.environ.get("DISCORD_OPS_SECRET") or os.environ.get("SOCIAL_OPS_SECRET") or "").strip()
    if not secret:
        return False
    return request.headers.get("X-Ops-Secret") == secret or request.args.get("ops_secret") == secret


@social_platform_bp.route("/api/social/platforms/hub", methods=["GET"])
def social_platforms_hub():
    from backend.services.social_platform_fanout_service import get_platform_hub
    return jsonify(get_platform_hub()), 200


@social_platform_bp.route("/api/social/platforms/fanout/run", methods=["POST"])
def social_platforms_fanout_run():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    body = request.get_json(silent=True) or {}
    dry_run = bool(body.get("dry_run"))
    platform = (body.get("platform") or "all").strip().lower()
    from backend.services import social_platform_fanout_service as svc

    if platform == "discord":
        result = svc.run_discord_fanouts(dry_run=dry_run)
    elif platform == "facebook":
        result = svc.run_facebook_fanout(dry_run=dry_run)
    elif platform == "youtube":
        result = svc.run_youtube_fanout(dry_run=dry_run)
    else:
        result = svc.run_all_fanouts(dry_run=dry_run)
    return jsonify(result), 200


@social_platform_bp.route("/api/social/platforms/rotator/<platform>", methods=["POST"])
def social_platform_rotator(platform: str):
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    body = request.get_json(silent=True) or {}
    from backend.services.social_platform_fanout_service import run_discovery_rotator
    result = run_discovery_rotator(platform=platform.strip().lower(), dry_run=bool(body.get("dry_run")))
    code = 200 if result.get("success") else 400
    return jsonify(result), code
