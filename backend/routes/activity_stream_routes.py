"""Public activity SSE stream — casino wins, MN2 ledger, aggregator stats."""
from __future__ import annotations

import json
import time

from flask import Blueprint, Response, jsonify, request, stream_with_context

activity_stream_bp = Blueprint("activity_stream", __name__)


@activity_stream_bp.route("/api/activity/stream", methods=["GET"])
def activity_stream():
    interval = max(3, min(int(request.args.get("interval", 10)), 60))
    sounds = request.args.get("sounds", "1").strip().lower() not in ("0", "false", "no")

    def generate():
        yield "data: " + json.dumps({
            "type": "connected",
            "interval_sec": interval,
            "sounds": sounds,
        }) + "\n\n"
        last_sig = None
        while True:
            try:
                from backend.services.activity_feed_service import recent_activity
                events = recent_activity(limit=30)
                sig = json.dumps(events[:5], sort_keys=True, default=str)
                if sig != last_sig:
                    last_sig = sig
                    yield "data: " + json.dumps({
                        "type": "activity",
                        "events": events,
                        "ts": time.time(),
                    }) + "\n\n"
                else:
                    yield "data: " + json.dumps({"type": "heartbeat", "ts": time.time()}) + "\n\n"
            except Exception as exc:
                yield "data: " + json.dumps({"type": "error", "error": str(exc)}) + "\n\n"
            time.sleep(interval)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@activity_stream_bp.route("/api/activity/recent", methods=["GET"])
def activity_recent():
    try:
        from backend.services.activity_feed_service import recent_activity
        limit = int(request.args.get("limit", 25))
        return jsonify({"success": True, "events": recent_activity(limit=limit)}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
