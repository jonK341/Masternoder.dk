"""Security cron HTTP endpoints."""
from __future__ import annotations

import os
from flask import Blueprint, jsonify, request

security_cron_bp = Blueprint("security_cron", __name__)


def _ops_ok() -> bool:
    secret = os.environ.get("DISCORD_OPS_SECRET") or os.environ.get("ADMIN_OPS_SECRET", "")
    if not secret:
        return request.environ.get("REMOTE_ADDR") in ("127.0.0.1", "::1")
    return request.headers.get("X-Ops-Secret") == secret


@security_cron_bp.route("/api/security/cron/sweep", methods=["POST"])
def security_sweep():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    results = {}
    try:
        from backend.services.mn2_conservation_gate import conservation_gate
        results["conservation"] = conservation_gate()
    except Exception as exc:
        results["conservation"] = {"error": str(exc)}
    try:
        from backend.services.activity_events_service import emit
        emit("security_cron_sweep", channel="ops", payload=results)
    except Exception:
        pass
    return jsonify({"success": True, "results": results}), 200
