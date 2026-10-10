"""
COGS / reference job — pricing inputs (USD, global defaults).

GET /api/system/cogs/reference-job  — estimate for the canonical reference job
GET /api/system/cogs/summary        — rates + reference (no secrets)
GET /api/system/cogs/metering-stats — p50/p90 from metering.jsonl (requires admin key)
"""
import os

from flask import Blueprint, jsonify, request

cogs_bp = Blueprint("cogs", __name__)


@cogs_bp.route("/api/system/cogs/reference-job", methods=["GET"])
def cogs_reference_job():
    from backend.services.cogs_metering_service import estimate_reference_job_usd, REFERENCE_JOB_SPEC

    return jsonify({
        "success": True,
        "reference_job": REFERENCE_JOB_SPEC,
        "estimate": estimate_reference_job_usd(),
    }), 200


@cogs_bp.route("/api/system/cogs/summary", methods=["GET"])
def cogs_summary():
    from backend.services.cogs_metering_service import summarize_effective_rates

    return jsonify({"success": True, **summarize_effective_rates()}), 200


@cogs_bp.route("/api/system/cogs/metering-stats", methods=["GET"])
def cogs_metering_stats():
    """
    Aggregate stats from logs/cogs/metering.jsonl (p50/p90, line items, ratio vs reference).
    Set COGS_ADMIN_REPORT_KEY in the environment; send the same value in header
    X-Cogs-Admin-Key or query ?key=
    """
    expected = (os.environ.get("COGS_ADMIN_REPORT_KEY") or "").strip()
    if not expected:
        return jsonify({"success": False, "error": "metering_stats_disabled", "hint": "set COGS_ADMIN_REPORT_KEY"}), 503
    supplied = (request.headers.get("X-Cogs-Admin-Key") or request.args.get("key") or "").strip()
    if supplied != expected:
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.cogs_metering_service import summarize_metering_jsonl

    data = summarize_metering_jsonl()
    if not data.get("success"):
        return jsonify(data), 404
    return jsonify({"success": True, **data}), 200
