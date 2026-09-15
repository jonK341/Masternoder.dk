"""
Agent automation: MN2-backed shop purchases for headless / cron / LLM agents.
Requires AGENT_MN2_SHOP_SECRET; send X-Agent-Shop-Key on POST.
"""
import os
import json
from flask import Blueprint, jsonify, request

agent_shop_crypto_bp = Blueprint("agent_shop_crypto", __name__)


def _data_path() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "data", "agent_crypto_wallet_agents.json")


def _authorized() -> bool:
    secret = (os.environ.get("AGENT_MN2_SHOP_SECRET") or "").strip()
    if not secret:
        return False
    got = (request.headers.get("X-Agent-Shop-Key") or request.args.get("agent_shop_key") or "").strip()
    return got == secret


@agent_shop_crypto_bp.route("/api/agent/shop/crypto-wallet-agents", methods=["GET"])
def list_crypto_wallet_agents():
    """Personas that can obtain shop items via MN2 (configure user_id per environment)."""
    agents = []
    path = _data_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, list):
                agents = raw
            elif isinstance(raw, dict) and isinstance(raw.get("agents"), list):
                agents = raw["agents"]
        except Exception:
            pass
    secret_set = bool((os.environ.get("AGENT_MN2_SHOP_SECRET") or "").strip())
    return jsonify({
        "success": True,
        "agents": agents,
        "execute_endpoint": "/api/agent/shop/execute-mn2-purchase",
        "auth": "Header X-Agent-Shop-Key (set AGENT_MN2_SHOP_SECRET on server)" if secret_set else "AGENT_MN2_SHOP_SECRET not set — POST execute is disabled",
    }), 200


@agent_shop_crypto_bp.route("/api/agent/shop/execute-mn2-purchase", methods=["POST"])
def execute_mn2_purchase():
    """
    Body JSON: user_id, item_id, quantity (optional), agent_id (optional, for activity log).
    Deducts in-wallet MN2 and grants item (same as shop payment_method=mn2).
    """
    if not _authorized():
        return jsonify({
            "success": False,
            "error": "Unauthorized",
            "hint": "Set AGENT_MN2_SHOP_SECRET in .env and send header X-Agent-Shop-Key with the same value.",
        }), 403
    data = request.get_json() or {}
    try:
        from backend.services.agent_kill_switch import check_action
        agent_id = (data.get("agent_id") or "").strip() or "crypto_wallet_agent"
        halt = check_action("execute_mn2_purchase", agent_id=agent_id)
        if not halt.get("allowed"):
            return jsonify({"success": False, **halt}), 503
    except ImportError:
        pass
    user_id = (data.get("user_id") or request.args.get("user_id") or "").strip()
    item_id = (data.get("item_id") or "").strip()
    agent_id = (data.get("agent_id") or "").strip() or "crypto_wallet_agent"
    try:
        quantity = max(1, int(data.get("quantity", 1)))
    except (TypeError, ValueError):
        quantity = 1
    if not user_id or not item_id:
        return jsonify({"success": False, "error": "user_id and item_id required"}), 400

    from backend.services.shop_mn2_purchase_core import purchase_with_mn2_balance

    body, status = purchase_with_mn2_balance(user_id, item_id, quantity, agent_id=agent_id)
    return jsonify(body), status


@agent_shop_crypto_bp.route("/api/agent/shop/tick", methods=["POST"])
def agent_shop_tick():
    """Cron/agent finish-move: buy cheapest catalog items with MN2 for bound users."""
    if not _authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    data = request.get_json(silent=True) or {}
    dry_run = bool(data.get("dry_run") or request.args.get("dry_run"))
    try:
        max_purchases = int(data.get("max_purchases") or request.args.get("max_purchases") or 6)
    except (TypeError, ValueError):
        max_purchases = 6
    from backend.services.agent_shop_tick_service import run_agent_shop_tick
    return jsonify(run_agent_shop_tick(max_purchases=max_purchases, dry_run=dry_run)), 200
