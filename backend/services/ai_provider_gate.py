"""
AI provider gate — deactivate credit-blocked backends, promote working ones.

Blocked paid I2V/T2V wallets (Runway / Pika / ModelsLab / Replicate / fal /
HeyGen / Stability / OpenAI image / Google imagen / OpenRouter video) waste
timeouts and produce nothing. This gate skips them until manually cleared.

Active stack (researched Nov 2026):
  Image: Pollinations free models — flux, z-image-turbo, gptimage
  Motion: story_gif_line (4–5s story panels in one horizontal strip) + premium_local
  Voice:  existing TTS / shop WAV / soft bed (always muxed)
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_GATE_FILE = os.path.join(_REPO_ROOT, "instance", "ai_provider_gate.json")

# Hard-blocked until credits return. Keys are stable backend ids.
_DEFAULT_BLOCKED: Dict[str, str] = {
    "runway": "no_api_key_or_credit",
    "pika": "no_api_key_or_credit",
    "modelslab": "subscription_required",
    "replicate": "insufficient_credit",
    "fal": "balance_exhausted",
    "heygen": "quota_exhausted",
    "stability": "no_api_key_or_credit",
    "openai_image": "credit_balance_exhausted",
    "google_imagen": "quota_exceeded",
    "openrouter_video": "requires_balance",
    "together": "edge_blocked",
    "huggingface_inference": "forbidden_or_unreachable",
}

# Replacement providers that actually answer without a paid wallet.
ACTIVE_IMAGE_PROVIDERS = (
    "pollinations_flux",
    "pollinations_z_image",
    "pollinations_gptimage",
)

ACTIVE_MOTION_PROVIDERS = (
    "story_gif_line",
    "premium_local",
)

# Pollinations free image models ranked by research + live probes.
POLLINATIONS_IMAGE_MODELS = (
    "flux",
    "z-image-turbo",
    "gptimage",
)

_CREDIT_ERROR_MARKERS = (
    "insufficient credit",
    "insufficient_quota",
    "credit_balance_exhausted",
    "out of credit",
    "exhausted balance",
    "top up your balance",
    "no credits remaining",
    "quota exceeded",
    "remaining_quota\": 0",
    "need to be subscribed",
    "buy subscription",
    "payment required",
    "requires at least $",
)


def _load() -> Dict[str, Any]:
    try:
        with open(_GATE_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"blocked": dict(_DEFAULT_BLOCKED), "updated_at": 0}


def _save(data: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(_GATE_FILE), exist_ok=True)
        tmp = _GATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
        os.replace(tmp, _GATE_FILE)
    except Exception:
        pass


def ensure_defaults() -> Dict[str, Any]:
    """Seed blocked list on first use; keep any newer blocks."""
    data = _load()
    blocked = data.get("blocked") if isinstance(data.get("blocked"), dict) else {}
    changed = False
    for key, reason in _DEFAULT_BLOCKED.items():
        if key not in blocked:
            blocked[key] = reason
            changed = True
    data["blocked"] = blocked
    if changed or not data.get("updated_at"):
        data["updated_at"] = int(time.time())
        data["active_image"] = list(ACTIVE_IMAGE_PROVIDERS)
        data["active_motion"] = list(ACTIVE_MOTION_PROVIDERS)
        data["pollinations_models"] = list(POLLINATIONS_IMAGE_MODELS)
        _save(data)
    return data


def is_blocked(backend: str) -> bool:
    data = ensure_defaults()
    blocked = data.get("blocked") or {}
    return str(backend or "").strip().lower() in blocked


def block(backend: str, reason: str = "credit_or_auth_failure") -> None:
    data = ensure_defaults()
    blocked = dict(data.get("blocked") or {})
    key = str(backend or "").strip().lower()
    if not key:
        return
    blocked[key] = (reason or "blocked")[:200]
    data["blocked"] = blocked
    data["updated_at"] = int(time.time())
    _save(data)


def unblock(backend: str) -> None:
    data = ensure_defaults()
    blocked = dict(data.get("blocked") or {})
    blocked.pop(str(backend or "").strip().lower(), None)
    data["blocked"] = blocked
    data["updated_at"] = int(time.time())
    _save(data)


def note_error(backend: str, error: Optional[str]) -> bool:
    """Auto-block when an error looks like a credit/quota lock. Returns True if blocked."""
    text = str(error or "").lower()
    if not text:
        return False
    if any(marker in text for marker in _CREDIT_ERROR_MARKERS):
        block(backend, text[:180])
        return True
    return False


def filter_available(backends: List[str]) -> List[str]:
    ensure_defaults()
    return [b for b in backends if b and not is_blocked(b)]


def status() -> Dict[str, Any]:
    data = ensure_defaults()
    return {
        "blocked": dict(data.get("blocked") or {}),
        "active_image": list(data.get("active_image") or ACTIVE_IMAGE_PROVIDERS),
        "active_motion": list(data.get("active_motion") or ACTIVE_MOTION_PROVIDERS),
        "pollinations_models": list(data.get("pollinations_models") or POLLINATIONS_IMAGE_MODELS),
        "updated_at": data.get("updated_at"),
    }
