"""Create App routes — Play Store + Podcast + Super Encoder nr. 1 + agent leaderboard MN2."""
from flask import Blueprint, jsonify, request

create_app_bp = Blueprint("create_app", __name__)


def _uid() -> str:
    return (
        request.args.get("user_id")
        or (request.get_json(silent=True) or {}).get("user_id")
        or request.headers.get("X-User-Id")
        or "default_user"
    )


@create_app_bp.route("/api/create-app/catalog", methods=["GET"])
def create_app_catalog():
    from backend.services.create_app_service import catalog
    return jsonify(catalog()), 200


@create_app_bp.route("/api/create-app/apps", methods=["GET"])
def create_app_list():
    from backend.services.create_app_service import list_user_apps
    return jsonify(list_user_apps(_uid())), 200


@create_app_bp.route("/api/create-app/apps", methods=["POST"])
def create_app_post():
    from backend.services.create_app_service import create_app

    body = request.get_json(silent=True) or {}
    result = create_app(
        _uid(),
        title=str(body.get("title") or "").strip(),
        template_id=str(body.get("template_id") or "playstore_podcast"),
        quality_goal=str(body.get("quality_goal") or "balanced"),
        duration_sec=int(body.get("duration_sec") or 120),
        content_hint=str(body.get("content_hint") or body.get("prompt") or ""),
        include_playstore=bool(body.get("include_playstore", True)),
        include_podcast=bool(body.get("include_podcast", True)),
    )
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@create_app_bp.route("/api/create-app/apps/<app_id>/finish", methods=["POST"])
def create_app_finish(app_id: str):
    from backend.services.create_app_service import finish_product
    result = finish_product(_uid(), app_id)
    code = 200 if result.get("success") else 404
    return jsonify(result), code


@create_app_bp.route("/api/create-app/apps/<app_id>/encode-jobs", methods=["GET"])
def create_app_encode_jobs(app_id: str):
    from backend.services.create_app_service import get_app_encode_jobs
    result = get_app_encode_jobs(_uid(), app_id)
    code = 200 if result.get("success") else 404
    return jsonify(result), code


@create_app_bp.route("/api/create-app/apps/<app_id>/super-encode", methods=["POST"])
def create_app_super_encode(app_id: str):
    from backend.services.create_app_service import super_encode_for_app
    body = request.get_json(silent=True) or {}
    result = super_encode_for_app(_uid(), app_id, body)
    code = 200 if result.get("success") else 404
    return jsonify(result), code


@create_app_bp.route("/api/create-app/finish-checks", methods=["GET"])
def create_app_finish_checks():
    from backend.services.create_app_finish_checks import run_finish_checks
    return jsonify(run_finish_checks(_uid())), 200


@create_app_bp.route("/api/create-app/finish-checks/<check_id>", methods=["GET"])
def create_app_finish_check_one(check_id: str):
    from backend.services.create_app_finish_checks import single_finish_check
    result = single_finish_check(check_id)
    code = 200 if result.get("success") else 404
    return jsonify(result), code


@create_app_bp.route("/api/create-app/encoder-hub", methods=["GET", "POST"])
def create_app_encoder_hub():
    """Gather video + audio + AI encoder in one hub payload."""
    from backend.services.super_encoder_service import gather_encoder_hub

    body = request.get_json(silent=True) if request.method == "POST" else {}
    cfg = dict(body or {})
    cfg["user_id"] = _uid()
    if request.args.get("quality_goal"):
        cfg["quality_goal"] = request.args.get("quality_goal")
    if request.args.get("content_hint"):
        cfg["content_hint"] = request.args.get("content_hint")
    return jsonify(gather_encoder_hub(cfg)), 200


@create_app_bp.route("/api/create-app/encoder-v2/status", methods=["GET"])
def encoder_v2_status_route():
    from backend.services.encoder_v2_service import encoder_v2_status

    return jsonify(encoder_v2_status(_uid())), 200


@create_app_bp.route("/api/create-app/encoder-v2/catalog", methods=["GET"])
def encoder_v2_catalog_route():
    from backend.services.encoder_v2_service import list_upgrades_for_user

    category = request.args.get("category")
    limit = min(250, max(1, int(request.args.get("limit") or 50)))
    offset = max(0, int(request.args.get("offset") or 0))
    return jsonify(list_upgrades_for_user(_uid(), category=category, limit=limit, offset=offset)), 200


