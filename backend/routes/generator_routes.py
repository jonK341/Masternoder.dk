"""
Generator, documentary, and AI-clips routes.
Moved here from missing_endpoints_routes for clarity. View logic remains in missing_endpoints_routes;
this module registers those views on generator_bp so URLs are served from the generator blueprint.
"""
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
        return jsonify(payload), 200
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
