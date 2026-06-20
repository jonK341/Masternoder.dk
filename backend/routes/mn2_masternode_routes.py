"""
MN2 masternode hosting + unified services catalog routes.

Public:
  GET /api/mn2/services           — all MN2 platform services in one place
  GET /api/mn2/masternode/service — hosting offer + live status

Ops (X-Ops-Token / MN2_OPS_SECRET):
  GET  /api/mn2/masternode/hosts
  POST /api/mn2/masternode/hosts
  DELETE /api/mn2/masternode/hosts/<host_id>
  GET  /api/mn2/masternode/collateral-outputs
"""
import os
from flask import Blueprint, jsonify, request

from backend.services.account_resolution_service import resolve_user_id
from backend.services import mn2_masternode_service as mn_service
from backend.services import mn2_masternode_hosting_service as mn_hosting
from backend.services import mn2_services_hub as services_hub

mn2_masternode_bp = Blueprint("mn2_masternode", __name__)


def _ops_authorized() -> bool:
    secret = (os.environ.get("MN2_OPS_SECRET") or os.environ.get("MN2_SCAN_SECRET") or "").strip()
    if not secret:
        return True
    token = (
        request.headers.get("X-Ops-Token")
        or request.headers.get("X-Scanner-Token")
        or request.headers.get("X-Ops-Secret")
        or request.args.get("token")
        or ""
    ).strip()
    return token == secret


def _body() -> dict:
    return request.get_json(silent=True) or {}


