"""Podcast audio — verify, generate fallbacks, stream episodes."""
from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import wave
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_AUDIO_DIR = os.path.join(_BASE, "static", "audio", "podcast")


def _ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg") or "ffmpeg"


def _episode_path(episode_id: str, ext: str = ".mp3") -> str:
    return os.path.join(_AUDIO_DIR, f"{episode_id}{ext}")


def _file_ok(path: str, min_bytes: int = 500) -> bool:
    return os.path.isfile(path) and os.path.getsize(path) >= min_bytes


def _write_wav_tone(path: str, duration_sec: float = 4.0, freq: float = 220.0) -> bool:
    """Minimal WAV tone when TTS/ffmpeg unavailable."""
    return _write_bbcg_flavor_tone(path, duration_sec=duration_sec, primary_freq=freq)


def _write_bbcg_flavor_tone(
    path: str,
    duration_sec: float = 5.0,
    primary_freq: float = 196.0,
) -> bool:
    """Blue Bubble Cheese Gum chord — blue bubble highs + cheese-gold mid."""
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        rate = 44100
        n = int(rate * duration_sec)
        freqs = [primary_freq, primary_freq * 1.25, primary_freq * 1.5, primary_freq * 2.0]
        weights = [0.45, 0.3, 0.15, 0.1]
        with wave.open(path, "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            for i in range(n):
                t = i / rate
                envelope = min(1.0, t * 6, (duration_sec - t) * 6)
                bubble = math.sin(2 * math.pi * 3.5 * t) * 0.08
                sample_f = sum(
                    wgt * math.sin(2 * math.pi * f * t + bubble)
                    for f, wgt in zip(freqs, weights)
                )
                sample = int(14000 * envelope * sample_f)
                sample = max(-32767, min(32767, sample))
                w.writeframes(struct.pack("<h", sample))
        return _file_ok(path, 100)
    except Exception:
        return False


def probe_audio_file(path: Optional[str]) -> Dict[str, Any]:
    """Return size, format, estimated duration for a file on disk."""
    if not path or not _file_ok(path, 1):
        return {"ok": False}
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    size = os.path.getsize(path)
    duration_sec = None
    try:
        if ext == "wav":
            with wave.open(path, "r") as w:
                duration_sec = round(w.getnframes() / float(w.getframerate()), 2)
        elif ext == "mp3":
            duration_sec = round(size / 16000.0, 2)
    except Exception:
        pass
    return {
        "ok": True,
        "path": path,
        "format": ext or "unknown",
        "bytes": size,
        "duration_sec": duration_sec,
        "bbcg_flavor": True,
    }


def _wav_to_mp3(wav_path: str, mp3_path: str) -> bool:
    ff = _ffmpeg_exe()
    try:
        proc = subprocess.run(
            [ff, "-y", "-i", wav_path, "-acodec", "libmp3lame", "-b:a", "128k", mp3_path],
            capture_output=True, text=True, timeout=120,
        )
        return proc.returncode == 0 and _file_ok(mp3_path)
    except Exception:
        return False


def ensure_episode_audio(episode: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure episode has playable audio on disk.
    TTS script → encode; else tone intro WAV → MP3.
    """
    eid = str(episode.get("id") or "").strip()
    if not eid:
        return {"success": False, "error": "no_episode_id"}

    configured = (episode.get("audio_url") or "").split("?")[0]
    if configured.startswith("/static/"):
        disk = os.path.join(_BASE, configured.lstrip("/").replace("/", os.sep))
        if _file_ok(disk):
            return {"success": True, "path": disk, "source": "configured", "format": "mp3"}

    mp3_path = _episode_path(eid, ".mp3")
    if _file_ok(mp3_path):
        return {"success": True, "path": mp3_path, "source": "cached", "format": "mp3"}

    title = episode.get("title") or eid
    desc = episode.get("description") or ""
    script = (
        f"Welcome to MasterNoder Podcast. {title}. "
        f"{desc[:400]} "
        f"This episode is brought to you with blue bubble cheese gum flavor audio. "
        f"Thanks for listening."
    )

    try:
        from backend.services.podcast_encode_service import generate_episode_audio
        gen = generate_episode_audio(
            script,
            profile=episode.get("encode_profile") or "premium",
            episode_id=eid,
            dest_dir=_AUDIO_DIR,
        )
        if gen.get("success") and gen.get("audio_path") and _file_ok(gen["audio_path"]):
            return {"success": True, "path": gen["audio_path"], "source": "tts_encode", "format": gen.get("format", "mp3")}
    except Exception:
        pass

    wav_path = _episode_path(eid, ".wav")
    if _write_bbcg_flavor_tone(wav_path, duration_sec=5.0, primary_freq=196.0):
        if _wav_to_mp3(wav_path, mp3_path):
            return {"success": True, "path": mp3_path, "source": "tone_fallback", "format": "mp3"}
        if _file_ok(wav_path):
            return {"success": True, "path": wav_path, "source": "tone_wav", "format": "wav"}

    return {"success": False, "error": "audio_generation_failed", "episode_id": eid}


def check_episode_audio(episode: Dict[str, Any]) -> Dict[str, Any]:
    eid = episode.get("id", "")
    configured = (episode.get("audio_url") or "").split("?")[0]
    disk = None
    if configured.startswith("/static/"):
        disk = os.path.join(_BASE, configured.lstrip("/").replace("/", os.sep))
    mp3 = _episode_path(eid, ".mp3")
    wav = _episode_path(eid, ".wav")

    status = "missing"
    path = None
    for p, label in ((disk, "configured"), (mp3, "generated_mp3"), (wav, "generated_wav")):
        if p and _file_ok(p):
            status = "ok"
            path = p
            break

    meta = probe_audio_file(path) if path else {"ok": False}
    return {
        "episode_id": eid,
        "status": status,
        "path": path,
        "play_url": f"/api/podcast/episodes/{eid}/audio",
        "configured_url": configured or None,
        "format": meta.get("format"),
        "bytes": meta.get("bytes"),
        "duration_sec": meta.get("duration_sec"),
        "bbcg_flavor": True,
    }


def sound_check_all(repair: bool = True) -> Dict[str, Any]:
    from backend.services.podcast_service import get_episodes
    results = []
    ok = 0
    missing = 0
    for ep in get_episodes():
        chk = check_episode_audio(ep)
        if chk["status"] == "ok":
            ok += 1
        else:
            missing += 1
            if repair:
                ensured = ensure_episode_audio(ep)
                chk["repair"] = ensured
                if ensured.get("success"):
                    chk["status"] = "repaired"
                    ok += 1
                    missing -= 1
        results.append(chk)
    return {
        "success": True,
        "total": len(results),
        "ok": ok,
        "missing": missing,
        "episodes": results,
        "audio_dir": _AUDIO_DIR,
    }


def get_sound_lab() -> Dict[str, Any]:
    """Deep sound diagnostics for Sound Lab panel."""
    from backend.services.podcast_service import get_episodes
    eps = get_episodes()
    rows = []
    total_bytes = 0
    for ep in eps:
        chk = check_episode_audio(ep)
        if chk.get("bytes"):
            total_bytes += int(chk["bytes"])
        rows.append({
            **chk,
            "title": ep.get("title"),
            "encode_profile": ep.get("encode_profile"),
        })
    ok = sum(1 for r in rows if r.get("status") == "ok")
    return {
        "success": True,
        "flavor": "blue_bubble_cheese_gum",
        "total": len(rows),
        "ok": ok,
        "missing": len(rows) - ok,
        "total_bytes": total_bytes,
        "audio_dir": _AUDIO_DIR,
        "ffmpeg": _ffmpeg_exe(),
        "episodes": rows,
        "features": [
            "bbcg_flavor_synth",
            "tts_encode_fallback",
            "stream_repair",
            "range_requests",
            "visualizer",
            "playback_speed",
            "queue",
            "chapters",
            "transcript",
            "rss_feed",
        ],
    }


def stream_episode_path(episode_id: str) -> Optional[str]:
    from backend.services.podcast_service import get_episode
    ep = get_episode(episode_id)
    if not ep:
        return None
    chk = check_episode_audio(ep)
    if chk["status"] == "ok" and chk.get("path"):
        return chk["path"]
    ensured = ensure_episode_audio(ep)
    if ensured.get("success"):
        return ensured.get("path")
    return None
