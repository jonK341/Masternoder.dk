"""
Agent automation layer for MN2 staking.

Gives headless / cron / LLM agents full parity with the user staking UI:
discover capabilities, read status/monitor, and execute stake/unstake/accept-terms/
auto-compound/heartbeat actions.

Requires AGENT_MN2_STAKING_SECRET (falls back to AGENT_MN2_SHOP_SECRET).
Send the key as header X-Agent-Staking-Key (or ?agent_staking_key=).
Read-only discovery/status endpoints are always available.
"""
import os
from flask import Blueprint, jsonify, request

import backend.services.mn2_staking_service as staking

agent_staking_bp = Blueprint("agent_staking", __name__)


def _secret() -> str:
    return (os.environ.get("AGENT_MN2_STAKING_SECRET")
            or os.environ.get("AGENT_MN2_SHOP_SECRET")
            or "").strip()


def _authorized() -> bool:
    secret = _secret()
    if not secret:
        return False
    got = (request.headers.get("X-Agent-Staking-Key")
           or request.args.get("agent_staking_key") or "").strip()
    return got == secret


_CAPABILITIES = [
    {"action": "accept_terms", "method": "POST", "params": ["user_id", "version?"],
     "description": "Accept the current staking terms for a user (required before staking)."},
    {"action": "stake", "method": "POST", "params": ["user_id", "amount"],
     "description": "Move MN2 from balance into the staking pool."},
    {"action": "unstake", "method": "POST", "params": ["user_id", "amount"],
     "description": "Instantly move staked MN2 back to balance."},
    {"action": "set_auto_compound", "method": "POST", "params": ["user_id", "enabled"],
     "description": "Toggle automatic restaking of rewards."},
    {"action": "heartbeat", "method": "POST", "params": ["user_id", "proof?", "nonce?"],
     "description": "Submit a staking-rig participation heartbeat (boosts reward weight)."},
    {"action": "status", "method": "GET", "params": ["user_id"],
     "description": "Read a user's full staking status."},
    {"action": "calculator", "method": "GET", "params": ["amount", "days?", "uptime?", "boost?"],
     "description": "Estimate rewards (no state change)."},
    {"action": "rewards_table", "method": "GET", "params": ["user_id", "limit?"],
     "description": "Read a user's per-interval reward history."},
    {"action": "monitor", "method": "GET", "params": ["limit?"],
     "description": "Read anonymized pool-wide staking processes and aggregates."},
    {"action": "onramp_quote", "method": "POST", "params": ["user_id", "usd"],
     "description": "Get a time-boxed PayPal->MN2 quote (KYC caps apply)."},
    {"action": "onramp_order", "method": "POST", "params": ["user_id", "quote_id", "return_url?", "cancel_url?"],
     "description": "Create the PayPal order for a quote; returns approve_url for the user to pay."},
    {"action": "onramp_status", "method": "GET", "params": ["user_id", "order_id?"],
     "description": "Poll an on-ramp order, or list the user's on-ramp orders + held MN2."},
    {"action": "p2p_listings", "method": "GET", "params": ["limit?"],
     "description": "List open P2P MN2 sell listings (Model B; guarded)."},
    {"action": "p2p_create_listing", "method": "POST", "params": ["user_id", "mn2_amount", "price_usd_per_mn2"],
     "description": "Escrow MN2 and list it for USD sale (seller verification may apply)."},
    {"action": "p2p_buy", "method": "POST", "params": ["user_id", "listing_id", "mn2_amount?", "return_url?", "cancel_url?"],
     "description": "Buy MN2 from a listing via PayPal; returns approve_url."},
    {"action": "p2p_status", "method": "GET", "params": ["user_id", "order_id?"],
     "description": "Poll a P2P order, or list the user's listings/purchases + payout balance."},
]


@agent_staking_bp.route("/api/agent/staking/capabilities", methods=["GET"])
def capabilities():
    secret_set = bool(_secret())
    return jsonify({
        "success": True,
        "capabilities": _CAPABILITIES,
        "execute_endpoint": "/api/agent/staking/execute",
        "auth": ("Header X-Agent-Staking-Key (set AGENT_MN2_STAKING_SECRET on server)"
                 if secret_set else
                 "AGENT_MN2_STAKING_SECRET not set — write actions are disabled; read actions still work"),
        "config": {
            "enabled": staking.get_config().get("enabled"),
            "min_stake": staking.get_config().get("min_stake"),
            "apr_percent": staking.dynamic_apr(),
            "terms_version": staking.get_config().get("terms_version"),
        },
    }), 200


