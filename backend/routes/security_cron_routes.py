"""Security cron HTTP endpoints (Phase 9)."""
from __future__ import annotations

import os
from flask import Blueprint, jsonify, request

security_cron_bp = Blueprint("security_cron", __name__)


def _ops_ok() -> bool:
    secret = (
        os.environ.get("MN2_OPS_SECRET")
        or os.environ.get("DISCORD_OPS_SECRET")
        or os.environ.get("ADMIN_OPS_SECRET")
        or ""
    ).strip()
    provided = (
        request.headers.get("X-Ops-Secret")
        or request.args.get("ops_secret")
        or request.args.get("token")
        or ""
    ).strip()
    if not secret:
        return request.environ.get("REMOTE_ADDR") in ("127.0.0.1", "::1")
    return bool(provided) and provided == secret


@security_cron_bp.route("/api/security/cron/presets", methods=["GET"])
def security_presets():
    from backend.services.security_cron_service import list_presets
    return jsonify(list_presets()), 200


@security_cron_bp.route("/api/security/cron/sweep", methods=["POST"])
def security_sweep():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    body = request.get_json(silent=True) or {}
    try:
        drift_limit = int(body.get("drift_limit") or request.args.get("drift_limit") or 100)
    except (TypeError, ValueError):
        drift_limit = 100
    preset = (body.get("preset") or request.args.get("preset") or "sweep").strip().lower()
    jobs = body.get("jobs")
    if isinstance(jobs, str):
        jobs = [j.strip() for j in jobs.split(",") if j.strip()]
    if not isinstance(jobs, list):
        jobs = None
    from backend.services.security_cron_service import run_security_sweep
    results = run_security_sweep(drift_limit=drift_limit, jobs=jobs, preset=preset if not jobs else None)
    status = 200 if results.get("ok") else 207
    return jsonify(results), status


@security_cron_bp.route("/api/security/cron/backup", methods=["POST"])
def security_backup():
    """Gate S: scheduled MN2/economy backup (ops/cron only)."""
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    try:
        from backend.services.backup_service import run_backup
        result = run_backup()
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@security_cron_bp.route("/api/security/cron/run", methods=["POST"])
def security_cron_run():
    """Alias for sweep with explicit preset/jobs (agent_cron-compatible)."""
    return security_sweep()
