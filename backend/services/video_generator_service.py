"""
Video Generator Service - Creates actual video files using MoviePy
Generates short documentary-style videos from prompts.
Phase 2: Errors are persisted to job (status=failed, error_message); run() wrapped in try/except.
"""
import os
import threading
import math
import re
from datetime import datetime
from typing import Dict, Optional, Callable, Tuple, List, Any
import textwrap
import json

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Production can override: VIDEOS_DIR=/var/www/html/vidgenerator/videos
VIDEOS_DIR = os.environ.get('VIDEOS_DIR') or os.path.join(_BASE, 'vidgenerator', 'videos')
os.makedirs(VIDEOS_DIR, exist_ok=True)

# Segment colors for rich video (R, G, B)
_SEGMENT_COLORS = [
    (15, 25, 45),   # dark blue
    (30, 20, 50),   # purple
    (15, 40, 35),   # dark green
    (45, 25, 25),   # dark red
    (25, 35, 50),   # slate
]
_MOOD_COLOR_MAP: Dict[str, tuple] = {
    "energetic": (50, 20, 15),
    "calm": (10, 25, 50),
    "dramatic": (40, 10, 10),
    "inspiring": (15, 35, 55),
    "mysterious": (25, 15, 45),
    "happy": (45, 40, 10),
    "dark": (10, 10, 18),
    "professional": (18, 22, 35),
    "nature": (10, 35, 20),
    "technology": (12, 20, 45),
    "creative": (40, 18, 50),
    "neutral": (20, 25, 38),
}

# Out-of-this-world variety: every video gets a different AI flavor
STYLE_PRESETS = [
    "cinematic", "documentary", "educational", "dramatic", "minimalist",
    "storytelling", "journalistic", "artistic", "scientific", "epic",
]
THEME_TONES = [
    "mysterious", "inspiring", "scientific", "calm", "energetic",
    "thought-provoking", "adventurous", "contemplative", "bold", "dreamy",
]
CREATIVE_TWISTS = [
    "Start with a surprising fact or question.",
    "Use a non-linear or flashback structure.",
    "Focus on one vivid detail and expand from it.",
    "Add a contrasting mood shift mid-video.",
    "End with an open question or call to action.",
]


def _get_style_and_tone_for_plan(extra_context: Optional[Dict] = None) -> Tuple[str, str, str]:
    """Pick narrative style, theme tone, and a creative twist so every video is unique. Returns (style, tone, twist)."""
    import random
    ctx = extra_context or {}
    style = (ctx.get("style_preset") or "").strip().lower()
    tone = (ctx.get("theme_tone") or "").strip().lower()
    twist = (ctx.get("creative_twist") or "").strip()
    if style not in STYLE_PRESETS:
        style = random.choice(STYLE_PRESETS)
    if tone not in THEME_TONES:
        tone = random.choice(THEME_TONES)
    if not twist and CREATIVE_TWISTS:
        twist = random.choice(CREATIVE_TWISTS)
    return style, tone, twist


def _ai_generate_prompt_ideas(topic: str, count: int = 5) -> Optional[List[Dict[str, str]]]:
    """Use LLM to generate unique video prompt ideas for a topic. Returns list of {title, prompt, angle} or None."""
    try:
        from backend.services.video_stage_cache import get as cache_get, put as cache_put
        cached = cache_get("prompt_ideas", topic, extra=str(count))
        if isinstance(cached, list) and cached:
            return cached
    except ImportError:
        cache_get = cache_put = None
    try:
        from backend.services.video_ai_bridge import complete_for_stage
        r = complete_for_stage(
            "prompt_ideas",
            (
                f"Topic or theme: {topic[:300]}\n\n"
                f"Generate exactly {count} different video ideas. Each must be unique in angle and style.\n"
                "Return strict JSON only:\n"
                '{"ideas":[{"title":"...","prompt":"1-2 sentence description","angle":"e.g. documentary, dramatic, educational"}]}'
            ),
            system_prompt="You are a creative director. Output strict JSON only. No markdown.",
            temperature=0.85,
            max_tokens=800,
            timeout=90,
        )
        if not (r and getattr(r, "success", False) and getattr(r, "content", None)):
            return None
        obj = _extract_json_object(getattr(r, "content", "") or "")
        ideas = (obj or {}).get("ideas")
        if isinstance(ideas, list) and len(ideas) > 0:
            out = [
                {
                    "title": str(i.get("title") or "")[:100],
                    "prompt": str(i.get("prompt") or "")[:400],
                    "angle": str(i.get("angle") or "")[:60],
                }
                for i in ideas[:count]
            ]
            try:
                if cache_put:
                    cache_put("prompt_ideas", topic, out, extra=str(count))
            except Exception:
                pass
            return out
    except Exception:
        pass
    return None


_MIN_VALID_MP4_BYTES = 1024
_MIN_FREE_BYTES_FOR_VIDEO = 100 * 1024 * 1024  # 100 MB minimum free for encoding


def _generation_visual_seed(doc_id: str, salt: str = "") -> int:
    """Stable per-job seed for visuals (intro/outro/animation variety). Same doc_id → same look if retried."""
    raw = f"{doc_id}:{salt}"
    h = 0
    for ch in raw:
        h = (h * 31 + ord(ch)) & 0x7FFFFFFF
    return max(1, h)


