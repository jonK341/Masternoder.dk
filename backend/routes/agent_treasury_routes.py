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
    public = {
        "success": True,
        "configured": bool(treasury.get("address")),
        "per_agent_mn2": treasury.get("per_agent_mn2") or 100000,
        "trader_agent_count": treasury.get("trader_agent_count") or 6,
    }
    if not _ops_ok():
        return jsonify(public), 200

    if treasury.get("address"):
        try:
            from backend.services.admin_audit_service import log_action
            log_action("treasury_address_view", actor="ops", payload={"configured": True})
        except Exception:
            pass
        from backend.services.agent_wallet_service import (
            get_treasury_pool_balance,
            scan_treasury_onchain_deposits,
            sync_treasury_pool_from_ledger,
        )
        scan = scan_treasury_onchain_deposits()
        sync_treasury_pool_from_ledger()
        return jsonify({
            **public,
            **treasury,
            "treasury_pool_balance_mn2": get_treasury_pool_balance(),
            "required_total_mn2": (treasury.get("per_agent_mn2") or 100000) * (treasury.get("trader_agent_count") or 6),
            "last_treasury_scan": scan,
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
                log_action("treasury_address_created", actor="ops", payload={"address_prefix": addr[:8]})
            except Exception:
                pass
            return jsonify({"success": True, **saved}), 200
        err = (r.get("error") if isinstance(r, dict) else None) or "getnewaddress returned no address"
        return jsonify({"success": False, "error": str(err), "treasury": treasury}), 503
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc), "treasury": treasury}), 503


@agent_treasury_bp.route("/api/agents/treasury/sign-off", methods=["GET", "POST"])
def treasury_sign_off():
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services import treasury_signoff_service as tss
    if request.method == "GET":
        return jsonify(tss.get_signoff()), 200
    body = request.get_json(silent=True) or {}
    result = tss.record_signoff(
        approver=(body.get("approver") or body.get("approved_by") or "ops").strip(),
        cold_wallet_address=(body.get("cold_wallet_address") or body.get("cold_wallet") or "").strip(),
        hot_cap_mn2=body.get("hot_cap_mn2"),
        max_batch_mn2=float(body.get("max_batch_mn2") or 600000),
        notes=(body.get("notes") or "").strip(),
        require_reconcile_ok=bool(body.get("require_reconcile_ok")),
    )
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@agent_treasury_bp.route("/api/agents/treasury/reconcile", methods=["GET"])
def treasury_reconcile_snapshot():
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.treasury_signoff_service import reconcile_snapshot
    snap = reconcile_snapshot()
    return jsonify({"success": True, **snap}), 200


@agent_treasury_bp.route("/api/agents/treasury/scan-deposits", methods=["POST"])
def treasury_scan_deposits():
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.agent_wallet_service import scan_treasury_onchain_deposits
    result = scan_treasury_onchain_deposits()
    code = 200 if result.get("success") else 503
    return jsonify(result), code


@agent_treasury_bp.route("/api/agents/treasury/distribute", methods=["POST"])
def treasury_distribute():
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    try:
        from backend.services.agent_wallet_service import distribute_agent_funding
        result = distribute_agent_funding()
        try:
            from backend.services.admin_audit_service import log_action
            log_action("treasury_distribute", actor="ops", payload={"distributed_total": result.get("distributed_total")})
        except Exception:
            pass
        try:
            from backend.services.activity_events_service import emit
            emit("agent_treasury_distribute", channel="agents", payload=result)
        except Exception:
            pass
        code = 200 if result.get("success") else 400
        return jsonify(result), code
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


def get_balance_safe(agent_id: str) -> float:
    from backend.services.agent_wallet_service import get_balance
    return get_balance(agent_id)
