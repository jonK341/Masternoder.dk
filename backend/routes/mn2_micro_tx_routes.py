"""
MN2 micro-transaction API — instant in-app reward payouts.

POST /api/mn2/micro-tx/payout — credit user wallet (callback or ops auth).
GET  /api/mn2/micro-tx/stats   — user or platform stats.
GET  /api/mn2/micro-tx/config  — public limits and allowed sources.
POST /api/mn2/micro-tx/ops/batch-sweep — nightly batch mark (ops auth).
"""
from __future__ import annotations

import os
from flask import Blueprint, jsonify, request

from backend.services.account_resolution_service import resolve_user_id
from backend.services.mn2_micro_tx_service import (
    get_platform_stats,
    get_public_config,
    get_user_stats,
    instant_payout,
    recent_ledger,
    run_batch_sweep,
)

mn2_micro_tx_bp = Blueprint("mn2_micro_tx", __name__)


def _body() -> dict:
    return request.get_json(silent=True) or {}


def _payout_authorized() -> bool:
    """Ops secret, callback secret, or dev bypass."""
    from backend.services.mn2_callback_auth import callback_authorized

    if callback_authorized():
        return True
    secret = (os.environ.get("MN2_OPS_SECRET") or os.environ.get("MN2_SCAN_SECRET") or "").strip()
    if not secret:
        return True
    token = (
        request.headers.get("X-Ops-Token")
        or request.headers.get("X-Ops-Secret")
        or request.headers.get("X-Scanner-Token")
        or request.args.get("token")
        or ""
    ).strip()
    return token == secret


def _ops_authorized() -> bool:
    secret = (os.environ.get("MN2_OPS_SECRET") or os.environ.get("MN2_SCAN_SECRET") or "").strip()
    if not secret:
        return True
    token = (
        request.headers.get("X-Ops-Token")
        or request.headers.get("X-Ops-Secret")
        or request.args.get("token")
        or ""
    ).strip()
    return token == secret


@mn2_micro_tx_bp.route("/api/mn2/micro-tx/payout", methods=["POST"])
def micro_tx_payout():
    """Instant MN2 micro-reward credit. Requires callback or ops auth."""
    if not _payout_authorized():
        return jsonify({"success": False, "error": "Unauthorized", "code": "auth_required"}), 403
    data = _body()
    user_id = (data.get("user_id") or "").strip()
    if not user_id:
        user_id = resolve_user_id(from_body=True, from_query=True) or ""
    amount = data.get("amount_mn2")
    if amount is None and "amount" in data:
        amount = data.get("amount")
    reason = (data.get("reason") or data.get("note") or "").strip()
    source = (data.get("source") or "manual_ops").strip()
    idem = (data.get("idempotency_key") or data.get("reference") or data.get("payout_id") or "").strip()
    meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else None
    try:
        result = instant_payout(
            user_id=user_id,
            amount_mn2=float(amount) if amount is not None else None,
            reason=reason,
            source=source,
            idempotency_key=idem or None,
            metadata=meta,
        )
        code = 200 if result.get("success") else 400
        if result.get("code") in ("auth_required", "source_denied"):
            code = 403 if result.get("code") == "source_denied" else 401
        return jsonify(result), code
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid amount_mn2"}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_micro_tx_bp.route("/api/mn2/micro-tx/stats", methods=["GET"])
def micro_tx_stats():
    """User stats (session/query user_id) or platform stats (?scope=platform)."""
    scope = (request.args.get("scope") or "user").strip().lower()
    if scope == "platform":
        if not _ops_authorized():
            return jsonify({"success": False, "error": "Ops auth required for platform stats"}), 403
        return jsonify(get_platform_stats()), 200
    user_id = (request.args.get("user_id") or "").strip()
    if not user_id:
        user_id = resolve_user_id(from_body=False, from_query=True) or ""
    return jsonify(get_user_stats(user_id)), 200


@mn2_micro_tx_bp.route("/api/mn2/micro-tx/claim-daily", methods=["POST"])
def claim_daily_reward():
    """Session-auth daily MN2 micro-reward (once per UTC day via idempotency)."""
    from datetime import datetime, timezone

    user_id = resolve_user_id(from_body=True, from_query=True) or ""
    if not user_id:
        return jsonify({"success": False, "error": "user_id required", "code": "auth_required"}), 401
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        result = instant_payout(
            user_id,
            source="daily_login",
            idempotency_key=f"daily_login:{user_id}:{today}",
            reason="Daily login reward",
        )
        if result.get("duplicate"):
            return jsonify({"success": True, "already_claimed": True, **result}), 200
        if not result.get("success"):
            code = 403 if result.get("code") == "auth_required" else 400
            return jsonify(result), code
        try:
            from backend.services.exchange_leveling_service import record_daily_login

            record_daily_login(user_id)
        except Exception:
            pass
        return jsonify({"success": True, "already_claimed": False, **result}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_micro_tx_bp.route("/api/mn2/micro-tx/config", methods=["GET"])
def micro_tx_config():
    """Public config: allowed sources and limits."""
    return jsonify(get_public_config()), 200


@mn2_micro_tx_bp.route("/api/mn2/micro-tx/ledger", methods=["GET"])
def micro_tx_ledger():
    """Recent micro-tx audit rows (ops or own user)."""
    user_id = (request.args.get("user_id") or "").strip()
    if not user_id:
        user_id = resolve_user_id(from_body=False, from_query=True) or ""
    limit = int(request.args.get("limit") or 50)
    if user_id and user_id != resolve_user_id(from_body=False, from_query=True):
        if not _ops_authorized():
            return jsonify({"success": False, "error": "Ops auth required"}), 403
    rows = recent_ledger(limit=limit, user_id=user_id or None)
    return jsonify({"success": True, "entries": rows, "count": len(rows)}), 200


@mn2_micro_tx_bp.route("/api/mn2/micro-tx/ops/batch-sweep", methods=["POST"])
def micro_tx_batch_sweep():
    """Mark users above sweep threshold (ops cron)."""
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    dry = (request.args.get("dry_run") or _body().get("dry_run") or "").lower() in ("1", "true", "yes")
    return jsonify(run_batch_sweep(dry_run=dry)), 200
