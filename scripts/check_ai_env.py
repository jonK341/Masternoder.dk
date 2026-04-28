#!/usr/bin/env python3
"""
Print which AI env vars are set (masked) — no network calls.
Run from project root: python scripts/check_ai_env.py

Uses the same key names as backend.services.llm_service.PROVIDERS + common video/TTS keys.
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_ROOT, ".env"))
except ImportError:
    pass

LLM_KEYS = [
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
    "GOOGLE_AI_API_KEY",
    "GOOGLE_GEMINI_API_KEY",
    "OPENROUTER_API_KEY",
    "CEREBRAS_API_KEY",
    "DEEPSEEK_API_KEY",
    "MISTRAL_API_KEY",
    "TOGETHER_API_KEY",
    "ANTHROPIC_API_KEY",
    "COHERE_API_KEY",
    "AZURE_OPENAI_API_KEY",
]
VIDEO_KEYS = [
    "RUNWAYML_API_KEY",
    "PIKA_LABS_API_KEY",
    "STABILITY_AI_API_KEY",
    "MODELSLAB_API_KEY",
    "REPLICATE_API_TOKEN",
    "HEYGEN_API_KEY",
    "ELEVENLABS_API_KEY",
]


def _mask(v: str) -> str:
    v = (v or "").strip()
    if not v:
        return "(empty)"
    return f"(set, {len(v)} chars)"


def main() -> int:
    print("AI environment (local .env loaded if python-dotenv installed)\n")
    pf = os.environ.get("LLM_PREFER_FREE", "").strip()
    print(f"LLM_PREFER_FREE (default uses free chain when 1/true): {pf or '(unset)'}")
    att = os.environ.get("AGENT_AI_LLM_TASK", "").strip()
    print(f"AGENT_AI_LLM_TASK (agent llm-insight routing): {att or '(unset, defaults to free)'}")
    print()
    try:
        from backend.services.llm_service import configured_providers, is_available
        print("LLM configured providers:", ", ".join(configured_providers()) or "(none)")
        print("LLM any available:", is_available())
    except Exception as e:
        print("LLM service import:", e)
    print()
    for title, keys in (("LLM / routing", LLM_KEYS), ("Video / TTS", VIDEO_KEYS)):
        print(f"--- {title} ---")
        for k in keys:
            print(f"  {k}: {_mask(os.environ.get(k, ''))}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
