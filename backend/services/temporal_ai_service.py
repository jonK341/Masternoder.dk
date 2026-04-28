"""
Temporal AI Service — AI steady presence across all 9 time perspectives.

Each perspective represents a distinct temporal horizon. For every horizon the
service:
  1. Collects real metrics from the database (points, videos, activity)
  2. Routes the prompt to the optimal AI provider for that time scale
  3. Returns a structured insight: summary, highlights, action, predictions

The 9 Perspectives
------------------
  now        — last 60 s   — speed   (Groq  / Cerebras)
  recent     — last 5 min  — speed   (Groq  / Cerebras)
  session    — last 1 h    — speed   (Groq  / Cerebras)
  daily      — last 24 h   — default (OpenAI → Groq fallback)
  weekly     — last 7 d    — default (OpenAI → Groq fallback)
  monthly    — last 30 d   — reason  (DeepSeek R1)
  quarterly  — last 90 d   — reason  (DeepSeek R1)
  yearly     — last 365 d  — context (Gemini 2.5 Flash — 1M token context)
  all_time   — all time    — reason  (DeepSeek R1 — deep analysis + predictions)
"""
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Perspective registry
# ---------------------------------------------------------------------------

PERSPECTIVES: Dict[str, Dict[str, Any]] = {
    "now": {
        "label": "Now",
        "icon": "⚡",
        "window_sec": 60,
        "window_label": "last 60 seconds",
        "task_type": "speed",
        "cache_ttl": 0,
        "includes_predictions": False,
        "description": "The immediate moment — what's alive right now.",
    },
    "recent": {
        "label": "Recent",
        "icon": "🔥",
        "window_sec": 300,
        "window_label": "last 5 minutes",
        "task_type": "speed",
        "cache_ttl": 60,
        "includes_predictions": False,
        "description": "The last 5 minutes of momentum.",
    },
    "session": {
        "label": "Session",
        "icon": "🎯",
        "window_sec": 3600,
        "window_label": "last hour",
        "task_type": "speed",
        "cache_ttl": 300,
        "includes_predictions": False,
        "description": "Everything that happened this session.",
    },
    "daily": {
        "label": "Daily",
        "icon": "📅",
        "window_sec": 86400,
        "window_label": "last 24 hours",
        "task_type": "default",
        "cache_ttl": 1800,
        "includes_predictions": False,
        "description": "Today's full activity arc.",
    },
    "weekly": {
        "label": "Weekly",
        "icon": "📈",
        "window_sec": 604800,
        "window_label": "last 7 days",
        "task_type": "default",
        "cache_ttl": 3600,
        "includes_predictions": False,
        "description": "This week's patterns and wins.",
    },
    "monthly": {
        "label": "Monthly",
        "icon": "🌙",
        "window_sec": 2592000,
        "window_label": "last 30 days",
        "task_type": "reason",
        "cache_ttl": 7200,
        "includes_predictions": True,
        "description": "Monthly growth, strategy, and trajectory.",
    },
    "quarterly": {
        "label": "Quarterly",
        "icon": "🗓️",
        "window_sec": 7776000,
        "window_label": "last 90 days",
        "task_type": "reason",
        "cache_ttl": 14400,
        "includes_predictions": True,
        "description": "Quarter-view: milestones and direction.",
    },
    "yearly": {
        "label": "Yearly",
        "icon": "🌟",
        "window_sec": 31536000,
        "window_label": "last 365 days",
        "task_type": "context",
        "cache_ttl": 21600,
        "includes_predictions": True,
        "description": "The year's full journey — evolution and identity.",
    },
    "all_time": {
        "label": "All Time",
        "icon": "♾️",
        "window_sec": None,
        "window_label": "all time",
        "task_type": "reason",
        "cache_ttl": 21600,
        "includes_predictions": True,
        "description": "Complete record of everything + predictions for what comes next.",
    },
}

# In-memory response cache: key -> (expires_at, payload)
_cache: Dict[str, tuple] = {}


def _cache_get(key: str) -> Optional[Dict]:
    entry = _cache.get(key)
    if entry and time.monotonic() < entry[0]:
        return entry[1]
    return None


