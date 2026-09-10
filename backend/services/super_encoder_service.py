"""
Super Encoder — one-click music + song + video creation with synchronized encoding.

Spotify-style track registry, 125-video storage cap, per-task AI routing using
configured API keys (LLM, ElevenLabs TTS, existing video pipeline).
"""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CFG_PATH = os.path.join(_BASE, "data", "creator_config.json")
_MAX_VIDEOS = 125
_DEFAULT_MODE_ID = "full_mv"


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def get_config() -> Dict[str, Any]:
    cfg = _read_json(_CFG_PATH)
    cfg.setdefault("max_videos", _MAX_VIDEOS)
    return cfg


def list_encoder_modes() -> Dict[str, Any]:
    """Return the encoder mode catalog from creator_config.json."""
    cfg = get_config()
    modes = [m for m in (cfg.get("encoder_modes") or []) if isinstance(m, dict) and m.get("id")]
    default_id = cfg.get("default_encoder_mode") or _DEFAULT_MODE_ID
    return {
        "success": True,
        "modes": modes,
        "count": len(modes),
        "default_mode": default_id,
    }


def get_encoder_mode(mode_id: Optional[str] = None) -> Dict[str, Any]:
    """Resolve a mode by id; fall back to default or first catalog entry."""
    catalog = list_encoder_modes()
    modes = catalog.get("modes") or []
    default_id = catalog.get("default_mode") or _DEFAULT_MODE_ID
    target = (mode_id or default_id or "").strip()
    for mode in modes:
        if mode.get("id") == target:
            return mode
    if modes:
        return modes[0]
    return {
        "id": _DEFAULT_MODE_ID,
        "label": "Full Song + MV",
        "icon": "🎬",
        "layers": {"lyrics": True, "audio": True, "video": True, "sync": True},
    }


def _resolve_mode_params(
    mode_id: Optional[str],
    title: str,
    genre: str,
    mood: str,
    duration: int,
) -> Tuple[Dict[str, Any], Dict[str, bool], int, str, str]:
    """Merge user inputs with mode defaults."""
    mode = get_encoder_mode(mode_id)
    layers_raw = mode.get("layers") or {}
    layers = {
        "lyrics": bool(layers_raw.get("lyrics", True)),
        "audio": bool(layers_raw.get("audio", True)),
        "video": bool(layers_raw.get("video", True)),
        "sync": bool(layers_raw.get("sync", True)),
    }
    dur = int(mode.get("default_duration") if mode.get("default_duration") is not None else duration or 60)
    if layers["audio"] or layers["video"]:
        dur = max(10, min(180, dur))
    else:
        dur = max(0, min(180, dur))
    resolved_genre = (genre or mode.get("default_genre") or "electronic").strip()
    resolved_mood = (mood or mode.get("default_mood") or "energetic").strip()
    return mode, layers, dur, resolved_genre, resolved_mood


def _storage_dir() -> str:
    cfg = get_config()
    rel = cfg.get("storage_dir") or "data/creator_videos"
    return os.path.join(_BASE, rel) if not os.path.isabs(rel) else rel


def _tracks_path() -> str:
    cfg = get_config()
    rel = cfg.get("tracks_catalog") or "data/creator_tracks.json"
    return os.path.join(_BASE, rel) if not os.path.isabs(rel) else rel


def _load_tracks() -> Dict[str, Any]:
    with _LOCK:
        return _read_json(_tracks_path())


def _save_tracks(data: dict) -> None:
    with _LOCK:
        data["updated_at"] = _iso()
        _write_json(_tracks_path(), data)


