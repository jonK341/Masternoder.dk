"""
Creator / Pro tier caps — evaluated before planning/encode.

Env:
  MONETIZATION_TIER_ENFORCEMENT=1  — enforce caps (default 0 = off for backward compatibility).
  MONETIZATION_FORCE_TIER=creator|pro — override resolved tier (admin/testing).

Tier resolution order:
  1) MONETIZATION_FORCE_TIER
  2) user profile preferences JSON key monetization_tier (if user_onboarding available)
  3) default from data/monetization_config.json
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Tuple

from backend.services.monetization_config_service import get_default_tier_id, get_tier_caps


def _tier_enforcement_enabled() -> bool:
    return (os.environ.get("MONETIZATION_TIER_ENFORCEMENT") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def resolve_user_tier(user_id: str) -> str:
    forced = (os.environ.get("MONETIZATION_FORCE_TIER") or "").strip().lower()
    if forced in ("creator", "pro"):
        return forced
    try:
        from backend.services.user_onboarding import user_onboarding

        prof = user_onboarding.get_user_profile(user_id) if user_onboarding else None
        if prof:
            prefs = prof.get("preferences")
            if isinstance(prefs, str):
                prefs = json.loads(prefs or "{}")
            if isinstance(prefs, dict):
                t = (prefs.get("monetization_tier") or prefs.get("subscription_tier") or "").strip().lower()
                if t in ("creator", "pro"):
                    return t
    except Exception:
        pass
    return get_default_tier_id()


def _estimate_segments_upper_bound(duration_sec: int) -> int:
    d = max(1, int(duration_sec or 180))
    return max(3, min(12, max(4, int(d / 15))))


def _estimate_llm_tokens(duration_sec: int, num_seg: int) -> int:
    def _ev(name: str, default: int) -> int:
        try:
            v = (os.environ.get(name) or "").strip()
            return int(float(v)) if v else default
        except (TypeError, ValueError):
            return default

    base = _ev("COGS_LLM_TOKENS_BASE", 2500)
    per = _ev("COGS_LLM_TOKENS_PER_SEGMENT", 800)
    return int(base) + int(num_seg) * int(per) + int(max(0, duration_sec) // 30) * 400


def evaluate_generation_against_tier(
    user_id: str,
    config: Dict[str, Any],
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Returns (allowed, error_payload).
    error_payload includes HTTP suggestion: status 403, code, upsell, caps.
    """
    if not _tier_enforcement_enabled():
        return True, None

    tier = resolve_user_tier(user_id)
    caps = get_tier_caps(tier)
    if not caps:
        return True, None

    duration = int(config.get("duration", 180) or 180)
    short = bool(config.get("short_clip", duration < 120))
    if short and duration > 120:
        duration = min(duration, 120)

    max_dur = int(caps.get("max_output_duration_sec") or 600)
    if duration > max_dur:
        return False, {
            "code": "TIER_LIMIT_DURATION",
            "http_status": 403,
            "tier": tier,
            "cap_key": "max_output_duration_sec",
            "limit": max_dur,
            "requested": duration,
            "message": f"Maximum video length for {caps.get('label', tier)} is {max_dur}s. Upgrade to Pro for longer outputs.",
            "upsell": {"target_tier": "pro", "reason": "duration"},
        }

    seg_ub = _estimate_segments_upper_bound(duration)
    max_seg = int(caps.get("max_segments_per_job") or 12)
    if seg_ub > max_seg:
        return False, {
            "code": "TIER_LIMIT_SEGMENTS",
            "http_status": 403,
            "tier": tier,
            "cap_key": "max_segments_per_job",
            "limit": max_seg,
            "estimated_segments": seg_ub,
            "message": f"Your plan allows up to {max_seg} scenes per video.",
            "upsell": {"target_tier": "pro", "reason": "segments"},
        }

    max_rw = int(caps.get("max_runway_output_seconds_billed_per_job") or 9999)
    num_clips_est = min(max_seg, max(1, duration // 15))
    est_runway_billed = num_clips_est * 5
    if est_runway_billed > max_rw:
        return False, {
            "code": "TIER_LIMIT_RUNWAY",
            "http_status": 402,
            "tier": tier,
            "cap_key": "max_runway_output_seconds_billed_per_job",
            "limit": max_rw,
            "estimated_runway_billed_sec": est_runway_billed,
            "message": "Runway usage for this request exceeds your plan. Reduce duration or upgrade.",
            "upsell": {"target_tier": "pro", "reason": "runway"},
        }

    est_tokens = _estimate_llm_tokens(duration, min(seg_ub, max_seg))
    max_tok = int(caps.get("max_llm_tokens_estimated_per_job") or 128000)
    if est_tokens > max_tok:
        return False, {
            "code": "TIER_LIMIT_LLM",
            "http_status": 403,
            "tier": tier,
            "cap_key": "max_llm_tokens_estimated_per_job",
            "limit": max_tok,
            "estimated": est_tokens,
            "message": "This request may exceed LLM usage for your plan. Simplify prompt or upgrade.",
            "upsell": {"target_tier": "pro", "reason": "llm"},
        }

    max_mb = int(caps.get("max_output_file_mb_per_job") or 400)
    rough_mb = (duration / 60.0) * 8.0
    if rough_mb > max_mb:
        return False, {
            "code": "TIER_LIMIT_OUTPUT_SIZE",
            "http_status": 403,
            "tier": tier,
            "cap_key": "max_output_file_mb_per_job",
            "limit": max_mb,
            "message": f"Estimated output size exceeds the {max_mb} MB cap for your plan.",
            "upsell": {"target_tier": "pro", "reason": "output_mb"},
        }

    return True, None
