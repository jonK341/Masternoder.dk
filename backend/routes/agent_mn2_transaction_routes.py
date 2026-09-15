"""Agent API for MN2 transaction cron — settlement, daemon probe, activity burst."""
import os
from flask import Blueprint, jsonify, request

agent_mn2_tx_bp = Blueprint("agent_mn2_tx", __name__)


def _authorized() -> bool:
    configured = []
    for key in ("AGENT_CRON_SECRET", "MN2_OPS_SECRET", "MN2_SCAN_SECRET"):
        secret = (os.environ.get(key) or "").strip()
        if secret:
            configured.append(secret)
    if not configured:
        return True
    tok = (
        request.headers.get("X-Agent-Cron-Token")
        or request.headers.get("X-Ops-Token")
        or request.headers.get("X-Scanner-Token")
        or request.args.get("token")
        or ""
    ).strip()
    return tok in configured


@agent_mn2_tx_bp.route("/api/agent/mn2/daemon/health", methods=["GET"])
def agent_mn2_daemon_health():
    """Probe masternoder2d RPC (block height, wallet). Public read."""
    from backend.services.mn2_daemon_health_service import probe_daemon
    extended = request.args.get("extended", "1") != "0"
    return jsonify(probe_daemon(extended=extended)), 200


@agent_mn2_tx_bp.route("/api/agent/mn2/transactions/run", methods=["POST", "GET"])
def agent_mn2_transactions_run():
    """
    Run MN2 ecosystem settlement (battle, aggregator, generator, casino, staking, daemon, chain).
    Auth: AGENT_CRON_SECRET, MN2_OPS_SECRET, or MN2_SCAN_SECRET.
    Query/body: systems=all|daemon,battle,...  dry_run=1
    """
    if not _authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    systems_raw = data.get("systems") or request.args.get("systems") or "all"
    if isinstance(systems_raw, str):
        systems = [s.strip() for s in systems_raw.split(",") if s.strip()]
    else:
        systems = list(systems_raw) if systems_raw else ["all"]
    dry_run = (request.args.get("dry_run") == "1") or data.get("dry_run") is True
    from backend.services.agent_mn2_settlement_service import run_mn2_ecosystem_settlement
    result = run_mn2_ecosystem_settlement(systems=systems, dry_run=dry_run)
    status = 200 if result.get("success") else 500
    return jsonify(result), status


@agent_mn2_tx_bp.route("/api/agent/mn2/activity/burst", methods=["POST"])
def agent_mn2_activity_burst():
    """Emit extra agent activity events (profile feed). Auth required."""
    if not _authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    try:
        max_events = int(data.get("max_events") or request.args.get("max_events") or 12)
    except (TypeError, ValueError):
        max_events = 12
    from backend.services.agent_mn2_settlement_service import _burst_agent_activity
    return jsonify({"success": True, "result": _burst_agent_activity(max_events=max_events)}), 200


@agent_mn2_tx_bp.route("/api/agent/mn2/masternodes/status", methods=["GET"])
def agent_mn2_masternodes_status():
    from backend.services.mn2_masternode_service import rented_masternodes_snapshot
    return jsonify(rented_masternodes_snapshot()), 200


@agent_mn2_tx_bp.route("/api/agent/mn2/micro/burst", methods=["POST", "GET"])
def agent_mn2_micro_burst():
    """Dust on-chain MN2 micro-transaction burst. Auth required."""
    if not _authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    dry_run = (request.args.get("dry_run") == "1") or data.get("dry_run") is True
    try:
        max_txs = int(data.get("max_txs") or request.args.get("max_txs") or 80)
    except (TypeError, ValueError):
        max_txs = 80
    from backend.services.mn2_micro_transactions_service import run_micro_transaction_burst
    result = run_micro_transaction_burst(max_txs=max_txs, dry_run=dry_run)
    status = 200 if result.get("success") else 503
    return jsonify(result), status


@agent_mn2_tx_bp.route("/api/agent/mn2/masternodes/bring-online", methods=["POST"])
def agent_mn2_masternodes_bring_online():
    if not _authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.mn2_masternode_service import bring_rented_masternodes_online
    result = bring_rented_masternodes_online()
    status = 200 if result.get("success") else 503
    return jsonify(result), status