def get_storage_stats() -> Dict[str, Any]:
    """Return current storage usage against the 125-video cap."""
    cfg = get_config()
    max_v = int(cfg.get("max_videos") or _MAX_VIDEOS)
    tracks = _load_tracks().get("tracks") or []
    count = len([t for t in tracks if isinstance(t, dict) and t.get("status") != "deleted"])
    sdir = _storage_dir()
    disk_bytes = 0
    if os.path.isdir(sdir):
        for f in os.listdir(sdir):
            fp = os.path.join(sdir, f)
            if os.path.isfile(fp):
                try:
                    disk_bytes += os.path.getsize(fp)
                except Exception:
                    pass
    return {
        "success": True,
        "max_videos": max_v,
        "stored_videos": count,
        "slots_remaining": max(0, max_v - count),
        "at_capacity": count >= max_v,
        "disk_bytes": disk_bytes,
        "storage_dir": sdir,
    }


def _enforce_storage_cap() -> Optional[Dict[str, Any]]:
    stats = get_storage_stats()
    if stats["at_capacity"]:
        return {
            "success": False,
            "error": f"Storage full: {stats['max_videos']} videos maximum. Delete old tracks to create new ones.",
            "storage": stats,
        }
    return None


def _resolve_ai_provider(task_key: str) -> Dict[str, Any]:
    """Pick best available AI provider for a task based on configured keys."""
    cfg = get_config()
    task_cfg = (cfg.get("ai_tasks") or {}).get(task_key) or {}
    available = []

    if task_cfg.get("provider") == "tts":
        from backend.services import tts_service
        prefs = task_cfg.get("preference") or ["elevenlabs", "piper", "gtts"]
        for p in prefs:
            if p == "elevenlabs" and tts_service._elevenlabs_key():
                available.append({"provider": "elevenlabs", "type": "tts"})
            elif p == "piper" and tts_service._piper_model_path():
                available.append({"provider": "piper", "type": "tts"})
            elif p in ("gtts", "pyttsx3"):
                available.append({"provider": p, "type": "tts"})
        return {"task": task_key, "selected": available[0] if available else {"provider": "gtts", "type": "tts"}, "available": available}

    if task_cfg.get("provider") == "video":
        prefs = task_cfg.get("preference") or ["modelslab", "runway", "pika", "replicate"]
        for p in prefs:
            try:
                if p == "modelslab":
                    from backend.services.modelslab_video_service import is_available
                    if is_available():
                        available.append({"provider": "modelslab", "type": "video"})
                elif p == "runway":
                    from backend.services.runwayml_service import is_available
                    if is_available():
                        available.append({"provider": "runway", "type": "video"})
                elif p == "pika":
                    from backend.services.pika_service import is_available
                    if is_available():
                        available.append({"provider": "pika", "type": "video"})
                elif p == "replicate":
                    from backend.services.replicate_video_service import is_available
                    if is_available():
                        available.append({"provider": "replicate", "type": "video"})
                elif p == "pollinations":
                    available.append({"provider": "pollinations", "type": "video"})
            except Exception:
                continue
        return {"task": task_key, "selected": available[0] if available else {"provider": "pollinations", "type": "video"}, "available": available}

    # LLM tasks
    prefs = task_cfg.get("provider_preference") or ["openai", "groq", "gemini"]
    try:
        from backend.services.llm_service import configured_providers
        live = set(configured_providers())
        for p in prefs:
            if p in live:
                available.append({"provider": p, "type": "llm"})
    except Exception:
        pass
    if not available:
        available.append({"provider": "auto", "type": "llm"})
    return {"task": task_key, "selected": available[0] if available else None, "available": available}


def get_ai_status() -> Dict[str, Any]:
    """Return AI routing status for all encoder tasks."""
    tasks = ["lyrics", "music_structure", "video_prompt", "audio_voice", "video_clips", "sync_encode"]
    routing = {t: _resolve_ai_provider(t) for t in tasks}
    music_status = {}
    try:
        from backend.services.music_api_service import get_music_provider_status
        music_status = get_music_provider_status()
    except Exception:
        pass
    return {
        "success": True,
        "ai_routing": routing,
        "music_hook": music_status,
        "max_videos": int(get_config().get("max_videos") or _MAX_VIDEOS),
    }


