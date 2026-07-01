"""Agent treasury deposit address + auto-distribution to trader agent wallets."""
from __future__ import annotations

import os
from flask import Blueprint, jsonify, request

agent_treasury_bp = Blueprint("agent_treasury", __name__)


def _ops_ok() -> bool:
    secret = os.environ.get("DISCORD_OPS_SECRET") or os.environ.get("ADMIN_OPS_SECRET", "")
    if not secret:
        return request.environ.get("REMOTE_ADDR") in ("127.0.0.1", "::1")
    return request.headers.get("X-Ops-Secret") == secret


@agent_treasury_bp.route("/api/agents/treasury/address", methods=["GET"])
def treasury_address():
    from backend.services.agent_wallet_service import get_treasury
    treasury = get_treasury()
    if treasury.get("address"):
        return jsonify({"success": True, **treasury}), 200
    try:
        from backend.services.mn2_rpc_client import getnewaddress
        r = getnewaddress()
        addr = (r.get("result") or "").strip() if isinstance(r, dict) else None
        if addr:
            from backend.services.agent_wallet_service import set_treasury_address
            saved = set_treasury_address(addr)
            return jsonify({"success": True, **saved}), 200
        err = (r.get("error") if isinstance(r, dict) else None) or "getnewaddress returned no address"
        return jsonify({"success": False, "error": str(err), "treasury": treasury}), 503
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc), "treasury": treasury}), 503


@agent_treasury_bp.route("/api/agents/treasury/distribute", methods=["POST"])
def treasury_distribute():
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.agent_wallet_service import get_treasury, credit, list_wallets
    treasury = get_treasury()
    per_agent = float(treasury.get("per_agent_mn2") or 100000)
    count = int(treasury.get("trader_agent_count") or 6)
    agent_ids = [f"trader_agent_{i+1}" for i in range(count)]
    existing = {w["agent_id"] for w in list_wallets()}
    results = []
    for aid in agent_ids:
        ref = f"treasury-fund:{aid}"
        if aid in existing and get_balance_safe(aid) >= per_agent:
            results.append({"agent_id": aid, "skipped": True, "reason": "already_funded"})
            continue
        r = credit(aid, per_agent, reference=ref, source="agent_treasury")
        results.append(r)
    from backend.services.activity_events_service import emit
    emit("agent_treasury_distribute", channel="agents", payload={"results": results})
    return jsonify({"success": True, "distributed": results, "per_agent_mn2": per_agent}), 200


def get_balance_safe(agent_id: str) -> float:
    from backend.services.agent_wallet_service import get_balance
    return get_balance(agent_id)
