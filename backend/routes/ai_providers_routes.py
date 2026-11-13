"""
AI Providers Routes — status, testing, and circuit-breaker management.

Endpoints:
  GET  /api/ai/providers              — list all providers + configured/available state
  GET  /api/ai/providers/test         — live test each configured provider with a ping
  POST /api/ai/providers/reset        — reset a provider's circuit breaker
  POST /api/ai/chat                   — generic chat endpoint with provider/task_type routing
  GET  /api/ai/video-providers        — status of video generation providers (RunwayML, ModelsLab, etc.)
  POST /api/ai/video-providers/test   — generate a short test clip via RunwayML
  POST /api/film-canvas/interactive-movie — start monitor interactive movie (plan→render)
  GET  /api/film-canvas/interactive-movie/<job_id> — poll interactive movie job
  GET  /api/film-canvas/interactive-movie/<job_id>/video — stream finished MP4
  GET  /api/film-canvas/billing — free-trial + MN2/PayPal pay status for film monitor
  POST /api/film-canvas/billing/pay-mn2 — buy 1 play credit with MN2 coins
  POST /api/film-canvas/billing/paypal-order — start PayPal checkout for 1 play credit
"""
import base64
import binascii
import json
import os
import re
import threading
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request, send_file

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
_interactive_movie_jobs = {}
_interactive_movie_lock = threading.Lock()


def _interactive_videos_dir() -> str:
    try:
        from backend.services.video_generator_service import VIDEOS_DIR
        if VIDEOS_DIR:
            os.makedirs(VIDEOS_DIR, exist_ok=True)
            return VIDEOS_DIR
    except Exception:
        pass
    fallback = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "vidgenerator",
        "videos",
    )
    os.makedirs(fallback, exist_ok=True)
    return fallback


def _interactive_job_path(job_id: str) -> str:
    safe = "".join(ch for ch in str(job_id) if ch.isalnum() or ch in ("_", "-"))
    return os.path.join(_interactive_videos_dir(), "interactive_%s.json" % safe)


def _save_interactive_job(job: dict) -> dict:
    job_id = str(job.get("job_id") or "")
    with _interactive_movie_lock:
        _interactive_movie_jobs[job_id] = dict(job)
    path = _interactive_job_path(job_id)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(job, handle)
    os.replace(tmp, path)
    return job


def _load_interactive_job(job_id: str):
    """Load job state. Prefer the on-disk sidecar so multi-worker uwsgi stays in sync."""
    path = _interactive_job_path(job_id)
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as handle:
                job = json.load(handle)
        except (OSError, json.JSONDecodeError):
            job = None
        if isinstance(job, dict):
            with _interactive_movie_lock:
                _interactive_movie_jobs[job_id] = dict(job)
            return job
    with _interactive_movie_lock:
        cached = _interactive_movie_jobs.get(job_id)
        if cached:
            return dict(cached)
    return None


def _public_interactive_job(job: dict) -> dict:
    return {
        "success": True,
        "job_id": job.get("job_id"),
        "status": job.get("status"),
        "progress": job.get("progress", 0),
        "message": job.get("message"),
        "error": job.get("error"),
        "planner": job.get("planner"),
        "renderer": job.get("renderer"),
        "prompt": job.get("prompt"),
        "prompt_used": job.get("prompt_used"),
        "duration_sec": job.get("duration_sec"),
        "has_face": bool(job.get("has_face")),
        "beats": job.get("beats"),
        "beat_plan": job.get("beat_plan"),
        "mode": job.get("mode"),
        "pipeline_run_id": job.get("pipeline_run_id"),
        "pipeline_style": job.get("pipeline_style"),
        "pipeline_mood": job.get("pipeline_mood"),
        "fx_pack": job.get("fx_pack"),
        "story": job.get("story"),
        "narration": job.get("narration"),
        "sellable": job.get("sellable"),
        "quality": job.get("quality"),
        "pipeline": job.get("pipeline"),
        "has_audio": job.get("has_audio"),
        "motion_backends": job.get("motion_backends"),
        "video_url": job.get("video_url"),
        "download_url": (
            (job.get("video_url") + ("&" if "?" in str(job.get("video_url") or "") else "?") + "download=1")
            if job.get("video_url") else None
        ),
        "xvid_url": (
            (job.get("video_url") + ("&" if "?" in str(job.get("video_url") or "") else "?") + "download=1&format=xvid")
            if job.get("video_url") and job.get("xvid_path") else None
        ),
        "updated_at": job.get("updated_at"),
    }


def _touch_interactive_job(job_id: str, **fields) -> dict:
    job = _load_interactive_job(job_id) or {"job_id": job_id}
    job.update(fields)
    job["updated_at"] = datetime.utcnow().isoformat() + "Z"
    return _save_interactive_job(job)


