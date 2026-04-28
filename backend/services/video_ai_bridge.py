"""
Video AI Bridge — routes all AI providers into the video/clip generation pipeline.

Bridges backend.services.llm_service (and optional other AI services) so that:
- Each pipeline stage uses the best-suited task_type (context, speed, reason, etc.),
  so different providers are used at different stages when multiple are configured.
- Optional "use_all_ais" mode: call multiple providers for key stages and pick/merge
  results to use full available AI power.

Stages and routing:
- scene_plan      → context (Gemini, OpenAI, Anthropic) — long context, structure
- segment_enhance → speed (Groq, Cerebras, Together) — fast batch enrichment
- opening_hook    → speed — one short line
- agent_angles    → speed — narrative angle from agents
- title_variations→ speed — creative titles
- prompt_ideas    → reason (DeepSeek, OpenRouter) — diverse ideas
- enhanced_descriptions → speed — paragraphs
- strategy        → reason — content strategy
- video_concept   → (ai_content_generator, then optional LLM) — concept text
- episode_storyline → reason — fresh per-run storyline paragraph for the planner
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# Stage → (task_type, use_best_for_long)
_STAGE_ROUTING: Dict[str, Tuple[str, bool]] = {
    "scene_plan": ("context", True),
    "segment_enhance": ("speed", False),
    "opening_hook": ("speed", False),
    "agent_angles": ("speed", False),
    "title_variations": ("speed", False),
    "prompt_ideas": ("reason", False),
    "enhanced_descriptions": ("speed", False),
    "strategy": ("reason", False),
    "video_concept": ("speed", False),
    "episode_storyline": ("reason", False),
}


def _accumulate_usage(extra_context: Optional[Dict[str, Any]], response: Any) -> None:
    """If extra_context['_llm_usage_totals'] is a dict, merge LLMResponse.usage into it."""
    if not extra_context or not response:
        return
    bucket = extra_context.get("_llm_usage_totals")
    if not isinstance(bucket, dict):
        return
    try:
        from backend.services.llm_service import accumulate_llm_usage_from_response

        accumulate_llm_usage_from_response(bucket, response)
    except Exception:
        pass


def _llm_complete(
    prompt: str,
    system_prompt: Optional[str] = None,
    *,
    temperature: float = 0.6,
    max_tokens: int = 1024,
    timeout: Optional[int] = None,
    task_type: str = "default",
    provider: Optional[str] = None,
    use_best: bool = False,
) -> Any:
    """Single LLM completion; returns LLMResponse or None on import error."""
    try:
        from backend.services.llm_service import llm_service
        if not (llm_service and llm_service.is_available()):
            return None
        return llm_service.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            provider=provider,
            task_type=task_type,
            use_best=use_best,
        )
    except Exception:
        return None


def _configured_providers_for_task(task_type: str) -> List[str]:
    """Ordered list of configured provider names for a task type."""
    try:
        from backend.services.llm_service import (
            TASK_ROUTES,
            _is_provider_configured,
        )
        chain = TASK_ROUTES.get(task_type, TASK_ROUTES["default"])
        return [p for p in chain if _is_provider_configured(p)]
    except Exception:
        return []


def complete_for_stage(
    stage: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    *,
    temperature: float = 0.6,
    max_tokens: int = 1024,
    timeout: Optional[int] = None,
    use_best: Optional[bool] = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Run one LLM completion for a pipeline stage. Uses the stage's task_type
    so the right provider(s) are tried (e.g. context for scene_plan, speed for hooks).
    Returns LLMResponse or None.
    """
    route = _STAGE_ROUTING.get(stage, ("default", False))
    task_type, default_use_best = route
    if use_best is None:
        use_best = default_use_best
    if extra_context:
        quality = str(extra_context.get("quality_mode") or "").strip().lower()
        if quality in ("best", "max", "ultra"):
            use_best = True
    r = _llm_complete(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        task_type=task_type,
        use_best=use_best,
    )
    _accumulate_usage(extra_context, r)
    return r


