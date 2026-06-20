"""
Unified ops SSE stream — conservation, RPC, generation, worker pressure, webhooks, kill switch.
"""
from __future__ import annotations

import json
import os
import time

from flask import Blueprint, Response, request, stream_with_context

ops_stream_bp = Blueprint("ops_stream", __name__)


def _ops_authorized() -> bool:
    secret = (os.environ.get("MN2_OPS_SECRET") or os.environ.get("MN2_SCAN_SECRET") or "").strip()
    if not secret:
        return True
    token = (
        request.headers.get("X-Ops-Token")
        or request.headers.get("X-Scanner-Token")
        or request.args.get("token")
        or ""
    ).strip()
    return token == secret


def _snapshot() -> dict:
    out: dict = {"ts": time.time()}
    try:
        from backend.services.mn2_conservation_gate import conservation_gate
        cg = conservation_gate()
        out["conservation"] = {"verdict": cg.get("verdict"), "ok": cg.get("ok")}
    except Exception as e:
        out["conservation"] = {"error": str(e)}
    try:
        from backend.services.mn2_rpc_client import health_check
        out["mn2_rpc"] = health_check()
    except Exception as e:
        out["mn2_rpc"] = {"status": "error", "error": str(e)}
    try:
        from backend.services.video_generator_service import _check_generation_services
        ok, msg, detail = _check_generation_services()
        out["generation"] = {"ready": ok, "message": msg, "detail": detail}
    except Exception as e:
        out["generation"] = {"ready": False, "error": str(e)}
    try:
        from backend.services.worker_pressure_service import worker_pressure
        out["worker_pressure"] = worker_pressure()
    except Exception as e:
        out["worker_pressure"] = {"error": str(e)}
    try:
        from backend.services.webhook_outbox import stats as wh_stats
        out["webhook_outbox"] = wh_stats()
    except Exception as e:
        out["webhook_outbox"] = {"error": str(e)}
    try:
        from backend.services.agent_kill_switch import get_status
        out["agent_kill_switch"] = get_status()
    except Exception as e:
        out["agent_kill_switch"] = {"error": str(e)}
    try:
        from backend.services.video_job_queue import queue_status
        out["video_queue"] = queue_status()
    except Exception as e:
        out["video_queue"] = {"error": str(e)}
    try:
        from backend.services.mn2_float_gate import assess
        out["float_gate"] = assess(0)
    except Exception as e:
        out["float_gate"] = {"error": str(e)}
    try:
        from backend.services.house_income_aggregator import summarize
        out["house_income_24h"] = summarize(since_hours=24)
    except Exception as e:
        out["house_income_24h"] = {"error": str(e)}
    try:
        from backend.services.generator_agent_service import get_generator_ops_snapshot
        gen = get_generator_ops_snapshot()
        out["generator"] = {
            "queue": gen.get("queue"),
            "last_24h": gen.get("last_24h"),
        }
    except Exception as e:
        out["generator"] = {"error": str(e)}
    return out


def _public_snapshot() -> dict:
    """Redacted ops view for browser control board (no RPC keys, no raw webhook payloads)."""
    full = _snapshot()
    wh = full.get("webhook_outbox") or {}
    pending = 0
    if isinstance(wh.get("by_status"), dict):
        pending = int(wh["by_status"].get("pending") or 0)
    fg = full.get("float_gate") or {}
    return {
        "ts": full.get("ts"),
        "conservation": full.get("conservation"),
        "worker_pressure": {
            "score": (full.get("worker_pressure") or {}).get("score"),
            "recommendation": (full.get("worker_pressure") or {}).get("recommendation"),
        },
        "video_queue": {
            "queued": (full.get("video_queue") or {}).get("queued"),
            "active": (full.get("video_queue") or {}).get("active"),
        },
        "generator": {
            "last_24h_success_rate": ((full.get("generator") or {}).get("last_24h") or {}).get("success_rate_percent"),
            "last_24h_total_jobs": ((full.get("generator") or {}).get("last_24h") or {}).get("total_jobs"),
        },
        "agent_kill_switch": {
            "global_halt": (full.get("agent_kill_switch") or {}).get("global_halt"),
        },
        "webhook_outbox": {"pending": pending},
        "float_gate": {"verdict": fg.get("verdict"), "allowed": fg.get("allowed")},
        "house_income_24h": {
            "combined_house": (full.get("house_income_24h") or {}).get("combined_house"),
        },
    }


@ops_stream_bp.route("/api/ops/stream", methods=["GET"])
def ops_stream():
    if not _ops_authorized():
        return Response('data: {"error":"Unauthorized"}\n\n', status=403, mimetype="text/event-stream")

    interval = max(5, min(int(request.args.get("interval", 15)), 60))

    def generate():
        yield "data: " + json.dumps({"type": "connected", "interval_sec": interval}) + "\n\n"
        while True:
            try:
                snap = _snapshot()
                yield "data: " + json.dumps({"type": "ops", **snap}) + "\n\n"
            except Exception as e:
                yield "data: " + json.dumps({"type": "error", "error": str(e)}) + "\n\n"
            time.sleep(interval)

    resp = Response(stream_with_context(generate()), mimetype="text/event-stream")
    resp.headers["X-Accel-Buffering"] = "no"
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["Connection"] = "keep-alive"
    return resp


@ops_stream_bp.route("/api/ops/snapshot", methods=["GET"])
def ops_snapshot():
    """Poll fallback for ops stream."""
    from flask import jsonify
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    return jsonify({"success": True, **_snapshot()}), 200


@ops_stream_bp.route("/api/ops/public-snapshot", methods=["GET"])
def ops_public_snapshot():
    """Browser-safe ops metrics for agents control board."""
    from flask import jsonify
    return jsonify({"success": True, **_public_snapshot()}), 200


@ops_stream_bp.route("/api/ops/public-stream", methods=["GET"])
def ops_public_stream():
    """SSE stream with redacted ops metrics (no ops secret required)."""
    interval = max(5, min(int(request.args.get("interval", 15)), 60))

    def generate():
        yield "data: " + json.dumps({"type": "connected", "interval_sec": interval}) + "\n\n"
        while True:
            try:
                snap = _public_snapshot()
                yield "data: " + json.dumps({"type": "ops", **snap}) + "\n\n"
            except Exception as e:
                yield "data: " + json.dumps({"type": "error", "error": str(e)}) + "\n\n"
            time.sleep(interval)

    resp = Response(stream_with_context(generate()), mimetype="text/event-stream")
    resp.headers["X-Accel-Buffering"] = "no"
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["Connection"] = "keep-alive"
    return resp