def _clamp_duration_sec(raw) -> int:
    try:
        value = int(round(float(raw)))
    except (TypeError, ValueError):
        value = 8
    return max(2, min(120, value))


def _save_face_image_data_url(data_url: str, dest_dir: str, job_id: str) -> str:
    """Persist a browser data-URL face image next to interactive movie outputs."""
    raw = (data_url or "").strip()
    match = re.match(r"^data:(image/[a-zA-Z0-9.+-]+);base64,(.+)$", raw, re.DOTALL)
    if not match:
        raise ValueError("face_image must be an image data URL")
    mime = match.group(1).lower()
    payload = match.group(2)
    ext = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/pjpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }.get(mime, ".jpg")
    try:
        binary = base64.b64decode(payload, validate=False)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("face_image base64 is invalid") from exc
    if len(binary) < 64:
        raise ValueError("face_image is too small")
    if len(binary) > 4 * 1024 * 1024:
        raise ValueError("face_image must be under 4 MB")
    os.makedirs(dest_dir, exist_ok=True)
    safe = "".join(ch for ch in str(job_id) if ch.isalnum() or ch in ("_", "-"))
    path = os.path.join(dest_dir, "face_%s%s" % (safe, ext))
    with open(path, "wb") as handle:
        handle.write(binary)
    return path


