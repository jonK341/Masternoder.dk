"""
System Overview — Mission Control endpoint.
GET /api/system/overview          — full overview (may call AI for coach tip)
GET /api/system/overview?compact=1 — fast, no AI calls
"""
import os
import hashlib
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request

system_overview_bp = Blueprint("system_overview", __name__)


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


@system_overview_bp.route("/api/system/overview", methods=["GET"])
def system_overview():
    compact = request.args.get("compact", "0") == "1"
    user_id = (request.args.get("user_id") or "default_user").strip()

    result = {
        "success":   True,
        "generated": datetime.now(timezone.utc).isoformat(),
        "platform":  "MasterNoder.dk",
        "version":   "2.1",
    }

    # LLM providers
    result["llm"] = _safe(_llm_status, {"configured": 0, "available": 0, "total": 0, "providers": []})

    # Video / media providers
    result["video_providers"] = _safe(_video_providers, [])

    # TTS (Piper / ElevenLabs / gTTS / pyttsx3)
    result["tts"] = _safe(_tts_status, {"active_provider": "none"})

    # Audio Enhancement (DeepFilterNet + FFmpeg loudnorm)
    result["audio_enhancement"] = _safe(_audio_enhancement_status, {})

    # User stats
    result["statistics"] = _safe(lambda: _stats(user_id), {})

    # Daily quests (from quest_routes cache if loaded)
    result["daily_quests"] = _safe(_quests, [])

    # Leaderboard top 3
    result["leaderboard_top3"] = _safe(_top3, [])

    # Shop daily deal
    result["daily_deal"] = _safe(_daily_deal, {})

    # AI coach tip (only on full scan)
    if not compact:
        result["ai_coach_tip"] = _safe(lambda: _coach_tip(user_id), "")

    # Health score
    llm_avail = int((result["llm"] or {}).get("available", 0))
    vid_avail = sum(1 for p in (result["video_providers"] or []) if p.get("available"))
    tts_ok    = (result["tts"] or {}).get("active_provider", "none") not in ("none", "")
    health    = min(100, llm_avail * 10 + vid_avail * 8 + (15 if tts_ok else 0))
    audio_enh = result.get("audio_enhancement") or {}
    ae_ready = (audio_enh.get("noise_reduction", {}).get("available") or
                audio_enh.get("loudnorm", {}).get("available"))
    result["health"] = {
        "score":  health,
        "grade":  "A" if health >= 80 else "B" if health >= 60 else "C" if health >= 40 else "D",
        "label":  "Excellent" if health >= 80 else "Good" if health >= 60 else "Fair" if health >= 40 else "Needs attention",
        "color":  "#4caf50" if health >= 80 else "#ff9800" if health >= 60 else "#f44336",
        "llm_providers_ready":   llm_avail,
        "video_providers_ready": vid_avail,
        "tts_ready":             tts_ok,
        "audio_enhancement_ready": ae_ready,
    }

    return jsonify(result), 200


# ---------------------------------------------------------------------------

def _llm_status():
    from backend.services.llm_service import get_provider_status, TASK_ROUTES
    statuses   = get_provider_status()
    configured = [s for s in statuses if s["configured"]]
    available  = [s for s in statuses if s["available"]]
    return {
        "configured":  len(configured),
        "available":   len(available),
        "total":       len(statuses),
        "task_routes": TASK_ROUTES,
        "providers": [
            {"name": s["provider"], "available": s["available"],
             "model": s["default_model"], "cost": s["cost_tier"]}
            for s in statuses
        ],
    }


def _video_providers():
    providers = []
    _checks = [
        ("RunwayML Gen-4",  "backend.services.runwayml_service",         "RUNWAYML_API_KEY",   "video"),
        ("Pika 2.2",        "backend.services.pika_service",              "PIKA_LABS_API_KEY",  "video"),
        ("HeyGen Avatar",   "backend.services.heygen_service",            "HEYGEN_API_KEY",     "video"),
        ("Replicate SVD",   "backend.services.replicate_video_service",   "REPLICATE_API_TOKEN","video"),
        ("ModelsLab",       "backend.services.modelslab_video_service",   "MODELSLAB_API_KEY",  "video"),
        ("Stability AI",    "backend.services.stability_image_service",   "STABILITY_AI_API_KEY","image"),
    ]
    for name, mod_path, key_env, kind in _checks:
        try:
            import importlib
            mod   = importlib.import_module(mod_path)
            avail = mod.is_available()
        except Exception:
            avail = False
        providers.append({"name": name, "key_env": key_env, "available": avail, "type": kind})
    providers.append({"name": "Pollinations.ai", "key_env": None, "available": True,
                      "type": "image", "note": "free/unlimited"})
    return providers


def _tts_status():
    from backend.services.tts_service import get_status
    return get_status()


def _audio_enhancement_status():
    from backend.services.audio_enhancement_service import get_status
    return get_status()


def _stats(user_id):
    from backend.services.unified_points_database import unified_points_db
    snap = unified_points_db.get_all_points(user_id) or {}
    if not snap.get("success"):
        return {}
    xp    = int(snap.get("xp_total", 0))
    level = int(snap.get("level",    1))
    rank  = "Master" if level >= 10 else "Expert" if level >= 5 else "Hunter" if level >= 2 else "Recruit"
    return {"xp": xp, "level": level, "rank": rank}


def _quests():
    """Read today's quests from the in-memory cache of quest_routes if loaded."""
    import sys
    quest_mod = sys.modules.get("backend.routes.quest_routes")
    if quest_mod is None:
        return []
    today  = quest_mod._today_str()
    cache  = quest_mod._daily_cache
    quests = cache.get(today, [])
    return [{"title": q["title"], "xp": q.get("xp_reward", 0),
             "difficulty": q.get("difficulty", "medium")} for q in quests]


def _top3():
    from backend.routes.leaderboard_routes import _get_all_players
    players = _get_all_players()[:3]
    return [{"rank": p["rank"], "name": p["display_name"], "level": p["level"],
             "xp": p["xp"], "badge": p.get("badge", "")} for p in players]


def _daily_deal():
    from backend.routes.shop_routes import _get_shop_items
    today    = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    day_hash = int(hashlib.md5(today.encode()).hexdigest()[:6], 16)
    items    = _get_shop_items()
    if not items:
        return {}
    item     = items[day_hash % len(items)]
    orig     = item.get("price", 100)
    disc_pct = 25 + (day_hash % 16)
    deal     = max(10, int(orig * (1 - disc_pct / 100))) if isinstance(orig, (int, float)) else orig
    return {"item_id": item.get("id"), "name": item.get("name"),
            "category": item.get("category"), "original_price": orig,
            "deal_price": deal, "discount_pct": disc_pct}


def _coach_tip(user_id):
    from backend.services.llm_service import chat
    xp = level = 0
    try:
        from backend.services.unified_points_database import unified_points_db
        snap = unified_points_db.get_all_points(user_id) or {}
        if snap.get("success"):
            xp    = int(snap.get("xp_total", 0))
            level = int(snap.get("level",    1))
    except Exception:
        pass
    resp = chat(
        messages=[{"role": "user", "content":
            f"One short punchy power tip for a MasterNoder.dk player: "
            f"level {level}, {xp} XP. Max 15 words. Direct and motivating."}],
        task_type="speed", max_tokens=35, temperature=0.9,
    )
    return resp.content.strip().strip('"') if resp.success else "Generate videos — every clip earns XP!"
