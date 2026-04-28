"""
Unified agent ↔ LLM intelligence: router, feedback, capability map, output evaluation.
"""
from flask import Blueprint, jsonify, request

agent_intelligence_bp = Blueprint("agent_intelligence", __name__)


@agent_intelligence_bp.route("/api/agents/capability-map", methods=["GET"])
def capability_map():
    """
    Single map: task kinds → agent + skill + LLM task_type; plus LLM providers status.
    """
    try:
        from backend.services.agent_ai_router import list_task_kinds, TASK_ROUTING_TABLE
        from backend.services.llm_service import TASK_ROUTES, get_provider_status

        return jsonify(
            {
                "success": True,
                "task_routing": list_task_kinds(),
                "task_kinds": list(TASK_ROUTING_TABLE.keys()),
                "llm_task_types": list(TASK_ROUTES.keys()),
                "providers": get_provider_status(),
            }
        ), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@agent_intelligence_bp.route("/api/agents/router/route", methods=["POST"])
def router_route():
    """Body: { task_kind, user_id?, override_task_type? } → trace_id, agent_id, skill_name, task_type, provider_chain."""
    data = request.get_json(silent=True) or {}
    task_kind = (data.get("task_kind") or request.args.get("task_kind") or "").strip()
    if not task_kind:
        return jsonify({"success": False, "error": "task_kind required"}), 400
    user_id = (data.get("user_id") or request.args.get("user_id") or "").strip() or None
    override = (data.get("override_task_type") or "").strip() or None

    try:
        from backend.services.agent_ai_router import route

        r = route(task_kind, user_id=user_id, override_task_type=override)
        return jsonify({"success": True, "routing": r}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@agent_intelligence_bp.route("/api/agents/feedback/outcome", methods=["POST"])
def feedback_outcome():
    """Body: trace_id, user_id, task_kind, success, user_edited?, points_delta?, notes?"""
    data = request.get_json(silent=True) or {}
    try:
        from backend.services.agent_feedback_loop import record_manual_outcome

        out = record_manual_outcome(
            trace_id=str(data.get("trace_id", "")),
            user_id=str(data.get("user_id", "")),
            task_kind=str(data.get("task_kind", "")),
            success=bool(data.get("success", False)),
            user_edited=bool(data.get("user_edited", False)),
            points_delta=float(data.get("points_delta") or 0),
            notes=str(data.get("notes", "")),
        )
        return jsonify({"success": True, "result": out}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@agent_intelligence_bp.route("/api/agents/evaluate/output", methods=["POST"])
def evaluate_output():
    """Body: { text, content_type?, title?, strict? } — quality gate for gallery / publish."""
    data = request.get_json(silent=True) or {}
    text = data.get("text") or data.get("content") or ""
    if not str(text).strip():
        return jsonify({"success": False, "error": "text required"}), 400
    try:
        from backend.services.agent_output_evaluator import evaluate_content

        ev = evaluate_content(
            str(text),
            content_type=str(data.get("content_type") or "general"),
            title=str(data.get("title") or ""),
            strict=bool(data.get("strict", False)),
        )
        return jsonify({"success": True, "evaluation": ev}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@agent_intelligence_bp.route("/api/agents/router/routed-chat", methods=["POST"])
def router_routed_chat():
    """
    Body: { messages, task_kind, user_id, ...chat options }
    One-shot: route + llm chat + feedback loop (skill XP on success).
    """
    data = request.get_json(silent=True) or {}
    messages = data.get("messages")
    task_kind = (data.get("task_kind") or "").strip()
    user_id = (data.get("user_id") or "default_user").strip()
    if not messages or not isinstance(messages, list):
        return jsonify({"success": False, "error": "messages required"}), 400
    if not task_kind:
        return jsonify({"success": False, "error": "task_kind required"}), 400

    try:
        from backend.services.agent_ai_router import routed_chat

        kwargs = {
            k: v
            for k, v in data.items()
            if k not in ("messages", "task_kind", "user_id")
            and k in ("model", "temperature", "max_tokens", "timeout", "provider", "use_best")
        }
        resp, routing = routed_chat(messages, task_kind, user_id, **kwargs)
        return jsonify(
            {
                "success": resp.success,
                "content": resp.content,
                "error": resp.error,
                "provider": resp.provider,
                "model": resp.model,
                "routing": routing,
            }
        ), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