def _run_interactive_movie_job(
    job_id: str,
    prompt: str,
    duration_sec: int = 8,
    face_path: str = None,
) -> None:
    duration_sec = _clamp_duration_sec(duration_sec)
    _touch_interactive_job(
        job_id,
        status="processing",
        progress=8,
        message="Planning %ss storyboard..." % duration_sec,
        prompt=prompt,
        duration_sec=duration_sec,
        has_face=bool(face_path),
    )
    try:
        from backend.services.sellable_film_pipeline import compose_sellable_movie

        def _on_progress(pct, message):
            _touch_interactive_job(job_id, progress=max(8, min(99, int(pct))), message=message)

        _touch_interactive_job(
            job_id,
            progress=10,
            message="Sellable pipeline v1 — story, hero frames, real motion, soundtrack…",
        )

        # Paid I2V needs headroom; scale with length but keep monitor UX bounded.
        timeout = max(180, min(600, 90 + int(duration_sec) * 8))
        result = compose_sellable_movie(
            prompt,
            dest_dir=_interactive_videos_dir(),
            duration_sec=duration_sec,
            face_path=face_path,
            timeout=timeout,
            on_progress=_on_progress,
            allow_draft_fallback=True,
        )
        if result.get("success") and result.get("local_path"):
            beats = result.get("beats")
            mode = result.get("mode")
            style = result.get("pipeline_style")
            sellable = bool(result.get("sellable"))
            _touch_interactive_job(
                job_id,
                status="completed",
                progress=100,
                message=(
                    ("Sellable movie ready" if sellable else "Draft movie ready")
                    + ((" · %s scenes" % beats) if beats else "")
                    + (" · audio" if result.get("has_audio") else "")
                    + ((" · %s" % style) if style else "")
                    + (
                        (" · " + ",".join(result.get("motion_backends") or [])[:40])
                        if result.get("motion_backends") else ""
                    )
                ),
                planner="sellable_architect",
                renderer=result.get("renderer") or result.get("canvas") or "sellable_v1",
                prompt_used=result.get("prompt_used"),
                local_path=result.get("local_path"),
                xvid_path=result.get("xvid_path"),
                video_url="/api/film-canvas/interactive-movie/%s/video" % job_id,
                beats=beats,
                beat_plan=result.get("beat_plan"),
                mode=mode,
                pipeline_run_id=result.get("pipeline_run_id"),
                pipeline_style=style,
                pipeline_mood=result.get("pipeline_mood"),
                fx_pack=result.get("fx_pack"),
                story=result.get("story"),
                narration=result.get("narration"),
                sellable=sellable,
                quality=result.get("quality"),
                pipeline=result.get("pipeline") or "sellable_v1",
                has_audio=bool(result.get("has_audio")),
                motion_backends=result.get("motion_backends"),
                error=None,
            )
        else:
            _touch_interactive_job(
                job_id,
                status="failed",
                progress=100,
                message="Sellable pipeline failed",
                planner="sellable_architect",
                renderer=result.get("renderer") or result.get("canvas") or "sellable_v1",
                prompt_used=result.get("prompt_used"),
                pipeline="sellable_v1",
                sellable=False,
                quality="failed",
                error=result.get("error") or "Sellable film compose failed",
            )
    except Exception as exc:
        _touch_interactive_job(
            job_id,
            status="failed",
            progress=100,
            message="Sellable pipeline failed",
            pipeline="sellable_v1",
            sellable=False,
            quality="failed",
            error=str(exc)[:300],
        )


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
        return jsonify({
            "success": True,
            "summary": {
                "total_providers": len(statuses),
                "configured": len(configured),
                "available": len(available),
                "task_routes": TASK_ROUTES,
            },
            "providers": statuses,
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 200


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
    target = request.args.get("provider")
    providers_to_test = [target] if target and target in PROVIDERS else configured_providers()

    results = []
    for pname in providers_to_test:
        import time as _t
        t0 = _t.monotonic()
        resp = chat(_TEST_PING, provider=pname, max_tokens=10, timeout=15)
        elapsed_ms = int((_t.monotonic() - t0) * 1000)
        results.append({
            "provider": pname,
            "label": PROVIDERS[pname]["label"],
            "success": resp.success,
            "response": resp.content if resp.success else None,
            "error": resp.error if not resp.success else None,
            "model_used": resp.model,
            "elapsed_ms": elapsed_ms,
        })

    passed = sum(1 for r in results if r["success"])
    return jsonify({
        "success": True,
        "tested": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
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
        from backend.services.film_canvas_service import (
            is_available as film_canvas_available,
            list_canvases,
            select_canvas,
        )
        for row in list_canvases():
            canvas_id = str(row.get("id") or "")
            purpose = "planning" if canvas_id == "dramacanva" else "render"
            providers.append({
                "name": row.get("label") or canvas_id,
                "id": canvas_id,
                "key_env": row.get("key_env"),
                "available": film_canvas_available(canvas_id, purpose=purpose),
                "type": "film_canvas",
                "uses": row.get("uses") or [],
                "websocket": row.get("websocket") or None,
                "http_base": row.get("http_base") or None,
                "generates_mp4": bool(row.get("generates_mp4")),
                "configured": bool(row.get("key_configured")),
            })
        providers.append({
            "name": "Film canvas auto-select",
            "id": "film_canvas_auto",
            "key_env": "FILM_CANVAS",
            "available": select_canvas("render") is not None,
            "type": "film_canvas",
            "selected_renderer": select_canvas("render"),
            "selected_planner": select_canvas("planning"),
        })
    except Exception:
        providers.append({
            "name": "Film canvases",
            "key_env": "FAL_API_KEY",
            "available": False,
            "type": "film_canvas",
        })

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


# ---------------------------------------------------------------------------
# Film monitor billing (free 24h → MN2 coins or PayPal)
# ---------------------------------------------------------------------------
def _film_billing_identity_from_request(data=None):
    data = data if isinstance(data, dict) else {}
    user_id = (
        data.get("user_id")
        or request.args.get("user_id")
        or request.headers.get("X-User-Id")
        or ""
    )
    trial_id = (
        data.get("trial_id")
        or request.args.get("trial_id")
        or request.cookies.get("fp_film_trial")
        or ""
    )
    return str(user_id).strip(), str(trial_id).strip()


@ai_providers_bp.route("/api/film-canvas/billing", methods=["GET", "POST"])
def film_canvas_billing_status():
    """Return free-trial clock and clear MN2 / PayPal pay options."""
    data = request.get_json(silent=True) or {}
    user_id, trial_id = _film_billing_identity_from_request(data)
    from backend.services.film_monitor_billing_service import get_status

    status = get_status(user_id, trial_id, start_trial=True)
    return jsonify(status), 200


@ai_providers_bp.route("/api/film-canvas/billing/pay-mn2", methods=["POST"])
def film_canvas_pay_mn2():
    """Debit MN2 coins and grant one film-monitor play credit."""
    data = request.get_json(silent=True) or {}
    user_id, trial_id = _film_billing_identity_from_request(data)
    from backend.services.film_monitor_billing_service import pay_with_mn2

    result = pay_with_mn2(user_id, trial_id)
    code = 200 if result.get("success") else 402
    if result.get("code") == "ACCOUNT_REQUIRED":
        code = 401
    return jsonify(result), code


@ai_providers_bp.route("/api/film-canvas/billing/paypal-order", methods=["POST"])
def film_canvas_paypal_order():
    """Create a PayPal order for one film-monitor play credit."""
    data = request.get_json(silent=True) or {}
    user_id, trial_id = _film_billing_identity_from_request(data)
    base = request.url_root.rstrip("/") if request.url_root else None
    from backend.services.film_monitor_billing_service import create_paypal_order

    result = create_paypal_order(user_id, trial_id, return_base=base)
    code = 200 if result.get("success") else 400
    if result.get("code") == "ACCOUNT_REQUIRED":
        code = 401
    return jsonify(result), code


# ---------------------------------------------------------------------------
# Interactive movie (Mission Control monitor)
# ---------------------------------------------------------------------------
@ai_providers_bp.route("/api/film-canvas/interactive-movie", methods=["POST"])
def start_interactive_movie():
    """Start interactive movie for the monitor (prompt + optional face + duration)."""
    data = request.get_json(silent=True) or {}
    prompt = str(data.get("prompt") or "").strip()
    if not prompt:
        prompt = "Cinematic control-room monitor: neon city rain, interactive film loop"
    duration_sec = _clamp_duration_sec(
        data.get("duration_sec", data.get("duration", data.get("timer_sec", 8)))
    )
    face_image = data.get("face_image") or data.get("face") or ""

    user_id, trial_id = _film_billing_identity_from_request(data)
    try:
        from backend.services.film_monitor_billing_service import assert_can_play

        access = assert_can_play(user_id, trial_id, consume_credit=True)
        if not access.get("can_play"):
            return jsonify(access), 402
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)[:300]}), 200

    try:
        from backend.services.film_canvas_service import (
            is_available as film_ok,
            pipeline_render_available,
        )
        can_plan = film_ok("dramacanva", purpose="planning")
        if not can_plan and not pipeline_render_available():
            return jsonify({
                "success": False,
                "error": "No film/video pipeline renderer is available",
            }), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)[:300]}), 200

    job_id = "im_" + uuid.uuid4().hex[:12]
    face_path = None
    if isinstance(face_image, str) and face_image.strip():
        try:
            face_path = _save_face_image_data_url(
                face_image,
                _interactive_videos_dir(),
                job_id,
            )
        except ValueError as exc:
            return jsonify({"success": False, "error": str(exc)}), 200
        except Exception as exc:
            return jsonify({"success": False, "error": "Could not save face image: %s" % exc}), 200

    if face_path and "[face reference" not in prompt.lower():
        prompt = (prompt + " [face reference attached]").strip()

    job = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "message": "Queued",
        "prompt": prompt[:500],
        "duration_sec": duration_sec,
        "has_face": bool(face_path),
        "face_path": face_path,
        "billing": {
            "free_active": bool(access.get("free_active")),
            "reason": access.get("reason"),
            "credits_left": access.get("credits"),
        },
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    _save_interactive_job(job)
    thread = threading.Thread(
        target=_run_interactive_movie_job,
        args=(job_id, prompt[:500], duration_sec, face_path),
        daemon=True,
    )
    thread.start()
    payload = _public_interactive_job(job)
    payload["billing"] = job.get("billing")
    return jsonify(payload), 202


