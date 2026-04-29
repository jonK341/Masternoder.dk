"""
COGS / reference job — pricing inputs (USD, global defaults).

GET /api/system/cogs/reference-job  — estimate for the canonical reference job
GET /api/system/cogs/summary        — rates + reference (no secrets)
GET /api/system/cogs/metering-stats — p50/p90 from metering.jsonl (requires admin key)
"""
import os
import urllib.parse
import uuid

from flask import Blueprint, jsonify, request

cogs_bp = Blueprint("cogs", __name__)


@cogs_bp.route("/api/system/cogs/reference-job", methods=["GET"])
def cogs_reference_job():
    from backend.services.cogs_metering_service import estimate_reference_job_usd, REFERENCE_JOB_SPEC

    return jsonify({
        "success": True,
        "reference_job": REFERENCE_JOB_SPEC,
        "estimate": estimate_reference_job_usd(),
    }), 200


@cogs_bp.route("/api/system/cogs/summary", methods=["GET"])
def cogs_summary():
    from backend.services.cogs_metering_service import summarize_effective_rates

    return jsonify({"success": True, **summarize_effective_rates()}), 200


@cogs_bp.route("/api/system/cogs/metering-stats", methods=["GET"])
def cogs_metering_stats():
    """
    Aggregate stats from logs/cogs/metering.jsonl (p50/p90, line items, ratio vs reference).
    Set COGS_ADMIN_REPORT_KEY in the environment; send the same value in header
    X-Cogs-Admin-Key or query ?key=
    """
    expected = (os.environ.get("COGS_ADMIN_REPORT_KEY") or "").strip()
    if not expected:
        return jsonify({"success": False, "error": "metering_stats_disabled", "hint": "set COGS_ADMIN_REPORT_KEY"}), 503
    supplied = (request.headers.get("X-Cogs-Admin-Key") or request.args.get("key") or "").strip()
    if supplied != expected:
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.cogs_metering_service import summarize_metering_jsonl

    data = summarize_metering_jsonl()
    if not data.get("success"):
        return jsonify(data), 404
    return jsonify({"success": True, **data}), 200


@cogs_bp.route("/api/monetization/report", methods=["GET"])
def monetization_revenue_report():
    """
    Phase 4 report: payment ledger + MN2 shop ledger + COGS metering.

    Requires COGS_ADMIN_REPORT_KEY via X-Cogs-Admin-Key or ?key=.
    Query:
      since_days=N
      scr_only=1
      mn2_usd_price=0.001  (optional estimate; otherwise env MN2_USD_PRICE)
    """
    expected = (os.environ.get("COGS_ADMIN_REPORT_KEY") or "").strip()
    if not expected:
        return jsonify({"success": False, "error": "monetization_report_disabled", "hint": "set COGS_ADMIN_REPORT_KEY"}), 503
    supplied = (request.headers.get("X-Cogs-Admin-Key") or request.args.get("key") or "").strip()
    if supplied != expected:
        return jsonify({"success": False, "error": "unauthorized"}), 401

    def _float_arg(name):
        raw = (request.args.get(name) or "").strip()
        if not raw:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    since_days = _float_arg("since_days")
    mn2_usd_price = _float_arg("mn2_usd_price")
    scr_only = (request.args.get("scr_only") or "").strip().lower() in ("1", "true", "yes")

    from backend.services.monetization_scr_blend_service import run_ledger_metering_blend

    out = run_ledger_metering_blend(
        ledger_path=None,
        metering_path=None,
        mn2_ledger_path=None,
        mn2_usd_price=mn2_usd_price,
        since_days=since_days,
        scr_only=scr_only,
    )
    return jsonify(out), 200


@cogs_bp.route("/api/monetization/config", methods=["GET"])
def monetization_public_config():
    """Pack SKUs, credit ↔ reference definition, tier ids — from data/monetization_config.json."""
    try:
        from backend.services.monetization_config_service import get_public_config

        return jsonify({"success": True, **get_public_config()}), 200
    except Exception as e:
        return jsonify({
            "success": True,
            "degraded": True,
            "error": str(e),
            "reference_job_id": None,
            "credit_definition": {"reference_fraction_per_credit": 0.25},
            "coin_packs": [],
            "tiers": ["creator"],
            "default_tier": "creator",
            "subscriptions": {"plans": {}},
            "b2b_studio_skus": [],
        }), 200


