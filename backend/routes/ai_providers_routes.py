"""
AI Providers Routes — status, testing, and circuit-breaker management.

Endpoints:
  GET  /api/ai/providers              — list all providers + configured/available state
  GET  /api/ai/providers/test         — live test each configured provider with a ping
  POST /api/ai/providers/reset        — reset a provider's circuit breaker
  POST /api/ai/chat                   — generic chat endpoint with provider/task_type routing
  GET  /api/ai/video-providers        — status of video generation providers (RunwayML, ModelsLab, etc.)
  POST /api/ai/video-providers/test   — generate a short test clip via RunwayML
"""
import json
import traceback

from flask import Blueprint, jsonify, request

from backend.services.llm_service import (
    get_provider_status,
    configured_providers,
    reset_circuit,
    chat,
    PROVIDERS,
    TASK_ROUTES,
)

ai_providers_bp = Blueprint("ai_providers", __name__)

_TEST_PING = [{"role": "user", "content": "Reply with just the word: ok"}]


def _json_safe(obj):
    """Ensure payload is JSON-serializable (avoids 500 from jsonify on odd types)."""
    try:
        json.dumps(obj, default=str)
        return obj
    except Exception:
        return json.loads(json.dumps(obj, default=str))


# ---------------------------------------------------------------------------
# GET /api/ai/providers
# ---------------------------------------------------------------------------
@ai_providers_bp.route("/api/ai/providers", methods=["GET"])
def provider_status():
    """Return status of all AI providers — configured, available, circuit state, models."""
    try:
        statuses = get_provider_status()
        configured = [s for s in statuses if s["configured"]]
        available = [s for s in statuses if s["available"]]
        # Plain dict so jsonify never sees non-JSON types from TASK_ROUTES / env
        task_routes_plain = {k: list(v) for k, v in TASK_ROUTES.items()}
        payload = {
            "success": True,
            "summary": {
                "total_providers": len(statuses),
                "configured": len(configured),
                "available": len(available),
                "task_routes": task_routes_plain,
            },
            "providers": statuses,
        }
        return jsonify(_json_safe(payload)), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "trace": traceback.format_exc()[-4000:],
        }), 200


# ---------------------------------------------------------------------------
# GET /api/ai/providers/test
# ---------------------------------------------------------------------------
@ai_providers_bp.route("/api/ai/providers/test", methods=["GET"])
def test_providers():
    """
    Live-ping every configured provider with a minimal message.
    Optional query param: ?provider=groq  to test a single provider only.
    Warning: this makes real API calls and counts against rate limits.
    """
    try:
        target = (request.args.get("provider") or "").strip()
        if target and target not in PROVIDERS:
            return jsonify({
                "success": False,
                "error": f"Unknown provider: {target!r}. Valid: {', '.join(sorted(PROVIDERS.keys()))}",
                "tested": 0,
                "passed": 0,
                "failed": 0,
                "results": [],
            }), 200

        providers_to_test = [target] if target else configured_providers()

        if not providers_to_test:
            return jsonify({
                "success": False,
                "error": "No LLM providers configured. Set at least one API key in .env (e.g. GROQ_API_KEY or OPENAI_API_KEY).",
                "tested": 0,
                "passed": 0,
                "failed": 0,
                "results": [],
            }), 200

        results = []
        for pname in providers_to_test:
            import time as _t
            t0 = _t.monotonic()
            try:
                resp = chat(_TEST_PING, provider=pname, max_tokens=10, timeout=15)
            except Exception as ex:
                elapsed_ms = int((_t.monotonic() - t0) * 1000)
                results.append({
                    "provider": pname,
                    "label": PROVIDERS.get(pname, {}).get("label", pname),
                    "success": False,
                    "response": None,
                    "error": f"{type(ex).__name__}: {ex}",
                    "model_used": None,
                    "elapsed_ms": elapsed_ms,
                })
                continue
            elapsed_ms = int((_t.monotonic() - t0) * 1000)
            results.append({
                "provider": pname,
                "label": PROVIDERS[pname]["label"],
                "success": bool(resp.success),
                "response": (resp.content or "")[:2000] if resp.success else None,
                "error": (resp.error or "")[:2000] if not resp.success else None,
                "model_used": resp.model,
                "elapsed_ms": elapsed_ms,
            })

        passed = sum(1 for r in results if r["success"])
        return jsonify(_json_safe({
            "success": True,
            "tested": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "results": results,
        })), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "trace": traceback.format_exc()[-4000:],
            "tested": 0,
            "passed": 0,
            "failed": 0,
            "results": [],
        }), 200


