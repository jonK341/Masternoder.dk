"""Agent treasury deposit address, dry-run status, sign-off, and gated distribution.

Option C: default ``live_distribute=false`` — status/dry-run only; no 600k auto-send.
"""
from __future__ import annotations

import os
from flask import Blueprint, jsonify, request

agent_treasury_bp = Blueprint("agent_treasury", __name__)


def _ops_ok() -> bool:
    secret = (
        os.environ.get("MN2_OPS_SECRET")
        or os.environ.get("DISCORD_OPS_SECRET")
        or os.environ.get("ADMIN_OPS_SECRET")
        or ""
    ).strip()
    provided = (
        request.headers.get("X-Ops-Secret")
        or request.args.get("token")
        or ""
    ).strip()
    if not secret:
        return request.environ.get("REMOTE_ADDR") in ("127.0.0.1", "::1")
    return bool(provided) and provided == secret


def _deny():
    return jsonify({"success": False, "error": "admin_required"}), 403


@agent_treasury_bp.route("/api/agents/treasury/address", methods=["GET"])
def treasury_address():
    """Ops-gated: return or create the ONE agent-treasury deposit address."""
    if not _ops_ok():
        return _deny()
    from backend.services.agent_wallet_service import (
        get_treasury,
        load_agent_funding_config,
        set_treasury_address,
        treasury_status,
    )
    treasury = get_treasury()
    cfg = load_agent_funding_config()
    if treasury.get("address"):
        status = treasury_status()
        return jsonify({"success": True, **treasury, "status": status}), 200
    try:
        from backend.services.mn2_rpc_client import getnewaddress
        r = getnewaddress()
        addr = (r.get("result") or "").strip() if isinstance(r, dict) else None
        if addr:
            saved = set_treasury_address(
                addr,
                per_agent_mn2=cfg["per_agent_mn2"],
                trader_count=cfg["trader_agent_count"],
                live_distribute=False,
            )
            return jsonify({"success": True, **saved, "status": treasury_status()}), 200
        err = (r.get("error") if isinstance(r, dict) else None) or "getnewaddress returned no address"
        return jsonify({"success": False, "error": str(err), "treasury": treasury, "config": cfg}), 503
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc), "treasury": treasury, "config": cfg}), 503


@agent_treasury_bp.route("/api/agents/treasury/status", methods=["GET"])
def treasury_status_route():
    """Dry-run funding status — never moves funds."""
    if not _ops_ok():
        return _deny()
    from backend.services.agent_wallet_service import treasury_status
    return jsonify(treasury_status()), 200


@agent_treasury_bp.route("/api/agents/treasury/reconcile", methods=["GET"])
def treasury_reconcile():
    if not _ops_ok():
        return _deny()
    from backend.services.treasury_signoff_service import reconcile_snapshot
    snap = reconcile_snapshot()
    return jsonify({"success": True, "reconcile": snap}), 200


@agent_treasury_bp.route("/api/agents/treasury/sign-off", methods=["GET", "POST"])
def treasury_signoff():
    if not _ops_ok():
        return _deny()
    from backend.services import treasury_signoff_service as tss
    if request.method == "GET":
        return jsonify(tss.get_signoff()), 200
    body = request.get_json(silent=True) or {}
    r = tss.record_signoff(
        approver=str(body.get("approver") or ""),
        cold_wallet_address=str(body.get("cold_wallet_address") or ""),
        hot_cap_mn2=body.get("hot_cap_mn2"),
        max_batch_mn2=float(body.get("max_batch_mn2") or 600000),
        notes=str(body.get("notes") or ""),
        require_reconcile_ok=bool(body.get("require_reconcile_ok")),
    )
    code = 200 if r.get("success") else 400
    return jsonify(r), code


@agent_treasury_bp.route("/api/agents/treasury/distribute", methods=["POST"])
def treasury_distribute():
    """Distribute only when live_distribute is armed; default is dry-run."""
    if not _ops_ok():
        return _deny()
    body = request.get_json(silent=True) or {}
    force_dry = bool(body.get("dry_run") or request.args.get("dry_run"))
    from backend.services.agent_wallet_service import distribute_agent_funding, load_agent_funding_config
    cfg = load_agent_funding_config()
    if force_dry or not cfg.get("live_distribute"):
        r = distribute_agent_funding(dry_run=True)
        r["message"] = (
            "dry_run_only — set data/mn2_config.json agent_funding.live_distribute=true "
            "and complete cold-wallet sign-off before live distribution"
        )
        return jsonify(r), 200
    r = distribute_agent_funding(dry_run=False)
    code = 200 if r.get("success") else 403
    if r.get("error") == "insufficient_treasury_pool":
        code = 409
    return jsonify(r), code