def _cache_set(key: str, payload: Dict, ttl: int) -> None:
    if ttl > 0:
        _cache[key] = (time.monotonic() + ttl, payload)


def _cache_bust(perspective: str, user_id: str) -> None:
    _cache.pop(f"{perspective}:{user_id}", None)


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def _collect_metrics(perspective_key: str, user_id: Optional[str]) -> Dict[str, Any]:
    """
    Pull real data from available DB tables for the given time window.
    Returns a dict of metrics — gracefully returns empty data if tables missing.
    """
    cfg = PERSPECTIVES[perspective_key]
    window_sec = cfg["window_sec"]
    since: Optional[datetime] = None
    if window_sec is not None:
        since = datetime.utcnow() - timedelta(seconds=window_sec)

    metrics: Dict[str, Any] = {
        "perspective": perspective_key,
        "window_label": cfg["window_label"],
        "since": since.isoformat() if since else None,
        "user_id": user_id,
        "points": {},
        "videos": {},
        "activity": {},
    }

    try:
        from sqlalchemy import text
        from src.db.models import db
        from src.app import create_app
        app = create_app()
        with app.app_context():
            metrics["points"] = _collect_points(db, text, since, user_id)
            metrics["videos"] = _collect_videos(db, text, since, user_id)
            metrics["activity"] = _collect_activity(db, text, since, user_id)
    except Exception as e:
        metrics["_db_error"] = str(e)[:200]

    return metrics


def _collect_points(db, text, since: Optional[datetime], user_id: Optional[str]) -> Dict:
    out = {"total_earned": 0, "total_spent": 0, "transaction_count": 0, "top_systems": []}
    try:
        where_parts = []
        params: Dict = {}
        if since:
            where_parts.append("created_at >= :since")
            params["since"] = since
        if user_id:
            where_parts.append("user_id = :uid")
            params["uid"] = user_id
        where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

        row = db.session.execute(text(f"""
            SELECT
                COALESCE(SUM(CASE WHEN transaction_type='credit' THEN amount ELSE 0 END),0) AS earned,
                COALESCE(SUM(CASE WHEN transaction_type='debit'  THEN amount ELSE 0 END),0) AS spent,
                COUNT(*) AS cnt
            FROM point_transactions {where}
        """), params).fetchone()
        if row:
            out["total_earned"] = float(row[0] or 0)
            out["total_spent"] = float(row[1] or 0)
            out["transaction_count"] = int(row[2] or 0)

        top = db.session.execute(text(f"""
            SELECT system_name, COALESCE(SUM(amount),0) AS total
            FROM point_transactions {where}
            GROUP BY system_name ORDER BY total DESC LIMIT 5
        """), params).fetchall()
        out["top_systems"] = [{"system": r[0], "total": float(r[1])} for r in top]
    except Exception:
        pass
    return out


def _collect_videos(db, text, since: Optional[datetime], user_id: Optional[str]) -> Dict:
    out = {"total": 0, "completed": 0, "failed": 0, "top_themes": []}
    try:
        where_parts = []
        params: Dict = {}
        if since:
            where_parts.append("created_at >= :since")
            params["since"] = since
        if user_id:
            where_parts.append("user_id = :uid")
            params["uid"] = user_id
        where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

        row = db.session.execute(text(f"""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS done,
                SUM(CASE WHEN status='failed'    THEN 1 ELSE 0 END) AS fail
            FROM video_generation_jobs {where}
        """), params).fetchone()
        if row:
            out["total"] = int(row[0] or 0)
            out["completed"] = int(row[1] or 0)
            out["failed"] = int(row[2] or 0)

        themes = db.session.execute(text(f"""
            SELECT COALESCE(theme,'default') AS t, COUNT(*) AS cnt
            FROM video_generation_jobs {where}
            GROUP BY t ORDER BY cnt DESC LIMIT 3
        """), params).fetchall()
        out["top_themes"] = [{"theme": r[0], "count": int(r[1])} for r in themes]
    except Exception:
        pass
    return out