def _run_llm_task(task_key: str, template_override: Optional[str] = None, **kwargs) -> str:
    cfg = get_config()
    task_cfg = (cfg.get("ai_tasks") or {}).get(task_key) or {}
    template = template_override or task_cfg.get("prompt_template") or ""
    if not template:
        return ""
    fmt_keys = {k: kwargs.get(k, "") for k in ("title", "genre", "mood", "lyrics_excerpt")}
    try:
        prompt = template.format(**fmt_keys)
    except KeyError:
        prompt = template
    task_type = task_cfg.get("task_type") or "default"
    routing = _resolve_ai_provider(task_key)
    provider = (routing.get("selected") or {}).get("provider")
    try:
        from backend.services.llm_service import chat
        kwargs_chat = {
            "messages": [{"role": "user", "content": prompt}],
            "task_type": task_type,
        }
        if provider and provider != "auto":
            kwargs_chat["provider"] = provider
        result = chat(**kwargs_chat)
        if result.success and result.content:
            return result.content.strip()
        return f"[AI fallback] {kwargs.get('title', 'Track')} — {kwargs.get('genre', 'electronic')}"
    except Exception as exc:
        return f"[AI fallback] {kwargs.get('title', 'Track')} — {kwargs.get('genre', 'electronic')} ({exc})"


