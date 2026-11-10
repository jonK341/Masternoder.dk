"""Landing monitor API for the frontpage entertainment surface."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

landing_monitor_bp = Blueprint("landing_monitor", __name__)


@landing_monitor_bp.route("/api/landing/monitor", methods=["GET"])
def landing_monitor_snapshot():
    from backend.services.landing_monitor_service import get_snapshot, refresh_snapshot

    force = str(request.args.get("refresh") or "").strip().lower() in ("1", "true", "yes")
    try:
        payload = refresh_snapshot(force=True) if force else get_snapshot(max_age_sec=12.0)
    except Exception as exc:
        payload = {
            "success": False,
            "error": str(exc)[:200],
            "bpm": 180,
            "refresh_ms": 5000,
            "stats": {},
            "special": {},
            "lightshow": {"id": "pulse", "name": "Pulse Lightshow", "explain": ""},
            "effect_explain": {"title": "Pulse", "body": "", "bpm": 180},
            "music": {"bpm": 180, "opt_in": True},
            "actions": [],
            "reel": [],
            "learning": {},
        }
    return jsonify(payload), 200, {"Cache-Control": "public, max-age=2"}


@landing_monitor_bp.route("/api/landing/monitor/tick", methods=["POST"])
def landing_monitor_tick():
    """Cron/ops tick — sync actions + rebuild cache."""
    from backend.services.landing_monitor_service import refresh_snapshot
    from backend.services.landing_monitor_actions_service import sync_from_activity

    sync = sync_from_activity(limit=40)
    payload = refresh_snapshot(force=True)
    return jsonify(
        {
            "success": True,
            "updated_at": payload.get("updated_at"),
            "bpm": payload.get("bpm"),
            "imported": sync.get("imported"),
            "reel_count": payload.get("reel_count"),
        }
    )


@landing_monitor_bp.route("/api/landing/monitor/actions", methods=["GET", "POST"])
def landing_monitor_actions():
    from backend.services import landing_monitor_actions_service as acts

    if request.method == "GET":
        category = (request.args.get("category") or "").strip() or None
        unplayed = str(request.args.get("unplayed") or "").lower() in ("1", "true", "yes")
        limit = request.args.get("limit", 40, type=int)
        return jsonify(acts.list_actions(limit=limit, category=category, unplayed_only=unplayed))

    body = request.get_json(silent=True) or {}
    result = acts.record_action(
        str(body.get("type") or body.get("event_type") or "manual_action"),
        title=body.get("title"),
        text=body.get("text"),
        channel=body.get("channel"),
        user_id=body.get("user_id"),
        payload=body.get("payload") if isinstance(body.get("payload"), dict) else {},
        category=body.get("category"),
        source=str(body.get("source") or "api"),
    )
    return jsonify(result), 201


@landing_monitor_bp.route("/api/landing/monitor/reel", methods=["GET"])
def landing_monitor_reel():
    from backend.services.landing_monitor_actions_service import build_reel

    limit = request.args.get("limit", 24, type=int)
    return jsonify(build_reel(limit=limit, prefer_unplayed=True))


@landing_monitor_bp.route("/api/landing/monitor/learning", methods=["GET"])
def landing_monitor_learning():
    from backend.services.landing_monitor_actions_service import learning_snapshot

    return jsonify(learning_snapshot())


@landing_monitor_bp.route("/api/landing/monitor/played", methods=["POST"])
def landing_monitor_played():
    from backend.services.landing_monitor_actions_service import mark_played

    body = request.get_json(silent=True) or {}
    ids = body.get("ids") or body.get("action_ids") or []
    if isinstance(ids, str):
        ids = [ids]
    if not isinstance(ids, list):
        ids = []
    return jsonify(mark_played(ids))


@landing_monitor_bp.route("/api/landing/monitor/sats", methods=["GET"])
def landing_monitor_sats():
    from backend.services.landing_monitor_pipeline_service import collect_sats_snapshot

    return jsonify(collect_sats_snapshot())


@landing_monitor_bp.route("/api/landing/monitor/pipeline", methods=["GET", "POST"])
def landing_monitor_pipeline():
    from backend.services.landing_monitor_pipeline_service import build_pipeline, get_pipeline

    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        use_llm = str(body.get("use_llm", "1")).lower() not in ("0", "false", "no")
        # Always a fresh cut on POST — never append to a saved history.
        return jsonify(build_pipeline(force=True, use_llm=use_llm, reason="client_regen"))

    force = str(request.args.get("refresh") or "").lower() in ("1", "true", "yes")
    use_llm = str(request.args.get("ai") or "0").lower() in ("1", "true", "yes")
    if force:
        return jsonify(build_pipeline(force=True, use_llm=use_llm, reason="refresh"))
    return jsonify(get_pipeline())


@landing_monitor_bp.route("/api/landing/monitor/online", methods=["GET"])
def landing_monitor_online():
    from backend.services.landing_monitor_pipeline_service import collect_online_leaderboard

    limit = request.args.get("limit", 25, type=int)
    hours = request.args.get("hours", 24, type=int)
    return jsonify(collect_online_leaderboard(limit=limit, recent_hours=hours))


@landing_monitor_bp.route("/api/landing/monitor/tts", methods=["POST"])
def landing_monitor_tts():
    """Human-like server TTS for lobby hosts (ElevenLabs when configured)."""
    import hashlib
    import os
    import shutil

    from flask import send_file

    # Ensure deploy .env keys (e.g. ELEVENLABS_API_KEY) are visible to TTS.
    try:
        from dotenv import load_dotenv

        load_dotenv(override=False)
    except Exception:
        pass

    from backend.services import tts_service

    body = request.get_json(silent=True) or {}
    text = str(body.get("text") or body.get("speak") or "").strip()[:420]
    speaker_id = str(body.get("speaker_id") or body.get("speaker") or "").strip()
    voice_key = str(body.get("voice_key") or "").strip().lower()

    speaker_voice = {
        "performer_nova": "josh",
        "performer_luna": "bella",
        "performer_ember": "domi",
        "performer_iris": "rachel",
        "performer_honey": "bella",
        "performer_storm": "adam",
        "performer_pixie": "josh",
        "performer_venus": "antoni",
        "performer_sage": "sam",
        "performer_aurora": "rachel",
        "performer_jade": "bella",
        "performer_velvet": "antoni",
        "performer_skylar": "josh",
        "performer_rio": "adam",
        "performer_mist": "sam",
    }
    if not voice_key:
        voice_key = speaker_voice.get(speaker_id, "bella")
    if voice_key not in getattr(tts_service, "VOICES", {}):
        voice_key = "bella"

    if not text:
        return jsonify({"success": False, "error": "empty_text"}), 400
    if not tts_service.is_available():
        return jsonify({"success": False, "error": "tts_unavailable", "fallback": "browser"}), 503

    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cache_dir = os.path.join(base, "static", "landing_monitor", "tts")
    os.makedirs(cache_dir, exist_ok=True)
    digest = hashlib.sha1(f"{voice_key}|{text}".encode("utf-8")).hexdigest()[:24]
    dest = os.path.join(cache_dir, f"{digest}.mp3")
    audio_path = dest if (os.path.isfile(dest) and os.path.getsize(dest) > 200) else None
    if not audio_path:
        path = tts_service.synthesize(text, voice_key=voice_key)
        if not path or not os.path.isfile(path):
            return jsonify({"success": False, "error": "synthesize_failed", "fallback": "browser"}), 502
        try:
            shutil.copyfile(path, dest)
            try:
                os.chmod(dest, 0o664)
            except Exception:
                pass
            audio_path = dest
        except Exception:
            audio_path = path

    want_file = str(request.args.get("redirect") or "").lower() in ("1", "true", "yes")
    accept = (request.headers.get("Accept") or "").lower()
    if want_file or "audio/" in accept:
        return send_file(audio_path, mimetype="audio/mpeg", conditional=True, as_attachment=False)

    # Prefer a public static URL when the cache write succeeded.
    if audio_path == dest or (os.path.isfile(dest) and os.path.getsize(dest) > 200):
        return jsonify(
            {
                "success": True,
                "url": "/static/landing_monitor/tts/" + os.path.basename(dest),
                "voice_key": voice_key,
                "speaker_id": speaker_id or None,
                "provider": (tts_service.get_status() or {}).get("active_provider"),
                "chars": len(text),
            }
        )

    # Cache dir not writable — stream bytes once with a short-lived route-friendly tip.
    return send_file(audio_path, mimetype="audio/mpeg", as_attachment=False)
