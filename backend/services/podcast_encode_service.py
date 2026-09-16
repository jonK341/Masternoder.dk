"""Podcast encode profiles — broadcast-grade AI audio encoder via FFmpeg."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

AUDIO_ENCODE_PROFILES: Dict[str, Dict[str, Any]] = {
    "standard": {
        "codec": "libmp3lame",
        "bitrate": "128k",
        "sample_rate": 44100,
        "channels": 2,
        "format": "mp3",
        "filter_chain": "highpass=f=80",
        "description": "Standard podcast — 128 kbps MP3, light high-pass.",
    },
    "premium": {
        "codec": "libmp3lame",
        "bitrate": "192k",
        "sample_rate": 48000,
        "channels": 2,
        "format": "mp3",
        "filter_chain": "highpass=f=80,acompressor=threshold=-18dB:ratio=3:attack=5:release=50,loudnorm=I=-16:TP=-1.5:LRA=11",
        "description": "Premium — compression + EBU R128 loudnorm.",
    },
    "ultra": {
        "codec": "libmp3lame",
        "bitrate": "320k",
        "sample_rate": 48000,
        "channels": 2,
        "format": "mp3",
        "filter_chain": "highpass=f=80,afftdn=nf=-25,acompressor=threshold=-16dB:ratio=4:attack=3:release=80,loudnorm=I=-14:TP=-1:LRA=9",
        "description": "Ultra MP3 — noise reduction + broadcast loudnorm.",
    },
    "broadcast": {
        "codec": "aac",
        "bitrate": "256k",
        "sample_rate": 48000,
        "channels": 2,
        "format": "m4a",
        "filter_chain": "highpass=f=80,afftdn=nf=-25,acompressor=threshold=-16dB:ratio=4:attack=3:release=80,loudnorm=I=-16:TP=-1.5:LRA=11",
        "description": "Broadcast AAC 256k — Apple/Spotify-ready M4A.",
    },
    "studio": {
        "codec": "aac",
        "bitrate": "320k",
        "sample_rate": 48000,
        "channels": 2,
        "format": "m4a",
        "filter_chain": "highpass=f=70,afftdn=nf=-28,deesser=i=0.5,acompressor=threshold=-14dB:ratio=5:attack=2:release=100,loudnorm=I=-14:TP=-0.5:LRA=8,stereotools=mlev=0.015625:slev=0.015625:sbal=0",
        "description": "Studio grade — de-ess, stereo polish, tight loudnorm.",
    },
    "opus_web": {
        "codec": "libopus",
        "bitrate": "128k",
        "sample_rate": 48000,
        "channels": 2,
        "format": "opus",
        "filter_chain": "highpass=f=80,acompressor=threshold=-18dB:ratio=3,loudnorm=I=-16:TP=-1.5:LRA=11",
        "description": "Opus 128k — low-latency web streaming.",
    },
}

VALID_AUDIO_PROFILES = frozenset(AUDIO_ENCODE_PROFILES.keys())
_AAC_CODEC_CACHE: Optional[str] = None


def _ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg") or "ffmpeg"


def _detect_aac_codec() -> str:
    global _AAC_CODEC_CACHE
    if _AAC_CODEC_CACHE:
        return _AAC_CODEC_CACHE
    for codec in ("aac", "libfdk_aac"):
        try:
            ff = _ffmpeg_exe()
            out = subprocess.run(
                [ff, "-hide_banner", "-encoders"],
                capture_output=True, text=True, timeout=12,
            )
            text = (out.stdout or "") + (out.stderr or "")
            if codec in text:
                _AAC_CODEC_CACHE = codec
                return codec
        except Exception:
            pass
    _AAC_CODEC_CACHE = "aac"
    return "aac"


def _resolve_codec(cfg: Dict[str, Any]) -> Tuple[str, str]:
    codec = cfg.get("codec", "libmp3lame")
    fmt = cfg.get("format", "mp3")
    if codec == "aac":
        return _detect_aac_codec(), fmt
    return codec, fmt


def _output_ext(fmt: str) -> str:
    return {"m4a": ".m4a", "opus": ".opus", "mp3": ".mp3"}.get(fmt, ".mp3")


def list_encode_profiles() -> List[Dict[str, Any]]:
    return [{"id": k, **v} for k, v in AUDIO_ENCODE_PROFILES.items()]


def encode_audio_file(
    input_path: str,
    output_path: str,
    profile: str = "standard",
    *,
    apply_filters: bool = True,
) -> Dict[str, Any]:
    prof = profile if profile in VALID_AUDIO_PROFILES else "standard"
    cfg = AUDIO_ENCODE_PROFILES[prof]
    if not os.path.isfile(input_path):
        return {"success": False, "error": "input_not_found", "input_path": input_path}

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    ff = _ffmpeg_exe()
    codec, fmt = _resolve_codec(cfg)

    cmd = [ff, "-y", "-i", input_path]
    if apply_filters and cfg.get("filter_chain"):
        cmd.extend(["-af", cfg["filter_chain"]])
    cmd.extend([
        "-acodec", codec,
        "-b:a", cfg["bitrate"],
        "-ar", str(cfg["sample_rate"]),
        "-ac", str(cfg.get("channels", 2)),
    ])
    if fmt == "m4a":
        cmd.extend(["-movflags", "+faststart"])
    cmd.append(output_path)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if proc.returncode != 0 or not os.path.isfile(output_path):
            # Fallback: simpler chain without optional filters (stereotools/deesser)
            simple = cfg.get("filter_chain", "").split(",")
            simple = [f for f in simple if "stereotools" not in f and "deesser" not in f]
            fallback_chain = ",".join(simple) if simple else "loudnorm=I=-16:TP=-1.5:LRA=11"
            cmd2 = [ff, "-y", "-i", input_path, "-af", fallback_chain,
                    "-acodec", codec, "-b:a", cfg["bitrate"],
                    "-ar", str(cfg["sample_rate"]), "-ac", str(cfg.get("channels", 2)), output_path]
            proc2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=600)
            if proc2.returncode != 0 or not os.path.isfile(output_path):
                return {
                    "success": False,
                    "error": "encode_failed",
                    "stderr": (proc.stderr or proc2.stderr or "")[-500:],
                }
        return {
            "success": True,
            "output_path": output_path,
            "profile": prof,
            "codec": codec,
            "format": fmt,
            "size_bytes": os.path.getsize(output_path),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_episode_audio(
    script: str,
    *,
    profile: str = "standard",
    dest_dir: Optional[str] = None,
    episode_id: Optional[str] = None,
) -> Dict[str, Any]:
    text = (script or "").strip()
    if not text:
        return {"success": False, "error": "empty_script"}

    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out_dir = dest_dir or os.path.join(base, "static", "audio", "podcast", "generated")
    os.makedirs(out_dir, exist_ok=True)
    eid = episode_id or f"gen-{int(time.time())}"
    prof = profile if profile in VALID_AUDIO_PROFILES else "standard"
    ext = _output_ext(AUDIO_ENCODE_PROFILES[prof].get("format", "mp3"))
    raw_path = os.path.join(tempfile.gettempdir(), f"podcast_raw_{eid}.wav")
    final_path = os.path.join(out_dir, f"{eid}{ext}")

    try:
        from backend.services.tts_service import generate_speech
        tts_path = generate_speech(text[:8000])
        if not tts_path or not os.path.isfile(tts_path):
            return {"success": False, "error": "tts_failed"}
        shutil.copy2(tts_path, raw_path)
    except Exception as e:
        return {"success": False, "error": f"tts_error:{e}"}

    if prof in ("premium", "ultra", "broadcast", "studio"):
        try:
            from backend.services.audio_enhancement_service import enhance_audio
            enhanced = enhance_audio(raw_path)
            if enhanced and os.path.isfile(enhanced):
                raw_path = enhanced
        except Exception:
            pass

    enc = encode_audio_file(raw_path, final_path, prof)
    if not enc.get("success"):
        return enc

    word_count = len(text.split())
    duration_est = max(30, int(word_count / 2.5))
    rel_path = final_path.replace("\\", "/")
    if "/static/" in rel_path:
        rel_path = "/static/" + rel_path.split("/static/", 1)[1]

    return {
        "success": True,
        "audio_path": final_path,
        "audio_url": rel_path,
        "profile": prof,
        "codec": enc.get("codec"),
        "format": enc.get("format"),
        "duration_sec_estimate": duration_est,
        "size_bytes": enc.get("size_bytes"),
    }