def _generate_audio(
    lyrics: str,
    track_id: str,
    title: str = "",
    genre: str = "electronic",
    duration: int = 60,
    mode: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Generate music via Suno/Replicate hook, then TTS vocal fallback."""
    mode = mode or {}
    sdir = _storage_dir()
    os.makedirs(sdir, exist_ok=True)
    out_path = os.path.join(sdir, f"{track_id}_audio.mp3")
    song_path = os.path.join(sdir, f"{track_id}_song.mp3")
    music_hint = mode.get("music_prompt") or ""
    skip_music = bool(mode.get("skip_music_gen"))
    skip_tts = bool(mode.get("skip_tts"))
    tone_freq = float(mode.get("tone_freq") or 440.0)
    tone_dur = min(float(duration or 30), 180.0) or 30.0

    music_prompt = " ".join(
        p for p in (music_hint, lyrics[:400] if lyrics and not skip_tts else "", f"{title} {genre}")
        if p
    ).strip() or f"{title} instrumental {genre}"

    # 1) Suno / MusicGen hook (preferred for full songs)
    if not skip_music:
        try:
            from backend.services.music_api_service import generate_music
            music = generate_music(
                prompt=music_prompt[:600],
                title=title or track_id,
                genre=genre,
                dest_path=song_path,
                duration_sec=max(10, duration),
            )
            if music.get("success") and music.get("path") and os.path.isfile(music["path"]):
                import shutil
                shutil.copy2(music["path"], out_path)
                return out_path
        except Exception:
            pass

    # 2) TTS vocal track
    if not skip_tts and lyrics:
        try:
            from backend.services.tts_service import synthesize, generate_speech
            src = synthesize(lyrics[:4000], voice_key="rachel") or generate_speech(lyrics[:4000], out_path)
            if src and os.path.isfile(src) and src != out_path:
                import shutil
                shutil.copy2(src, out_path)
            if os.path.isfile(out_path):
                return out_path
            if src and os.path.isfile(src):
                return src
        except Exception:
            pass
    # Tone fallback when TTS/music unavailable
    try:
        from backend.services.podcast_audio_service import _write_wav_tone, _wav_to_mp3
        wav = os.path.join(sdir, f"{track_id}_tone.wav")
        if _write_wav_tone(wav, duration_sec=tone_dur, freq=tone_freq):
            if _wav_to_mp3(wav, out_path) or os.path.isfile(wav):
                return out_path if os.path.isfile(out_path) else wav
    except Exception:
        pass
    return None


def _start_video_job(
    track_id: str,
    title: str,
    prompt: str,
    user_id: str,
    duration: int,
    mode: Optional[Dict[str, Any]] = None,
) -> str:
    """Start video generation via existing generator pipeline."""
    mode = mode or {}
    doc_id = f"creator_{track_id}"
    config = {
        "title": title,
        "prompt": prompt,
        "description": prompt,
        "duration": duration,
        "short_clip": bool(mode.get("short_clip")) or duration <= 90,
        "user_id": user_id,
        "source": "super_encoder",
        "creator_track_id": track_id,
        "encoder_mode": mode.get("id"),
        "audio_style": mode.get("audio_style") or "energetic",
    }
    try:
        from backend.routes.generator_shared import start_documentary_encoding
        start_documentary_encoding(doc_id, config)
    except Exception:
        pass
    return doc_id


def _sync_encode(track_id: str, audio_path: Optional[str], video_path: Optional[str]) -> Optional[str]:
    """Mux audio + video with ffmpeg synchronized encoding."""
    sdir = _storage_dir()
    out_path = os.path.join(sdir, f"{track_id}_sync.mp4")
    if not video_path or not os.path.isfile(video_path):
        return video_path
    if not audio_path or not os.path.isfile(audio_path):
        return video_path
    cfg = get_config()
    sync_cfg = (cfg.get("ai_tasks") or {}).get("sync_encode") or {}
    vcodec = sync_cfg.get("video_codec") or "libx264"
    acodec = sync_cfg.get("audio_codec") or "aac"
    offset = int(sync_cfg.get("audio_offset_ms") or 0)
    offset_flag = f"-itsoffset {offset / 1000.0}" if offset else ""
    cmd = f'ffmpeg -y -i "{video_path}" {offset_flag} -i "{audio_path}" -c:v {vcodec} -c:a {acodec} -shortest -map 0:v:0 -map 1:a:0 "{out_path}"'
    try:
        subprocess.run(cmd, shell=True, capture_output=True, timeout=300)
        if os.path.isfile(out_path) and os.path.getsize(out_path) > 1024:
            return out_path
    except Exception:
        pass
    return video_path


def _register_track(
    track_id: str,
    user_id: str,
    title: str,
    genre: str,
    mood: str,
    lyrics: str,
    doc_id: str,
    audio_path: Optional[str],
    sync_path: Optional[str],
    status: str = "encoding",
    mode: Optional[Dict[str, Any]] = None,
    duration_sec: Optional[int] = None,
) -> Dict[str, Any]:
    """Spotify-style track registry entry."""
    mode = mode or {}
    catalog = _load_tracks()
    tracks: List[dict] = catalog.get("tracks") or []
    layer_flags = {
        "song": bool(lyrics),
        "audio": bool(audio_path),
        "video": bool(doc_id),
        "sync": bool(sync_path),
    }
    if mode.get("stems"):
        layer_flags["stems"] = mode.get("stems")
    if mode.get("karaoke"):
        layer_flags["karaoke"] = True
    entry = {
        "id": track_id,
        "user_id": user_id,
        "title": title,
        "genre": genre,
        "mood": mood,
        "encoder_mode": mode.get("id"),
        "encoder_mode_label": mode.get("label"),
        "encoder_mode_icon": mode.get("icon"),
        "lyrics_preview": (lyrics or "")[:200],
        "doc_id": doc_id,
        "audio_url": f"/api/creator/tracks/{track_id}/audio" if audio_path else None,
        "video_url": f"/api/creator/tracks/{track_id}/video" if doc_id else None,
        "sync_url": f"/api/creator/tracks/{track_id}/sync" if sync_path else None,
        "status": status,
        "duration_sec": duration_sec,
        "avg_rating": 0.0,
        "rating_count": 0,
        "created_at": _iso(),
        "updated_at": _iso(),
        "encoder_bot": f"super_encoder_{mode.get('id') or 'default'}",
        "layers": layer_flags,
    }
    tracks = [t for t in tracks if t.get("id") != track_id]
    tracks.insert(0, entry)
    # Enforce 125 cap — remove oldest beyond max
    max_v = int(get_config().get("max_videos") or _MAX_VIDEOS)
    if len(tracks) > max_v:
        for old in tracks[max_v:]:
            old["status"] = "evicted"
        tracks = tracks[:max_v]
    catalog["tracks"] = tracks
    _save_tracks(catalog)
    return entry


def list_tracks(user_id: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    catalog = _load_tracks()
    tracks = [t for t in (catalog.get("tracks") or []) if isinstance(t, dict) and t.get("status") != "evicted"]
    if user_id:
        tracks = [t for t in tracks if t.get("user_id") == user_id or t.get("status") == "completed"]
    tracks.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return {"success": True, "tracks": tracks[:limit], "count": len(tracks), "storage": get_storage_stats()}


def get_track(track_id: str) -> Optional[Dict[str, Any]]:
    catalog = _load_tracks()
    for t in catalog.get("tracks") or []:
        if t.get("id") == track_id:
            return t
    return None


def _encode_worker(
    track_id: str,
    user_id: str,
    title: str,
    genre: str,
    mood: str,
    duration: int,
    mode_id: Optional[str] = None,
) -> None:
    """Background worker: mode-aware lyrics → audio → video → sync."""
    mode, layers, duration, genre, mood = _resolve_mode_params(mode_id, title, genre, mood, duration)
    prompts = mode.get("prompts") or {}
    try:
        lyrics = ""
        structure = ""
        video_prompt = ""

        if layers["lyrics"]:
            lyrics = _run_llm_task(
                "lyrics",
                template_override=prompts.get("lyrics"),
                title=title, genre=genre, mood=mood,
            )
        if layers["audio"] or layers["video"]:
            structure = _run_llm_task(
                "music_structure",
                template_override=prompts.get("music_structure"),
                title=title, genre=genre, mood=mood,
            )
        if layers["video"]:
            video_prompt = _run_llm_task(
                "video_prompt",
                template_override=prompts.get("video_prompt"),
                title=title, genre=genre, mood=mood,
                lyrics_excerpt=lyrics[:300],
            )

        full_prompt = f"{mode.get('label') or 'Super Encode'} — {title} ({genre}). {video_prompt}"
        if lyrics:
            full_prompt += f"\n\nLyrics:\n{lyrics[:500]}"
        if structure:
            full_prompt += f"\n\nStructure:\n{structure[:400]}"

        audio_path = None
        if layers["audio"]:
            audio_path = _generate_audio(
                lyrics, track_id, title=title, genre=genre, duration=duration, mode=mode,
            )

        doc_id = ""
        sync_path = None
        video_path = None
        if layers["video"]:
            doc_id = _start_video_job(track_id, title, full_prompt, user_id, duration, mode=mode)
            from backend.services.video_generator_service import VIDEOS_DIR
            video_path = os.path.join(VIDEOS_DIR, f"{doc_id}.mp4")
            for _ in range(120):
                if os.path.isfile(video_path) and os.path.getsize(video_path) > 1024:
                    break
                time.sleep(5)

        if layers["sync"] and video_path and os.path.isfile(video_path):
            sync_path = _sync_encode(track_id, audio_path, video_path)

        if layers["lyrics"] and not layers["audio"] and not layers["video"]:
            status = "completed"
        elif sync_path:
            status = "completed"
        elif video_path and os.path.isfile(video_path):
            status = "completed" if not layers["sync"] else "processing"
        elif audio_path:
            status = "completed"
        else:
            status = "processing"

        _register_track(
            track_id, user_id, title, genre, mood, lyrics, doc_id,
            audio_path, sync_path, status=status, mode=mode, duration_sec=duration or None,
        )
        cfg = get_config()
        earn = float((cfg.get("encode") or {}).get("earn_on_finish_mn2") or 0.008)
        if earn > 0 and status == "completed":
            try:
                from backend.services.generator_mn2_service import _credit
                _credit(user_id, earn, "creator_encode_earn", {"track_id": track_id, "mode": mode.get("id")})
            except Exception:
                pass
    except Exception as exc:
        _register_track(
            track_id, user_id, title, genre, mood, "", "",
            None, None, status=f"failed: {exc}", mode=mode,
        )


def one_click_encode(
    user_id: str,
    title: str,
    genre: str = "electronic",
    mood: str = "energetic",
    duration: int = 60,
    pay_with_mn2: bool = True,
    mode_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    One-click Super Encode: charge MN2, spawn background worker for
    mode-specific lyrics + audio + video + synchronized mux.
    """
    cap_err = _enforce_storage_cap()
    if cap_err:
        return cap_err

    mode, layers, duration, genre, mood = _resolve_mode_params(mode_id, title, genre, mood, duration)
    cfg = get_config()
    encode_cfg = cfg.get("encode") or {}
    base_price = float(encode_cfg.get("one_click_mn2") or 0.15)
    price = float(mode.get("price_mn2") if mode.get("price_mn2") is not None else base_price)

    if pay_with_mn2 and price > 0:
        try:
            from backend.services.generator_mn2_service import _debit
            debit = _debit(user_id, price, {"source": "super_encoder", "title": title, "mode": mode.get("id")})
            if not debit.get("success"):
                return debit
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    track_id = f"trk_{uuid.uuid4().hex[:12]}"

    _register_track(
        track_id, user_id, title, genre, mood, "", "",
        None, None, status="queued", mode=mode, duration_sec=duration or None,
    )

    thread = threading.Thread(
        target=_encode_worker,
        args=(track_id, user_id, title, genre, mood, duration, mode.get("id")),
        daemon=True,
    )
    thread.start()

    layer_desc = []
    if layers["lyrics"]:
        layer_desc.append("lyrics")
    if layers["audio"]:
        layer_desc.append("audio")
    if layers["video"]:
        layer_desc.append("video")
    if layers["sync"]:
        layer_desc.append("sync")

    return {
        "success": True,
        "track_id": track_id,
        "status": "queued",
        "title": title,
        "genre": genre,
        "mood": mood,
        "mode": mode.get("id"),
        "mode_label": mode.get("label"),
        "mode_icon": mode.get("icon"),
        "duration_sec": duration,
        "price_mn2": price if pay_with_mn2 else 0,
        "layers": layers,
        "ai_routing": get_ai_status().get("ai_routing"),
        "progress_url": f"/api/creator/tracks/{track_id}",
        "message": f"{mode.get('label') or 'Super Encode'} started — {' → '.join(layer_desc) or 'processing'}.",
    }


def get_mobile_config() -> Dict[str, Any]:
    """Capacitor / PWA / store metadata for creator mobile shell."""
    cfg = get_config()
    mobile = cfg.get("mobile") if isinstance(cfg.get("mobile"), dict) else {}
    base = os.environ.get("PLATFORM_BASE_URL") or "https://masternoder.dk"
    base = base.rstrip("/")
    start_path = mobile.get("start_url") or "/creator/?app=creator-capacitor"
    return {
        "success": True,
        "app_name": cfg.get("app_name") or "MasterNoder Super Encoder",
        "app_version": mobile.get("app_version") or "1.0.0",
        "package_id": mobile.get("package_id") or "dk.masternoder.creator",
        "play_store_url": mobile.get("play_store_url") or "",
        "app_store_url": mobile.get("app_store_url") or "",
        "download_apk_url": f"{base}{mobile.get('download_apk_url') or '/static/downloads/masternoder-creator.apk'}",
        "download_apk_filename": mobile.get("download_apk_filename") or "masternoder-creator.apk",
        "distribution": "self_hosted",
        "manifest_url": f"{base}/creator/manifest.webmanifest",
        "start_url": f"{base}{start_path}" if start_path.startswith("/") else start_path,
        "landing_url": cfg.get("landing_url") or f"{base}/",
        "deep_link_base": f"{base}/creator/",
        "capacitor_app_param": "creator-capacitor",
        "pwa_app_param": "creator-pwa",
        "theme_color": mobile.get("theme_color") or "#1A1035",
        "max_videos": int(cfg.get("max_videos") or _MAX_VIDEOS),
        "rating": cfg.get("rating") or {},
        "encode": cfg.get("encode") or {},
        "encoder_modes": list_encoder_modes(),
    }
