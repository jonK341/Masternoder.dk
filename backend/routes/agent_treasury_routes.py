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
    """Gate S: treasury deposit address is ops-only (not public)."""
    if not _ops_ok():
        return jsonify({
            "success": True,
            "ops_only": True,
            "message": "Treasury address available to authenticated ops only",
        }), 200
    from backend.services.agent_wallet_service import get_treasury
    treasury = get_treasury()
    if treasury.get("address"):
        pool = 0.0
        try:
            from backend.services.agent_wallet_service import get_treasury_pool_balance
            pool = get_treasury_pool_balance()
        except Exception:
            pass
        return jsonify({
            "success": True,
            **treasury,
            "pool_balance_mn2": pool,
            "required_total_mn2": float(treasury.get("per_agent_mn2") or 100000) * int(treasury.get("trader_agent_count") or 6),
        }), 200
    try:
        from backend.services.mn2_rpc_client import getnewaddress
        r = getnewaddress()
        addr = (r.get("result") or "").strip() if isinstance(r, dict) else None
        if addr:
            from backend.services.agent_wallet_service import set_treasury_address
            saved = set_treasury_address(addr)
            try:
                from backend.services.admin_audit_service import log_action
                log_action("treasury_address_created", actor="ops", payload={"address_prefix": addr[:12]})
            except Exception:
                pass
            return jsonify({"success": True, **saved}), 200
        err = (r.get("error") if isinstance(r, dict) else None) or "getnewaddress returned no address"
        return jsonify({"success": False, "error": str(err), "treasury": treasury}), 503
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc), "treasury": treasury}), 503


@agent_treasury_bp.route("/api/agents/treasury/sign-off", methods=["GET", "POST"])
def treasury_signoff():
    """Gate S: cold-wallet sign-off before large agent funding batches."""
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.treasury_signoff_service import get_signoff, record_signoff

    if request.method == "GET":
        return jsonify(get_signoff()), 200

    body = request.get_json(silent=True) or {}
    approver = (body.get("approver") or request.headers.get("X-Ops-Actor") or "ops").strip()
    result = record_signoff(
        approver=approver,
        cold_wallet_address=(body.get("cold_wallet_address") or "").strip(),
        max_batch_mn2=body.get("max_batch_mn2"),
        hot_cap_mn2=body.get("hot_cap_mn2"),
        notes=(body.get("notes") or "").strip(),
    )
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@agent_treasury_bp.route("/api/agents/treasury/distribute", methods=["POST"])
def treasury_distribute():
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.agent_wallet_service import distribute_agent_funding

    result = distribute_agent_funding()
    if not result.get("success"):
        return jsonify(result), 403

    try:
        from backend.services.admin_audit_service import log_action
        log_action(
            "agent_treasury_distribute",
            actor=request.headers.get("X-Ops-Actor") or "ops",
            payload={
                "per_agent_mn2": result.get("per_agent_mn2"),
                "pool_balance": result.get("pool_balance"),
                "results_count": len(result.get("results") or []),
            },
        )
    except Exception:
        pass

    from backend.services.activity_events_service import emit
    emit("agent_treasury_distribute", channel="agents", payload=result)
    return jsonify(result), 200


@agent_treasury_bp.route("/api/agents/treasury/status", methods=["GET"])
def treasury_status():
    """Pool balance, per-agent targets, and wallet balances (ops or localhost)."""
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.agent_wallet_service import (
        get_treasury,
        get_treasury_pool_balance,
        list_wallets,
    )
    treasury = get_treasury()
    per_agent = float(treasury.get("per_agent_mn2") or 100000)
    count = int(treasury.get("trader_agent_count") or 6)
    agents = []
    for w in list_wallets():
        aid = w.get("agent_id", "")
        if aid.startswith("trader_agent_"):
            agents.append(w)
    return jsonify({
        "success": True,
        "treasury": treasury,
        "pool_balance_mn2": get_treasury_pool_balance(),
        "required_total_mn2": per_agent * count,
        "trader_agents": agents,
    }), 200