@create_app_bp.route("/api/create-app/encoder-v2/unlock", methods=["POST"])
def encoder_v2_unlock_route():
    from backend.services.encoder_v2_service import purchase_upgrade

    body = request.get_json(silent=True) or {}
    upgrade_id = str(body.get("upgrade_id") or "").strip()
    if not upgrade_id:
        return jsonify({"success": False, "error": "upgrade_id_required"}), 400
    result = purchase_upgrade(_uid(), upgrade_id)
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@create_app_bp.route("/api/create-app/encoder-v2/hub", methods=["GET", "POST"])
def encoder_v2_hub_route():
    from backend.services.encoder_v2_service import gather_encoder_v2_hub

    body = request.get_json(silent=True) if request.method == "POST" else {}
    cfg = dict(body or {})
    cfg["user_id"] = _uid()
    if request.args.get("quality_goal"):
        cfg["quality_goal"] = request.args.get("quality_goal")
    return jsonify(gather_encoder_v2_hub(cfg)), 200


@create_app_bp.route("/api/create-app/super-encoder/status", methods=["GET"])
def super_encoder_status_route():
    from backend.services.super_encoder_service import super_encoder_status
    return jsonify(super_encoder_status()), 200


@create_app_bp.route("/api/create-app/super-encoder/optimize", methods=["POST"])
def super_encoder_optimize():
    from backend.services.super_encoder_service import ai_optimize_encode_plan

    body = request.get_json(silent=True) or {}
    result = ai_optimize_encode_plan(
        target=str(body.get("target") or "hybrid"),
        quality_goal=str(body.get("quality_goal") or "balanced"),
        duration_sec=int(body.get("duration_sec") or 120),
        content_hint=str(body.get("content_hint") or body.get("prompt") or ""),
        user_id=_uid(),
    )
    return jsonify({"success": True, "plan": result}), 200


@create_app_bp.route("/api/create-app/encoder-orders/quote", methods=["POST"])
def encoder_orders_quote():
    from backend.services.encoder_order_service import quote_order

    body = request.get_json(silent=True) or {}
    kind = str(body.get("kind") or "").strip()
    if not kind:
        return jsonify({"success": False, "error": "kind_required"}), 400
    return jsonify(quote_order(kind, body)), 200


@create_app_bp.route("/api/create-app/encoder-orders", methods=["GET", "POST"])
def encoder_orders_route():
    if request.method == "GET":
        from backend.services.encoder_order_service import list_orders

        limit = min(100, max(1, int(request.args.get("limit") or 20)))
        return jsonify(list_orders(_uid(), limit=limit)), 200

    from backend.services.encoder_order_service import create_balance_order, create_onchain_order

    body = request.get_json(silent=True) or {}
    kind = str(body.get("kind") or "").strip()
    if not kind:
        return jsonify({"success": False, "error": "kind_required"}), 400
    method = str(body.get("payment_method") or "balance").strip().lower()
    cfg = dict(body.get("config") or body)
    cfg.pop("kind", None)
    cfg.pop("payment_method", None)
    if method == "onchain":
        result = create_onchain_order(_uid(), kind, cfg)
    else:
        result = create_balance_order(_uid(), kind, cfg, auto_fulfill=bool(body.get("auto_fulfill", True)))
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@create_app_bp.route("/api/create-app/encoder-orders/<order_id>", methods=["GET"])
def encoder_orders_get(order_id: str):
    from backend.services.encoder_order_service import get_order

    order = get_order(order_id)
    if not order:
        return jsonify({"success": False, "error": "not_found"}), 404
    if order.get("user_id") != _uid():
        return jsonify({"success": False, "error": "forbidden"}), 403
    return jsonify({"success": True, "order": order}), 200


@create_app_bp.route("/api/create-app/agents/leaderboard", methods=["GET"])
def create_app_agent_leaderboard():
    from backend.services.agent_leaderboard_rewards_service import build_agent_leaderboard

    limit = min(50, max(1, int(request.args.get("limit") or 20)))
    return jsonify(build_agent_leaderboard(limit=limit)), 200


@create_app_bp.route("/api/create-app/agents/leaderboard/claim", methods=["POST"])
def create_app_agent_leaderboard_claim():
    from backend.services.agent_leaderboard_rewards_service import claim_leaderboard_reward

    body = request.get_json(silent=True) or {}
    agent_id = str(body.get("agent_id") or "").strip()
    if not agent_id:
        return jsonify({"success": False, "error": "agent_id_required"}), 400
    result = claim_leaderboard_reward(_uid(), agent_id)
    code = 200 if result.get("success") else 400
    return jsonify(result), code