def _collect_activity(db, text, since: Optional[datetime], user_id: Optional[str]) -> Dict:
    """Pull from xp_history or daily_activities when available."""
    out = {"xp_gained": 0, "events": 0}
    try:
        where_parts = []
        params: Dict = {}
        if since:
            where_parts.append("created_at >= :since")
            params["since"] = since
        if user_id:
            where_parts.append("user_id = :uid")
            params["uid"] = user_id
        where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

        row = db.session.execute(text(f"""
            SELECT COALESCE(SUM(xp_amount),0), COUNT(*) FROM xp_history {where}
        """), params).fetchone()
        if row:
            out["xp_gained"] = float(row[0] or 0)
            out["events"] = int(row[1] or 0)
    except Exception:
        pass
    return out


# ---------------------------------------------------------------------------
# AI insight generation
# ---------------------------------------------------------------------------

def _build_prompt(perspective_key: str, metrics: Dict) -> str:
    cfg = PERSPECTIVES[perspective_key]
    pts = metrics.get("points", {})
    vids = metrics.get("videos", {})
    act = metrics.get("activity", {})
    inc_pred = cfg["includes_predictions"]

    top_sys = ", ".join(
        f"{s['system']}({s['total']:.0f}pts)" for s in pts.get("top_systems", [])
    ) or "none"
    top_themes = ", ".join(
        f"{t['theme']}({t['count']})" for t in vids.get("top_themes", [])
    ) or "none"

    data_block = (
        f"Time window: {cfg['window_label']}\n"
        f"Points earned: {pts.get('total_earned', 0):.0f} | "
        f"Points spent: {pts.get('total_spent', 0):.0f} | "
        f"Transactions: {pts.get('transaction_count', 0)}\n"
        f"Top point systems: {top_sys}\n"
        f"Videos created: {vids.get('total', 0)} "
        f"(completed: {vids.get('completed', 0)}, failed: {vids.get('failed', 0)})\n"
        f"Top video themes: {top_themes}\n"
        f"XP gained: {act.get('xp_gained', 0):.0f} | Activity events: {act.get('events', 0)}"
    )

    pred_instruction = (
        "\n\nAlso include a 'predictions' field: 3 concrete predictions about what will happen "
        "in the next period based on the current trends."
        if inc_pred else ""
    )

    return (
        f"You are the intelligence layer of MasterNoder.dk — an AI video generation and gaming platform.\n\n"
        f"Analyze the following activity data for the '{cfg['label']}' time perspective "
        f"({cfg['description']}):\n\n"
        f"{data_block}\n\n"
        "Generate a JSON insight object with exactly these fields:\n"
        '  "summary": string (2 sentences max — what the data says)\n'
        '  "highlights": array of 3 strings (most notable observations)\n'
        '  "action": string (1 clear next-step recommendation)\n'
        '  "energy": string — one of: high | medium | low | dormant'
        + (', "predictions": array of 3 strings' if inc_pred else "")
        + "\n\nReturn strict JSON only. No markdown fences."
        + pred_instruction
    )


