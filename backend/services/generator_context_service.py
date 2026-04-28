"""
Generator Context Service — Build clip-with-context for every run.
Gathers profile, agents, and optional points; produces segments for generate_rich_video_sync.
Used by: create flow (missing_endpoints), make_a_vid.py, and any "quick clip" endpoint.
"""
from typing import Dict, List, Any, Optional


def gather_context_for_user(user_id: str) -> Dict[str, Any]:
    """Gather context from profile, agent connections, and optional unified points."""
    ctx = {
        "user_id": user_id,
        "profile": None,
        "profile_display": None,
        "agent_connections": [],
        "agent_groups": {},
        "unified_points": {},
        "service_worker_context": {
            "cache_name": "vidgenerator-sw-v3",
            "api_prefixes": [
                "/vidgenerator/api/generator/",
                "/vidgenerator/api/documentary/",
                "/vidgenerator/api/unified/",
            ],
            "role": "offline queue, generator progress, agent API",
        },
    }

    # Profile
    try:
        from backend.services.user_profile import UserProfile
        up = UserProfile()
        ctx["profile_display"] = up.get_profile_display(user_id)
        if ctx["profile_display"] and ctx["profile_display"].get("success"):
            ctx["profile"] = ctx["profile_display"].get("profile", {})
    except Exception:
        pass

    # Agent–generator connections
    try:
        from backend.services.generator_agent_connections import get_connections
        ctx["agent_connections"] = get_connections() or []
    except Exception:
        pass

    # Optional: unified points (for level/streak in clip)
    try:
        from backend.services.unified_points_database import unified_points_db
        if unified_points_db:
            data = unified_points_db.get_all_points(user_id)
            if isinstance(data, dict):
                ctx["unified_points"] = {
                    "xp_total": data.get("xp_total", 0),
                    "level": data.get("level", 1),
                    "generation_points": (data.get("systems") or {}).get("generation_points", 0),
                }
    except Exception:
        pass

    return ctx


def context_to_segments(
    ctx: Dict[str, Any],
    user_prompt: Optional[str] = None,
    user_title: Optional[str] = None,
    short: bool = False,
    max_segments: int = 12,
    include_points_in_clip: bool = True,
) -> List[Dict[str, Any]]:
    """
    Turn gathered context into video segments (title, description, duration).
    Segments are built around the user's actual content (title + prompt/description).
    """
    segments: List[Dict[str, Any]] = []
    t = (user_title or "").strip()[:80] or "Documentary"
    p = (user_prompt or "").strip()[:500] or t

    profile = ctx.get("profile") or {}
    display_name = profile.get("display_name") or profile.get("username") or ctx.get("user_id", "User")
    bio = (profile.get("bio") or "").strip()[:180]

    if short:
        segments.append({
            "title": t,
            "description": f"Introduction: {p[:160]}",
            "duration": 5,
        })
        segments.append({
            "title": f"About: {t}",
            "description": p[:200],
            "duration": 6,
        })
        if bio:
            segments.append({
                "title": f"By {display_name}",
                "description": f"{bio[:120]} — {p[:60]}",
                "duration": 4,
            })
        else:
            segments.append({
                "title": "Summary",
                "description": f"Conclusion: {t}. {p[:120]}",
                "duration": 4,
            })
        try:
            from backend.services.video_generator_service import _ai_enhance_segments
            segments = _ai_enhance_segments(segments, t, p, ctx.get("user_id", ""))
        except Exception:
            pass
        try:
            from backend.services.video_generator_service import _rulebased_ai_enrich
            segments = _rulebased_ai_enrich(segments, t, p, ctx.get("user_id", ""))
        except Exception:
            pass
        return segments

    # Long-form: break user prompt into content chapters
    words = p.split()
    chunk_size = max(1, len(words) // 4)
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)][:4]
    while len(chunks) < 4:
        chunks.append(p[:100])

    segments.append({
        "title": t,
        "description": f"Introduction: {p[:160]}",
        "duration": 5,
    })

    if bio:
        segments.append({
            "title": f"Presented by {display_name}",
            "description": f"{bio[:140]}",
            "duration": 4,
        })

    chapter_names = ["Background", "Details", "Analysis", "Insights"]
    for i, (name, chunk) in enumerate(zip(chapter_names, chunks)):
        segments.append({
            "title": f"Chapter {i+1}: {name}",
            "description": chunk[:200],
            "duration": 4,
        })

    if include_points_in_clip:
        pts = ctx.get("unified_points") or {}
        level = int(pts.get("level", 1))
        gen_pts = int(pts.get("generation_points", 0))
        if level > 1 or gen_pts > 0:
            segments.append({
                "title": f"Level {level} · {gen_pts} Generation Points",
                "description": f"Progress and achievements for {display_name}.",
                "duration": 3,
            })

    connections = ctx.get("agent_connections") or []
    for c in connections[:max(0, max_segments - len(segments) - 1)]:
        segments.append({
            "title": c.get("agent", "Agent"),
            "description": (c.get("description") or "")[:80],
            "duration": 3,
        })

    # Outro
    segments.append({
        "title": f"Conclusion: {t}",
        "description": f"Summary of {t}. {p[:100]}",
        "duration": 3,
    })

    # AI enhancement pass — LLM-powered (requires OpenAI credits)
    try:
        from backend.services.video_generator_service import _ai_enhance_segments
        segments = _ai_enhance_segments(segments[:max_segments], t, p, ctx.get("user_id", ""))
    except Exception:
        pass

    # Rule-based AI pass — always works (no LLM needed)
    try:
        from backend.services.video_generator_service import _rulebased_ai_enrich
        segments = _rulebased_ai_enrich(segments[:max_segments], t, p, ctx.get("user_id", ""))
    except Exception:
        pass

    return segments[: max_segments]
