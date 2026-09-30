"""
Generator, documentary, and AI-clips routes.
Moved here from missing_endpoints_routes for clarity. View logic remains in missing_endpoints_routes;
this module registers those views on generator_bp so URLs are served from the generator blueprint.
"""
import os

from flask import Blueprint, jsonify, request

generator_bp = Blueprint("generator", __name__)


@generator_bp.route("/api/generator/pricing", methods=["GET"])
def generator_pricing():
    """Public MN2 pricing tiers for generator express/premium encodes."""
    try:
        from backend.services.generator_mn2_service import get_public_pricing, quote_generation

        duration = int(request.args.get("duration", 180))
        short_clip = request.args.get("short_clip", "").lower() in ("1", "true", "yes")
        tier = (request.args.get("tier") or "standard").strip().lower()
        payload = get_public_pricing()
        payload["quote"] = quote_generation(duration=duration, short_clip=short_clip, tier=tier)
        try:
            from backend.services.generator_crypto_rewards_service import public_crypto_rewards_info
            payload["crypto_rewards"] = public_crypto_rewards_info()
        except Exception:
            pass
        try:
            from backend.services.generator_pricing_service import pricing_suggestion
            cogs = pricing_suggestion()
            if cogs.get("success"):
                payload["cogs_advisory"] = cogs
                ref_usd = float(cogs.get("suggested_retail_usd_per_reference_job") or 0)
                if ref_usd > 0:
                    mn2_usd = float(os.environ.get("MN2_USD_PRICE") or 0) or None
                    if mn2_usd and mn2_usd > 0:
                        payload["cogs_advisory"]["approx_mn2_per_ref_job"] = round(ref_usd / mn2_usd, 6)
        except Exception:
            pass
        try:
            from backend.services.generator_encode_service import encode_profile_public
            payload["encode_profiles"] = encode_profile_public().get("profiles", [])
        except Exception:
            pass
        return jsonify(payload), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@generator_bp.route("/api/generator/encode-profiles", methods=["GET"])
def generator_encode_profiles():
    """CRF encode ladder (E8): fast_ai / premium / ultra."""
    try:
        from backend.services.generator_encode_service import encode_profile_public
        return jsonify(encode_profile_public()), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@generator_bp.route("/api/generator/crypto-rewards", methods=["GET"])
def generator_crypto_rewards_info():
    """Public MN2 earn rates for generator completions."""
    try:
        from backend.services.generator_crypto_rewards_service import public_crypto_rewards_info
        return jsonify(public_crypto_rewards_info()), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@generator_bp.route("/api/generator/agent-tools", methods=["GET"])
def generator_agent_tools():
    """Capability map for agents (Generator #21)."""
    from backend.services.generator_agent_service import AGENT_TOOLS
    return jsonify({
        "success": True,
        "tools": AGENT_TOOLS,
        "note": "Mutating actions via /api/generator/agent-action require approved=true.",
    }), 200


@generator_bp.route("/api/generator/agent-action", methods=["POST"])
def generator_agent_action():
    """Execute a generator action as an agent (#21)."""
    try:
        from backend.services.generator_agent_service import execute_agent_action
        data = request.get_json(silent=True) or {}
        result = dict(execute_agent_action(data))
        code = int(result.pop("http_status", 200))
        return jsonify(result), code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _register(rule, view_func, methods, endpoint=None):
    """Register one rule; endpoint must be unique per rule."""
    if endpoint is None:
        endpoint = rule.replace("/", "_").strip("_").replace("-", "_") or "index"
    generator_bp.add_url_rule(rule, endpoint=endpoint, view_func=view_func, methods=methods)


def register_generator_routes():
    """Import view functions from missing_endpoints_routes and register on generator_bp."""
    from backend.routes import missing_endpoints_routes as me

    routes = [
        ("/api/unified/generate-video", me.unified_generate_video, ["POST"]),
        ("/api/generator/jobs", me.generator_jobs_list, ["GET"]),
        ("/api/generator/history", me.generator_history, ["GET"]),
        ("/api/generator/statistics", me.generator_statistics, ["GET"]),
        ("/api/generator/generation-health", me.generator_generation_health, ["GET"]),
        ("/api/generator/queue-status", me.generator_queue_status, ["GET"]),
        ("/api/generator/performance", me.generator_performance, ["GET"]),
        ("/api/generator/presets", me.generator_presets, ["GET"]),
        ("/api/generator/ai-ideas", me.generator_ai_ideas, ["GET", "POST"]),
        ("/api/generator/quick-actions", me.generator_quick_actions, ["GET"]),
        ("/api/generator/debug-routes", me.generator_debug_routes, ["GET"]),
        ("/api/generator/test", me.generator_test, ["GET"]),
        ("/api/generator/reset-for-test", me.generator_reset_for_test, ["GET", "POST"]),
        ("/api/generator/agent-connections", me.generator_agent_connections, ["GET"]),
        ("/api/generator/magic-generate", me.generator_magic_generate, ["POST"]),
        ("/api/generator/create", me.generator_create, ["POST"]),
        ("/api/generator/ai-clips", me.generator_ai_clips, ["POST"]),
        ("/api/ai-clips/generate", me.ai_clips_generate, ["POST"]),
        ("/api/documentary/progress/<doc_id>", me.documentary_progress, ["GET"]),
        ("/api/documentary/restart/<doc_id>", me.documentary_restart, ["POST"]),
        ("/api/documentary/video/<doc_id>", me.documentary_video, ["GET"]),
        ("/api/documentary/thumbnail/<doc_id>", me.documentary_thumbnail, ["GET"]),
        ("/api/video-generation/calculate", me.video_generation_calculate, ["POST"]),
        ("/api/video-generation/solve-problems", me.video_generation_solve_problems, ["POST"]),
        ("/api/themes/list", me.themes_list, ["GET"]),
        ("/api/themes/user", me.themes_user, ["GET"]),
        ("/api/content-categories/list", me.content_categories_list, ["GET"]),
    ]
    for rule, view_func, methods in routes:
        _register(rule, view_func, methods)
    _register("/api/generator/ai-clips/<job_id>", me.generator_ai_clips_status, ["GET"])


# Register on import so the blueprint is ready when the app registers it
register_generator_routes()