# ---------------------------------------------------------------------------
# POST /api/ai/providers/reset
# ---------------------------------------------------------------------------
@ai_providers_bp.route("/api/ai/providers/reset", methods=["POST"])
def reset_provider_circuit():
    """
    Manually reset a provider's circuit breaker.
    Body: {"provider": "groq"}
    """
    try:
        data = request.get_json(silent=True) or {}
        provider = data.get("provider", "").strip()
        if not provider:
            return jsonify({"success": False, "error": "provider field required"}), 200
        ok = reset_circuit(provider)
        if not ok:
            return jsonify({"success": False, "error": f"Unknown provider: {provider}"}), 200
        return jsonify({"success": True, "message": f"Circuit breaker reset for '{provider}'"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 200


# ---------------------------------------------------------------------------
# POST /api/ai/chat
# ---------------------------------------------------------------------------
@ai_providers_bp.route("/api/ai/chat", methods=["POST"])
def ai_chat():
    """
    Generic AI chat endpoint with provider/task_type routing.

    Body (JSON):
      prompt      : str  — simple prompt (alternative to messages)
      messages    : list — full message list [{"role": "user", "content": "..."}]
      provider    : str  — force a specific provider (optional)
      task_type   : str  — "speed"|"code"|"reason"|"context"|"free"|"default"
      model       : str  — override model (optional)
      temperature : float (default 0.7)
      max_tokens  : int   (default 1024)
      system      : str  — system prompt (used when prompt is provided)
    """
    try:
        data = request.get_json(silent=True) or {}
        prompt = data.get("prompt", "").strip()
        messages = data.get("messages")
        provider = data.get("provider") or None
        task_type = data.get("task_type", "default")
        model = data.get("model") or None
        temperature = float(data.get("temperature", 0.7))
        max_tokens = int(data.get("max_tokens", 1024))
        system = data.get("system", "").strip()

        if not messages:
            if not prompt:
                return jsonify({"success": False, "error": "Provide 'prompt' or 'messages'"}), 200
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

        resp = chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            provider=provider,
            task_type=task_type,
        )

        return jsonify({
            "success": resp.success,
            "content": resp.content,
            "provider": resp.provider,
            "model": resp.model,
            "usage": resp.usage,
            "error": resp.error,
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 200


# ---------------------------------------------------------------------------
# GET /api/ai/video-providers
# ---------------------------------------------------------------------------
@ai_providers_bp.route("/api/ai/video-providers", methods=["GET"])
def video_provider_status():
    """Return availability of AI video/image generation providers."""
    providers = []

    try:
        from backend.services.runwayml_service import is_available as runway_ok
        providers.append({"name": "RunwayML Gen-4", "key_env": "RUNWAYML_API_KEY", "available": runway_ok(), "type": "video"})
    except Exception:
        providers.append({"name": "RunwayML Gen-4", "key_env": "RUNWAYML_API_KEY", "available": False, "type": "video"})

    try:
        from backend.services.modelslab_video_service import is_available as ml_ok
        providers.append({"name": "ModelsLab", "key_env": "MODELSLAB_API_KEY", "available": ml_ok(), "type": "video"})
    except Exception:
        providers.append({"name": "ModelsLab", "key_env": "MODELSLAB_API_KEY", "available": False, "type": "video"})

    try:
        from backend.services.pika_service import is_available as pika_ok
        providers.append({"name": "Pika 2.2", "key_env": "PIKA_LABS_API_KEY", "available": pika_ok(), "type": "video"})
    except Exception:
        providers.append({"name": "Pika 2.2", "key_env": "PIKA_LABS_API_KEY", "available": False, "type": "video"})

    try:
        from backend.services.heygen_service import is_available as heygen_ok
        providers.append({"name": "HeyGen Avatar", "key_env": "HEYGEN_API_KEY", "available": heygen_ok(), "type": "video"})
    except Exception:
        providers.append({"name": "HeyGen Avatar", "key_env": "HEYGEN_API_KEY", "available": False, "type": "video"})

    try:
        from backend.services.replicate_video_service import is_available as replicate_ok
        providers.append({"name": "Replicate SVD", "key_env": "REPLICATE_API_TOKEN", "available": replicate_ok(), "type": "video"})
    except Exception:
        providers.append({"name": "Replicate SVD", "key_env": "REPLICATE_API_TOKEN", "available": False, "type": "video"})

    try:
        from backend.services.stability_image_service import is_available as stab_ok
        providers.append({"name": "Stability AI", "key_env": "STABILITY_AI_API_KEY", "available": stab_ok(), "type": "image"})
    except Exception:
        providers.append({"name": "Stability AI", "key_env": "STABILITY_AI_API_KEY", "available": False, "type": "image"})

    providers.append({"name": "Pollinations.ai", "key_env": None, "available": True, "type": "image", "note": "free/unlimited"})

    try:
        from backend.services.tts_service import get_status as tts_status, list_voices
        tts = tts_status()
        providers.append({"name": "TTS (Piper / ElevenLabs / gTTS)", "key_env": "ELEVENLABS_API_KEY",
                          "available": (tts or {}).get("active_provider", "none") not in ("none", ""),
                          "type": "audio", "detail": tts,
                          "voices": list_voices()})
    except Exception:
        providers.append({"name": "TTS (Piper / ElevenLabs / gTTS)", "key_env": "ELEVENLABS_API_KEY",
                          "available": False, "type": "audio"})

    try:
        from backend.services.audio_enhancement_service import get_status as ae_status
        ae = ae_status()
        ae_avail = (ae.get("noise_reduction", {}).get("available") or
                    ae.get("loudnorm", {}).get("available"))
        providers.append({"name": "Audio Enhancement (DeepFilterNet / FFmpeg loudnorm)",
                          "key_env": "AUDIO_ENHANCE", "available": ae_avail,
                          "type": "audio", "detail": ae})
    except Exception:
        providers.append({"name": "Audio Enhancement (DeepFilterNet / FFmpeg loudnorm)",
                          "key_env": "AUDIO_ENHANCE", "available": False, "type": "audio"})

    available_count = sum(1 for p in providers if p["available"])
    return jsonify({
        "success": True,
        "summary": {"total": len(providers), "available": available_count},
        "providers": providers,
    }), 200


# ---------------------------------------------------------------------------
# POST /api/ai/video-providers/test
# ---------------------------------------------------------------------------
@ai_providers_bp.route("/api/ai/video-providers/test", methods=["POST"])
def test_runway():
    """
    Generate a 2-second test clip via RunwayML Gen-4.
    Body: {"prompt": "optional custom prompt"}
    Warning: consumes RunwayML credits.
    """
    try:
        from backend.services.runwayml_service import is_available as runway_ok, generate_clip
        if not runway_ok():
            return jsonify({"success": False, "error": "RUNWAYML_API_KEY not configured"}), 200
        data = request.get_json(silent=True) or {}
        prompt = data.get("prompt", "Cinematic aerial shot of a futuristic city at sunset, 4K").strip()
        result = generate_clip(prompt=prompt, duration=2, timeout=120)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 200
