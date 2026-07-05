"""
Platform upgrade roadmap API — batch 1 (100) and batch 2 (200).
"""
from flask import Blueprint, jsonify, request

from backend.middleware.response_cache_middleware import cached_response
from backend.services.platform_upgrades_batch2_service import get_batch2_roadmap, get_batch2_widgets
from backend.services.platform_upgrades_service import get_area_summary, get_roadmap

platform_upgrades_bp = Blueprint("platform_upgrades", __name__)


@platform_upgrades_bp.route("/api/platform/upgrades", methods=["GET"])
@cached_response(ttl=60)
def platform_upgrades_roadmap():
    area = request.args.get("area")
    return jsonify(get_roadmap(area)), 200


@platform_upgrades_bp.route("/api/platform/area/<area>/summary", methods=["GET"])
def platform_area_summary(area: str):
    user_id = request.args.get("user_id")
    data = get_area_summary(area, user_id=user_id)
    code = 200 if data.get("success") else 404
    return jsonify(data), code


@platform_upgrades_bp.route("/api/platform/health", methods=["GET"])
@cached_response(ttl=30)
def platform_cross_health():
    areas = ["explorer", "exchange", "command-center"]
    snapshots = {}
    for a in areas:
        snapshots[a] = get_area_summary(a)
    return jsonify({
        "success": True,
        "areas": snapshots,
        "roadmap": get_roadmap(),
        "batch2": get_batch2_roadmap(),
    }), 200


@platform_upgrades_bp.route("/api/platform/upgrades/batch2", methods=["GET"])
@cached_response(ttl=60)
def platform_upgrades_batch2_roadmap():
    area = request.args.get("area")
    return jsonify(get_batch2_roadmap(area)), 200


@platform_upgrades_bp.route("/api/platform/batch2/<area>/widgets", methods=["GET"])
def platform_batch2_widgets(area: str):
    user_id = request.args.get("user_id")
    data = get_batch2_widgets(area, user_id=user_id)
    code = 200 if data.get("success") else 404
    return jsonify(data), code


@platform_upgrades_bp.route("/api/platform/quests/claim-all", methods=["POST", "GET"])
def platform_quests_claim_all():
    """Batch-2 #276 — claim all ready quests."""
    data = request.get_json(silent=True) or {}
    uid = (request.args.get("user_id") or data.get("user_id") or "").strip()
    if not uid:
        return jsonify({"success": False, "error": "user_id required"}), 400
    claimed = []
    try:
        from backend.services.trophy_quest_service import get_unified_quests, claim_quest
        qs = get_unified_quests(uid)
        pool = qs if isinstance(qs, list) else (qs.get("quests") or qs.get("daily") or [])
        for q in pool:
            if isinstance(q, dict) and (q.get("claimable") or q.get("ready")):
                out = claim_quest(uid, q.get("id") or q.get("quest_id"))
                if out.get("success"):
                    claimed.append(q.get("id") or q.get("quest_id"))
    except Exception:
        pass
    return jsonify({"success": True, "user_id": uid, "claimed": claimed, "count": len(claimed)}), 200


@platform_upgrades_bp.route("/api/platform/batch2/<area>/extras", methods=["GET"])
def platform_batch2_extras(area: str):
    user_id = request.args.get("user_id")
    from backend.services.platform_batch2_extras_service import enrich_area_widgets
    base = get_batch2_widgets(area, user_id=user_id)
    if not base.get("success"):
        return jsonify(base), 404
    return jsonify(base), 200


@platform_upgrades_bp.route("/api/platform/batch2/explorer/wallet-qr", methods=["GET"])
def platform_batch2_explorer_wallet_qr():
    from backend.services.platform_batch2_remaining_service import wallet_qr_payload
    address = request.args.get("address")
    return jsonify(wallet_qr_payload(address)), 200


@platform_upgrades_bp.route("/api/platform/generator/reorder-queue", methods=["POST"])
def platform_generator_reorder_queue():
    data = request.get_json(silent=True) or {}
    job_ids = data.get("job_ids") or request.args.getlist("job_id")
    from backend.services.platform_batch2_remaining_service import reorder_generator_queue
    return jsonify(reorder_generator_queue(job_ids)), 200


@platform_upgrades_bp.route("/api/platform/generator/export-inventory", methods=["POST", "GET"])
def platform_generator_export_inventory():
    data = request.get_json(silent=True) or {}
    uid = (request.args.get("user_id") or data.get("user_id") or "").strip()
    if not uid:
        return jsonify({"success": False, "error": "user_id required"}), 400
    job_id = request.args.get("job_id") or data.get("job_id")
    from backend.services.platform_batch2_remaining_service import export_generator_to_inventory
    return jsonify(export_generator_to_inventory(uid, job_id=job_id)), 200


@platform_upgrades_bp.route("/api/platform/upgrades/combined", methods=["GET"])
@cached_response(ttl=60)
def platform_upgrades_combined():
    b1 = get_roadmap()
    b2 = get_batch2_roadmap()
    return jsonify({
        "success": True,
        "batch1": {"total": b1.get("total"), "done": b1.get("done"), "planned": b1.get("planned")},
        "batch2": {"total": b2.get("total"), "done": b2.get("done"), "planned": b2.get("planned")},
        "combined_total": (b1.get("total") or 0) + (b2.get("total") or 0),
        "combined_done": (b1.get("done") or 0) + (b2.get("done") or 0),
    }), 200
