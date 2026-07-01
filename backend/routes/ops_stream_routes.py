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
    return out


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


@ops_stream_bp.route("/api/ops/health", methods=["GET"])
def ops_health():
    """Unified ops health: daemons, treasury, masternode hosting, payout."""
    from flask import jsonify
    from datetime import datetime, timezone

    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    out: dict = {
        "success": True,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    try:
        from scripts.daemon_inventory import collect
        out["daemon_inventory"] = collect()
    except Exception as exc:
        out["daemon_inventory"] = {"success": False, "error": str(exc)}
    try:
        from backend.services.exchange_treasury_service import treasury_status
        out["treasury"] = treasury_status()
    except Exception as exc:
        out["treasury"] = {"success": False, "error": str(exc)}
    try:
        from backend.services.mn2_masternode_service import get_service_status
        out["masternode_hosting"] = get_service_status()
    except Exception as exc:
        out["masternode_hosting"] = {"success": False, "error": str(exc)}
    try:
        from backend.services.exchange_payout_service import payout_status
        out["payout"] = payout_status()
    except Exception as exc:
        out["payout"] = {"success": False, "error": str(exc)}
    return jsonify(out), 200