@cogs_bp.route("/api/monetization/webhooks/paypal-subscription", methods=["POST"])
def monetization_paypal_subscription_webhook():
    """
    PayPal Subscriptions webhook URL — configure the same path in the PayPal developer dashboard.

    Verification: set PAYPAL_WEBHOOK_ID; optional PAYPAL_WEBHOOK_BYPASS=1 for local testing only.
    """
    import os

    body = request.get_json(force=True, silent=True) or {}
    if not isinstance(body, dict) or not body:
        return jsonify({"success": False, "error": "expected_json_body"}), 400

    bypass = (os.environ.get("PAYPAL_WEBHOOK_BYPASS") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    wid = (os.environ.get("PAYPAL_WEBHOOK_ID") or "").strip()
    if not bypass and not wid:
        return jsonify({
            "success": False,
            "error": "webhook_not_configured",
            "hint": "Set PAYPAL_WEBHOOK_ID (and PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET) or PAYPAL_WEBHOOK_BYPASS=1 for dev only.",
        }), 503

    if not bypass:
        from backend.services.paypal_webhook_service import verify_paypal_webhook_signature

        if not verify_paypal_webhook_signature(request.headers, body):
            return jsonify({"success": False, "error": "webhook_verification_failed"}), 401

    from backend.services.monetization_subscription_service import process_paypal_webhook_event

    payload, status = process_paypal_webhook_event(body)
    return jsonify(payload), status


def _subscription_shop_base_url() -> str:
    base = (os.environ.get("BASE_URL") or "").strip().rstrip("/")
    if base.endswith("/vidgenerator"):
        base = base.rsplit("/vidgenerator", 1)[0]
    if not base:
        base = request.url_root.rstrip("/")
    return base


@cogs_bp.route("/api/monetization/subscription/create", methods=["POST"])
def monetization_subscription_create():
    """
    Start PayPal Subscriptions checkout: returns approve_url.
    Body: { "plan_id": "P-..." } (optional if config has exactly one plan).
    """
    from backend.services.account_resolution_service import resolve_user_id
    from backend.services.monetization_config_service import get_subscription_plan, list_subscription_plan_ids
    from backend.services.paypal_service import create_billing_subscription

    data = request.get_json() or {}
    user_id = (data.get("user_id") or "").strip() or resolve_user_id()
    if not user_id or str(user_id).strip().lower() in ("", "default_user"):
        return jsonify({
            "success": False,
            "error": "ACCOUNT_REQUIRED",
            "message": "Log in or create an account before subscribing.",
        }), 400

    plan_id = (data.get("plan_id") or "").strip()
    if not plan_id:
        ids = list_subscription_plan_ids()
        if len(ids) == 1:
            plan_id = ids[0]
    if not plan_id:
        return jsonify({"success": False, "error": "plan_id_required"}), 400

    pinfo = get_subscription_plan(plan_id)
    if not pinfo:
        return jsonify({"success": False, "error": "unknown_plan_id", "plan_id": plan_id}), 400

    base = _subscription_shop_base_url()
    q = urllib.parse.urlencode({
        "paypal_subscription": "success",
        "plan_id": plan_id,
        "user_id": user_id,
    })
    return_url = f"{base}/shop?{q}"
    cancel_url = f"{base}/shop?paypal_subscription=cancel&plan_id={urllib.parse.quote(plan_id, safe='')}"

    result = create_billing_subscription(
        plan_id,
        custom_id=user_id,
        return_url=return_url,
        cancel_url=cancel_url,
    )
    if not result.get("success"):
        return jsonify({
            "success": False,
            "error": result.get("error", "paypal_subscription_create_failed"),
        }), 502
    return jsonify({
        "success": True,
        "subscription_id": result.get("subscription_id"),
        "status": result.get("status"),
        "approve_url": result.get("approve_url"),
        "plan_id": plan_id,
    }), 200


@cogs_bp.route("/api/monetization/subscription/bind", methods=["POST"])
def monetization_subscription_bind():
    """
    After the user approves a PayPal subscription, call with { subscription_id, plan_id }
    so recurring PAYMENT.SALE.COMPLETED events can grant coins/credits to the right account.
    """
    from backend.services.account_resolution_service import resolve_user_id
    from backend.services.monetization_subscription_service import save_subscription_binding

    data = request.get_json() or {}
    user_id = (data.get("user_id") or "").strip() or resolve_user_id()
    subscription_id = (data.get("subscription_id") or "").strip()
    plan_id = (data.get("plan_id") or "").strip()

    if not user_id or str(user_id).strip().lower() in ("", "default_user"):
        return jsonify({
            "success": False,
            "error": "ACCOUNT_REQUIRED",
            "message": "Log in or create an account before binding a subscription.",
        }), 400

    out = save_subscription_binding(subscription_id, user_id, plan_id)
    if not out.get("success"):
        return jsonify(out), 400
    return jsonify(out), 200


_ALLOWED_DEAL_KINDS = frozenset({"b2b_block", "deposit", "invoice_settlement"})


@cogs_bp.route("/api/monetization/b2b/record-payment", methods=["POST"])
def monetization_b2b_record_payment():
    """
    Studio Cash Rail (§4): append one cash line to payment_ledger.jsonl for wire / invoice / manual settlement.

    Set B2B_LEDGER_SECRET in the environment; send the same value in header
    X-B2B-Ledger-Key or query ?key=
    """
    expected = (os.environ.get("B2B_LEDGER_SECRET") or "").strip()
    if not expected:
        return jsonify({"success": False, "error": "b2b_ledger_disabled", "hint": "set B2B_LEDGER_SECRET"}), 503
    supplied = (request.headers.get("X-B2B-Ledger-Key") or request.args.get("key") or "").strip()
    if supplied != expected:
        return jsonify({"success": False, "error": "unauthorized"}), 401

    data = request.get_json() or {}
    user_id = (data.get("user_id") or "").strip()
    if not user_id or user_id.lower() == "default_user":
        return jsonify({"success": False, "error": "user_id_required"}), 400

    try:
        amount_usd = float(data.get("amount_usd", 0) or 0)
    except (TypeError, ValueError):
        amount_usd = 0.0
    if amount_usd <= 0:
        return jsonify({"success": False, "error": "amount_usd_must_be_positive"}), 400

    deal_kind = (data.get("deal_kind") or "").strip().lower()
    if deal_kind not in _ALLOWED_DEAL_KINDS:
        return jsonify({
            "success": False,
            "error": "invalid_deal_kind",
            "allowed": sorted(_ALLOWED_DEAL_KINDS),
        }), 400

    from backend.services.monetization_config_service import get_b2b_studio_sku, reload_monetization_config
    from backend.services.monetization_ledger_service import append_payment_event

    reload_monetization_config()
    studio_sku_id = (data.get("studio_sku_id") or "").strip()
    sku = get_b2b_studio_sku(studio_sku_id) if studio_sku_id else {}
    if studio_sku_id and not sku:
        return jsonify({"success": False, "error": "unknown_studio_sku_id", "studio_sku_id": studio_sku_id}), 400

    gen_credits = data.get("generation_credits_granted")
    if gen_credits is None and sku.get("generation_credits_pool") is not None:
        try:
            gen_credits = float(sku["generation_credits_pool"])
        except (TypeError, ValueError):
            gen_credits = 0.0
    else:
        try:
            gen_credits = float(gen_credits or 0)
        except (TypeError, ValueError):
            gen_credits = 0.0

    try:
        coins_granted = int(data.get("coins_granted", 0) or 0)
    except (TypeError, ValueError):
        coins_granted = 0

    invoice_ref = (data.get("invoice_ref") or "").strip()
    org_label = (data.get("org_label") or "").strip()
    currency = (data.get("currency") or "USD").strip() or "USD"

    ledger_order = (data.get("ledger_order_id") or invoice_ref or "").strip() or f"b2b-{uuid.uuid4().hex[:20]}"
    item_id = studio_sku_id or deal_kind
    item_name = (sku.get("label") or "").strip() or f"SCR {deal_kind}"

    append_payment_event(
        provider="b2b_scr",
        user_id=user_id,
        order_id=ledger_order,
        capture_id=None,
        amount_usd=amount_usd,
        currency=currency,
        item_id=item_id,
        item_name=item_name,
        coins_granted=coins_granted,
        generation_credits_granted=gen_credits,
        subscription_id=None,
        deal_kind=deal_kind,
        invoice_ref=invoice_ref or None,
        org_label=org_label or None,
        studio_sku_id=studio_sku_id or None,
        extra=data.get("extra") if isinstance(data.get("extra"), dict) else None,
    )

    return jsonify({
        "success": True,
        "ledger_order_id": ledger_order,
        "deal_kind": deal_kind,
        "amount_usd": amount_usd,
        "generation_credits_granted": gen_credits,
    }), 200