@ai_providers_bp.route("/api/film-canvas/interactive-movie/<job_id>", methods=["GET"])
def interactive_movie_status(job_id):
    job = _load_interactive_job(job_id)
    if not job:
        return jsonify({"success": False, "error": "Job not found"}), 404
    return jsonify(_public_interactive_job(job)), 200


@ai_providers_bp.route("/api/film-canvas/interactive-movie/<job_id>/video", methods=["GET"])
def interactive_movie_video(job_id):
    job = _load_interactive_job(job_id) or {}
    fmt = str(request.args.get("format") or "").strip().lower()
    path = job.get("local_path")
    mimetype = "video/mp4"
    download_name = "masternoder-movie-%s.mp4" % (
        "".join(ch for ch in str(job_id) if ch.isalnum() or ch in ("_", "-"))[:24]
        or "clip"
    )
    if fmt in ("xvid", "avi", "mpeg4"):
        xvid_path = job.get("xvid_path")
        if (not xvid_path or not os.path.isfile(xvid_path)) and path and os.path.isfile(path):
            try:
                from backend.services.film_canvas_service import _ffmpeg_encode_xvid
                encoded = _ffmpeg_encode_xvid(path)
                if encoded.get("success") and encoded.get("local_path"):
                    xvid_path = encoded["local_path"]
                    _touch_interactive_job(job_id, xvid_path=xvid_path)
            except Exception:
                xvid_path = None
        if xvid_path and os.path.isfile(xvid_path):
            path = xvid_path
            mimetype = "video/x-msvideo"
            download_name = download_name.replace(".mp4", ".avi")
    if not path or not os.path.isfile(path):
        return jsonify({"success": False, "error": "Video not ready"}), 404
    as_download = str(request.args.get("download") or "").strip().lower() in (
        "1", "true", "yes", "download",
    )
    return send_file(
        path,
        mimetype=mimetype,
        conditional=True,
        as_attachment=as_download,
        download_name=download_name if as_download else None,
    )
