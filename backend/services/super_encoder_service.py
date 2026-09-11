"""Super Encoder — New encoder nr. 1 (E1 hardware) + podcast audio + AI API tuning."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from backend.services.generator_encode_service import (
    encode_profile_public,
    hardware_encode_status,
    resolve_encode_profile,
    VALID_PROFILES,
)
from backend.services.podcast_encode_service import list_encode_profiles


def super_encoder_status() -> Dict[str, Any]:
    """Public status for Create App + generator ops."""
    video = encode_profile_public()
    audio_profiles = list_encode_profiles()
    return {
        "success": True,
        "encoder_id": "new_encoder_nr_1",
        "label": "New encoder nr. 1 — Super Encoder",
        "e1_hardware": hardware_encode_status(),
        "video_profiles": video.get("profiles") or [],
        "audio_profiles": audio_profiles,
        "ai_api": _ai_provider_hint(),
        "default_video_profile": "premium",
        "default_audio_profile": "ultra",
    }


def _ai_provider_hint() -> Dict[str, Any]:
    try:
        from backend.services.llm_service import configured_providers

        providers = configured_providers() or []
        return {"configured": bool(providers), "providers": providers[:8]}
    except Exception:
        return {"configured": False, "providers": []}


def _heuristic_encode_plan(
    *,
    target: str,
    quality_goal: str,
    duration_sec: int,
) -> Dict[str, Any]:
    """Fallback when AI is unavailable."""
    goal = (quality_goal or "balanced").strip().lower()
    tgt = (target or "video").strip().lower()
    dur = max(0, int(duration_sec or 0))

    if tgt == "podcast" or tgt == "audio":
        if goal in ("max", "ultra", "broadcast"):
            audio = "studio"
        elif goal in ("fast", "draft"):
            audio = "standard"
        else:
            audio = "ultra"
        return {
            "video_profile": None,
            "audio_profile": audio,
            "rationale": f"Heuristic: {audio} audio for {goal} podcast target.",
            "ai_used": False,
        }

    if goal in ("max", "ultra", "best"):
        video = "ultra"
    elif goal in ("fast", "draft", "express"):
        video = "fast_ai"
    elif goal in ("premium", "high"):
        video = "premium"
    else:
        video = "standard"

    if dur > 600 and video == "ultra":
        video = "premium"

    return {
        "video_profile": video,
        "audio_profile": "premium" if tgt == "hybrid" else None,
        "rationale": f"Heuristic: {video} video (E1 HW when available) for {goal}.",
        "ai_used": False,
    }


def _parse_ai_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    else:
        brace = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if brace:
            cleaned = brace.group(0)
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _create_app_cfg() -> Dict[str, Any]:
    try:
        import os
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(base, "data", "mn2_config.json"), "r", encoding="utf-8") as f:
            return (json.load(f).get("create_app") or {})
    except Exception:
        return {}


def ai_optimize_encode_plan(
    *,
    target: str = "hybrid",
    quality_goal: str = "balanced",
    duration_sec: int = 120,
    content_hint: str = "",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ask the AI API for optimal video/audio encode profiles.
    Falls back to heuristics when no provider is configured.
    """
    hw = hardware_encode_status()
    base = _heuristic_encode_plan(
        target=target, quality_goal=quality_goal, duration_sec=duration_sec,
    )

    if not _create_app_cfg().get("super_encoder_ai_enabled", True):
        out = dict(base)
        out["rationale"] = "AI disabled in create_app config; using heuristic plan."
        out["ai_disabled"] = True
        return out

    system = (
        "You are the MasterNoder Super Encoder (New encoder nr. 1, E1 hardware H.264). "
        "Return ONLY valid JSON with keys: video_profile (fast_ai|standard|premium|ultra or null), "
        "audio_profile (standard|premium|ultra|broadcast|studio|opus_web or null), "
        "rationale (one sentence)."
    )
    user_msg = (
        f"target={target}; quality_goal={quality_goal}; duration_sec={duration_sec}; "
        f"hardware_codec={hw.get('codec')}; content_hint={content_hint[:400]}"
    )

    try:
        from backend.services.llm_service import chat

        resp = chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=256,
            task_type="speed",
        )
        if not resp.success:
            out = dict(base)
            out["ai_error"] = resp.error
            return out

        parsed = _parse_ai_json(resp.content or "")
        if not parsed:
            out = dict(base)
            out["ai_error"] = "could_not_parse_ai_response"
            return out

        video = str(parsed.get("video_profile") or "").strip().lower()
        audio = str(parsed.get("audio_profile") or "").strip().lower()
        if video and video not in VALID_PROFILES:
            video = base.get("video_profile")
        if audio and audio not in {p["id"] for p in list_encode_profiles()}:
            audio = base.get("audio_profile")

        return {
            "video_profile": video or base.get("video_profile"),
            "audio_profile": audio or base.get("audio_profile"),
            "rationale": str(parsed.get("rationale") or base.get("rationale") or ""),
            "ai_used": True,
            "ai_provider": getattr(resp, "provider", None),
            "user_id": user_id,
        }
    except Exception as exc:
        out = dict(base)
        out["ai_error"] = str(exc)[:200]
        return out


def gather_encoder_hub(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Single payload: video E1 + podcast audio + AI plan + selected package."""
    cfg = dict(config or {})
    status = super_encoder_status()
    package = build_super_encode_package(cfg)
    return {
        "success": True,
        "hub_id": "encoder_hub_unified",
        "encoder_nr": 1,
        "label": "New encoder nr. 1 — gathered in app",
        "status": status,
        "package": package,
        "sections": {
            "video": {
                "title": "Video encoder (E1 hardware H.264)",
                "profiles": status.get("video_profiles") or [],
                "hardware": status.get("e1_hardware"),
                "selected": package.get("video_profile"),
            },
            "audio": {
                "title": "Podcast / audio encoder",
                "profiles": status.get("audio_profiles") or [],
                "selected": package.get("audio_profile"),
            },
            "ai": {
                "title": "AI API encode tuning",
                "configured": (status.get("ai_api") or {}).get("configured"),
                "providers": (status.get("ai_api") or {}).get("providers") or [],
                "plan": package.get("ai_plan"),
            },
        },
    }


def build_super_encode_package(
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge explicit config, MN2 tier, and AI plan into one encode package."""
    cfg = dict(config or {})
    target = str(cfg.get("target") or "hybrid")
    quality = str(cfg.get("quality_goal") or cfg.get("quality_mode") or "balanced")
    duration = int(cfg.get("duration_sec") or cfg.get("duration") or 120)

    explicit_video = str(cfg.get("encode_profile") or cfg.get("video_profile") or "").strip().lower()
    explicit_audio = str(cfg.get("audio_profile") or cfg.get("podcast_encode_profile") or "").strip().lower()

    plan = ai_optimize_encode_plan(
        target=target,
        quality_goal=quality,
        duration_sec=duration,
        content_hint=str(cfg.get("content_hint") or cfg.get("prompt") or ""),
        user_id=cfg.get("user_id"),
    )

    video_profile = explicit_video if explicit_video in VALID_PROFILES else plan.get("video_profile")
    if not video_profile:
        video_profile = resolve_encode_profile(cfg)

    audio_profile = explicit_audio or plan.get("audio_profile") or "ultra"

    return {
        "success": True,
        "encoder_id": "new_encoder_nr_1",
        "video_profile": video_profile,
        "audio_profile": audio_profile,
        "e1_hardware": hardware_encode_status(),
        "ai_plan": plan,
        "targets": {
            "playstore": cfg.get("include_playstore", True),
            "podcast": cfg.get("include_podcast", True),
        },
    }