def _system_prompt() -> str:
    return (
        "You are the temporal intelligence layer of an AI platform. "
        "Analyze data concisely and return strict JSON only. "
        "Be specific, data-driven, and actionable."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_insight(
    perspective_key: str,
    user_id: Optional[str] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Get AI insight for a single perspective.

    Returns:
        {
            "success": bool,
            "perspective": str,
            "label": str,
            "icon": str,
            "window_label": str,
            "description": str,
            "task_type": str,
            "provider_used": str,
            "metrics": {...},
            "insight": {
                "summary": str,
                "highlights": [...],
                "action": str,
                "energy": str,
                "predictions": [...]  # only for monthly+
            },
            "cached": bool,
            "generated_at": str,
            "error": str  # only on failure
        }
    """
    if perspective_key not in PERSPECTIVES:
        return {"success": False, "error": f"Unknown perspective: '{perspective_key}'. "
                f"Valid: {', '.join(PERSPECTIVES)}"}

    cfg = PERSPECTIVES[perspective_key]
    cache_key = f"{perspective_key}:{user_id or 'global'}"

    if not force_refresh:
        cached = _cache_get(cache_key)
        if cached:
            return {**cached, "cached": True}

    # 1. Collect metrics
    metrics = _collect_metrics(perspective_key, user_id)

    # 2. Build prompt and call AI
    from backend.services.llm_service import complete as llm_complete
    import json as _json

    prompt = _build_prompt(perspective_key, metrics)
    ai_resp = llm_complete(
        prompt=prompt,
        system_prompt=_system_prompt(),
        temperature=0.4,
        max_tokens=600,
        task_type=cfg["task_type"],
    )

    # 3. Parse AI response
    insight: Dict[str, Any] = {}
    if ai_resp.success and ai_resp.content:
        raw = ai_resp.content.strip()
        # Strip markdown fences if any provider adds them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            parsed = _json.loads(raw)
            insight = {
                "summary": str(parsed.get("summary", "")),
                "highlights": [str(h) for h in parsed.get("highlights", [])[:3]],
                "action": str(parsed.get("action", "")),
                "energy": str(parsed.get("energy", "medium")),
            }
            if cfg["includes_predictions"] and "predictions" in parsed:
                insight["predictions"] = [str(p) for p in parsed["predictions"][:3]]
        except Exception:
            insight = {
                "summary": ai_resp.content[:200],
                "highlights": [],
                "action": "",
                "energy": "medium",
                "_raw": True,
            }
    else:
        insight = {
            "summary": "AI unavailable for this perspective right now.",
            "highlights": [],
            "action": "Check provider status at /api/ai/providers",
            "energy": "dormant",
        }

    payload = {
        "success": True,
        "perspective": perspective_key,
        "label": cfg["label"],
        "icon": cfg["icon"],
        "window_label": cfg["window_label"],
        "description": cfg["description"],
        "task_type": cfg["task_type"],
        "provider_used": ai_resp.provider,
        "metrics": metrics,
        "insight": insight,
        "cached": False,
        "generated_at": datetime.utcnow().isoformat(),
        "ai_success": ai_resp.success,
        "ai_error": ai_resp.error if not ai_resp.success else None,
    }

    _cache_set(cache_key, payload, cfg["cache_ttl"])
    return payload


def get_all_insights(
    user_id: Optional[str] = None,
    perspectives: Optional[List[str]] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Get AI insights for multiple (or all) perspectives at once.

    Args:
        perspectives: list of perspective keys to include. None = all 9.
        force_refresh: bypass cache.

    Returns:
        {
            "success": bool,
            "total": int,
            "ai_success": int,
            "perspectives": { "now": {...}, "daily": {...}, ... }
        }
    """
    keys = perspectives or list(PERSPECTIVES.keys())
    results = {}
    ai_success_count = 0

    for key in keys:
        result = get_insight(key, user_id=user_id, force_refresh=force_refresh)
        results[key] = result
        if result.get("ai_success"):
            ai_success_count += 1

    return {
        "success": True,
        "total": len(keys),
        "ai_success": ai_success_count,
        "user_id": user_id,
        "generated_at": datetime.utcnow().isoformat(),
        "perspectives": results,
    }


def get_perspectives_list() -> List[Dict[str, Any]]:
    """Return metadata for all 9 perspectives (no DB queries, no AI calls)."""
    return [
        {
            "key": k,
            "label": v["label"],
            "icon": v["icon"],
            "window_label": v["window_label"],
            "description": v["description"],
            "task_type": v["task_type"],
            "cache_ttl": v["cache_ttl"],
            "includes_predictions": v["includes_predictions"],
        }
        for k, v in PERSPECTIVES.items()
    ]


def bust_cache(user_id: Optional[str] = None) -> int:
    """Clear cached insights for a user (or all). Returns number cleared."""
    if user_id:
        before = len(_cache)
        for k in list(PERSPECTIVES.keys()):
            _cache_bust(k, user_id)
        return before - len(_cache)
    else:
        count = len(_cache)
        _cache.clear()
        return count
