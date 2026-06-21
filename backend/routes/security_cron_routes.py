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
        from backend.services.backup_service import run_backup
        results["backup"] = run_backup()
    except Exception as exc:
        results["backup"] = {"error": str(exc)}
    try:
        from backend.services.mn2_deposit_scanner import run_scanner
        results["deposit_rescan"] = run_scanner()
    except Exception as exc:
        results["deposit_rescan"] = {"error": str(exc)}
    try:
        results["anomaly"] = _anomaly_sweep()
    except Exception as exc:
        results["anomaly"] = {"error": str(exc)}
    try:
        from backend.services.mn2_balance_commit import recover_stale
        results["commit_recovery"] = recover_stale(max_age_minutes=30)
    except Exception as exc:
        results["commit_recovery"] = {"error": str(exc)}
    try:
        from backend.services.webhook_outbox import process_pending
        results["webhook_outbox"] = process_pending(limit=50)
    except Exception as exc:
        results["webhook_outbox"] = {"error": str(exc)}
    try:
        from backend.services.casino_discord_fanout import run_fanout
        results["casino_discord_fanout"] = run_fanout()
    except Exception as exc:
        results["casino_discord_fanout"] = {"error": str(exc)}
    try:
        from backend.services.activity_events_service import emit
        emit("security_cron_sweep", channel="ops", payload=results)
    except Exception:
        pass
    return jsonify({"success": True, "results": results}), 200


def _anomaly_sweep() -> dict:
    """Flag users with excessive MN2 earn events in the last 24h."""
    import json
    from datetime import datetime, timezone, timedelta
    from collections import Counter

    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base, "logs", "activity_events.jsonl")
    if not os.path.isfile(path):
        return {"success": True, "flagged": []}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    counts: Counter = Counter()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            ts = row.get("ts") or row.get("timestamp") or ""
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                continue
            if dt < cutoff:
                continue
            et = row.get("type") or row.get("event") or ""
            if et in ("game_mn2_reward", "generator_mn2_credit", "debugger_quiz"):
                uid = row.get("user_id") or ""
                if uid:
                    counts[uid] += 1
    flagged = [{"user_id": uid, "earn_events_24h": n} for uid, n in counts.items() if n > 50]
    return {"success": True, "flagged": flagged, "threshold": 50}


@security_cron_bp.route("/api/security/cron/backup", methods=["POST"])
def security_backup():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    from backend.services.backup_service import run_backup
    return jsonify(run_backup()), 200