_READ_ACTIONS = {"status", "calculator", "rewards_table", "monitor", "onramp_status",
                 "p2p_listings", "p2p_status"}


@agent_staking_bp.route("/api/agent/staking/execute", methods=["POST"])
def execute():
    data = request.get_json(silent=True) or {}
    action = (data.get("action") or request.args.get("action") or "").strip().lower()
    if not action:
        return jsonify({"success": False, "error": "action required",
                        "valid_actions": [c["action"] for c in _CAPABILITIES]}), 400

    if action not in _READ_ACTIONS and not _authorized():
        return jsonify({
            "success": False, "error": "Unauthorized",
            "hint": "Set AGENT_MN2_STAKING_SECRET and send header X-Agent-Staking-Key.",
        }), 403

    user_id = (data.get("user_id") or request.args.get("user_id") or "").strip()

    try:
        if action == "accept_terms":
            return jsonify(staking.accept_terms(user_id, data.get("version"))), 200
        if action == "stake":
            r = staking.stake(user_id, data.get("amount"))
            return jsonify(r), 200 if r.get("success") else 400
        if action == "unstake":
            r = staking.unstake(user_id, data.get("amount"))
            return jsonify(r), 200 if r.get("success") else 400
        if action == "set_auto_compound":
            return jsonify(staking.set_auto_compound(user_id, bool(data.get("enabled")))), 200
        if action == "heartbeat":
            return jsonify(staking.submit_work_proof(user_id, proof=data.get("proof"),
                                                     nonce=data.get("nonce"), ts=data.get("ts"))), 200
        if action == "status":
            return jsonify({"success": True, **staking.get_stake(user_id)}), 200
        if action == "calculator":
            return jsonify(staking.estimate_rewards(
                amount=data.get("amount", 0), days=data.get("days", 30),
                uptime=data.get("uptime", 1.0), boost=data.get("boost", 1.0))), 200
        if action == "rewards_table":
            return jsonify(staking.get_rewards_table(user_id, limit=int(data.get("limit", 100)))), 200
        if action == "monitor":
            return jsonify(staking.get_staking_monitor(limit=int(data.get("limit", 50)))), 200
        if action in ("onramp_quote", "onramp_order", "onramp_status"):
            import backend.services.mn2_onramp_service as onramp
            if action == "onramp_quote":
                r = onramp.get_quote(data.get("usd"), user_id)
                return jsonify(r), 200 if r.get("success") else 400
            if action == "onramp_order":
                r = onramp.create_order(quote_id=(data.get("quote_id") or "").strip(), user_id=user_id,
                                        return_url=data.get("return_url"), cancel_url=data.get("cancel_url"))
                return jsonify(r), 200 if r.get("success") else 400
            order_id = (data.get("order_id") or "").strip()
            if order_id:
                return jsonify(onramp.get_status(order_id, user_id)), 200
            return jsonify(onramp.get_user_orders(user_id)), 200
        if action in ("p2p_listings", "p2p_create_listing", "p2p_buy", "p2p_status"):
            import backend.services.mn2_p2p_service as p2p
            if action == "p2p_listings":
                return jsonify(p2p.list_listings(limit=int(data.get("limit", 100)))), 200
            if action == "p2p_create_listing":
                r = p2p.create_listing(user_id, data.get("mn2_amount"), data.get("price_usd_per_mn2"))
                return jsonify(r), 200 if r.get("success") else 400
            if action == "p2p_buy":
                r = p2p.create_purchase(user_id, (data.get("listing_id") or "").strip(),
                                        mn2_amount=data.get("mn2_amount"),
                                        return_url=data.get("return_url"), cancel_url=data.get("cancel_url"))
                return jsonify(r), 200 if r.get("success") else 400
            order_id = (data.get("order_id") or "").strip()
            if order_id:
                return jsonify(p2p.get_order(order_id, user_id)), 200
            return jsonify(p2p.get_user_overview(user_id)), 200
        return jsonify({"success": False, "error": f"unknown action '{action}'",
                        "valid_actions": [c["action"] for c in _CAPABILITIES]}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
