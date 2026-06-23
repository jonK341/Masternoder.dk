"""Generator agent-native tools and Game Hub quest hooks."""
from __future__ import annotations

import os
from typing import Any, Dict, List

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AGENT_TOOLS: List[Dict[str, Any]] = [
    {
        "action": "create",
        "method": "POST",
        "path": "/api/generator/create",
        "mutating": True,
        "params": ["title", "description", "user_id", "duration", "short_clip"],
        "description": "Start a documentary video job; returns documentary_id.",
    },
    {
        "action": "progress",
        "method": "GET",
        "path": "/api/documentary/progress/<doc_id>",
        "mutating": False,
        "params": ["doc_id"],
        "description": "Poll generation progress until completed or failed.",
    },
    {
        "action": "history",
        "method": "GET",
        "path": "/api/generator/history",
        "mutating": False,
        "params": ["user_id", "limit"],
        "description": "Recent generator jobs for a user.",
    },
    {
        "action": "ai_ideas",
        "method": "POST",
        "path": "/api/generator/ai-ideas",
        "mutating": False,
        "params": ["topic", "count"],
        "description": "AI prompt ideas for a topic.",
    },
    {
        "action": "queue_status",
        "method": "GET",
        "path": "/api/generator/queue-status",
        "mutating": False,
        "params": ["user_id"],
        "description": "Queue depth and user position.",
    },
    {
        "action": "pricing",
        "method": "GET",
        "path": "/api/generator/pricing",
        "mutating": False,
        "description": "MN2 tiers, quote, crypto earn rates, COGS advisory.",
    },
    {
        "action": "restart",
        "method": "POST",
        "path": "/api/documentary/restart/<doc_id>",
        "mutating": True,
        "params": ["doc_id"],
        "description": "Restart a failed job with saved config.",
    },
]


def shop_unlocked_theme_ids(user_id: str) -> List[str]:
    """Theme IDs from shop inventory (theme-* item_id prefix)."""
    out: List[str] = []
    try:
        from backend.services.shop_db_service import get_inventory
        for item in get_inventory(user_id) or []:
            iid = str(item.get("item_id") or "").strip().lower()
            if not iid.startswith("theme-"):
                continue
            tid = iid[6:].strip()
            if tid:
                out.append(tid)
    except Exception:
        pass
    return sorted(set(out))


def record_video_quest_progress(user_id: str) -> Dict[str, Any]:
    """Increment daily generate_video + weekly_videos platform quests."""
    uid = str(user_id or "").strip()
    if not uid or uid == "default_user":
        return {"success": True, "skipped": "guest"}
    results: Dict[str, Any] = {}
    try:
        from backend.services.user_engagement import update_quest_progress
        results["generate_video"] = update_quest_progress(uid, "generate_video", increment=1)
        results["weekly_videos"] = update_quest_progress(uid, "weekly_videos", increment=1)
    except Exception as e:
        results["error"] = str(e)
    return {"success": True, "user_id": uid, "quests": results}


def execute_agent_action(body: Dict[str, Any]) -> Dict[str, Any]:
    """Run a generator agent action; returns dict with optional http_status."""
    action = (body.get("action") or "").strip()
    tool = next((t for t in AGENT_TOOLS if t["action"] == action), None)
    if not tool:
        return {
            "success": False,
            "error": "Unknown action",
            "available": [t["action"] for t in AGENT_TOOLS],
            "http_status": 400,
        }
    if tool["mutating"] and not body.get("approved"):
        return {
            "success": False,
            "error": "Mutating action requires approved=true",
            "action": action,
            "http_status": 403,
        }

    from flask import current_app
    from backend.routes import missing_endpoints_routes as me

    def _as_dict(resp):
        if hasattr(resp, "get_json"):
            data = resp.get_json(silent=True) or {}
            code = getattr(resp, "status_code", 200)
            if isinstance(data, dict):
                data.setdefault("http_status", code)
            return data
        return {"success": True, "result": resp, "http_status": 200}

    try:
        if action == "create":
            with current_app.test_request_context(method="POST", json=body):
                return _as_dict(me.generator_create())
        if action == "progress":
            doc_id = str(body.get("doc_id") or "").strip()
            if not doc_id:
                return {"success": False, "error": "doc_id required", "http_status": 400}
            with current_app.test_request_context(method="GET"):
                return _as_dict(me.documentary_progress(doc_id))
        if action == "history":
            uid = str(body.get("user_id") or "")
            limit = min(50, max(1, int(body.get("limit") or 10)))
            qs = f"user_id={uid}&limit={limit}" if uid else f"limit={limit}"
            with current_app.test_request_context(method="GET", query_string=qs):
                return _as_dict(me.generator_history())
        if action == "ai_ideas":
            with current_app.test_request_context(method="POST", json=body):
                return _as_dict(me.generator_ai_ideas())
        if action == "queue_status":
            uid = str(body.get("user_id") or "")
            qs = f"user_id={uid}" if uid else ""
            with current_app.test_request_context(method="GET", query_string=qs):
                return _as_dict(me.generator_queue_status())
        if action == "pricing":
            duration = int(body.get("duration") or 180)
            short = "1" if body.get("short_clip") else "0"
            tier = str(body.get("tier") or "standard")
            qs = f"duration={duration}&short_clip={short}&tier={tier}"
            with current_app.test_request_context(method="GET", query_string=qs):
                from backend.routes.generator_routes import generator_pricing
                return _as_dict(generator_pricing())
        if action == "restart":
            doc_id = str(body.get("doc_id") or "").strip()
            if not doc_id:
                return {"success": False, "error": "doc_id required", "http_status": 400}
            with current_app.test_request_context(method="POST", json=body):
                return _as_dict(me.documentary_restart(doc_id))
        return {"success": False, "error": "Unhandled action", "http_status": 400}
    except Exception as e:
        return {"success": False, "error": str(e), "http_status": 500}


def get_generator_ops_snapshot() -> Dict[str, Any]:
    """24h generator stats for ops stream / dashboard."""
    snap: Dict[str, Any] = {"success": True}
    try:
        from backend.services.video_job_queue import queue_status
        snap["queue"] = queue_status()
    except Exception as e:
        snap["queue"] = {"error": str(e)}
    try:
        from backend.services.generator_db_service import get_job_statistics, get_job_performance, generator_tables_exist
        if generator_tables_exist():
            stats = get_job_statistics(user_id=None, days=1) or {}
            perf = get_job_performance(user_id=None, limit=200) or {}
            snap["last_24h"] = {
                "total_jobs": stats.get("total_jobs", 0),
                "by_status": stats.get("by_status", {}),
                "success_rate_percent": perf.get("success_rate_percent", 0),
                "completed_count": perf.get("completed_count", 0),
                "failed_count": perf.get("failed_count", 0),
            }
        else:
            snap["last_24h"] = {"message": "generator DB migration not run"}
    except Exception as e:
        snap["last_24h"] = {"error": str(e)}
    return snap
