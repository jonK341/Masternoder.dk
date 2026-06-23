"""
Routes for pay-to-click ads, sponsored click quests, and traffic rotators.
"""
import os
from flask import Blueprint, jsonify, redirect, request

from backend.services.account_resolution_service import resolve_user_id
import backend.services.ptc_ads_service as ptc


ptc_ads_bp = Blueprint("ptc_ads", __name__)


def _client_ip() -> str:
    forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return forwarded or request.remote_addr or ""


def _admin_authorized() -> bool:
    secret = (
        os.environ.get("PTC_ADS_ADMIN_KEY")
        or os.environ.get("AGENT_MN2_SHOP_SECRET")
        or os.environ.get("B2B_LEDGER_SECRET")
        or ""
    ).strip()
    if not secret:
        return False
    got = (
        request.headers.get("X-PTC-Admin-Key")
        or request.headers.get("X-Agent-Shop-Key")
        or request.args.get("ptc_admin_key")
        or ""
    ).strip()
    return got == secret


def _admin_actor() -> str:
    return (
        request.headers.get("X-Agent-Id")
        or request.headers.get("X-Admin-User")
        or request.args.get("actor")
        or "admin"
    ).strip()


@ptc_ads_bp.route("/api/ptc/rotator", methods=["GET"])
def ptc_rotator():
    placement = (request.args.get("placement") or "home_smartlinks").strip()
    limit = request.args.get("limit", 2)
    campaigns = ptc.get_rotator_campaigns(placement, limit=limit)
    return jsonify({"success": True, "placement": placement, "campaigns": campaigns}), 200


@ptc_ads_bp.route("/api/ptc/impression", methods=["POST"])
def ptc_impression():
    data = request.get_json() or {}
    user_id = resolve_user_id(from_body=True, from_query=True)
    result = ptc.record_impression(
        campaign_id=(data.get("campaign_id") or "").strip(),
        placement=(data.get("placement") or request.args.get("placement") or "").strip(),
        user_id=user_id,
        ip=_client_ip(),
        user_agent=request.headers.get("User-Agent", ""),
    )
    return jsonify(result), 200 if result.get("success") else 400


@ptc_ads_bp.route("/api/ptc/click/start", methods=["POST"])
def ptc_click_start():
    data = request.get_json() or {}
    user_id = resolve_user_id(from_body=True, from_query=True)
    result = ptc.start_click(
        campaign_id=(data.get("campaign_id") or "").strip(),
        placement=(data.get("placement") or "").strip(),
        user_id=user_id,
        ip=_client_ip(),
        user_agent=request.headers.get("User-Agent", ""),
        impression_id=(data.get("impression_id") or "").strip(),
    )
    return jsonify(result), 200 if result.get("success") else 400


@ptc_ads_bp.route("/api/ptc/click/redirect", methods=["GET"])
def ptc_click_redirect():
    destination = ptc.get_click_destination((request.args.get("click_id") or "").strip())
    if not destination:
        return redirect("/", code=302)
    return redirect(destination, code=302)


@ptc_ads_bp.route("/api/ptc/click/verify", methods=["POST"])
def ptc_click_verify():
    data = request.get_json() or {}
    user_id = resolve_user_id(from_body=True, from_query=True)
    result = ptc.verify_click(
        click_id=(data.get("click_id") or "").strip(),
        user_id=user_id,
        ip=_client_ip(),
    )
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@ptc_ads_bp.route("/api/ptc/click-quests", methods=["GET"])
def ptc_click_quests():
    user_id = resolve_user_id(from_body=False, from_query=True)
    limit = request.args.get("limit", 3)
    return jsonify({"success": True, "quests": ptc.click_quests(user_id, limit=limit)}), 200


@ptc_ads_bp.route("/api/ptc/advertiser-packages", methods=["GET"])
def ptc_advertiser_packages():
    return jsonify({"success": True, "packages": ptc.get_advertiser_packages()}), 200


@ptc_ads_bp.route("/api/ptc/admin/report", methods=["GET"])
def ptc_admin_report():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    campaign_id = (request.args.get("campaign_id") or "").strip() or None
    return jsonify(ptc.campaign_report(campaign_id=campaign_id)), 200


@ptc_ads_bp.route("/api/ptc/admin/campaign", methods=["POST"])
def ptc_admin_campaign():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    data = request.get_json() or {}
    result = ptc.upsert_campaign(data, actor=_admin_actor())
    return jsonify(result), 200 if result.get("success") else 400


@ptc_ads_bp.route("/api/ptc/admin/campaign/<campaign_id>/status", methods=["POST"])
def ptc_admin_campaign_status(campaign_id):
    if not _admin_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    data = request.get_json() or {}
    result = ptc.set_campaign_status(campaign_id, data.get("status"), actor=_admin_actor())
    return jsonify(result), 200 if result.get("success") else 400


@ptc_ads_bp.route("/api/ptc/admin/budget-event", methods=["POST"])
def ptc_admin_budget_event():
    if not _admin_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    data = request.get_json() or {}
    result = ptc.record_budget_event(
        package_id=(data.get("package_id") or "").strip(),
        campaign_id=(data.get("campaign_id") or "").strip(),
        provider=(data.get("provider") or "manual").strip(),
        amount=data.get("amount") or 0,
        actor=_admin_actor(),
        metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else {},
    )
    return jsonify(result), 200 if result.get("success") else 400