@mn2_masternode_bp.route("/api/mn2/services", methods=["GET"])
def mn2_services_catalog():
    """Unified MN2 services registry with live status probes."""
    try:
        use_cache = request.args.get("fresh") not in ("1", "true", "yes")
        return jsonify(services_hub.get_services_catalog(use_cache=use_cache)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_masternode_bp.route("/api/mn2/services/<service_id>", methods=["GET"])
def mn2_service_detail(service_id: str):
    try:
        svc = services_hub.get_service_by_id((service_id or "").strip())
        if not svc:
            return jsonify({"success": False, "error": "service not found"}), 404
        return jsonify({"success": True, "service": svc}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_masternode_bp.route("/api/mn2/masternode/service", methods=["GET"])
def masternode_service_public():
    """Public hosting service snapshot (capacity, network, platform nodes)."""
    try:
        return jsonify(mn_service.get_service_status()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_masternode_bp.route("/api/mn2/masternode/hosts", methods=["GET"])
def masternode_hosts_list():
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    try:
        include_internal = request.args.get("internal") in ("1", "true", "yes")
        return jsonify({
            "success": True,
            "hosts": mn_service.list_hosts(include_internal=include_internal),
            "status": mn_service.get_service_status(),
        }), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_masternode_bp.route("/api/mn2/masternode/hosts", methods=["POST"])
def masternode_hosts_register():
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    try:
        result = mn_service.register_host(_body())
        code = 200 if result.get("success") else 400
        return jsonify(result), code
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_masternode_bp.route("/api/mn2/masternode/hosts/<host_id>", methods=["DELETE"])
def masternode_hosts_remove(host_id: str):
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    try:
        result = mn_service.remove_host(host_id)
        code = 200 if result.get("success") else 404
        return jsonify(result), code
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_masternode_bp.route("/api/mn2/masternode/collateral-outputs", methods=["GET"])
def masternode_collateral_outputs():
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    try:
        return jsonify(mn_service.list_collateral_outputs()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_masternode_bp.route("/api/mn2/masternode/checkout/config", methods=["GET"])
def masternode_checkout_config():
    try:
        result = mn_hosting.get_paypal_config()
        st = mn_service.get_service_status()
        sample = mn_hosting.pricing_for_slots(1)
        return jsonify({
            "success": True,
            **result,
            "slots_available": st.get("slots_available"),
            "hosted_count": st.get("hosted_count"),
            "collateral_mn2": st.get("collateral_mn2"),
            "pricing_sample": sample,
        }), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_masternode_bp.route("/api/mn2/masternode/checkout/quote", methods=["GET", "POST"])
def masternode_checkout_quote():
    try:
        user_id = resolve_user_id(from_body=True, from_query=True)
        slots = _body().get("slots") if request.method == "POST" else request.args.get("slots", 1)
        if slots is None:
            slots = request.args.get("slots", 1)
        result = mn_hosting.get_quote(slots, user_id)
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_masternode_bp.route("/api/mn2/masternode/checkout/order", methods=["POST"])
def masternode_checkout_order():
    try:
        data = _body()
        user_id = resolve_user_id(from_body=True, from_query=True)
        result = mn_hosting.create_order(
            quote_id=(data.get("quote_id") or "").strip(),
            user_id=user_id,
            return_url=data.get("return_url"),
            cancel_url=data.get("cancel_url"),
            promo_code=(data.get("promo_code") or "").strip() or None,
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_masternode_bp.route("/api/mn2/masternode/checkout/capture", methods=["POST"])
def masternode_checkout_capture():
    try:
        data = _body()
        user_id = resolve_user_id(from_body=True, from_query=True)
        result = mn_hosting.capture(
            order_id=(data.get("order_id") or data.get("quote_id") or "").strip(),
            user_id=user_id,
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_masternode_bp.route("/api/mn2/masternode/checkout/status", methods=["GET"])
def masternode_checkout_status():
    try:
        user_id = resolve_user_id(from_body=False, from_query=True)
        order_id = (request.args.get("order_id") or request.args.get("quote_id") or "").strip()
        if not order_id:
            return jsonify({"success": False, "error": "order_id required"}), 400
        return jsonify(mn_hosting.get_order(order_id, user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_masternode_bp.route("/api/mn2/masternode/checkout/pay-coins", methods=["POST"])
def masternode_checkout_pay_coins():
    try:
        data = _body()
        user_id = resolve_user_id(from_body=True, from_query=True)
        quote_id = (data.get("quote_id") or data.get("order_id") or "").strip()
        if not quote_id:
            return jsonify({"success": False, "error": "quote_id required"}), 400
        result = mn_hosting.purchase_with_coins(quote_id, user_id)
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_masternode_bp.route("/api/mn2/masternode/checkout/pay-mn2", methods=["POST"])
def masternode_checkout_pay_mn2():
    try:
        data = _body()
        user_id = resolve_user_id(from_body=True, from_query=True)
        quote_id = (data.get("quote_id") or data.get("order_id") or "").strip()
        if not quote_id:
            return jsonify({"success": False, "error": "quote_id required"}), 400
        result = mn_hosting.purchase_with_mn2_balance(quote_id, user_id)
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_masternode_bp.route("/api/mn2/masternode/checkout/pay-onchain", methods=["POST"])
def masternode_checkout_pay_onchain():
    try:
        data = _body()
        user_id = resolve_user_id(from_body=True, from_query=True)
        quote_id = (data.get("quote_id") or data.get("order_id") or "").strip()
        if not quote_id:
            return jsonify({"success": False, "error": "quote_id required"}), 400
        result = mn_hosting.create_onchain_payment(quote_id, user_id)
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_masternode_bp.route("/api/mn2/masternode/webhook", methods=["POST"])
def masternode_paypal_webhook():
    """PayPal webhook — auto-capture and provision slots without browser return."""
    try:
        event = request.get_json(silent=True) or {}
        try:
            from backend.services.paypal_webhook_service import verify_paypal_webhook_signature
            signature_ok = verify_paypal_webhook_signature(request.headers, event)
        except Exception:
            signature_ok = False
        result = mn_hosting.handle_webhook(event, signature_ok)
        if isinstance(result, dict) and result.get("error") == "Webhook signature not verified":
            return jsonify(result), 400
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_masternode_bp.route("/api/mn2/masternode/provision-pending", methods=["POST"])
def masternode_provision_pending():
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    try:
        raw_limit = request.args.get("limit", 20)
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            limit = 20
        return jsonify(mn_service.process_pending_hosts(limit=limit)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_masternode_bp.route("/api/mn2/masternode/purge-stale-hosts", methods=["POST"])
def masternode_purge_stale_hosts():
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    try:
        data = _body()
        max_age = data.get("max_age_hours")
        if max_age is None:
            max_age = request.args.get("max_age_hours", 6)
        force = bool(data.get("force_no_collateral") or request.args.get("force_no_collateral"))
        dry_run = bool(data.get("dry_run") or request.args.get("dry_run"))
        result = mn_service.purge_stale_provisioning_hosts(
            max_age_hours=float(max_age),
            force_no_collateral=force,
            dry_run=dry_run,
        )
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