def complete_multi_provider(
    stage: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    *,
    max_providers: int = 3,
    temperature: float = 0.6,
    max_tokens: int = 1024,
    timeout: Optional[int] = 30,
    extra_context: Optional[Dict[str, Any]] = None,
) -> List[Tuple[str, Any]]:
    """
    Call up to max_providers configured providers for this stage. Returns
    list of (provider_name, LLMResponse) for successful responses only.
    Use this when use_all_ais=True to gather multiple AI outputs (e.g. pick best hook).
    """
    route = _STAGE_ROUTING.get(stage, ("default", False))
    task_type = route[0]
    providers = _configured_providers_for_task(task_type)
    if not providers:
        return []
    to_try = providers[: max(1, max_providers)]
    results: List[Tuple[str, Any]] = []
    for pname in to_try:
        r = _llm_complete(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            task_type=task_type,
            provider=pname,
        )
        _accumulate_usage(extra_context, r)
        if r is not None and getattr(r, "success", False) and getattr(r, "content", None):
            results.append((pname, r))
    return results


def pick_best_scene_plan(
    responses: List[Tuple[str, Any]],
    normalize_fn: Any,
    max_segments: int = 8,
) -> Optional[List[Dict[str, Any]]]:
    """
    From multiple (provider, response) pairs for scene_plan, return first valid
    normalized scene plan. normalize_fn(parsed_json, max_segments) -> list or None.
    """
    for _provider, r in responses:
        content = getattr(r, "content", None) or ""
        if not content or "scenes" not in content:
            continue
        try:
            start = content.find("{")
            if start >= 0:
                import json
                obj = json.loads(content[start : content.rfind("}") + 1])
                segs = normalize_fn(obj, max_segments=max_segments)
                if segs:
                    return segs
        except Exception:
            continue
    return None


def pick_best_opening_hook(responses: List[Tuple[str, Any]], max_words: int = 15) -> Optional[str]:
    """
    From multiple (provider, response) pairs, pick one opening hook: prefer
    short, non-empty, no JSON/quotes. Returns single string or None.
    """
    candidates: List[str] = []
    for _provider, r in responses:
        raw = (getattr(r, "content", None) or "").strip().strip('"').strip()
        if not raw or len(raw) < 10:
            continue
        raw = raw[:120]
        words = raw.split()
        if max_words and len(words) > max_words:
            raw = " ".join(words[:max_words])
        if raw and raw not in candidates:
            candidates.append(raw)
    return candidates[0] if candidates else None


def merge_segment_enhancements(
    segments: List[Dict[str, Any]],
    responses: List[Tuple[str, Any]],
    title: str,
    prompt: str,
) -> List[Dict[str, Any]]:
    """
    Given multiple LLM responses for segment_enhance (each with JSON scenes),
    merge into one enhanced segment list: take first successful full parse, then
    optionally overlay non-empty fields from other responses. Returns enhanced segments.
    """
    import json
    merged: List[Dict[str, Any]] = []
    for i, seg in enumerate(segments):
        merged.append(dict(seg))
    for _provider, r in responses:
        content = getattr(r, "content", None) or ""
        if not content or "scenes" not in content:
            continue
        try:
            start = content.find("{")
            if start >= 0:
                obj = json.loads(content[start : content.rfind("}") + 1])
            else:
                continue
            scenes = obj.get("scenes") or []
            if not isinstance(scenes, list) or len(scenes) < 1:
                continue
            for i, seg in enumerate(merged):
                if i >= len(scenes):
                    break
                ai = scenes[i]
                if isinstance(ai, dict):
                    for key in ("description", "mood", "tagline", "key_fact"):
                        val = ai.get(key)
                        if isinstance(val, str) and val.strip():
                            if key == "description" and len(val) > 10:
                                merged[i]["description"] = val[:260]
                            elif key == "mood":
                                merged[i]["mood"] = val.strip().lower()
                            elif key == "tagline":
                                merged[i]["tagline"] = val.strip()[:60]
                            elif key == "key_fact":
                                merged[i]["key_fact"] = val.strip()[:80]
            break
        except Exception:
            continue
    return merged


# Optional: expose stage routing for UI/docs
def get_stage_routing() -> Dict[str, Dict[str, Any]]:
    """Return stage → task_type and description for docs/UI."""
    return {
        stage: {"task_type": tt, "use_best_default": ub}
        for stage, (tt, ub) in _STAGE_ROUTING.items()
    }
