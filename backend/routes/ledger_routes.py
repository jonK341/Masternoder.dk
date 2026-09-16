"""Community ledger sales and agent chat routes."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, request

ledger_bp = Blueprint("ledger", __name__)


def _ops_ok() -> bool:
    secret = os.environ.get("DISCORD_OPS_SECRET", "")
    if not secret:
        return False
    return request.headers.get("X-Ops-Secret") == secret or request.args.get("ops_secret") == secret


@ledger_bp.route("/api/ledger/sales/queue", methods=["GET"])
def ledger_sales_queue():
    """Ops/camgirls — pending ledger rows eligible for outreach."""
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    from backend.services.ledger_coin_sales_service import get_sales_queue

    limit = request.args.get("limit", 50, type=int)
    return jsonify(get_sales_queue(limit=limit)), 200


@ledger_bp.route("/api/ledger/sales/offer", methods=["POST"])
def ledger_sales_offer():
    """Create MN2 coin sale offer (PayPal / USDT / USDC)."""
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    body = request.get_json(silent=True) or {}
    from backend.services.ledger_coin_sales_service import create_offer

    result = create_offer(
        ledger_row_id=(body.get("ledger_row_id") or "").strip(),
        mn2_amount=float(body.get("mn2_amount") or body.get("amount_mn2") or 0),
        price_usd=float(body.get("price_usd") or 0),
        rail=(body.get("rail") or body.get("rails") or "paypal"),
        performer_id=(body.get("performer_id") or body.get("camgirl_id") or "").strip() or None,
        agent_id=(body.get("agent_id") or "").strip() or None,
        operator=(body.get("operator") or request.headers.get("X-Ops-User") or "ops").strip(),
    )
    return jsonify(result), 200 if result.get("success") else 400


@ledger_bp.route("/api/ledger/sales/fulfill", methods=["POST"])
def ledger_sales_fulfill():
    """Fulfill offer after payment capture."""
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    body = request.get_json(silent=True) or {}
    offer_id = (body.get("offer_id") or "").strip()
    if not offer_id:
        return jsonify({"success": False, "error": "offer_id required"}), 400
    from backend.services.ledger_coin_sales_service import fulfill_offer

    result = fulfill_offer(
        offer_id,
        payment_ref=(body.get("payment_ref") or body.get("order_id") or "").strip() or None,
        capture=body.get("capture"),
        operator=(body.get("operator") or request.headers.get("X-Ops-User") or "ops").strip(),
    )
    return jsonify(result), 200 if result.get("success") else 400


@ledger_bp.route("/api/ledger/sales/offers", methods=["GET"])
def ledger_sales_offers_list():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    from backend.services.ledger_coin_sales_service import list_offers

    lid = (request.args.get("ledger_row_id") or "").strip() or None
    return jsonify(list_offers(ledger_row_id=lid)), 200


@ledger_bp.route("/api/ledger/agent/chat", methods=["POST"])
def ledger_agent_chat():
    """Agent/camgirl sends message to ledger customer."""
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    body = request.get_json(silent=True) or {}
    from backend.services.ledger_agent_service import post_chat_message

    result = post_chat_message(
        (body.get("ledger_row_id") or "").strip(),
        (body.get("message") or "").strip(),
        sender=(body.get("sender") or "agent").strip(),
        sender_id=(body.get("sender_id") or body.get("agent_id") or body.get("camgirl_id") or "").strip() or None,
        camgirl_persona=(body.get("camgirl_persona") or body.get("persona") or "").strip() or None,
    )
    return jsonify(result), 200 if result.get("success") else 400


@ledger_bp.route("/api/ledger/agent/thread", methods=["GET"])
def ledger_agent_thread():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    lid = (request.args.get("ledger_row_id") or "").strip()
    if not lid:
        return jsonify({"success": False, "error": "ledger_row_id required"}), 400
    from backend.services.ledger_agent_service import get_thread

    return jsonify(get_thread(lid)), 200


@ledger_bp.route("/api/ledger/agent/greet", methods=["POST"])
def ledger_agent_greet():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    body = request.get_json(silent=True) or {}
    from backend.services.ledger_agent_service import auto_greet

    result = auto_greet((body.get("ledger_row_id") or "").strip(), force=bool(body.get("force")))
    return jsonify(result), 200 if result.get("success") else 400


@ledger_bp.route("/api/ledger/population/sources", methods=["GET"])
def ledger_population_sources():
    from backend.services.community_ledger_population import load_population_catalog

    return jsonify({"success": True, **load_population_catalog()}), 200
