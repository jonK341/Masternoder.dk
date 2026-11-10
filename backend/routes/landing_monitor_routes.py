"""Landing monitor API for the frontpage entertainment surface."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

landing_monitor_bp = Blueprint("landing_monitor", __name__)


@landing_monitor_bp.route("/api/landing/monitor", methods=["GET"])
def landing_monitor_snapshot():
    from backend.services.landing_monitor_service import get_snapshot, refresh_snapshot

    force = str(request.args.get("refresh") or "").strip().lower() in ("1", "true", "yes")
    try:
        payload = refresh_snapshot(force=True) if force else get_snapshot(max_age_sec=12.0)
    except Exception as exc:
        payload = {
            "success": False,
            "error": str(exc)[:200],
            "bpm": 180,
            "refresh_ms": 5000,
            "stats": {},
            "special": {},
            "lightshow": {"id": "pulse", "name": "Pulse Lightshow", "explain": ""},
            "effect_explain": {"title": "Pulse", "body": "", "bpm": 180},
            "music": {"bpm": 180, "opt_in": True},
        }
    return jsonify(payload), 200, {"Cache-Control": "public, max-age=2"}

@landing_monitor_bp.route("/api/landing/monitor/tick", methods=["POST"])
def landing_monitor_tick():
    """Cron/ops tick — rebuild cache immediately."""
    from backend.services.landing_monitor_service import refresh_snapshot

    payload = refresh_snapshot(force=True)
    return jsonify({"success": True, "updated_at": payload.get("updated_at"), "bpm": payload.get("bpm")})