def _visual_profile_from_seed(seed: int) -> Dict[str, Any]:
    """Fresh template variant each run: accent, motion bias, density."""
    import random
    rng = random.Random(seed)
    accents = [
        (0, 255, 136),
        (120, 200, 255),
        (255, 180, 80),
        (200, 120, 255),
        (80, 220, 200),
        (255, 100, 140),
    ]
    accent = accents[seed % len(accents)]
    return {
        "seed": seed,
        "accent": accent,
        "intro_variant": seed % 4,
        "particle_density": 10 + (seed % 8),
        "cam_bias": (seed // 7) % 4,
        "brand_line": "MASTERNODER.DK",
    }


def _check_generation_services() -> Tuple[bool, str, Dict[str, Any]]:
    """
    Pre-flight for video generation: disk, LLM availability, ffmpeg for MoviePy.
    Returns (all_ok, message, details).
    """
    details: Dict[str, Any] = {"disk": {}, "llm": {}, "ffmpeg": {}}
    messages: List[str] = []

    ok_disk, disk_err = _check_disk_space()
    details["disk"] = {"ok": ok_disk, "videos_dir": VIDEOS_DIR, "error": disk_err}
    if not ok_disk:
        messages.append(disk_err or "Insufficient disk space")

    llm_ok = False
    try:
        from backend.services.llm_service import llm_service
        llm_ok = bool(llm_service and llm_service.is_available())
    except Exception:
        llm_ok = False
    details["llm"] = {"ok": llm_ok}
    if not llm_ok:
        messages.append("No AI provider API keys configured (generation needs at least one LLM)")

    ffmpeg_ok = False
    try:
        import shutil
        ffmpeg_ok = shutil.which("ffmpeg") is not None
    except Exception:
        ffmpeg_ok = False
    details["ffmpeg"] = {"ok": ffmpeg_ok}

    # LLM + disk are required for the AI-first pipeline; ffmpeg may be bundled via imageio on some installs.
    all_ok = ok_disk and llm_ok
    if not ffmpeg_ok:
        details["ffmpeg"]["note"] = "Optional; MoviePy may still use bundled ffmpeg"
    msg = "; ".join(messages) if messages else ""
    return (all_ok, msg, details)


def _ai_generate_episode_storyline(
    title: str,
    prompt: str,
    run_id: str,
    style: str,
    tone: str,
    twist: str,
) -> Optional[str]:
    """One fresh narrative setup paragraph so each video is not a generic repeat."""
    cache_key = f"{title[:80]}|{prompt[:120]}|{style}|{tone}|{twist}"
    try:
        from backend.services.video_stage_cache import get as cache_get, put as cache_put
        cached = cache_get("episode_storyline", cache_key, extra=run_id[:8])
        if isinstance(cached, str) and len(cached) > 40:
            return cached
    except ImportError:
        cache_get = cache_put = None
    try:
        from backend.services.video_ai_bridge import complete_for_stage
        r = complete_for_stage(
            "episode_storyline",
            (
                f"Video run id: {run_id}\n"
                f"Working title: {title[:120]}\n"
                f"Topic / user prompt: {prompt[:400]}\n"
                f"Style: {style}. Tone: {tone}. Creative direction: {twist}\n\n"
                "Write ONE short paragraph (3–5 sentences) that defines a UNIQUE storyline for THIS run only: "
                "setup, central tension or question, and intended viewer takeaway. "
                "Do not repeat boilerplate about 'this video will explore'. Be specific and varied."
            ),
            system_prompt="You are a showrunner. Output plain prose only, no JSON, no title line.",
            temperature=0.88,
            max_tokens=320,
            timeout=45,
        )
        if r and getattr(r, "success", False) and getattr(r, "content", None):
            text = (getattr(r, "content", "") or "").strip()
            if len(text) > 40:
                try:
                    if cache_put:
                        cache_put("episode_storyline", cache_key, text[:900], extra=run_id[:8])
                except Exception:
                    pass
                return text[:900]
    except Exception:
        pass
    return None


def _fallback_episode_storyline(seed: int, style: str, tone: str, twist: str) -> str:
    import random
    rng = random.Random(seed)
    hooks = [
        "A thread pulls loose and the whole picture shifts.",
        "One detail refuses to stay in the background.",
        "The familiar frame cracks just enough to let another story through.",
        "Time compresses: cause, effect, and consequence in one breath.",
        "The question is not what happened, but what it rearranges next.",
    ]
    return (
        f"{rng.choice(hooks)} Angle: {style} / {tone}. {twist} "
        f"(variation #{seed % 10000})"
    )[:500]


def _prepare_generation_config(doc_id: str, config: Dict[str, Any]) -> None:
    """
    Mutates config in place: random style/tone/twist when omitted, fresh storyline text,
    visual seed for template variety. Idempotent if keys already set by client.
    """
    ec = config
    style, tone, twist = _get_style_and_tone_for_plan(ec)
    ec["style_preset"] = ec.get("style_preset") or style
    ec["theme_tone"] = ec.get("theme_tone") or tone
    ec["creative_twist"] = ec.get("creative_twist") or twist

    seed = _generation_visual_seed(doc_id, ec.get("user_id") or "")
    ec["_visual_seed"] = seed
    ec["_visual_profile"] = _visual_profile_from_seed(seed)

    title = str(ec.get("title") or ec.get("prompt") or "Video")[:200]
    prompt = str(ec.get("prompt") or ec.get("description") or title)[:800]
    run_id = f"{doc_id}-{seed % 100000}"

    brief = _ai_generate_episode_storyline(
        title, prompt, run_id, ec["style_preset"], ec["theme_tone"], ec["creative_twist"]
    )
    if not brief:
        brief = _fallback_episode_storyline(seed, ec["style_preset"], ec["theme_tone"], ec["creative_twist"])
    ec["_storyline_addon"] = brief
    ec["_generation_run_id"] = run_id


def _check_disk_space() -> Tuple[bool, Optional[str]]:
    """Check if VIDEOS_DIR has enough free space for video encoding. Returns (ok, error_message)."""
    try:
        import shutil
        usage = shutil.disk_usage(VIDEOS_DIR)
        if usage.free < _MIN_FREE_BYTES_FOR_VIDEO:
            free_mb = usage.free / (1024 * 1024)
            return (False, f"No space left on device: only {free_mb:.1f} MB free. Free at least 100 MB in {VIDEOS_DIR}")
        return (True, None)
    except Exception as e:
        return (True, None)  # Don't block on check failure


def _normalize_write_error(exc: Exception) -> str:
    """Convert FFMPEG/MoviePy errors into user-friendly messages."""
    msg = str(exc).lower()
    if "no space left on device" in msg or "errno 28" in msg:
        return "No space left on device. Free disk space in the videos directory and try again."
    if "broken pipe" in msg and "no space" in msg:
        return "No space left on device. Free disk space in the videos directory and try again."
    return str(exc)


# ---------------------------------------------------------------------------
#  AI Enhancement Layer — enrich segments with LLM-generated content
# ---------------------------------------------------------------------------
def _ai_enhance_segments(
    segments: List[Dict[str, Any]],
    title: str,
    prompt: str,
    user_id: str = "default_user",
    theme: str = "",
    extra_context: Optional[Dict[str, Any]] = None,
    providers_used: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Pass every segment through available AI services to enrich descriptions,
    generate mood colors, and add narrative flow.  When use_all_ais in extra_context,
    calls multiple providers and merges results. Tracks provider names in providers_used.
    """
    prompt_text = (
        f"You are a video script writer.  Given a video titled '{title}' "
        f"about: {prompt[:300]}\n"
        f"Scenes: {' | '.join(s.get('title', '')[:40] for s in segments)}\n\n"
        "For EACH scene write:\n"
        "1. A vivid 1-2 sentence description (concrete, no filler)\n"
        "2. A mood keyword from: energetic, calm, dramatic, inspiring, mysterious, "
        "happy, dark, professional, nature, technology, creative, neutral\n"
        "3. A short tagline (max 8 words)\n"
        "4. A key_fact: one surprising or memorable fact or hook for this scene (max 12 words)\n\n"
        f"Return strict JSON: {{\"scenes\": [{{\"description\": \"...\", "
        f"\"mood\": \"...\", \"tagline\": \"...\", \"key_fact\": \"...\"}}]}}  ({len(segments)} items)"
    )
    try:
        from backend.services.video_ai_bridge import (
            complete_for_stage,
            complete_multi_provider,
            merge_segment_enhancements,
        )
        use_all_ais = bool((extra_context or {}).get("use_all_ais"))
        if use_all_ais:
            multi = complete_multi_provider(
                "segment_enhance",
                prompt_text,
                system_prompt="Output strict JSON only. No markdown fences.",
                max_providers=6,
                temperature=0.5,
                max_tokens=800,
                timeout=90,
                extra_context=extra_context,
            )
            if multi:
                if providers_used is not None:
                    providers_used.extend(p for p, _ in multi)
                merged = merge_segment_enhancements(segments, multi, title, prompt)
                if merged:
                    return merged
        r = complete_for_stage(
            "segment_enhance",
            prompt_text,
            system_prompt="Output strict JSON only. No markdown fences.",
            temperature=0.5,
            max_tokens=800,
            timeout=90,
            extra_context=extra_context,
        )
        if r and getattr(r, "success", False) and getattr(r, "content", None):
            if providers_used is not None:
                p = getattr(r, "provider", None)
                if p and p not in providers_used:
                    providers_used.append(p)
        if not (r and getattr(r, "success", False) and getattr(r, "content", None)):
            return segments
        obj = _extract_json_object(getattr(r, "content", "") or "")
        ai_scenes = (obj or {}).get("scenes") or []
        if not isinstance(ai_scenes, list) or len(ai_scenes) < 1:
            return segments
    except Exception:
        return segments

    enhanced = []
    for i, seg in enumerate(segments):
        e = dict(seg)
        if i < len(ai_scenes):
            ai = ai_scenes[i]
            ai_desc = str(ai.get("description") or "").strip()
            if ai_desc and len(ai_desc) > 10:
                e["description"] = ai_desc[:260]
            mood = str(ai.get("mood") or "").strip().lower()
            if mood in _MOOD_COLOR_MAP:
                e["bg_color"] = _MOOD_COLOR_MAP[mood]
                e["mood"] = mood
            tagline = str(ai.get("tagline") or "").strip()
            if tagline:
                e["tagline"] = tagline[:60]
            key_fact = str(ai.get("key_fact") or "").strip()
            if key_fact:
                e["key_fact"] = key_fact[:80]
        enhanced.append(e)
    return enhanced


def _ai_generate_enhanced_descriptions(
    title: str,
    prompt: str,
    segment_count: int = 4,
) -> Optional[List[str]]:
    """
    Ask the LLM to write rich paragraph descriptions for each chapter of a video.
    Returns a list of description strings or None on failure.
    """
    try:
        from backend.services.video_ai_bridge import complete_for_stage
        r = complete_for_stage(
            "enhanced_descriptions",
            (
                f"Write {segment_count} short paragraphs (2-3 sentences each) for a video about:\n"
                f"Title: {title}\nDescription: {prompt[:400]}\n\n"
                "Each paragraph is one chapter: introduction, body chapters, and conclusion.\n"
                "Be specific, vivid, and informative.  Return strict JSON:\n"
                f'{{\"paragraphs\": [\"paragraph 1\", \"paragraph 2\", ...]}}'
            ),
            system_prompt="Output strict JSON only. No markdown fences. Be concise.",
            temperature=0.6,
            max_tokens=600,
            timeout=90,
        )
        if not (r and getattr(r, "success", False) and getattr(r, "content", None)):
            return None
        obj = _extract_json_object(getattr(r, "content", "") or "")
        paras = (obj or {}).get("paragraphs")
        if isinstance(paras, list) and len(paras) >= 2:
            return [str(p).strip()[:260] for p in paras]
    except Exception:
        pass
    return None


def _ai_generate_title_variations(title: str, count: int = 4) -> Optional[List[str]]:
    """Generate creative chapter title variations via LLM."""
    try:
        from backend.services.video_ai_bridge import complete_for_stage
        r = complete_for_stage(
            "title_variations",
            (
                f"Generate {count} creative chapter titles for a video called '{title}'.\n"
                f'Return strict JSON: {{\"titles\": [\"title1\", \"title2\", ...]}}'
            ),
            system_prompt="Output strict JSON only.",
            temperature=0.7,
            max_tokens=200,
            timeout=90,
        )
        if r and getattr(r, "success", False) and getattr(r, "content", None):
            obj = _extract_json_object(getattr(r, "content", "") or "")
            titles = (obj or {}).get("titles")
            if isinstance(titles, list) and len(titles) >= 2:
                return [str(t).strip()[:60] for t in titles]
    except Exception:
        pass
    return None


def _ai_content_strategy(title: str, prompt: str) -> Optional[Dict[str, Any]]:
    """Use AI content generator to get a strategy for the video."""
    try:
        from backend.services.ai_content_generator import ai_content_generator
        strat = ai_content_generator.generate_content(
            "strategy",
            {"goal": f"video_production:{title}", "constraints": {"topic": prompt[:200]}},
            agent_class="content_agent",
        )
        if isinstance(strat, dict) and not strat.get("error"):
            return strat
    except Exception:
        pass
    return None


def _ai_video_concept(prompt: str) -> Optional[str]:
    """Use AI content generator to produce a video concept description."""
    try:
        from backend.services.ai_content_generator import ai_content_generator
        vidc = ai_content_generator.generate_content(
            "video",
            {"topic": prompt[:200]},
            agent_class="content_agent",
        )
        if isinstance(vidc, dict) and vidc.get("description"):
            return str(vidc["description"])[:400]
    except Exception:
        pass
    return None


def _ai_generate_opening_hook(
    title: str,
    prompt: str,
    style: str = "",
    tone: str = "",
    extra_context: Optional[Dict] = None,
    providers_used: Optional[List[str]] = None,
) -> Optional[str]:
    """Use LLM to generate one catchy opening line for the video. If use_all_ais, calls multiple providers and picks best."""
    try:
        from backend.services.video_ai_bridge import (
            complete_for_stage,
            complete_multi_provider,
            pick_best_opening_hook,
        )
        use_all_ais = bool((extra_context or {}).get("use_all_ais"))
        prompt_text = (
            f"Video title: {title}\nTopic: {prompt[:250]}\n"
            f"Style: {style or 'documentary'}. Tone: {tone or 'engaging'}.\n\n"
            "Write exactly ONE short opening line (max 15 words) that hooks the viewer. No quotes, no JSON."
        )
        sys_prompt = "You are a documentary narrator. Output only the opening line, nothing else."
        if use_all_ais:
            multi = complete_multi_provider(
                "opening_hook",
                prompt_text,
                system_prompt=sys_prompt,
                max_providers=5,
                temperature=0.7,
                max_tokens=80,
                timeout=30,
                extra_context=extra_context,
            )
            if multi:
                if providers_used is not None:
                    providers_used.extend(p for p, _ in multi)
                line = pick_best_opening_hook(multi, max_words=15)
                if line:
                    return line
        r = complete_for_stage(
            "opening_hook",
            prompt_text,
            system_prompt=sys_prompt,
            temperature=0.7,
            max_tokens=80,
            timeout=30,
            extra_context=extra_context,
        )
        if r and getattr(r, "success", False) and getattr(r, "content", None):
            if providers_used is not None:
                p = getattr(r, "provider", None)
                if p and p not in providers_used:
                    providers_used.append(p)
            line = (getattr(r, "content", "") or "").strip().strip('"').strip()[:120]
            if len(line) > 10:
                return line
    except Exception:
        pass
    return None


def _ai_generate_agent_angles(
    user_id: str,
    prompt: str,
    title: str,
    extra_context: Optional[Dict] = None,
    providers_used: Optional[List[str]] = None,
) -> Optional[str]:
    """Get user's assigned agents and use LLM to suggest narrative angles they would bring to this video."""
    try:
        from backend.services.user_agent_skills import user_agent_skills
        from backend.services.video_ai_bridge import complete_for_stage, complete_multi_provider
        skills = user_agent_skills.get_user_skills(user_id)
        agents = (skills or {}).get("assigned_agents") or []
        if not agents:
            return None
        agent_list = ", ".join(agents[:5])
        prompt_text = (
            f"Assigned AI agents for this video: {agent_list}\n"
            f"Title: {title}\nTopic: {prompt[:200]}\n\n"
            "In one short sentence (max 25 words), suggest how these agents' perspectives could shape the narrative (e.g. content, learning, analytics). Output only that sentence."
        )
        use_all_ais = bool((extra_context or {}).get("use_all_ais"))
        if use_all_ais:
            multi = complete_multi_provider(
                "agent_angles",
                prompt_text,
                system_prompt="You are a creative director. Output one sentence only.",
                max_providers=4,
                temperature=0.5,
                max_tokens=100,
                timeout=25,
                extra_context=extra_context,
            )
            if multi and providers_used is not None:
                providers_used.extend(p for p, _ in multi)
            for _p, r in multi:
                line = (getattr(r, "content", None) or "").strip().strip('"')[:200]
                if len(line) > 5:
                    return line
        r = complete_for_stage(
            "agent_angles",
            prompt_text,
            system_prompt="You are a creative director. Output one sentence only.",
            temperature=0.5,
            max_tokens=100,
            timeout=25,
            extra_context=extra_context,
        )
        if r and getattr(r, "success", False) and getattr(r, "content", None):
            if providers_used is not None:
                p = getattr(r, "provider", None)
                if p and p not in providers_used:
                    providers_used.append(p)
            line = (getattr(r, "content", "") or "").strip().strip('"')[:200]
            if len(line) > 5:
                return line
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
#  Rule-Based AI Layer — works WITHOUT OpenAI credits
# ---------------------------------------------------------------------------
def _rulebased_ai_enrich(
    segments: List[Dict[str, Any]],
    title: str,
    prompt: str,
    user_id: str = "default_user",
) -> List[Dict[str, Any]]:
    """
    Enrich segments using rule-based AI services (no LLM needed).
    Uses: agent_ai_intelligence (strategy, context, prediction, pattern recognition)
          ai_content_generator (strategy + video concept fallbacks)
          ai_skill_implementations (content optimization + analysis)
    """
    try:
        from backend.services.agent_ai_intelligence import agent_ai_intelligence as ai_intel
    except Exception:
        return segments

    agent_id = f"video_gen_{user_id}"

    # 1. Strategy: get production phases for the video topic
    strategy_data = {}
    try:
        strat = ai_intel.develop_strategy(
            agent_id,
            goal=f"create_video:{title[:60]}",
            constraints={"topic": prompt[:200], "segments": len(segments)},
        )
        strategy_data = strat or {}
    except Exception:
        pass

    # 2. Context understanding: analyze the video request
    context_data = {}
    try:
        ctx = ai_intel.understand_context(agent_id, {
            "title": title[:80],
            "prompt": prompt[:200],
            "segment_count": len(segments),
            "type": "video_production",
        })
        context_data = ctx or {}
    except Exception:
        pass

    # 3. Prediction: predict quality outcome
    prediction = {}
    try:
        pred = ai_intel.predict_outcome(
            agent_id,
            action={"type": "encode_video", "segments": len(segments), "title": title[:60]},
            context={"prompt_length": len(prompt), "segment_count": len(segments)},
        )
        prediction = pred or {}
    except Exception:
        pass

    # 4. Learn from experience (track this generation)
    try:
        ai_intel.learn_from_experience(agent_id, {
            "type": "video_generation",
            "title": title[:60],
            "segments": len(segments),
            "prompt_length": len(prompt),
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception:
        pass

    # 5. Apply AI insights to segments
    phases = strategy_data.get("phases", [])
    confidence = prediction.get("confidence", 0.7)
    priority_elements = context_data.get("priority_elements", [])

    enhanced = []
    for i, seg in enumerate(segments):
        e = dict(seg)
        # Add strategy phase as tagline if segment doesn't have one
        if not e.get("tagline") and i < len(phases):
            phase = phases[i]
            action = str(phase.get("action", "")).replace("_", " ").title()
            e["tagline"] = f"Phase {phase.get('phase', i+1)}: {action}"
        # Add confidence to description if not already AI-enriched
        if not e.get("mood"):
            desc = e.get("description", "")
            conf_pct = int(confidence * 100)
            if conf_pct > 0 and "AI confidence" not in desc:
                e["description"] = f"{desc} [AI confidence: {conf_pct}%]"[:260]
        enhanced.append(e)

    # 6. Content optimization via ai_skill_implementations
    try:
        from backend.services.ai_skill_implementations import ai_skill_implementations as ai_skills
        for i, seg in enumerate(enhanced):
            opt = ai_skills.content_optimization(
                seg.get("description", "")[:200],
                optimization_goal="engagement",
                agent_id=agent_id,
            )
            if isinstance(opt, dict) and opt.get("success"):
                optimization = opt.get("optimization", {})
                if isinstance(optimization, dict):
                    score = optimization.get("optimization_score", 0)
                    if score and not seg.get("tagline"):
                        enhanced[i]["tagline"] = f"Engagement score: {int(score * 100)}%"
    except Exception:
        pass

    # 7. Video concept from ai_content_generator (rule-based fallback)
    concept = _ai_video_concept(prompt)
    if concept and len(enhanced) > 0 and not enhanced[0].get("mood"):
        first_desc = enhanced[0].get("description", "")
        if len(first_desc) < 200:
            enhanced[0]["description"] = f"{first_desc} — {concept[:100]}"[:260]

    # 8. Agent credit: add assigned agents to last segment for transparency
    try:
        from backend.services.user_agent_skills import user_agent_skills
        skills = user_agent_skills.get_user_skills(user_id)
        assigned = list((skills or {}).get("assigned_agents") or [])[:5]
        if assigned and len(enhanced) > 0:
            last = enhanced[-1]
            agent_label = ", ".join(a.replace("_", " ").title() for a in assigned)
            credit = f"Agent-assisted: {agent_label}"
            if last.get("tagline"):
                last["tagline"] = f"{last['tagline']} · {credit}"[:80]
            else:
                last["tagline"] = credit[:60]
    except Exception:
        pass

    # 9. Content strategy from ai_content_generator
    strat_content = _ai_content_strategy(title, prompt)
    if isinstance(strat_content, dict):
        strat_inner = strat_content.get("strategy", {})
        if isinstance(strat_inner, dict):
            strat_id = strat_inner.get("strategy_id", "")
            est_success = strat_inner.get("estimated_success", 0)
            if est_success and len(enhanced) > 0:
                last = enhanced[-1]
                if "strategy" not in (last.get("tagline") or "").lower():
                    enhanced[-1]["tagline"] = f"Strategy confidence: {int(est_success * 100)}%"

    return enhanced


def _status_sidecar_path(doc_id: str) -> str:
    return os.path.join(VIDEOS_DIR, f"{doc_id}.status.json")


def _run_sidecar_path(doc_id: str) -> str:
    return os.path.join(VIDEOS_DIR, f"{doc_id}.run.json")


def write_run_sidecar(doc_id: str, pid: int, duration_sec: int = 180) -> None:
    """Track subprocess PID for stale reaper (E10)."""
    try:
        payload = {
            "doc_id": doc_id,
            "pid": int(pid),
            "started_at": datetime.utcnow().isoformat() + "Z",
            "duration_sec": max(30, int(duration_sec or 180)),
        }
        with open(_run_sidecar_path(doc_id), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass


def clear_run_sidecar(doc_id: str) -> None:
    try:
        p = _run_sidecar_path(doc_id)
        if os.path.isfile(p):
            os.remove(p)
    except Exception:
        pass


def _infer_encode_stage(message: str) -> str:
    """Map progress message to encoder stage id (E9)."""
    msg = (message or "").strip()
    low = msg.lower()
    if low.startswith("planning") or "scene plan" in low:
        return "planning"
    if low.startswith("enhancing") or "enhance segment" in low:
        return "enhancing"
    seg = re.search(r"building segment\s+(\d+)", low)
    if seg:
        return f"segment_{seg.group(1)}"
    if "concat" in low:
        return "concat"
    if "encoding video" in low or low.startswith("encoding") or "mux" in low:
        return "mux"
    if any(k in low for k in ("generating ai", "runway", "heygen", "replicate", "pika", "modelslab")):
        return "enhancing"
    return "processing"


def _service_check_summary(detail: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Slim dict for status sidecar / dashboards (avoids huge nested blobs)."""
    if not isinstance(detail, dict):
        return None
    return {
        "disk_ok": (detail.get("disk") or {}).get("ok"),
        "llm_ok": (detail.get("llm") or {}).get("ok"),
        "ffmpeg_ok": (detail.get("ffmpeg") or {}).get("ok"),
    }


def _generation_meta_for_sidecar(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Fields to merge into progress sidecar from a generation config."""
    if not config:
        return {}
    meta: Dict[str, Any] = {}
    run_id = config.get("_generation_run_id")
    if run_id:
        meta["generation_run_id"] = str(run_id)[:160]
    addon = config.get("_storyline_addon")
    if addon:
        meta["storyline_preview"] = str(addon)[:600]
    vs = config.get("_visual_seed")
    if vs is not None:
        try:
            meta["visual_seed"] = int(vs)
        except Exception:
            pass
    sc = config.get("_service_check")
    summ = _service_check_summary(sc if isinstance(sc, dict) else None)
    if summ:
        meta["service_check"] = summ
    return meta


def _write_status_sidecar(
    doc_id: str,
    status: str,
    message: str,
    error_message: Optional[str] = None,
    progress: Optional[int] = None,
    video_url: Optional[str] = None,
    title: Optional[str] = None,
    prompt: Optional[str] = None,
    providers_used: Optional[List[str]] = None,
    generation_meta: Optional[Dict[str, Any]] = None,
    stage: Optional[str] = None,
) -> None:
    try:
        now = datetime.utcnow()
        payload = {
            "id": doc_id,
            "status": status,
            "message": message,
            "error_message": error_message or "",
            "progress": int(progress if progress is not None else (100 if status == "completed" else 0)),
            "video_url": video_url or (f"/api/documentary/video/{doc_id}" if status == "completed" else None),
            "updated_at": now.isoformat() + "Z",
        }
        if stage:
            payload["stage"] = str(stage)[:40]
        if status == "completed":
            from datetime import timedelta
            from backend.services.video_retention_service import TEMP_EXPIRY_MINUTES
            payload["expires_at"] = (now + timedelta(minutes=TEMP_EXPIRY_MINUTES)).isoformat() + "Z"
        if title:
            payload["title"] = str(title)[:180]
        if prompt:
            payload["prompt"] = str(prompt)[:500]
        if providers_used:
            payload["providers_used"] = list(providers_used)[:20]
        if generation_meta:
            for k, v in generation_meta.items():
                if v is not None:
                    payload[k] = v
        with open(_status_sidecar_path(doc_id), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _rearrange_segments_for_timeline(segments: List[Dict[str, Any]], target_duration: int) -> List[Dict[str, Any]]:
    """
    Rearrange/normalize segment timeline so clips/videos become one coherent whole-file flow.
    """
    cleaned: List[Dict[str, Any]] = []
    for i, seg in enumerate(segments or []):
        title = str((seg or {}).get("title") or f"Scene {i + 1}").strip()[:80]
        desc = str((seg or {}).get("description") or "").strip()[:260]
        if not desc:
            continue
        try:
            dur = int((seg or {}).get("duration", 6))
        except Exception:
            dur = 6
        dur = max(2, min(20, dur))
        entry = {
            "title": title,
            "description": desc,
            "duration": dur,
            "image_path": (seg or {}).get("image_path"),
        }
        for extra_key in ("mood", "tagline", "bg_color"):
            val = (seg or {}).get(extra_key)
            if val:
                entry[extra_key] = val
        cleaned.append(entry)

    if not cleaned:
        return []

    desired = max(6, int(target_duration or sum(s["duration"] for s in cleaned)))
    total = max(1, sum(s["duration"] for s in cleaned))
    scale = desired / float(total)
    normalized: List[Dict[str, Any]] = []
    for seg in cleaned:
        nd = max(2, min(20, int(round(seg["duration"] * scale))))
        entry = {
            "title": seg["title"],
            "description": seg["description"],
            "duration": nd,
            "image_path": seg.get("image_path"),
        }
        for extra_key in ("mood", "tagline", "bg_color"):
            val = seg.get(extra_key)
            if val:
                entry[extra_key] = val
        normalized.append(entry)

    current = sum(s["duration"] for s in normalized)
    diff = desired - current
    idx = 0
    while diff != 0 and normalized and idx <= 500:
        s = normalized[idx % len(normalized)]
        if diff > 0 and s["duration"] < 20:
            s["duration"] += 1
            diff -= 1
        elif diff < 0 and s["duration"] > 2:
            s["duration"] -= 1
            diff += 1
        idx += 1
    return normalized


def _write_generation_pipeline_file(bundle_id: str, payload: Dict[str, Any]) -> Optional[str]:
    """Persist pipeline data as one sidecar whole-file JSON."""
    try:
        out_path = os.path.join(VIDEOS_DIR, f"{bundle_id}.pipeline.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return out_path
    except Exception:
        return None


def _resolve_audio_profile(config: Optional[Dict[str, Any]] = None, fallback_style: str = "auto") -> Dict[str, Any]:
    """Derive audio style/intensity settings from generation config."""
    cfg = dict(config or {})
    hint = " ".join([
        str(cfg.get("audio_style") or ""),
        str(cfg.get("template") or ""),
        str(cfg.get("theme") or ""),
        str(cfg.get("content_category") or ""),
        str(cfg.get("description") or "")[:120],
    ]).lower()

    style = str(cfg.get("audio_style") or "auto").strip().lower()
    if style in ("", "auto", "default"):
        preset = str(cfg.get("style_preset") or "").strip().lower()
        tone = str(cfg.get("theme_tone") or "").strip().lower()
        if preset == "documentary" or "documentary" in hint:
            style = "documentary"
        elif tone == "energetic" or any(k in hint for k in ("energetic", "upbeat", "action", "sport")):
            style = "energetic"
        elif any(k in hint for k in ("epic", "battle", "heroic", "war")):
            style = "epic"
        elif any(k in hint for k in ("dark", "mystery", "horror", "night", "conspiracy")):
            style = "dark"
        elif any(k in hint for k in ("calm", "ambient", "meditation", "nature", "soft")):
            style = "calm"
        else:
            style = fallback_style or "cinematic"

    if style not in ("cinematic", "documentary", "energetic", "dark", "epic", "calm"):
        style = "cinematic"

    intensity = str(cfg.get("audio_intensity") or "high").strip().lower()
    if intensity not in ("low", "medium", "high", "max"):
        intensity = "high"

    transitions = str(cfg.get("audio_transitions") or "on").strip().lower() not in ("off", "false", "0", "none")
    fades = str(cfg.get("audio_fades") or "on").strip().lower() not in ("off", "false", "0", "none")

    narration = cfg.get("narration_enabled")
    if narration is None:
        qm = str(cfg.get("quality_mode") or "").strip().lower()
        ep = str(cfg.get("encode_profile") or "").strip().lower()
        narration = qm in ("high", "best", "max", "ultra") or ep in ("premium", "ultra")
    else:
        narration = bool(narration)

    return {
        "style": style,
        "intensity": intensity,
        "transitions": transitions,
        "fades": fades,
        "narration_enabled": narration,
        "narration_voice": str(cfg.get("narration_voice") or "rachel").strip().lower(),
    }


def _build_dynamic_audio_clip(
    total_duration: float,
    segments: List[Dict[str, Any]],
    audio_profile: Optional[Dict[str, Any]] = None,
):
    """
    Build a generated stereo soundtrack with per-segment variation and fades.
    Returns a MoviePy AudioClip or None when dependencies are unavailable.
    """
    try:
        import numpy as np
        from moviepy import AudioClip
    except Exception:
        return None

    total_duration = max(1.0, float(total_duration or 1.0))
    profile = audio_profile or {}
    style = str(profile.get("style") or "cinematic").lower()
    intensity = str(profile.get("intensity") or "high").lower()
    use_transitions = bool(profile.get("transitions", True))
    use_fades = bool(profile.get("fades", True))
    intensity_gain = {"low": 0.72, "medium": 0.88, "high": 1.0, "max": 1.18}.get(intensity, 1.0)

    palette_by_style = {
        "cinematic": [82.0, 98.0, 110.0, 123.47, 146.83, 164.81, 196.0, 220.0],
        "documentary": [73.42, 82.41, 98.0, 110.0, 123.47, 130.81, 146.83],
        "energetic": [110.0, 130.81, 146.83, 164.81, 196.0, 220.0, 246.94],
        "dark": [55.0, 65.4, 73.4, 82.4, 92.5, 98.0, 110.0],
        "epic": [98.0, 123.47, 146.83, 174.61, 196.0, 246.94],
        "calm": [130.81, 146.83, 164.81, 174.61, 196.0, 220.0],
    }
    bed_params_by_style = {
        "cinematic": {"base_hz": 42.0, "harm_hz": 84.0, "bed_gain": 0.06, "pulse_scale": 1.0},
        "documentary": {"base_hz": 55.0, "harm_hz": 110.0, "bed_gain": 0.075, "pulse_scale": 0.65},
        "energetic": {"base_hz": 62.0, "harm_hz": 124.0, "bed_gain": 0.05, "pulse_scale": 1.35},
        "dark": {"base_hz": 38.0, "harm_hz": 76.0, "bed_gain": 0.07, "pulse_scale": 0.85},
        "epic": {"base_hz": 48.0, "harm_hz": 96.0, "bed_gain": 0.065, "pulse_scale": 1.1},
        "calm": {"base_hz": 52.0, "harm_hz": 104.0, "bed_gain": 0.055, "pulse_scale": 0.75},
    }
    base_palette = palette_by_style.get(style, palette_by_style["cinematic"])
    bed_cfg = bed_params_by_style.get(style, bed_params_by_style["cinematic"])
    if not segments:
        segments = [{"title": "Scene", "description": "", "duration": int(total_duration)}]

    timeline = []
    cursor = 0.0
    for i, seg in enumerate(segments):
        seg_dur = max(1.2, min(30.0, float(seg.get("duration", 4) or 4)))
        start = cursor
        end = min(total_duration, start + seg_dur)
        if end <= start:
            continue
        text = f"{seg.get('title', '')} {seg.get('description', '')}"
        signature = sum(ord(ch) for ch in text) % 997 if text else (i * 53 + 17)
        base = base_palette[(i + signature) % len(base_palette)]
        modulation = 0.08 + ((signature % 9) / 100.0)
        pulse_hz = 0.22 + ((signature % 7) * 0.06)
        pan = ((signature % 200) / 100.0) - 1.0
        gain = (0.23 + ((signature % 5) * 0.035)) * intensity_gain
        timeline.append({
            "start": start,
            "end": end,
            "dur": end - start,
            "base": base,
            "mod": modulation,
            "pulse": pulse_hz,
            "pan": pan,
            "gain": gain,
            "phase": (signature % 360) * (math.pi / 180.0),
        })
        cursor = end
        if cursor >= total_duration:
            break

    if timeline and timeline[-1]["end"] < total_duration:
        last = dict(timeline[-1])
        last["start"] = timeline[-1]["end"]
        last["end"] = total_duration
        last["dur"] = max(0.001, total_duration - last["start"])
        timeline.append(last)

    def make_audio_frame(t):
        arr = np.atleast_1d(np.array(t, dtype=np.float64))
        out = np.zeros((arr.size, 2), dtype=np.float32)

        bed_scale = 1.0 if style != "calm" else 1.15
        bed_dark = 0.95 if style != "dark" else 1.25
        b_gain = float(bed_cfg.get("bed_gain", 0.06))
        b_base = float(bed_cfg.get("base_hz", 42.0)) * bed_dark
        b_harm = float(bed_cfg.get("harm_hz", 84.0)) * bed_dark
        bed = (
            (b_gain * bed_scale) * np.sin(2.0 * math.pi * b_base * arr) +
            (b_gain * 0.58 * bed_scale) * np.sin(2.0 * math.pi * b_harm * arr + 0.75)
        )
        if style == "documentary":
            bed += (0.022 * bed_scale) * np.sin(2.0 * math.pi * 27.5 * arr + 0.4)
        elif style == "energetic":
            beat_period = 0.55
            phase = np.mod(arr, beat_period) / beat_period
            tick = np.exp(-((phase - 0.06) ** 2) / (2.0 * (0.014 ** 2)))
            bed += (0.038 * bed_scale) * tick * np.sin(2.0 * math.pi * 220.0 * arr)
        out[:, 0] += bed
        out[:, 1] += bed * 0.96

        for seg in timeline:
            mask = (arr >= seg["start"]) & (arr < seg["end"])
            if not np.any(mask):
                continue
            local_t = arr[mask] - seg["start"]
            seg_dur = max(0.25, seg["dur"])
            fade_len = min(1.2, max(0.25, seg_dur * 0.22))
            if use_fades:
                fade_in = np.clip(local_t / fade_len, 0.0, 1.0)
                fade_out = np.clip((seg_dur - local_t) / fade_len, 0.0, 1.0)
                envelope = np.minimum(fade_in, fade_out)
            else:
                envelope = np.ones_like(local_t)

            base = seg["base"]
            wobble = 1.0 + seg["mod"] * np.sin(2.0 * math.pi * 0.10 * local_t + seg["phase"])
            fundamental = np.sin(2.0 * math.pi * (base * wobble) * local_t)
            harmonic = 0.44 * np.sin(2.0 * math.pi * (base * 1.5) * local_t + seg["phase"])
            shimmer = 0.22 * np.sin(2.0 * math.pi * (base * 2.02) * local_t + 0.3)
            pulse = 0.82 + 0.18 * np.sin(2.0 * math.pi * seg["pulse"] * local_t * float(bed_cfg.get("pulse_scale", 1.0)))

            signal = seg["gain"] * envelope * pulse * (0.62 * fundamental + harmonic + shimmer)
            if use_transitions:
                # Short transition accent ("special fx") near each scene start.
                onset = np.exp(-((local_t - 0.08) ** 2) / (2.0 * (0.055 ** 2)))
                sweep = np.sin(2.0 * math.pi * (420.0 + 140.0 * local_t) * local_t + seg["phase"])
                signal += (0.07 * intensity_gain) * onset * sweep

            pan = max(-1.0, min(1.0, seg["pan"]))
            left_w = 1.0 - max(0.0, pan) * 0.45
            right_w = 1.0 + min(0.0, pan) * 0.45
            out[mask, 0] += signal * left_w
            out[mask, 1] += signal * right_w

        if use_fades:
            intro = np.clip(arr / 1.0, 0.0, 1.0)
            outro = np.clip((total_duration - arr) / 1.2, 0.0, 1.0)
            master = np.minimum(intro, outro).reshape((-1, 1))
            out *= master

        out = np.tanh(out * (1.5 * intensity_gain)) * 0.70

        if np.isscalar(t):
            return [float(out[0, 0]), float(out[0, 1])]
        return out

    try:
        return AudioClip(make_audio_frame, duration=total_duration, fps=44100)
    except Exception:
        return None


def _apply_text_overlay(
    base_clip, title: str, body: str, width: int, height: int, duration_sec: int,
    bg_color: Optional[tuple] = None, tagline: str = "", mood: str = "",
):
    """
    Burn title/body/tagline onto a solid-colour frame using Pillow.
    Returns pure-RGB ImageClip (safe for all ffmpeg builds).
    AI-enriched segments can pass bg_color, tagline, and mood for richer visuals.
    """
    combined = f"{(title or '').strip()} {(body or '').strip()}".strip()[:520]
    if not combined:
        return base_clip, False

    try:
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont
        from moviepy import ImageClip

        if bg_color and isinstance(bg_color, (list, tuple)) and len(bg_color) >= 3:
            bg = (int(bg_color[0]), int(bg_color[1]), int(bg_color[2]))
        else:
            bg = (15, 25, 45)
            try:
                frame0 = base_clip.get_frame(0)
                if frame0 is not None and hasattr(frame0, 'shape') and frame0.shape[0] > 0:
                    bg = (int(frame0[0][0][0]), int(frame0[0][0][1]), int(frame0[0][0][2]))
            except Exception:
                pass

        img = Image.new("RGB", (width, height), bg)
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        margin_x = int(width * 0.08)

        # Decorative top bar
        bar_color = (0, 255, 136)
        if mood in _MOOD_COLOR_MAP:
            mc = _MOOD_COLOR_MAP[mood]
            bar_color = (min(255, mc[0] * 4 + 80), min(255, mc[1] * 4 + 80), min(255, mc[2] * 3 + 60))
        draw.rectangle([(0, 0), (width, 4)], fill=bar_color)

        y = int(height * 0.10)

        # Tagline (small accent text above title)
        if tagline:
            for line in textwrap.wrap(tagline[:60], width=60):
                draw.text((margin_x, y), line.upper(), font=font, fill=bar_color)
                y += 16
            y += 6

        # Title
        title_text = (title or '').strip()[:80]
        if title_text:
            title_color = (0, 255, 136)
            for line in textwrap.wrap(title_text, width=48):
                draw.text((margin_x, y), line, font=font, fill=title_color)
                y += 24
            y += 12

        # Separator line
        draw.line([(margin_x, y), (width - margin_x, y)], fill=(60, 80, 120), width=1)
        y += 12

        # Body
        body_text = (body or '').strip()[:400]
        if body_text:
            for line in textwrap.wrap(body_text, width=72):
                draw.text((margin_x, y), line, font=font, fill=(225, 240, 255))
                y += 18
                if y > int(height * 0.82):
                    break

        # Mood badge bottom-right
        if mood:
            badge_text = mood.upper()
            bx = width - margin_x - len(badge_text) * 7
            by = height - 30
            draw.rectangle([(bx - 6, by - 2), (bx + len(badge_text) * 7 + 6, by + 16)], fill=bar_color)
            draw.text((bx, by), badge_text, font=font, fill=(10, 10, 10))

        # Bottom bar
        draw.rectangle([(0, height - 4), (width, height)], fill=bar_color)

        clip = ImageClip(np.array(img)).with_duration(duration_sec)
        return clip, True
    except Exception:
        return base_clip, False


def _compact_context_payload(payload: Dict[str, Any], max_chars: int = 10000) -> Dict[str, Any]:
    """
    Keep AI planner context rich but bounded so long prompts don't break JSON planning.
    """
    compact = dict(payload or {})

    try:
        profile = dict(compact.get("profile") or {})
        if "bio" in profile:
            profile["bio"] = str(profile.get("bio") or "")[:220]
        compact["profile"] = profile
    except Exception:
        pass

    try:
        req = dict(compact.get("generator_request") or {})
        if "content_context" in req:
            req["content_context"] = str(req.get("content_context") or "")[:500]
        if "description" in req:
            req["description"] = str(req.get("description") or "")[:500]
        compact["generator_request"] = req
    except Exception:
        pass

    try:
        ac = compact.get("agent_connections") or []
        compact["agent_connections"] = list(ac)[:12]
    except Exception:
        compact["agent_connections"] = []

    if "rulebook_doc_excerpt" in compact:
        compact["rulebook_doc_excerpt"] = str(compact.get("rulebook_doc_excerpt") or "")[:1200]

    try:
        fusion = dict(compact.get("ai_fusion") or {})
        if "video_description" in fusion:
            fusion["video_description"] = str(fusion.get("video_description") or "")[:300]
        compact["ai_fusion"] = fusion
    except Exception:
        pass

    try:
        packed = json.dumps(compact, ensure_ascii=True)
        if len(packed) > max_chars:
            compact.pop("rulebook_doc_excerpt", None)
            compact["agent_connections"] = (compact.get("agent_connections") or [])[:6]
            req = dict(compact.get("generator_request") or {})
            if "content_context" in req:
                req["content_context"] = str(req.get("content_context") or "")[:260]
            compact["generator_request"] = req
    except Exception:
        pass
    return compact


def _extract_json_object(raw_text: str) -> Optional[Dict[str, Any]]:
    """Extract first JSON object from a model response."""
    raw = (raw_text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass
    s_idx = raw.find("{")
    e_idx = raw.rfind("}")
    if s_idx != -1 and e_idx != -1 and e_idx > s_idx:
        try:
            obj = json.loads(raw[s_idx:e_idx + 1])
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    return None


def _normalize_scene_plan(obj: Optional[Dict[str, Any]], max_segments: int) -> List[Dict[str, Any]]:
    """Normalize scene-plan JSON into internal segment schema. Supports opening_hook from LLM."""
    if not isinstance(obj, dict):
        return []
    scenes = obj.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return []
    opening_hook = str((obj.get("opening_hook") or "")).strip()[:120]
    segs: List[Dict[str, Any]] = []
    for i, sc in enumerate(scenes[:max_segments]):
        desc = str((sc or {}).get("description") or "").strip()[:260]
        ttl = str((sc or {}).get("title") or "Scene").strip()[:80]
        dur_raw = (sc or {}).get("duration", 6)
        try:
            dur = max(2, min(20, int(dur_raw)))
        except Exception:
            dur = 6
        if desc:
            seg = {"title": ttl, "description": desc, "duration": dur}
            if opening_hook and i == 0:
                seg["opening_hook"] = opening_hook
            segs.append(seg)
    return segs


def _build_content_fallback_segments(
    title: str, prompt: str, duration_sec: int, short: bool = False,
    extra_context: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Build content-rich segments from user input.
    Uses AI (LLM) to generate vivid descriptions and chapter titles when available;
    falls back to splitting user text into chapters if LLM is offline.
    """
    t = (title or "Documentary").strip()[:80]
    p = (prompt or t).strip()[:500]
    addon = ""
    if extra_context and (extra_context.get("_storyline_addon") or extra_context.get("episode_setup")):
        addon = str(extra_context.get("_storyline_addon") or extra_context.get("episode_setup") or "")[:400]
    if addon:
        p = f"{p}\n\nStory setup for this run: {addon}"[:800]

    # Try AI-powered descriptions first
    ai_descs = _ai_generate_enhanced_descriptions(t, p, segment_count=3 if short else 6)
    ai_titles = _ai_generate_title_variations(t, count=3 if short else 6)

    style, tone, _ = _get_style_and_tone_for_plan(extra_context)
    opening_hook = _ai_generate_opening_hook(t, p, style, tone, extra_context=extra_context)
    if short or duration_sec <= 30:
        segs = [
            {"title": (ai_titles[0] if ai_titles and len(ai_titles) > 0 else t),
             "description": (ai_descs[0] if ai_descs and len(ai_descs) > 0 else f"Introduction: {p}"),
             "duration": 5, **({"opening_hook": opening_hook} if opening_hook else {})},
            {"title": (ai_titles[1] if ai_titles and len(ai_titles) > 1 else f"About: {t}"),
             "description": (ai_descs[1] if ai_descs and len(ai_descs) > 1 else p[:200]),
             "duration": 6},
            {"title": (ai_titles[2] if ai_titles and len(ai_titles) > 2 else "Summary"),
             "description": (ai_descs[2] if ai_descs and len(ai_descs) > 2 else f"Conclusion: {t}. {p[:120]}"),
             "duration": 4},
        ]
        segs = _ai_enhance_segments(segs, t, p, extra_context=extra_context)
        return _rulebased_ai_enrich(segs, t, p)

    words = p.split()
    chunk_size = max(1, len(words) // 4)
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)][:4]
    while len(chunks) < 4:
        chunks.append(p[:100])
    seg_dur = max(4, duration_sec // 6)
    default_chapter_names = ["Background", "Details", "Analysis", "Insights"]
    first_seg = {"title": (ai_titles[0] if ai_titles and len(ai_titles) > 0 else t),
                 "description": (ai_descs[0] if ai_descs and len(ai_descs) > 0 else f"Introduction: {p[:160]}"),
                 "duration": seg_dur}
    if opening_hook:
        first_seg["opening_hook"] = opening_hook
    segs = [first_seg]
    for i in range(4):
        segs.append({
            "title": (ai_titles[i + 1] if ai_titles and len(ai_titles) > i + 1 else f"Chapter {i+1}: {default_chapter_names[i]}"),
            "description": (ai_descs[i + 1] if ai_descs and len(ai_descs) > i + 1 else chunks[i][:200]),
            "duration": seg_dur,
        })
    segs.append({
        "title": (ai_titles[5] if ai_titles and len(ai_titles) > 5 else "Summary"),
        "description": (ai_descs[5] if ai_descs and len(ai_descs) > 5 else f"Conclusion: {t}. {p[:120]}"),
        "duration": seg_dur,
    })
    segs = _ai_enhance_segments(segs, t, p, extra_context=extra_context)
    return _rulebased_ai_enrich(segs, t, p)


def _plan_ai_segments(
    user_id: str,
    prompt: str,
    title: str,
    duration_sec: int,
    short: bool = False,
    max_segments: int = 8,
    extra_context: Optional[Dict[str, Any]] = None,
    require_ai: bool = True,
    providers_used: Optional[List[str]] = None,
) -> Tuple[List[Dict[str, Any]], str, str]:
    """
    Zip profile+prompt+context into one AI plan and return scene segments.
    Returns (segments, ai_script_text, profile_context_text).
    """
    profile_context_text = ""
    fallback_segments: List[Dict[str, Any]] = []
    context_payload: Dict[str, Any] = {"user_id": user_id}
    try:
        from backend.services.generator_context_service import gather_context_for_user, context_to_segments
        ctx = gather_context_for_user(user_id)
        profile = (ctx or {}).get("profile") or {}
        p_name = profile.get("display_name") or profile.get("username") or user_id
        p_bio = (profile.get("bio") or "").strip()
        pts = (ctx or {}).get("unified_points") or {}
        profile_context_text = (
            f"name={p_name}; bio={p_bio[:180]}; level={int(pts.get('level', 1))}; "
            f"generation_points={int(pts.get('generation_points', 0))}"
        )
        context_payload.update({
            "profile": {
                "display_name": p_name,
                "bio": p_bio[:260],
            },
            "points": {
                "level": int(pts.get("level", 1)),
                "generation_points": int(pts.get("generation_points", 0)),
                "xp_total": int(pts.get("xp_total", 0)),
            },
            "agent_connections": (ctx or {}).get("agent_connections", [])[:20],
            "service_worker_context": (ctx or {}).get("service_worker_context", {}),
        })
        fallback_segments = context_to_segments(
            ctx,
            user_prompt=prompt,
            user_title=title,
            short=short,
            max_segments=max_segments,
            include_points_in_clip=True,
        )
        if not fallback_segments:
            fallback_segments = _build_content_fallback_segments(
                title, prompt, duration_sec, short, extra_context=extra_context,
            )
    except Exception:
        profile_context_text = f"name={user_id}; level=1; generation_points=0"
        context_payload.update({
            "profile": {"display_name": user_id, "bio": ""},
            "points": {"level": 1, "generation_points": 0, "xp_total": 0},
            "agent_connections": [],
            "service_worker_context": {},
        })
        # Build content-rich fallback from user input so video is never blank
        fallback_segments = _build_content_fallback_segments(
            title, prompt, duration_sec, short, extra_context=extra_context,
        )

    if extra_context:
        # Merge route-level generator context so all content goes into the same AI prompt.
        context_payload["generator_request"] = {
            "content_category": extra_context.get("content_category"),
            "content_context": extra_context.get("content_context"),
            "template": extra_context.get("template"),
            "resolution": extra_context.get("resolution"),
            "short_clip": bool(extra_context.get("short_clip", short)),
            "include_points_in_clip": bool(extra_context.get("include_points_in_clip", True)),
            "duration": int(extra_context.get("duration", duration_sec) or duration_sec),
            "theme": extra_context.get("theme"),
            "description": extra_context.get("description"),
        }

    # User's assigned agents (content_generator_agent, learning_agent, etc.) for narrative angles
    try:
        from backend.services.user_agent_skills import user_agent_skills
        skills = user_agent_skills.get_user_skills(user_id)
        context_payload["assigned_agents"] = list((skills or {}).get("assigned_agents") or [])[:10]
    except Exception:
        context_payload["assigned_agents"] = []

    # Include rulebook context (V15 index + compact doc context) as additional AI signal.
    try:
        rb_idx_path = os.path.join(_BASE, "data", "rulebook_index_v15.json")
        if os.path.isfile(rb_idx_path):
            with open(rb_idx_path, "r", encoding="utf-8") as f:
                rb_idx = json.load(f)
            context_payload["rulebook"] = {
                "version": rb_idx.get("version"),
                "name": rb_idx.get("name"),
                "description": rb_idx.get("description"),
                "agent_prompt": rb_idx.get("agent_prompt"),
                "tech_spec": rb_idx.get("tech_spec"),
                "manual": rb_idx.get("manual"),
                "rulebook_count": len(rb_idx.get("rulebooks") or []),
            }
    except Exception:
        pass
    try:
        rb_doc = os.path.join(_BASE, "docs", "RULEBOOK_AGENT_CONTEXT.md")
        if os.path.isfile(rb_doc):
            with open(rb_doc, "r", encoding="utf-8") as f:
                txt = f.read()
            context_payload["rulebook_doc_excerpt"] = txt[:2000]
    except Exception:
        pass

    # Multi-AI fusion: attach strategy/video concepts from AI content generator.
    ai_fusion: Dict[str, Any] = {}
    try:
        from backend.services.ai_content_generator import ai_content_generator
        strat = ai_content_generator.generate_content(
            "strategy",
            {
                "goal": f"video_plan:{title or 'documentary'}",
                "constraints": {
                    "duration_sec": duration_sec,
                    "short": short,
                    "max_segments": max_segments,
                    "user_id": user_id,
                },
            },
            agent_class="content_agent",
        )
        vidc = ai_content_generator.generate_content(
            "video",
            {
                "topic": prompt or title or "documentary",
            },
            agent_class="content_agent",
        )
        ai_fusion = {
            "strategy": (strat or {}).get("strategy") if isinstance(strat, dict) else None,
            "strategy_llm": ((strat or {}).get("strategy") or {}).get("llm_strategy") if isinstance(strat, dict) else None,
            "video_description": (vidc or {}).get("description") if isinstance(vidc, dict) else None,
        }
    except Exception:
        ai_fusion = {}
    if ai_fusion:
        context_payload["ai_fusion"] = ai_fusion

    try:
        from backend.services.generator_context_cache import get as ctx_cache_get, put as ctx_cache_put
        cached = ctx_cache_get(user_id, context_payload)
        if isinstance(cached, dict) and cached.get("segments"):
            return (
                cached.get("segments") or [],
                str(cached.get("ai_script") or ""),
                str(cached.get("profile_context_text") or profile_context_text),
            )

        def _cache_plan(segs, ai_script):
            try:
                ctx_cache_put(user_id, context_payload, {
                    "segments": segs,
                    "ai_script": ai_script,
                    "profile_context_text": profile_context_text,
                })
            except Exception:
                pass
    except Exception:
        def _cache_plan(segs, ai_script):
            pass

    try:
        from backend.services.video_ai_bridge import complete_for_stage
        from backend.services.llm_service import llm_service
        if llm_service and llm_service.is_available():
            scene_count = 3 if short else max(4, min(max_segments, int(duration_sec / 15)))
            compact_context = _compact_context_payload(context_payload)
            packed_context_json = json.dumps(compact_context, ensure_ascii=True)
            style, tone, twist = _get_style_and_tone_for_plan(extra_context)
            agent_angles = _ai_generate_agent_angles(user_id, prompt, title, extra_context=extra_context, providers_used=providers_used)
            agent_angle_line = f"\nAgent narrative angle (weave into scenes): {agent_angles}" if agent_angles else ""
            assigned = context_payload.get("assigned_agents") or []
            agent_list_line = ""
            if assigned:
                agent_list_line = f"\nAssigned agents for this user: {', '.join(assigned[:6])}. Consider their expertise (content, learning, analytics) when writing scene descriptions."
            run_id = str((extra_context or {}).get("_generation_run_id") or (extra_context or {}).get("_storyline_run") or "")[:120]
            story_addon = str((extra_context or {}).get("_storyline_addon") or "").strip()
            story_block = ""
            if story_addon:
                story_block = f"\nUnique storyline for THIS generation only (honor it in every scene):\n{story_addon[:900]}\n"
            if run_id:
                story_block = f"Generation run id: {run_id}\n" + story_block
            base_prompt = (
                "Create a JSON scene plan for a video using ALL provided context.\n"
                f"User prompt: {prompt}\n"
                f"Title: {title}\n"
                f"Packed context JSON: {packed_context_json}\n"
                f"Target scenes: {scene_count}\n"
                f"Narrative style: {style}. Theme tone: {tone}. Creative direction: {twist}\n"
                f"{agent_list_line}{agent_angle_line}\n"
                f"{story_block}"
                "Make this video unique—vary structure, phrasing, and emphasis so it feels different every time.\n"
                "Return strict JSON only with this schema:\n"
                '{"opening_hook":"one short catchy opening line (max 15 words)", "scenes":[{"title":"...","description":"...","duration":6}]}\n'
                "Rules:\n"
                "1) Every scene description must incorporate profile + prompt + request context.\n"
                "2) Avoid generic filler lines like 'profile, agents, and your request'.\n"
                "3) Keep descriptions concrete, specific, and tied to user intent.\n"
                "4) Durations should sum close to requested duration.\n"
                "5) Use ai_fusion signals and agent angles to enrich narrative direction.\n"
                "6) Honor the narrative style and theme tone above for a distinct result.\n"
                "7) Include opening_hook to grab the viewer in the first scene."
            )
            # Adaptive planner: route to long-context provider; use best model for complex/high-quality requests.
            quality_mode = str((extra_context or {}).get("quality_mode") or "").strip().lower()
            high_complexity = (duration_sec >= 150) or (scene_count >= 8)
            prefer_best = quality_mode in ("best", "max", "ultra") or high_complexity

            attempts = [
                {"temperature": 0.35, "max_tokens": 1100, "prompt": base_prompt},
                {
                    "temperature": 0.2,
                    "max_tokens": 1200,
                    "prompt": (
                        base_prompt
                        + "\nIMPORTANT: Return ONLY valid JSON object. No prose, no markdown fences."
                        + " Fix any previous formatting and output strict schema now."
                    ),
                },
            ]

            use_all_ais = bool((extra_context or {}).get("use_all_ais"))
            if use_all_ais:
                from backend.services.video_ai_bridge import complete_multi_provider, pick_best_scene_plan
                multi = complete_multi_provider(
                    "scene_plan",
                    base_prompt,
                    system_prompt="You are a video storyboard planner. Output strict JSON only.",
                    max_providers=5,
                    temperature=0.35,
                    max_tokens=1100,
                    timeout=90,
                    extra_context=extra_context,
                )
                if multi and providers_used is not None:
                    providers_used.extend(p for p, _ in multi)
                segs = pick_best_scene_plan(multi, _normalize_scene_plan, max_segments=max_segments)
                if segs:
                    if not any(s.get("opening_hook") for s in segs):
                        hook = _ai_generate_opening_hook(
                            title, prompt, style, tone,
                            extra_context=extra_context,
                            providers_used=providers_used,
                        )
                        if hook and len(segs) > 0:
                            segs[0]["opening_hook"] = hook
                    ai_script = "\n".join([f"- {s['title']}: {s['description']}" for s in segs])
                    _cache_plan(segs, ai_script)
                    return segs, ai_script, profile_context_text

            for attempt in attempts:
                r = complete_for_stage(
                    "scene_plan",
                    attempt["prompt"],
                    system_prompt="You are a video storyboard planner. Output strict JSON only.",
                    temperature=attempt["temperature"],
                    max_tokens=attempt["max_tokens"],
                    timeout=90,
                    use_best=prefer_best,
                    extra_context=extra_context,
                )
                if not (r and getattr(r, "success", False) and getattr(r, "content", None)):
                    continue
                obj = _extract_json_object(getattr(r, "content", "") or "")
                segs = _normalize_scene_plan(obj, max_segments=max_segments)
                if segs:
                    if not any(s.get("opening_hook") for s in segs):
                        hook = _ai_generate_opening_hook(
                            title, prompt, style, tone,
                            extra_context=extra_context,
                            providers_used=providers_used,
                        )
                        if hook and len(segs) > 0:
                            segs[0]["opening_hook"] = hook
                    if providers_used is not None and r and getattr(r, "provider", None):
                        p = getattr(r, "provider", None)
                        if p and p not in providers_used:
                            providers_used.append(p)
                    ai_script = "\n".join([f"- {s['title']}: {s['description']}" for s in segs])
                    _cache_plan(segs, ai_script)
                    return segs, ai_script, profile_context_text
    except Exception:
        pass

    # Strict mode: do not silently fall back to generic/non-AI scenes.
    if require_ai:
        return [], "", profile_context_text
    ai_script = "\n".join([f"- {(s.get('title') or '')}: {(s.get('description') or '')}" for s in fallback_segments])
    return fallback_segments, ai_script[:4000], profile_context_text


def _generate_video_sync(doc_id: str, prompt: str, title: str, duration_sec: int,
                         width: int, height: int, on_progress: Optional[Callable[[int, str], None]] = None,
                         encode_profile: Optional[str] = None,
                         ) -> Tuple[Optional[str], Optional[str]]:
    """
    Generate a video file synchronously.
    Returns (path, None) on success or (None, error_message) on failure.
    Uses MoviePy ColorClip if available; otherwise copies sample video.
    """
    out_path = os.path.join(VIDEOS_DIR, f'{doc_id}.mp4')
    last_error = None

    # Try MoviePy first
    try:
        from moviepy import ColorClip
    except ImportError:
        try:
            from moviepy.editor import ColorClip
        except ImportError:
            ColorClip = None

    if ColorClip is not None:
        ok, space_err = _check_disk_space()
        if not ok:
            last_error = space_err
            if on_progress:
                on_progress(0, last_error)
            return (None, last_error)
        if on_progress:
            on_progress(10, 'Creating video clip...')
        duration_sec = min(max(3, int(duration_sec)), 180)
        w, h = min(width, 854), min(height, 480)
        try:
            from moviepy import concatenate_videoclips
        except ImportError:
            try:
                from moviepy.editor import concatenate_videoclips
            except ImportError:
                concatenate_videoclips = None

        try:
            segments = _build_content_fallback_segments(title, prompt, duration_sec, duration_sec < 120)
            clips_to_concat = []
            for i, seg in enumerate(segments):
                seg_dur = max(2, min(15, int(seg.get("duration", 5))))
                seg_bg = seg.get("bg_color") or _SEGMENT_COLORS[i % len(_SEGMENT_COLORS)]
                color = tuple(seg_bg) if isinstance(seg_bg, (list, tuple)) else _SEGMENT_COLORS[i % len(_SEGMENT_COLORS)]
                c = ColorClip(size=(w, h), color=color, duration=seg_dur)
                tagline_text = (seg.get("opening_hook") or seg.get("tagline", "")).strip() if i == 0 else (seg.get("tagline", "") or "")
                c, _ = _apply_text_overlay(
                    c,
                    title=(seg.get("title") or "")[:70],
                    body=(seg.get("description") or "")[:260],
                    width=w, height=h, duration_sec=seg_dur,
                    bg_color=seg_bg, tagline=tagline_text, mood=seg.get("mood", ""),
                )
                clips_to_concat.append(c)
            if on_progress:
                on_progress(40, 'Concatenating segments...')
            if concatenate_videoclips and len(clips_to_concat) > 1:
                try:
                    clip = concatenate_videoclips(clips_to_concat, method="chain")
                except Exception:
                    clip = concatenate_videoclips(clips_to_concat)
            else:
                clip = clips_to_concat[0] if clips_to_concat else ColorClip(size=(w, h), color=(15, 25, 45), duration=duration_sec)
            if on_progress:
                on_progress(60, 'Encoding video...')
            from backend.services.generator_encode_service import build_write_kwargs, resolve_encode_profile, moviepy_write_kwargs
            prof = str(encode_profile or "fast_ai").strip().lower()
            if prof not in ("fast_ai", "standard", "premium", "ultra"):
                prof = resolve_encode_profile({"encode_profile": encode_profile})
            write_kw = build_write_kwargs(doc_id, prof, add_audio=False, videos_dir=VIDEOS_DIR)
            clip.write_videofile(out_path, **moviepy_write_kwargs(write_kw))
            try:
                if not os.path.isfile(out_path) or os.path.getsize(out_path) < _MIN_VALID_MP4_BYTES:
                    raise RuntimeError("Encoded file too small")
            except Exception as size_err:
                last_error = f"Encode validation error: {size_err}"
                if on_progress:
                    on_progress(0, last_error)
                if hasattr(clip, 'close'):
                    clip.close()
                raise RuntimeError(last_error)
            if hasattr(clip, 'close'):
                clip.close()
            if on_progress:
                on_progress(100, 'Complete')
            return (out_path, None)
        except Exception as e:
            last_error = f'MoviePy error: {_normalize_write_error(e)}'
            if on_progress:
                on_progress(0, last_error)

    # Fallback: copy sample video if it exists
    sample_paths = [
        os.path.join(_BASE, 'output', 'videos', 'f5ebc903.mp4'),
        os.path.join(_BASE, 'vidgenerator', 'videos', 'f5ebc903.mp4'),
    ]
    for sample in sample_paths:
        if os.path.isfile(sample):
            try:
                import shutil
                shutil.copy2(sample, out_path)
                if not os.path.isfile(out_path) or os.path.getsize(out_path) < _MIN_VALID_MP4_BYTES:
                    raise RuntimeError("Sample video too small")
                if on_progress:
                    on_progress(100, 'Complete (sample video)')
                return (out_path, None)
            except Exception as e:
                last_error = f'Copy error: {str(e)}'
                if on_progress:
                    on_progress(0, last_error)
                break

    last_error = last_error or 'Video generation unavailable. Install: pip install moviepy imageio-ffmpeg'
    if on_progress:
        on_progress(0, last_error)
    return (None, last_error)


def generate_ai_clips_background(job_id: str, config: Dict, job_store_get, job_store_set):
    """
    Build AI clips in a background thread and persist status/progress/clips.
    Creates short MP4 files and returns them via job['clips'].
    """
    def run():
        try:
            job = job_store_get(job_id) or {'id': job_id}
            job['status'] = 'processing'
            job['progress'] = 0
            job['message'] = 'Preparing AI clips...'
            job['updated_at'] = datetime.utcnow().isoformat()
            job_store_set(job_id, job)

            _services_ok, _svc_msg, _svc_detail = _check_generation_services()
            config["_service_check"] = _svc_detail
            if not (_svc_detail.get("disk") or {}).get("ok"):
                _set_job_failed(
                    job_id, "AI clips generation failed",
                    _svc_msg or "Insufficient disk space",
                    job_store_get, job_store_set,
                )
                return
            if not (_svc_detail.get("llm") or {}).get("ok"):
                _set_job_failed(
                    job_id, "AI clips generation failed",
                    _svc_msg or "No AI provider configured",
                    job_store_get, job_store_set,
                )
                return
            _prepare_generation_config(job_id, config)
            try:
                from backend.services.generator_encode_service import resolve_encode_profile
                config["encode_profile"] = resolve_encode_profile(config)
            except Exception:
                pass
            if "use_all_ais" not in config:
                try:
                    from backend.services.llm_service import configured_providers
                    provs = configured_providers()
                    gm = str(config.get("generation_method") or "").strip().lower()
                    config["use_all_ais"] = len(provs) >= 2 or gm == "adaptive_ai_v2"
                except Exception:
                    config["use_all_ais"] = False

            prompt = str(config.get('prompt') or config.get('title') or 'Untitled clip idea').strip()
            user_id = config.get('user_id', 'default_user')
            clip_count = max(1, min(10, int(config.get('clip_count', 3))))
            clip_duration = max(3, min(30, int(config.get('duration', 6))))
            quality_mode = str(config.get("quality_mode") or "").strip().lower()
            generation_method = str(config.get("generation_method") or "").strip().lower()
            strict_ai = quality_mode in ("best", "max", "ultra") and generation_method != "adaptive_ai_v2"
            ai_segments, ai_script_text, profile_context_text = _plan_ai_segments(
                user_id=user_id,
                prompt=prompt,
                title=config.get("title") or "AI Clip",
                duration_sec=clip_duration * clip_count,
                short=True,
                max_segments=max(clip_count, 3),
                extra_context=config,
                require_ai=strict_ai,
            )
            if config.get("enhanced_script"):
                ai_script_text = str(config.get("enhanced_script"))[:4000]
            script_lines = [ln.strip(" -*\t") for ln in ai_script_text.splitlines() if ln.strip()]
            if not ai_segments and strict_ai:
                # Recovery path for production stability when strict planner misses.
                ai_segments, ai_script_text, profile_context_text = _plan_ai_segments(
                    user_id=user_id,
                    prompt=prompt,
                    title=config.get("title") or "AI Clip",
                    duration_sec=clip_duration * clip_count,
                    short=True,
                    max_segments=max(clip_count, 3),
                    extra_context=config,
                    require_ai=False,
                )
                script_lines = [ln.strip(" -*\t") for ln in ai_script_text.splitlines() if ln.strip()]

            if not ai_segments and not script_lines:
                _set_job_failed(
                    job_id,
                    "AI clips generation failed",
                    "AI planner unavailable or returned invalid scene plan",
                    job_store_get,
                    job_store_set,
                )
                return
            profile_excerpt = profile_context_text or f"Profile context for user {user_id}."
            profile_sources = ["display_name", "bio", "level", "generation_points"]
            audio_profile = _resolve_audio_profile(config, fallback_style="epic")
            res = config.get('resolution', '1280x768')
            try:
                parts = str(res).split('x')
                w = int(parts[0]) if len(parts) > 0 else 1280
                h = int(parts[1]) if len(parts) > 1 else 768
            except (ValueError, TypeError):
                w, h = 1280, 768

            clips = []
            clip_pipeline_entries: List[Dict[str, Any]] = []
            for idx in range(clip_count):
                clip_doc_id = f'{job_id}_clip_{idx + 1}'
                clip_title = f'Clip {idx + 1}'
                if ai_segments:
                    seg = ai_segments[idx % len(ai_segments)]
                    base_scene_text = str(seg.get("description") or "").strip()
                    clip_title = str(seg.get("title") or clip_title)[:80]
                    seg_duration = max(3, min(20, int(seg.get("duration", clip_duration))))
                else:
                    base_scene_text = script_lines[idx % len(script_lines)] if script_lines else f'{prompt} - scene {idx + 1}'
                    seg_duration = clip_duration
                scene_text = f"{base_scene_text}. {profile_excerpt}".strip()[:260]
                progress = int(5 + (75 * idx / max(1, clip_count)))
                job = job_store_get(job_id) or {'id': job_id}
                job['progress'] = progress
                job['message'] = f'Generating clip {idx + 1}/{clip_count}...'
                job['updated_at'] = datetime.utcnow().isoformat()
                job_store_set(job_id, job)

                segments = [
                    {
                        'title': clip_title,
                        'description': scene_text,
                        'duration': max(2, seg_duration - 2),
                    },
                    {
                        'title': 'Prompt',
                        'description': prompt[:160],
                        'duration': 2,
                    },
                ]
                clip_pipeline_entries.append({
                    "clip_id": clip_doc_id,
                    "timeline_index": idx + 1,
                    "segments": segments,
                })
                clip_vp = _visual_profile_from_seed(_generation_visual_seed(clip_doc_id))
                clip_mode = str(config.get("clip_video_mode") or "auto").strip().lower()
                if clip_mode in ("avatar", "heygen"):
                    video_ai_pref = "heygen"
                elif clip_mode in ("runway", "replicate", "auto", ""):
                    video_ai_pref = clip_mode or "auto"
                else:
                    video_ai_pref = "auto"
                path, err = generate_rich_video_sync(
                    clip_doc_id,
                    segments,
                    width=w,
                    height=h,
                    add_audio=True,
                    audio_profile=audio_profile,
                    on_progress=None,
                    visual_profile=clip_vp,
                    video_ai_preference=video_ai_pref,
                    encode_profile=str(config.get("encode_profile") or "fast_ai"),
                )
                if not path:
                    path, err = _generate_video_sync(
                        clip_doc_id,
                        scene_text,
                        clip_title,
                        clip_duration,
                        w,
                        h,
                        None,
                    )
                if path:
                    relative_clip_url = f'/api/documentary/video/{clip_doc_id}'
                    full_clip_url = f'/api/documentary/video/{clip_doc_id}'
                    try:
                        from backend.services.generator_thumbnail_service import build_video_thumbnails
                        build_video_thumbnails(clip_doc_id, path)
                    except Exception:
                        pass
                    clips.append({
                        'clip_id': clip_doc_id,
                        'title': clip_title,
                        'content': scene_text,
                        'profile_excerpt': profile_excerpt[:180],
                        'profile_powered': True,
                        'profile_source_fields': profile_sources,
                        'prompt': prompt,
                        'script_excerpt': scene_text[:200],
                        'status': 'completed',
                        'duration': clip_duration,
                        'url': relative_clip_url,
                        'access_urls': {
                            'short': relative_clip_url,
                            'vidgenerator_short': full_clip_url,
                        },
                    })
                else:
                    clips.append({
                        'clip_id': clip_doc_id,
                        'title': clip_title,
                        'status': 'failed',
                        'error': err or 'Clip generation failed',
                    })

            completed = [c for c in clips if c.get('status') == 'completed']
            if not completed:
                _set_job_failed(
                    job_id,
                    'AI clips generation failed',
                    'No clips could be generated',
                    job_store_get,
                    job_store_set,
                )
                return

            job = job_store_get(job_id) or {'id': job_id}
            job['status'] = 'completed'
            job['progress'] = 100
            job['message'] = 'AI clips ready'
            job['clips'] = clips
            job['generated_script'] = ai_script_text[:4000]
            job['profile_context'] = profile_excerpt[:1000]
            pipeline_file = _write_generation_pipeline_file(
                job_id,
                {
                    "type": "clips_pipeline",
                    "bundle_id": job_id,
                    "user_id": user_id,
                    "prompt": prompt[:500],
                    "rearranged_clips": clip_pipeline_entries,
                    "created_at": datetime.utcnow().isoformat(),
                },
            )
            if pipeline_file:
                job['pipeline_file'] = pipeline_file
            job['user_id'] = job.get('user_id') or user_id
            job['updated_at'] = datetime.utcnow().isoformat()
            job_store_set(job_id, job)

            try:
                from backend.services.discord_m8_streams import post_generator_showcase
                post_generator_showcase(
                    job_id=job_id,
                    title=(prompt or "New AI clips")[:120],
                    user_id=user_id,
                )
            except Exception:
                pass

            try:
                from backend.routes.gallery_routes import invalidate_gallery_cache
                invalidate_gallery_cache()
            except Exception:
                pass

            # Award points to user profile (same pipeline as documentary: generation_points, XP, activity, etc.)
            num_completed = len(completed)
            clip_points = float(GENERATION_POINTS_PER_CLIP) * num_completed
            segment_bonus = sum(len((c.get("segments") or [])) for c in clip_pipeline_entries) * float(POINTS_PER_SEGMENT)
            total_points = clip_points + segment_bonus
            clip_config = dict(config or {})
            clip_config['type'] = 'ai_clips'
            clip_config['user_id'] = user_id
            total_earned = _award_generation_points(user_id, job_id, total_points, config=clip_config)
            job = job_store_get(job_id) or {}
            job['points_earned'] = total_earned
            job_store_set(job_id, job)
            try:
                from backend.services.cogs_metering_service import record_completed_video_job
                record_completed_video_job(
                    job_kind="ai_clips",
                    job_id=job_id,
                    user_id=user_id,
                    config=clip_config,
                    output_path=None,
                    video_metrics={"ai_clips_completed": num_completed},
                    duration_config_sec=max(30, int(config.get("duration", 30) or 30)),
                    num_segments=num_completed,
                )
            except Exception:
                pass
        except Exception as e:
            _set_job_failed(job_id, 'AI clips generation failed', str(e), job_store_get, job_store_set)

    t = threading.Thread(target=run, daemon=True)
    t.start()


def _make_animated_segment_clip(
    w: int, h: int, duration_sec: int, seg_index: int,
    title: str, body: str, tagline: str, mood: str,
    bg_color: Optional[tuple] = None,
    image_path: Optional[str] = None,
    visual_profile: Optional[Dict[str, Any]] = None,
):
    """
    Build an animated segment clip (RGB-only, memory-efficient).
    Ken Burns camera + particles + animated text + pulsing elements.
    Uses numpy blending instead of RGBA compositing to stay under ~200MB.
    """
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from moviepy import VideoClip

    dur = max(1.0, float(duration_sec))
    vp = visual_profile or {}
    gseed = int(vp.get("seed") or 0)
    cam_effect = (seg_index + int(vp.get("cam_bias") or 0)) % 4
    seed = (seg_index * 137 + 53 + gseed) % 997

    bg_arr = None
    src_w, src_h = int(w * 1.3), int(h * 1.3)
    if image_path and os.path.isfile(image_path):
        try:
            bg_arr = np.array(
                Image.open(image_path).convert("RGB").resize((src_w, src_h), Image.LANCZOS)
            )
        except Exception:
            pass

    if bg_color and isinstance(bg_color, (list, tuple)) and len(bg_color) >= 3:
        bg_rgb = (int(bg_color[0]), int(bg_color[1]), int(bg_color[2]))
    else:
        bg_rgb = _SEGMENT_COLORS[seg_index % len(_SEGMENT_COLORS)]

    if bg_arr is None:
        bg_arr = np.full((src_h, src_w, 3), bg_rgb, dtype=np.uint8)

    bar_color = (0, 255, 136)
    if mood in _MOOD_COLOR_MAP:
        mc = _MOOD_COLOR_MAP[mood]
        bar_color = (min(255, mc[0] * 4 + 80), min(255, mc[1] * 4 + 80), min(255, mc[2] * 3 + 60))
    elif vp.get("accent"):
        ac = vp["accent"]
        if isinstance(ac, (list, tuple)) and len(ac) >= 3:
            bar_color = (int(ac[0]), int(ac[1]), int(ac[2]))

    # Pre-bake a darkening gradient mask (numpy, computed once)
    dark_mask = np.ones((h, w), dtype=np.float32)
    gw = int(w * 0.55)
    for gx in range(gw):
        dark_mask[:, gx] = min(1.0, 0.45 + 0.55 * (gx / gw))
    bh = int(h * 0.25)
    for gy in range(bh):
        yy = h - bh + gy
        dark_mask[yy, :] *= min(1.0, 0.5 + 0.5 * (1.0 - gy / bh))

    n_particles = int(vp.get("particle_density") or (12 + (seed % 6)))
    p_x = [(seed * (i + 1) * 73) % w for i in range(n_particles)]
    p_y0 = [h + (seed * (i + 1) * 41) % h for i in range(n_particles)]
    p_spd = [28 + (seed * (i + 1) * 29) % 40 for i in range(n_particles)]
    p_sz = [2 + (seed * (i + 1) * 17) % 2 for i in range(n_particles)]
    p_br = [0.4 + ((seed * (i + 1) * 13) % 60) / 100.0 for i in range(n_particles)]
    p_dr = [((seed * (i + 1) * 11) % 30) - 15 for i in range(n_particles)]

    title_lines = textwrap.wrap((title or "").strip()[:80], width=40) if title else []
    body_lines = textwrap.wrap((body or "").strip()[:400], width=65) if body else []
    tagline_text = (tagline or "").strip().upper()[:60]

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    margin_x = int(w * 0.08)

    def make_frame(t):
        progress = min(1.0, t / dur)

        if cam_effect == 0:
            z = 1.0 + 0.25 * progress
        elif cam_effect == 1:
            z = 1.25 - 0.25 * progress
        else:
            z = 1.1

        crop_w = max(4, min(int(w / z), src_w))
        crop_h = max(4, min(int(h / z), src_h))
        cx, cy = src_w // 2, src_h // 2
        if cam_effect == 2:
            cx = int(src_w * (0.35 + 0.3 * progress))
        elif cam_effect == 3:
            cx = int(src_w * (0.65 - 0.3 * progress))

        x1 = max(0, min(cx - crop_w // 2, src_w - crop_w))
        y1 = max(0, min(cy - crop_h // 2, src_h - crop_h))
        cropped = bg_arr[y1:y1 + crop_h, x1:x1 + crop_w]
        frame_np = np.array(Image.fromarray(cropped).resize((w, h), Image.BILINEAR))

        # Apply pre-baked dark gradient via numpy (no RGBA)
        frame_np = (frame_np * dark_mask[:, :, np.newaxis]).astype(np.uint8)

        # Convert to PIL RGB for drawing
        frame_img = Image.fromarray(frame_np, "RGB")
        draw = ImageDraw.Draw(frame_img)

        pulse = 0.7 + 0.3 * math.sin(2 * math.pi * 1.5 * t)
        pulsed = tuple(min(255, int(c * pulse)) for c in bar_color)

        # Pulsing top bar
        bw = int(w * (0.3 + 0.7 * min(1.0, t / 0.8)))
        draw.rectangle([(0, 0), (bw, 3)], fill=pulsed)

        y = int(h * 0.12)

        # Tagline slides in
        if tagline_text:
            off = max(0, int(margin_x * (1.0 - min(1.0, t / 0.6))))
            draw.text((margin_x - off, y), tagline_text, font=font, fill=pulsed)
            y += 20

        # Title typewriter
        if title_lines:
            vis = min(sum(len(l) for l in title_lines), int(t * 28))
            cc = 0
            for tl in title_lines:
                shown = tl[:max(0, vis - cc)]
                cc += len(tl)
                if shown:
                    draw.text((margin_x, y), shown, font=font, fill=(0, 255, 136))
                y += 26
            y += 8

        # Separator extends
        sp = min(1.0, max(0, (t - 0.3)) / 0.5)
        se = int(margin_x + (w - 2 * margin_x) * sp)
        draw.line([(margin_x, y), (se, y)], fill=(60, 100, 160), width=1)
        y += 14

        # Body lines fade in
        if body_lines:
            for li, bl in enumerate(body_lines):
                lt = t - 0.8 - li * 0.3
                if lt < 0:
                    break
                a = min(255, int(255 * min(1.0, lt / 0.4)))
                draw.text((margin_x, y), bl, font=font, fill=(a, min(255, a + 10), 255))
                y += 18
                if y > int(h * 0.78):
                    break

        # Particles
        for pi in range(n_particles):
            py = int((p_y0[pi] - p_spd[pi] * t) % (h + 30) - 15)
            px = int(p_x[pi] + p_dr[pi] * math.sin(t * 0.8 + pi)) % w
            tw = 0.5 + 0.5 * math.sin(t * 3 + pi * 1.7)
            br = int(255 * p_br[pi] * tw)
            sz = p_sz[pi]
            draw.ellipse([(px - sz, py - sz), (px + sz, py + sz)],
                         fill=(min(255, bar_color[0] + br // 3),
                               min(255, bar_color[1] + br // 4),
                               min(255, bar_color[2] + br // 4)))

        # Mood badge
        if mood:
            bt = mood.upper()
            bx = w - margin_x - len(bt) * 7
            by = h - 34
            draw.rectangle([(bx - 6, by - 2), (bx + len(bt) * 7 + 6, by + 16)], fill=pulsed)
            draw.text((bx, by), bt, font=font, fill=(10, 10, 10))

        # Progress bar at bottom
        draw.rectangle([(0, h - 3), (int(w * progress), h)], fill=bar_color)

        return np.array(frame_img)

    return VideoClip(make_frame, duration=dur).with_fps(16)


def _make_intro_clip(
    w: int, h: int, title: str, subtitle: str = "", duration: float = 4.0,
    visual_profile: Optional[Dict[str, Any]] = None,
):
    """Cinematic intro — RGB only, low memory."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from moviepy import VideoClip

    dur = max(2.0, float(duration))
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    vp = visual_profile or {}
    brand = str(vp.get("brand_line") or "MASTERNODER.DK")[:40]
    title_text = (title or "AI Documentary").strip()[:60]
    sub_text = (subtitle or "").strip()[:80]
    accent = vp.get("accent")
    if isinstance(accent, (list, tuple)) and len(accent) >= 3:
        accent = (int(accent[0]), int(accent[1]), int(accent[2]))
    else:
        accent = (0, 255, 136)

    n_stars = 18 + int(vp.get("intro_variant", 0) or 0) % 15
    sx = [(hash((i, 7)) % w) for i in range(n_stars)]
    sy = [(hash((i, 13)) % h) for i in range(n_stars)]
    s_ph = [((hash((i, 31)) % 100) / 100.0) * 6.28 for i in range(n_stars)]

    def make_frame(t):
        img = Image.new("RGB", (w, h), (8, 12, 24))
        draw = ImageDraw.Draw(img)
        cx = w // 2

        for si in range(n_stars):
            tw = 0.3 + 0.7 * max(0, math.sin(t * 2.5 + s_ph[si]))
            br = int(160 * tw * min(1.0, t / 0.8))
            draw.ellipse([(sx[si] - 1, sy[si] - 1), (sx[si] + 1, sy[si] + 1)],
                         fill=(br, min(255, br + 20), 255))

        bx = cx - len(brand) * 4
        by = int(h * 0.28)
        fa = min(1.0, t / 1.2)
        draw.text((bx, by), brand, font=font,
                   fill=tuple(int(c * fa) for c in accent))

        lp = min(1.0, max(0, (t - 0.4)) / 0.8)
        lhalf = int((w * 0.35) * lp)
        ly = by + 22
        if lhalf > 2:
            draw.line([(cx - lhalf, ly), (cx + lhalf, ly)], fill=accent, width=2)

        vis = max(0, int((t - 0.8) * 25))
        shown = title_text[:vis]
        if shown:
            draw.text((cx - len(title_text) * 4, int(h * 0.46)), shown,
                       font=font, fill=(255, 255, 255))

        if sub_text:
            sa = min(1.0, max(0, (t - 2.0)) / 0.8)
            sc = int(180 * sa)
            draw.text((cx - len(sub_text) * 3, int(h * 0.56)), sub_text,
                       font=font, fill=(sc, min(255, sc + 20), min(255, sc + 50)))

        for pi in range(10):
            py = h - int((t * 25 + pi * 60) % (h + 40))
            px = int(w * (0.05 + 0.9 * (pi / 10.0))) + int(6 * math.sin(t + pi))
            br = int(80 * (0.4 + 0.6 * math.sin(t * 2 + pi * 0.8)))
            draw.ellipse([(px - 2, py - 2), (px + 2, py + 2)],
                         fill=(br, min(255, accent[1] - 40 + br), br))

        bw = int(w * min(1.0, t / 2.5))
        draw.rectangle([(0, h - 3), (bw, h)], fill=accent)

        return np.array(img)

    return VideoClip(make_frame, duration=dur).with_fps(16)


def _make_outro_clip(
    w: int, h: int, title: str = "", duration: float = 4.0,
    visual_profile: Optional[Dict[str, Any]] = None,
):
    """Cinematic outro — RGB only, low memory."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from moviepy import VideoClip

    dur = max(2.0, float(duration))
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    vp = visual_profile or {}
    accent = vp.get("accent")
    if isinstance(accent, (list, tuple)) and len(accent) >= 3:
        accent = (int(accent[0]), int(accent[1]), int(accent[2]))
    else:
        accent = (0, 255, 136)
    thanks = "THANK YOU FOR WATCHING"
    brand = str(vp.get("brand_line") or "MASTERNODER.DK")[:40]
    title_text = (title or "").strip()[:50]

    n_parts = 20
    p_ang = [(hash((i, 3)) % 628) / 100.0 for i in range(n_parts)]
    p_spd = [40 + (hash((i, 7)) % 50) for i in range(n_parts)]

    def make_frame(t):
        fade_out = max(0.0, 1.0 - max(0, (t - (dur - 1.5))) / 1.5)
        img = Image.new("RGB", (w, h), (8, 12, 24))
        draw = ImageDraw.Draw(img)
        cx, cy = w // 2, h // 2

        for pi in range(n_parts):
            d = p_spd[pi] * t * 0.6
            px = cx + int(d * math.cos(p_ang[pi]))
            py = cy + int(d * math.sin(p_ang[pi]))
            if 0 <= px < w and 0 <= py < h:
                br = int(120 * fade_out * (0.5 + 0.5 * math.sin(t * 2 + pi)))
                draw.ellipse([(px - 2, py - 2), (px + 2, py + 2)],
                             fill=(br, min(255, accent[1] - 80 + br), br))

        fa = min(1.0, t / 1.0) * fade_out
        tc = tuple(int(c * fa) for c in accent)
        draw.text((cx - len(thanks) * 4, int(h * 0.32)), thanks, font=font, fill=tc)

        if title_text:
            ta = min(1.0, max(0, (t - 0.5)) / 0.8) * fade_out
            draw.text((cx - len(title_text) * 4, int(h * 0.44)), title_text,
                       font=font, fill=tuple(int(220 * ta) for _ in range(3)))

        lp = min(1.0, max(0, (t - 0.6)) / 0.6) * fade_out
        lhalf = int((w * 0.3) * lp)
        if lhalf > 2:
            draw.line([(cx - lhalf, int(h * 0.54)), (cx + lhalf, int(h * 0.54))],
                       fill=accent, width=2)

        ba = min(1.0, max(0, (t - 1.2)) / 0.8) * fade_out
        draw.text((cx - len(brand) * 4, int(h * 0.62)), brand,
                   font=font, fill=tuple(int(c * ba) for c in accent))

        ya = min(1.0, max(0, (t - 1.8)) / 0.6) * fade_out
        yr = "2026"
        draw.text((cx - len(yr) * 3, int(h * 0.72)), yr,
                   font=font, fill=tuple(int(160 * ya) for _ in range(3)))

        bc = tuple(int(c * fade_out) for c in accent)
        draw.rectangle([(0, 0), (w, 3)], fill=bc)
        draw.rectangle([(0, h - 3), (w, h)], fill=bc)

        return np.array(img)

    return VideoClip(make_frame, duration=dur).with_fps(16)


def _safe_fadein(duration: float):
    """Return a fadein effect, handling different MoviePy versions."""
    try:
        from moviepy.video.fx import FadeIn
        return FadeIn(duration)
    except (ImportError, AttributeError):
        pass
    try:
        from moviepy import vfx
        return vfx.FadeIn(duration)
    except (ImportError, AttributeError):
        pass
    return None


def _safe_fadeout(duration: float):
    """Return a fadeout effect, handling different MoviePy versions."""
    try:
        from moviepy.video.fx import FadeOut
        return FadeOut(duration)
    except (ImportError, AttributeError):
        pass
    try:
        from moviepy import vfx
        return vfx.FadeOut(duration)
    except (ImportError, AttributeError):
        pass
    return None


def generate_rich_video_sync(
    doc_id: str,
    segments: List[Dict[str, Any]],
    width: int = 1280,
    height: int = 768,
    add_audio: bool = True,
    audio_profile: Optional[Dict[str, Any]] = None,
    on_progress: Optional[Callable[[int, str], None]] = None,
    visual_profile: Optional[Dict[str, Any]] = None,
    metrics_out: Optional[Dict[str, Any]] = None,
    video_ai_preference: Optional[str] = None,
    encode_profile: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Generate a longer video from segments (pictures/slides + optional text).
    Each segment: title (str), description (str), duration (int sec), optional image_path (str).
    Concatenates clips and can add generated dynamic audio. Returns (path, None) or (None, error).
    visual_profile: per-run seed (accent, motion) so intro/outro/animation differ each video.
    """
    out_path = os.path.join(VIDEOS_DIR, f'{doc_id}.mp4')
    w, h = min(width, 854), min(height, 480)
    vp = visual_profile or _visual_profile_from_seed(_generation_visual_seed(doc_id))
    try:
        from moviepy import ColorClip, concatenate_videoclips
    except ImportError:
        try:
            from moviepy.editor import ColorClip, concatenate_videoclips
        except ImportError:
            return (None, "moviepy not available")

    pref = str(video_ai_preference or "auto").strip().lower()
    if pref == "avatar":
        pref = "heygen"
    use_auto = not pref or pref == "auto"

    # Pre-generate AI video clips if ModelsLab is available
    if use_auto:
        try:
            from backend.services.modelslab_video_service import is_available as modelslab_ok, generate_segment_clips
            if modelslab_ok():
                if on_progress:
                    on_progress(3, "Generating AI video clips (ModelsLab)...")
                segments = generate_segment_clips(segments, max_clips=min(3, len(segments)), timeout_per_clip=120)
        except Exception:
            pass

    # Upgrade key segments with RunwayML Gen-4 Turbo (premium cinematic quality)
    if use_auto or pref == "runway":
        try:
            from backend.services.runwayml_service import is_available as runway_ok, generate_segment_clips as runway_clips
            if runway_ok():
                if on_progress:
                    on_progress(5, "Generating premium RunwayML Gen-4 clip...")
                segments = runway_clips(segments, max_clips=1, duration=5, timeout_per_clip=90)
        except Exception:
            pass

    # Pika 2.2 — secondary premium video provider for additional segments
    if use_auto:
        try:
            from backend.services.pika_service import is_available as pika_ok, generate_segment_clips as pika_clips
            if pika_ok():
                if on_progress:
                    on_progress(6, "Generating Pika 2.2 clip...")
                segments = pika_clips(segments, max_clips=1, duration=5, timeout_per_clip=90)
        except Exception:
            pass

    # HeyGen — 30s talking-avatar clips (script → avatar video)
    if use_auto or pref == "heygen":
        try:
            from backend.services.heygen_service import is_available as heygen_ok, generate_segment_clips as heygen_clips
            if heygen_ok():
                if on_progress:
                    on_progress(6, "Generating HeyGen avatar clip...")
                segments = heygen_clips(segments, max_clips=1, timeout_per_clip=300)
        except Exception:
            pass

    # Replicate — Stable Video Diffusion (image-to-video)
    if use_auto or pref == "replicate":
        try:
            from backend.services.replicate_video_service import is_available as replicate_ok, generate_segment_clips as replicate_clips
            if replicate_ok():
                if on_progress:
                    on_progress(6, "Generating Replicate SVD clip...")
                segments = replicate_clips(segments, max_clips=1, timeout_per_clip=300)
        except Exception:
            pass

    # Pre-generate AI images — Stability AI (paid) then Pollinations.ai (free, no key)
    try:
        segments_needing_images = [s for s in segments if not s.get("ai_video_path") and not s.get("image_path")]
        if segments_needing_images:
            if on_progress:
                on_progress(7, "Generating AI images...")
            stability_used = False
            try:
                from backend.services.stability_image_service import is_available as stability_ok, generate_segment_images as stability_gen
                if stability_ok():
                    stability_gen(segments, max_images=len(segments), style_preset="cinematic")
                    stability_used = any(s.get("image_path") for s in segments)
            except Exception:
                pass
            if not stability_used:
                try:
                    from backend.services.free_image_service import generate_segment_images as free_gen
                    free_gen(segments, max_images=len(segments))
                except Exception:
                    pass
    except Exception:
        pass

    clips_to_concat = []
    total = len(segments)
    for i, seg in enumerate(segments):
        if on_progress:
            title_snippet = (seg.get("title") or "")[:30]
            on_progress(
                int(10 + 70 * i / max(1, total)),
                f"Building segment {i + 1}/{total}: {title_snippet}" if title_snippet else f"Building segment {i + 1}/{total}",
            )
        duration_sec = max(2, min(15, int(seg.get("duration", 4))))
        seg_bg = seg.get("bg_color") or _SEGMENT_COLORS[i % len(_SEGMENT_COLORS)]
        seg_tagline = (seg.get("opening_hook") or seg.get("tagline", "")).strip() if i == 0 else (seg.get("tagline", "") or "").strip()
        seg_mood = seg.get("mood", "")

        # Priority 1: AI-generated video clip from ModelsLab/RunwayML
        ai_video = seg.get("ai_video_path")
        if ai_video and os.path.isfile(ai_video):
            try:
                from moviepy import VideoFileClip
                vclip = VideoFileClip(ai_video)
                if vclip.duration < duration_sec:
                    vclip = vclip.loop(duration=duration_sec)
                else:
                    vclip = vclip.subclipped(0, duration_sec)
                vclip = vclip.resized((w, h))
                clips_to_concat.append(vclip)
                continue
            except Exception:
                pass

        # Priority 2: Animated segment (Ken Burns + particles + animated text)
        image_path = seg.get("image_path")
        if image_path:
            image_path = os.path.abspath(image_path)
        seg_body = (seg.get("description") or "")[:260]
        if seg.get("key_fact"):
            seg_body = f"{seg_body}\n\n{seg.get('key_fact', '')[:80]}".strip()[:400]
        try:
            clip = _make_animated_segment_clip(
                w=w, h=h, duration_sec=duration_sec, seg_index=i,
                title=(seg.get("title") or "")[:70],
                body=seg_body,
                tagline=seg_tagline, mood=seg_mood,
                bg_color=seg_bg,
                image_path=image_path if (image_path and os.path.isfile(image_path)) else None,
                visual_profile=vp,
            )
            clips_to_concat.append(clip)
            continue
        except Exception:
            pass

        # Priority 3: Static fallback
        color = tuple(seg_bg) if isinstance(seg_bg, (list, tuple)) else _SEGMENT_COLORS[i % len(_SEGMENT_COLORS)]
        clip = ColorClip(size=(w, h), color=color, duration=duration_sec)
        clip, _ = _apply_text_overlay(
            clip,
            title=(seg.get("title") or "")[:70],
            body=seg_body,
            width=w, height=h, duration_sec=duration_sec,
            bg_color=seg_bg, tagline=seg_tagline, mood=seg_mood,
        )
        clips_to_concat.append(clip)

    if not clips_to_concat:
        return (None, "No segments to render")

    # Cinematic intro and outro
    video_title = ""
    video_subtitle = ""
    if segments:
        video_title = (segments[0].get("title") or "AI Documentary")[:60]
        all_titles = [s.get("title", "") for s in segments if s.get("title")]
        video_subtitle = f"{len(segments)} segments" if len(all_titles) > 1 else ""
    try:
        intro_clip = _make_intro_clip(
            w, h, title=video_title, subtitle=video_subtitle, duration=4.0,
            visual_profile=vp,
        )
        clips_to_concat.insert(0, intro_clip)
    except Exception:
        pass
    try:
        outro_clip = _make_outro_clip(w, h, title=video_title, duration=4.0, visual_profile=vp)
        clips_to_concat.append(outro_clip)
    except Exception:
        pass

    # Apply crossfade transitions between segments
    if len(clips_to_concat) > 1:
        try:
            fade_dur = 0.5
            faded = []
            for ci, c in enumerate(clips_to_concat):
                try:
                    fi = _safe_fadein(fade_dur) if ci > 0 else None
                    fo = _safe_fadeout(fade_dur) if ci < len(clips_to_concat) - 1 else None
                    effects = [e for e in (fi, fo) if e is not None]
                    if effects:
                        c = c.with_effects(effects)
                except Exception:
                    pass
                faded.append(c)
            clips_to_concat = faded
        except Exception:
            pass

    if on_progress:
        on_progress(80, "Concatenating clips...")
    try:
        final = concatenate_videoclips(clips_to_concat, method="chain")
    except Exception:
        final = concatenate_videoclips(clips_to_concat)

    if add_audio:
        if on_progress:
            on_progress(85, "Muxing audio...")
        profile = audio_profile or _resolve_audio_profile({}, fallback_style="cinematic")
        dynamic_audio = _build_dynamic_audio_clip(
            total_duration=float(getattr(final, "duration", 0) or 0),
            segments=segments,
            audio_profile=profile,
        )
        if dynamic_audio is not None:
            try:
                final = final.with_audio(dynamic_audio)
            except Exception:
                dynamic_audio = None
        if dynamic_audio is None:
            add_audio = False

    # TTS narration — timed voice-over per segment (E5)
    profile = audio_profile or {}
    if profile.get("narration_enabled", False):
        try:
            from backend.services.tts_service import generate_timed_narration_for_segments, is_available as tts_ok
            if tts_ok():
                if on_progress:
                    on_progress(88, "Generating TTS narration...")
                voice_key = profile.get("narration_voice") or "rachel"
                narration_path = generate_timed_narration_for_segments(
                    segments,
                    total_duration=float(getattr(final, "duration", 0) or 0),
                    voice_key=voice_key,
                )
                if narration_path and os.path.isfile(narration_path):
                # Optional: DeepFilterNet noise reduction + FFmpeg loudnorm (env AUDIO_ENHANCE=1)
                path_to_use = narration_path
                enhanced_path = None
                try:
                    from backend.services.audio_enhancement_service import enhance_audio
                    enhanced_path = enhance_audio(narration_path)
                    if enhanced_path and enhanced_path != narration_path and os.path.isfile(enhanced_path):
                        path_to_use = enhanced_path
                except Exception:
                    pass
                try:
                    from moviepy import AudioFileClip, CompositeAudioClip
                    narration = AudioFileClip(path_to_use)
                    vid_dur = float(getattr(final, "duration", 0) or 0)
                    if vid_dur > 0:
                        if narration.duration > vid_dur:
                            narration = narration.subclipped(0, vid_dur)
                        cur_audio = getattr(final, "audio", None)
                        if cur_audio is not None:
                            try:
                                mixed = CompositeAudioClip([
                                    cur_audio.with_volume_scaled(0.4),
                                    narration.with_volume_scaled(0.9),
                                ])
                                final = final.with_audio(mixed)
                            except Exception:
                                final = final.with_audio(narration)
                        else:
                            final = final.with_audio(narration)
                        add_audio = True
                finally:
                    try:
                        if path_to_use and os.path.isfile(path_to_use):
                            os.unlink(path_to_use)
                    except Exception:
                        pass
                    if narration_path != path_to_use and narration_path and os.path.isfile(narration_path):
                        try:
                            os.unlink(narration_path)
                        except Exception:
                            pass
        except Exception:
            pass

    ok, space_err = _check_disk_space()
    if not ok:
        for c in clips_to_concat:
            if hasattr(c, "close"):
                c.close()
        if hasattr(final, "close"):
            final.close()
        return (None, space_err)

    if on_progress:
        on_progress(90, "Encoding video (mux)...")

    _encode_t0 = None
    try:
        import time as _time
        _encode_t0 = _time.monotonic()
    except Exception:
        pass

    def _cleanup_partial(path: str):
        """Remove a partial/invalid output file left by a failed write."""
        try:
            if os.path.isfile(path) and os.path.getsize(path) < _MIN_VALID_MP4_BYTES:
                os.remove(path)
        except Exception:
            pass

    try:
        import gc
        from backend.services.generator_encode_service import build_write_kwargs, resolve_encode_profile, ENCODE_CRF, moviepy_write_kwargs
        gc.collect()
        prof = str(encode_profile or "fast_ai").strip().lower()
        if prof not in ENCODE_CRF:
            prof = resolve_encode_profile({"encode_profile": encode_profile})
        write_kwargs = build_write_kwargs(doc_id, prof, add_audio=add_audio, videos_dir=VIDEOS_DIR)
        if metrics_out is not None:
            metrics_out["encode_profile"] = prof
            metrics_out["encode_crf"] = ENCODE_CRF.get(prof, 28)
            if write_kwargs.get("hw_encode"):
                metrics_out["hw_encode"] = write_kwargs.get("hw_encode")
        final.write_videofile(out_path, **moviepy_write_kwargs(write_kwargs))
    except Exception as e1:
        _cleanup_partial(out_path)
        try:
            import gc
            from backend.services.generator_encode_service import build_write_kwargs, moviepy_write_kwargs
            gc.collect()
            fallback = build_write_kwargs(doc_id, "fast_ai", add_audio=False, videos_dir=VIDEOS_DIR)
            final.write_videofile(out_path, **moviepy_write_kwargs(fallback))
        except Exception as e2:
            _cleanup_partial(out_path)
            for c in clips_to_concat:
                if hasattr(c, "close"):
                    c.close()
            return (None, _normalize_write_error(e2))
    try:
        if not os.path.isfile(out_path) or os.path.getsize(out_path) < _MIN_VALID_MP4_BYTES:
            _cleanup_partial(out_path)
            for c in clips_to_concat:
                if hasattr(c, "close"):
                    c.close()
            if hasattr(final, "close"):
                final.close()
            return (None, "Encoded file too small — encoding may have been interrupted")
    except Exception:
        pass

    _out_duration_sec = 0.0
    try:
        _out_duration_sec = float(getattr(final, "duration", 0) or 0)
    except Exception:
        _out_duration_sec = 0.0

    _encode_wall = 0.0
    try:
        if _encode_t0 is not None:
            import time as _time
            _encode_wall = max(0.0, _time.monotonic() - _encode_t0)
    except Exception:
        _encode_wall = 0.0

    if metrics_out is not None:
        try:
            from backend.services.runwayml_service import DEFAULT_DURATION as _RW_DUR
        except Exception:
            _RW_DUR = 5
        rw_paths = [s for s in segments if s.get("runway_video_path")]
        metrics_out["runway_clips"] = len(rw_paths)
        metrics_out["runway_seconds_per_clip"] = int(_RW_DUR)
        metrics_out["runway_output_seconds_billed"] = float(len(rw_paths) * int(_RW_DUR))
        metrics_out["output_video_duration_sec"] = _out_duration_sec
        metrics_out["encode_wall_seconds"] = round(_encode_wall, 3)
        metrics_out["segment_count"] = len(segments)
        metrics_out["encode_used_gpu"] = bool(os.environ.get("COGS_ENCODE_ASSUME_GPU", "").strip() in ("1", "true", "True"))
        if out_path and os.path.isfile(out_path):
            try:
                metrics_out["output_file_bytes"] = int(os.path.getsize(out_path))
            except Exception:
                pass

    for c in clips_to_concat:
        if hasattr(c, "close"):
            c.close()
    if hasattr(final, "close"):
        final.close()
    if on_progress:
        on_progress(100, "Complete")
    return (out_path, None)


def _set_job_failed(doc_id: str, message: str, error_detail: Optional[str], job_store_get, job_store_set):
    """Set job to failed and persist message + error_message."""
    try:
        from backend.services.generator_mn2_service import refund_on_failure
        refund_on_failure(doc_id, reason=error_detail or message or "generation_failed")
    except Exception:
        pass
    _write_status_sidecar(
        doc_id=doc_id,
        status="failed",
        message=message,
        error_message=error_detail or message,
        progress=0,
    )
    try:
        job = job_store_get(doc_id)
        if job:
            job['status'] = 'failed'
            job['progress'] = 0
            job['message'] = message
            job['error_message'] = error_detail or message
            job['updated_at'] = datetime.utcnow().isoformat()
            job_store_set(doc_id, job)
    except Exception:
        pass


def _job_config_path(doc_id: str) -> str:
    """Path to persisted job config for subprocess runner."""
    return os.path.join(VIDEOS_DIR, f"{doc_id}.job.json")


def write_job_config_for_subprocess(doc_id: str, config: Dict) -> bool:
    """Write job config to disk so a subprocess can run encoding without holding the web worker."""
    try:
        path = _job_config_path(doc_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def read_job_config_for_subprocess(doc_id: str) -> Optional[Dict]:
    """Load persisted job config written for subprocess encoding."""
    try:
        path = _job_config_path(doc_id)
        if not os.path.isfile(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def run_video_generation_standalone(doc_id: str, config: Dict) -> None:
    """
    Run the full video generation pipeline in the current process (e.g. subprocess).
    Uses only sidecar for progress so web workers stay free. Call this from a separate
    process so uWSGI workers are not blocked by encoding.
    """
    def _noop_get(_jid):
        return {}
    def _noop_set(_jid, _data):
        pass
    try:
        _run_video_generation_impl(doc_id, config, _noop_get, _noop_set)
    finally:
        clear_run_sidecar(doc_id)


# Points awarded per completed video (generation_points in unified DB + job.points_earned)
GENERATION_POINTS_PER_VIDEO = 55
# Points for short "quick clip" (fewer segments, faster run)
GENERATION_POINTS_PER_CLIP = 28
# Points per segment (each "mark" or "stone" in the video) — awarded on top of base
POINTS_PER_SEGMENT = 10
# Bonus for longer/full documentaries (duration >= 90 seconds)
DURATION_BONUS_THRESHOLD_SEC = 90
DURATION_BONUS_POINTS = 10


def _load_content_categories() -> Dict:
    """Load content categories (conspiracy, religious_conspiracy, alternative_theories) for bonus points."""
    try:
        import json
        path = os.path.join(_BASE, 'data', 'content_categories.json')
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {'categories': [], 'unified_point_system': {}}


def _check_and_award_trophies(user_id: str, doc_id: str, config: Optional[Dict] = None):
    """Check for trophy eligibility after video generation and award trophies."""
    try:
        from backend.services.unified_points_database import unified_points_db
        if not unified_points_db:
            return
        
        # Get user stats
        points_data = unified_points_db.get_all_points(user_id)
        systems = points_data.get('systems', {})
        generation_points = systems.get('generation_points', 0)
        
        # Get generation count from metadata or calculate
        try:
            from backend.routes.missing_endpoints_routes import get_generator_statistics
            stats = get_generator_statistics()
            if stats and stats.get('success'):
                total_videos = stats.get('statistics', {}).get('total_videos', 0)
                completed_videos = stats.get('statistics', {}).get('completed_videos', 0)
            else:
                total_videos = int(generation_points / GENERATION_POINTS_PER_VIDEO)
                completed_videos = total_videos
        except Exception:
            total_videos = int(generation_points / GENERATION_POINTS_PER_VIDEO)
            completed_videos = total_videos
        
        # Trophy definitions - check and award
        cfg = config or {}
        providers_used = list(cfg.get("_providers_used") or [])
        multi_ai_this_run = len(providers_used) >= 2
        trophies_to_check = [
            {'id': 'first_video', 'name': 'First Video', 'condition': completed_videos >= 1, 'icon': '🎬', 'category': 'generation'},
            {'id': 'video_creator', 'name': 'Video Creator', 'condition': completed_videos >= 10, 'icon': '🎥', 'category': 'generation'},
            {'id': 'video_master', 'name': 'Video Master', 'condition': completed_videos >= 50, 'icon': '🏆', 'category': 'generation'},
            {'id': 'video_legend', 'name': 'Video Legend', 'condition': completed_videos >= 100, 'icon': '👑', 'category': 'generation'},
            {'id': 'multi_ai_power', 'name': 'Multi-AI Power', 'condition': multi_ai_this_run, 'icon': '🤖', 'category': 'generation'},
            {'id': 'generation_points_1k', 'name': 'Generation Points Collector', 'condition': generation_points >= 1000, 'icon': '⭐', 'category': 'points'},
            {'id': 'generation_points_10k', 'name': 'Generation Points Master', 'condition': generation_points >= 10000, 'icon': '💎', 'category': 'points'},
            {'id': 'generation_points_100k', 'name': 'Generation Points Legend', 'condition': generation_points >= 100000, 'icon': '🌟', 'category': 'points'},
        ]
        
        # Award trophies via API
        for trophy in trophies_to_check:
            if trophy['condition']:
                try:
                    import requests
                    requests.post(
                        f'http://127.0.0.1:5000/api/trophies/award',
                        json={'user_id': user_id, 'trophy_id': trophy['id']},
                        timeout=2
                    )
                except Exception:
                    # Fallback: direct DB call
                    try:
                        from backend.services.trophies_db_service import award_trophy
                        award_trophy(user_id, trophy['id'])
                    except Exception:
                        pass
    except Exception:
        pass


def _award_generation_points(
    user_id: str,
    doc_id: str,
    points: float = GENERATION_POINTS_PER_VIDEO,
    config: Optional[Dict] = None,
) -> float:
    """
    Award points across ALL systems after a successful video generation.
    Hits: unified_points_db, unified_points_db_enhanced, unified_points_trigger_integration,
          profile (user_onboarding), communication_psychology, trophies, agent_ai_intelligence.
    Returns total generation points awarded.
    """
    cfg = config or {}
    category_id = cfg.get('content_category') or 'general'
    bonus = 0.0
    category_point_type = None
    data = _load_content_categories()
    for cat in data.get('categories', []):
        if (cat.get('id') or '').lower() == category_id:
            bonus = float(cat.get('bonus_unified_points', 0) or 0)
            category_point_type = cat.get('unified_point_type')
            break
    total_generation = points + bonus
    if cfg.get('style_preset') or cfg.get('theme_tone') or cfg.get('creative_twist'):
        total_generation += 5.0  # AI creativity bonus for using presets/twist
    providers_used = list(cfg.get("_providers_used") or [])
    if len(providers_used) >= 2:
        total_generation += min(20.0, 5.0 * (len(providers_used) - 1))  # multi-AI bonus (5 per extra provider, cap 20)
    gen_type = (cfg.get('type') or 'documentary').strip().lower()
    meta = {'documentary_id': doc_id, 'type': gen_type, 'content_category': category_id}
    if providers_used:
        meta['providers_used'] = providers_used

    # --- 1. Unified Points DB (primary) ---
    try:
        from backend.services.unified_points_database import unified_points_db
        if unified_points_db:
            unified_points_db.add_points(user_id, 'generation_points', total_generation, source='video_generation', metadata=meta)
            unified_points_db.add_points(user_id, 'xp_points', total_generation * 1.5, source='video_generation', metadata=meta)
            unified_points_db.add_points(user_id, 'activity_points', 10, source='video_generation', metadata=meta)
            unified_points_db.add_points(user_id, 'knowledge_points', 5, source='video_generation', metadata=meta)
            unified_points_db.add_points(user_id, 'coins', 0.5, source='video_generation', metadata=meta)
            if category_point_type and bonus > 0:
                unified_points_db.add_points(user_id, category_point_type, bonus, source='video_generation_category', metadata=meta)
    except Exception:
        pass
    try:
        from backend.services.unified_points_sync import unified_points_sync_device
        unified_points_sync_device.record_domain_sync('generator')
    except Exception:
        pass

    # --- 2. Enhanced Unified Points DB (transaction log) ---
    try:
        from backend.services.unified_points_database_enhanced import unified_points_db_enhanced
        if unified_points_db_enhanced:
            unified_points_db_enhanced.add_points(user_id, 'generation_points', total_generation, source='video_generation', metadata=meta)
            unified_points_db_enhanced.add_points(user_id, 'xp_points', total_generation * 1.5, source='video_generation', metadata=meta)
            unified_points_db_enhanced.add_points(user_id, 'activity_points', 10, source='video_generation', metadata=meta)
    except Exception:
        pass

    # --- 3. Trigger Integration (fires trigger-based rewards chain) ---
    try:
        from backend.services.unified_points_trigger_integration import unified_points_trigger_integration
        if unified_points_trigger_integration:
            unified_points_trigger_integration.award_points_with_trigger(
                'video_generation', user_id=user_id, amount=int(total_generation), metadata=meta,
            )
            unified_points_trigger_integration.award_points_with_trigger(
                'quality', user_id=user_id, amount=5, metadata=meta,
            )
    except Exception:
        pass

    # --- 4. Communication Psychology (themed content) ---
    try:
        comm_psych_categories = ('conspiracy', 'alternative_theories', 'religious_conspiracy', 'theory')
        if (category_id or '').lower() in comm_psych_categories:
            from backend.services.communication_psychology_service import award_points_for_activity
            award_points_for_activity(
                user_id,
                amount=min(25.0, 10.0 + bonus),
                source_activity='video_generation',
                metadata={'documentary_id': doc_id, 'content_category': category_id},
            )
    except Exception:
        pass

    # --- 5. Profile update (user_onboarding) ---
    try:
        import json as _json
        from backend.services.user_onboarding import user_onboarding
        if user_onboarding:
            profile = user_onboarding.get_user_profile(user_id)
            if profile:
                prefs = profile.get('preferences')
                if isinstance(prefs, str):
                    prefs = _json.loads(prefs or '{}')
                else:
                    prefs = dict(prefs or {})
                prefs['last_documentary_id'] = doc_id
                prefs['total_videos_created'] = int(prefs.get('total_videos_created', 0) or 0) + 1
                prefs['last_video_points'] = total_generation
                if providers_used:
                    prefs['last_providers_used'] = providers_used
                    prefs['total_multi_ai_generations'] = int(prefs.get('total_multi_ai_generations', 0) or 0) + (1 if len(providers_used) >= 2 else 0)
                user_onboarding.update_user_profile(user_id, {'preferences': _json.dumps(prefs)})
    except Exception:
        pass

    # --- 6. Agent AI Intelligence (learning from experience) ---
    try:
        from backend.services.agent_ai_intelligence import agent_ai_intelligence as ai_intel
        learn_payload = {
            'type': 'points_awarded',
            'documentary_id': doc_id,
            'generation_points': total_generation,
            'xp_awarded': total_generation * 1.5,
            'category': category_id,
            'timestamp': datetime.utcnow().isoformat(),
        }
        if providers_used:
            learn_payload['providers_used'] = providers_used
        ai_intel.learn_from_experience(f"video_gen_{user_id}", learn_payload)
    except Exception:
        pass

    # --- 7. Trophies ---
    _check_and_award_trophies(user_id, doc_id, config)

    # --- 8. Agent skill trigger (content_generator_agent) ---
    try:
        from backend.services.agent_db_service import agent_db_service
        from backend.services.user_agent_skills import user_agent_skills
        skills_data = user_agent_skills.get_user_skills(user_id)
        # Find a content or assigned agent to credit
        assigned = skills_data.get('assigned_agents', [])
        target_agent = None
        for aid in assigned:
            if 'content' in aid or 'generator' in aid:
                target_agent = aid
                break
        if not target_agent and assigned:
            target_agent = assigned[0]
        if target_agent:
            agent_db_service.record_agent_activity(
                user_id=user_id,
                agent_id=target_agent,
                action='generate_video',
                skill='generate_video',
                xp_gained=30,
                points_gained=total_generation,
                metadata={'documentary_id': doc_id, 'category': category_id},
            )
            user_agent_skills.level_up_skill(user_id, 'generate_video', experience=30)
    except Exception:
        pass

    # --- MN2 / crypto finish rewards ---
    try:
        from backend.services.generator_crypto_rewards_service import award_generator_crypto_rewards
        crypto = award_generator_crypto_rewards(user_id, doc_id, cfg)
        cfg["_crypto_rewards"] = crypto
    except Exception:
        cfg["_crypto_rewards"] = {}

    # --- Game Hub quests (daily generate_video + weekly_videos) ---
    try:
        from backend.services.generator_agent_service import record_video_quest_progress
        cfg["_quest_progress"] = record_video_quest_progress(user_id)
    except Exception:
        pass

    return total_generation


def _run_video_generation_impl(doc_id: str, config: Dict, job_store_get, job_store_set):
    """
    Shared implementation for video generation. Used by both the in-process thread
    and the standalone subprocess. job_store_get/set may be no-ops for standalone.
    """
    try:
        print(f"[VideoGenerator] Generation started doc_id={doc_id} duration={config.get('duration', 180)}", flush=True)
    except Exception:
        pass

    _services_ok, _svc_msg, _svc_detail = _check_generation_services()
    config["_service_check"] = _svc_detail
    if not (_svc_detail.get("disk") or {}).get("ok"):
        _set_job_failed(
            doc_id, "Video generation failed",
            _svc_msg or "Insufficient disk space for video output",
            job_store_get, job_store_set,
        )
        return
    if not (_svc_detail.get("llm") or {}).get("ok") and config.get("use_context", True):
        _set_job_failed(
            doc_id, "Video generation failed",
            _svc_msg or "No AI provider configured — cannot build a unique scene plan",
            job_store_get, job_store_set,
        )
        return

    _prepare_generation_config(doc_id, config)

    try:
        from backend.services.generator_encode_service import resolve_encode_profile, is_fast_encode_profile
        enc_prof = resolve_encode_profile(config)
        config["encode_profile"] = enc_prof
    except Exception:
        enc_prof = str(config.get("encode_profile") or "fast_ai")

    _uid = config.get("user_id", "default_user")

    # Tier caps (Creator / Pro) — before planning/encode; enable MONETIZATION_TIER_ENFORCEMENT=1
    try:
        from backend.services.monetization_tier_service import evaluate_generation_against_tier

        _ok, _terr = evaluate_generation_against_tier(_uid, config)
        if not _ok and _terr:
            _set_job_failed(
                doc_id,
                "Plan limit",
                _terr.get("message") or "Plan limit",
                job_store_get,
                job_store_set,
            )
            try:
                job = job_store_get(doc_id)
                if job:
                    job["error_code"] = _terr.get("code")
                    job["tier_limit"] = _terr
                    job["upsell"] = _terr.get("upsell")
                    job_store_set(doc_id, job)
            except Exception:
                pass
            return
    except Exception:
        pass

    # SCR org pool (§4) — optional; MONETIZATION_ORG_POOL_ENFORCEMENT=1
    try:
        from backend.services.monetization_org_pool_service import evaluate_org_pool_for_generation

        _ok_org, _oerr = evaluate_org_pool_for_generation(_uid, config)
        if not _ok_org and _oerr:
            _set_job_failed(
                doc_id,
                "Studio pool limit",
                _oerr.get("message") or "Studio pool limit",
                job_store_get,
                job_store_set,
            )
            try:
                job = job_store_get(doc_id)
                if job:
                    job["error_code"] = _oerr.get("code")
                    job["org_pool"] = _oerr
                    job_store_set(doc_id, job)
            except Exception:
                pass
            return
    except Exception:
        pass

    def on_progress(percent: int, message: str):
        try:
            encode_stage = _infer_encode_stage(message)
            job = job_store_get(doc_id)
            _is_final = percent >= 100 and 'complete' in (message or '').lower()
            _sidecar_status = 'completed' if _is_final else 'processing'
            if job:
                job['progress'] = percent
                job['message'] = message
                job['encode_stage'] = encode_stage
                job['updated_at'] = datetime.utcnow().isoformat()
                if _is_final:
                    job['status'] = 'completed'
                    job['video_url'] = f'/api/documentary/video/{doc_id}'
                job_store_set(doc_id, job)
            _write_status_sidecar(
                doc_id=doc_id,
                status=_sidecar_status,
                message=message,
                progress=percent,
                title=config.get('title'),
                prompt=config.get('prompt') or config.get('description'),
                video_url=f'/api/documentary/video/{doc_id}' if _is_final else None,
                generation_meta=_generation_meta_for_sidecar(config),
                stage=encode_stage,
            )
        except Exception:
            pass

    try:
        prompt = config.get('prompt', config.get('title', config.get('description', 'Untitled')))
        title = config.get('title', prompt[:80] if prompt else 'Documentary')
        duration = int(config.get('duration', 180))
        res = config.get('resolution', '1280x768')
        try:
            parts = res.split('x')
            w = int(parts[0]) if len(parts) > 0 else 1280
            h = int(parts[1]) if len(parts) > 1 else 768
        except (ValueError, TypeError):
            w, h = 1280, 768

        user_id = config.get('user_id', 'default_user')
        path = None
        error_message = None
        num_segments = 1  # fallback single-clip counts as one "mark"/segment
        providers_used: List[str] = []

        # COGS: aggregate LLMResponse.usage from all planning/enhancement bridge calls into one job total.
        if "_llm_usage_totals" not in config:
            config["_llm_usage_totals"] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        # Multi-AI: combine providers for scene plan / hooks when adaptive pipeline or 2+ providers.
        if "use_all_ais" not in config:
            try:
                from backend.services.llm_service import configured_providers
                provs = configured_providers()
                gm = str(config.get("generation_method") or "").strip().lower()
                config["use_all_ais"] = len(provs) >= 2 or gm == "adaptive_ai_v2"
            except Exception:
                config["use_all_ais"] = False

        # AI-first planning: zip profile+prompt+context into one generated scene plan.
        use_context = config.get('use_context', True)
        if use_context:
            try:
                _write_status_sidecar(
                    doc_id=doc_id,
                    status="processing",
                    message="Planning scenes with AI...",
                    progress=8,
                    title=config.get("title"),
                    prompt=config.get("prompt") or config.get("description"),
                    generation_meta=_generation_meta_for_sidecar(config),
                    stage="planning",
                )
                short = config.get('short_clip', duration < 120)
                require_ai_content = bool(config.get("require_ai_content", False))
                quality_mode = str(config.get("quality_mode") or "").strip().lower()
                generation_method = str(config.get("generation_method") or "").strip().lower()
                strict_ai = require_ai_content or (
                    quality_mode in ("best", "max", "ultra") and generation_method != "adaptive_ai_v2"
                )
                segments, ai_script_text, profile_context_text = _plan_ai_segments(
                    user_id=user_id,
                    prompt=prompt if isinstance(prompt, str) else str(prompt),
                    title=title,
                    duration_sec=duration,
                    short=short,
                    max_segments=12,
                    extra_context=config,
                    require_ai=strict_ai,
                    providers_used=providers_used,
                )
                if not segments and strict_ai and not require_ai_content:
                    segments, ai_script_text, profile_context_text = _plan_ai_segments(
                        user_id=user_id,
                        prompt=prompt if isinstance(prompt, str) else str(prompt),
                        title=title,
                        duration_sec=duration,
                        short=short,
                        max_segments=12,
                        extra_context=config,
                        require_ai=False,
                        providers_used=providers_used,
                    )
                if segments:
                    segments = _rearrange_segments_for_timeline(segments, target_duration=duration)
                    num_segments = len(segments)
                    _write_status_sidecar(
                        doc_id=doc_id,
                        status="processing",
                        message="Enhancing segments with AI...",
                        progress=18,
                        title=config.get("title"),
                        prompt=config.get("prompt") or config.get("description"),
                        generation_meta=_generation_meta_for_sidecar(config),
                        stage="enhancing",
                    )
                    # Enrich segments with mood/tagline/key_fact from AI (and track providers when use_all_ais).
                    segments = _ai_enhance_segments(
                        segments,
                        title,
                        prompt if isinstance(prompt, str) else str(prompt),
                        user_id=user_id,
                        theme=config.get("theme") or "",
                        extra_context=config,
                        providers_used=providers_used,
                    )
                    pipeline_file = _write_generation_pipeline_file(
                        doc_id,
                        {
                            "type": "video_pipeline",
                            "bundle_id": doc_id,
                            "user_id": user_id,
                            "title": str(title)[:180],
                            "prompt": str(prompt)[:1000],
                            "generation_method": str(config.get("generation_method") or "adaptive_ai_v2"),
                            "quality_mode": str(config.get("quality_mode") or "auto"),
                            "rearranged_segments": segments,
                            "generated_script": ai_script_text[:4000],
                            "profile_context": profile_context_text[:1000],
                            "providers_used": list(dict.fromkeys(providers_used)),
                            "created_at": datetime.utcnow().isoformat(),
                            "service_check": config.get("_service_check"),
                            "storyline_addon": (config.get("_storyline_addon") or "")[:1200],
                            "visual_seed": config.get("_visual_seed"),
                        },
                    )
                    is_prod = os.environ.get("FLASK_ENV", "").strip().lower() != "development"
                    try:
                        from backend.services.generator_encode_service import is_fast_encode_profile
                        fast_ai_profile = is_fast_encode_profile(enc_prof) or (
                            is_prod and str(config.get("encode_profile") or "").strip().lower() == "fast_ai"
                        )
                    except Exception:
                        fast_ai_profile = is_prod or str(config.get("encode_profile") or "").strip().lower() == "fast_ai"
                    out_w = 854 if fast_ai_profile else w
                    out_h = 480 if fast_ai_profile else h
                    add_audio_flag = bool(config.get("audio_enabled", True))
                    video_cogs_metrics: Dict[str, Any] = {}
                    path, error_message = generate_rich_video_sync(
                        doc_id,
                        segments,
                        width=out_w,
                        height=out_h,
                        add_audio=add_audio_flag,
                        audio_profile=_resolve_audio_profile(config, fallback_style="cinematic"),
                        on_progress=on_progress,
                        visual_profile=config.get("_visual_profile"),
                        metrics_out=video_cogs_metrics,
                        encode_profile=enc_prof,
                    )
                    config["_video_cogs_metrics"] = video_cogs_metrics
                    try:
                        job = job_store_get(doc_id)
                        if job:
                            job['generated_script'] = ai_script_text[:4000]
                            job['profile_context'] = profile_context_text[:1000]
                            if pipeline_file:
                                job['pipeline_file'] = pipeline_file
                            job_store_set(doc_id, job)
                    except Exception:
                        pass
                else:
                    _set_job_failed(
                        doc_id,
                        "Video generation failed",
                        "AI planner unavailable or returned invalid scene plan",
                        job_store_get,
                        job_store_set,
                    )
                    return
            except Exception as e:
                error_message = str(e)
                path = None

        require_ai_content = bool(config.get("require_ai_content", False))
        if not path and not require_ai_content:
            path, error_message = _generate_video_sync(
                doc_id, prompt, title, duration, w, h, on_progress, encode_profile=enc_prof,
            )
        elif not path and require_ai_content:
            error_message = error_message or "AI content required, but AI scene planning/encoding failed"

        if not path:
            _set_job_failed(doc_id, 'Video generation failed', error_message or 'Unknown error', job_store_get, job_store_set)
        else:
            short = config.get('short_clip', duration < 120)
            base_points = float(GENERATION_POINTS_PER_CLIP) if short else float(GENERATION_POINTS_PER_VIDEO)
            segment_points = num_segments * float(POINTS_PER_SEGMENT)
            points = base_points + segment_points
            if duration >= DURATION_BONUS_THRESHOLD_SEC:
                points += float(DURATION_BONUS_POINTS)
            award_config = dict(config)
            award_config["_providers_used"] = list(dict.fromkeys(providers_used))
            total_earned = _award_generation_points(user_id, doc_id, points, config=award_config)
            crypto = award_config.get("_crypto_rewards") or {}
            try:
                job = job_store_get(doc_id)
                if job:
                    job['points_earned'] = total_earned
                    job['user_id'] = job.get('user_id') or user_id
                    job['status'] = 'completed'
                    job['progress'] = 100
                    job['message'] = 'Complete'
                    job['video_url'] = f'/api/documentary/video/{doc_id}'
                    job['providers_used'] = list(dict.fromkeys(providers_used))
                    if crypto.get('total_mn2'):
                        job['mn2_earned'] = crypto.get('total_mn2')
                        job['crypto_breakdown'] = crypto.get('breakdown')
                    job['updated_at'] = datetime.utcnow().isoformat()
                    job_store_set(doc_id, job)
            except Exception:
                pass
            gen_meta = _generation_meta_for_sidecar(config)
            gen_meta['points_earned'] = total_earned
            if crypto.get('total_mn2'):
                gen_meta['mn2_earned'] = crypto.get('total_mn2')
                gen_meta['crypto_breakdown'] = crypto.get('breakdown')
            _write_status_sidecar(
                doc_id=doc_id,
                status="completed",
                message="Complete",
                progress=100,
                video_url=f"/api/documentary/video/{doc_id}",
                title=config.get("title"),
                prompt=config.get("prompt") or config.get("description"),
                providers_used=providers_used,
                generation_meta=gen_meta,
                stage="complete",
            )
            try:
                from backend.services.generator_thumbnail_service import build_video_thumbnails
                build_video_thumbnails(doc_id, path)
            except Exception:
                pass
            try:
                from backend.routes.gallery_routes import invalidate_gallery_cache
                invalidate_gallery_cache()
            except Exception:
                pass
            try:
                print(f"[VideoGenerator] Generation finished doc_id={doc_id} status=completed", flush=True)
            except Exception:
                pass
            try:
                bp_uid = str((job or {}).get("user_id") or user_id or "").strip()
                if bp_uid:
                    from backend.services.battle_pass_service import record_battle_pass_action

                    record_battle_pass_action(bp_uid, "generator_complete")
            except Exception:
                pass
            try:
                from backend.services.discord_m8_streams import post_generator_showcase
                post_generator_showcase(
                    job_id=doc_id,
                    title=str(title)[:120],
                    user_id=user_id,
                    video_url=f"/api/documentary/video/{doc_id}",
                )
            except Exception:
                pass
            try:
                _vm = dict(config.get("_video_cogs_metrics") or {})
                _ut = config.get("_llm_usage_totals")
                if isinstance(_ut, dict):
                    tt = int(_ut.get("total_tokens") or 0)
                    if tt <= 0:
                        tt = int(_ut.get("prompt_tokens") or 0) + int(_ut.get("completion_tokens") or 0)
                    if tt > 0:
                        _vm["llm_usage_tokens"] = dict(_ut)
                        _vm["llm_tokens_actual"] = tt
                        config["_video_cogs_metrics"] = _vm
                from backend.services.cogs_metering_service import record_completed_video_job
                record_completed_video_job(
                    job_kind="rich_video",
                    job_id=doc_id,
                    user_id=user_id,
                    config=config,
                    output_path=path,
                    video_metrics=config.get("_video_cogs_metrics"),
                    duration_config_sec=int(duration),
                    num_segments=num_segments,
                )
            except Exception:
                pass
            try:
                config.pop("_video_cogs_metrics", None)
            except Exception:
                pass
    except Exception as e:
        try:
            print(f"[VideoGenerator] Generation finished doc_id={doc_id} status=failed error={e!r}", flush=True)
        except Exception:
            pass
        _set_job_failed(doc_id, 'Video generation failed', str(e), job_store_get, job_store_set)


def generate_video_background(doc_id: str, config: Dict, job_store_get, job_store_set):
    """
    Run video generation in a background thread and update job store on progress/completion.
    On failure, job is set to status=failed. Prefer run_video_generation_standalone via subprocess
    so uWSGI workers stay free (no encoding in web process).
    """
    t = threading.Thread(
        target=_run_video_generation_impl,
        args=(doc_id, config, job_store_get, job_store_set),
        daemon=True,
    )
    t.start()
