"""Generator encode profiles — CRF presets (E8), hardware encode (E1), MoviePy write kwargs."""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any, Dict, Optional, Tuple

# CRF ladder: lower = higher quality / slower encode
ENCODE_CRF: Dict[str, int] = {
    "fast_ai": 28,
    "standard": 26,
    "premium": 23,
    "ultra": 18,
}

ENCODE_PRESET: Dict[str, str] = {
    "fast_ai": "ultrafast",
    "standard": "veryfast",
    "premium": "medium",
    "ultra": "slow",
}

ENCODE_FPS: Dict[str, int] = {
    "fast_ai": 16,
    "standard": 20,
    "premium": 24,
    "ultra": 24,
}

VALID_PROFILES = frozenset(ENCODE_CRF.keys())

_HW_CODEC_CACHE: Optional[Tuple[str, str]] = None  # (codec, quality_flag)


def _ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg") or "ffmpeg"


def detect_hardware_encoder(force_refresh: bool = False) -> Optional[Tuple[str, str]]:
    """
    Detect best hardware H.264 encoder via ffmpeg -encoders.
    Returns (codec, quality_param_name) e.g. ('h264_nvenc', 'cq') or None.
    """
    global _HW_CODEC_CACHE
    if _HW_CODEC_CACHE is not None and not force_refresh:
        return _HW_CODEC_CACHE

    flag = (os.environ.get("GENERATOR_HW_ENCODE") or "auto").strip().lower()
    if flag in ("0", "false", "off", "no"):
        _HW_CODEC_CACHE = None
        return None

    candidates = [
        ("h264_nvenc", "cq"),
        ("h264_qsv", "global_quality"),
        ("h264_vaapi", "qp"),
        ("h264_amf", "qp_i"),
    ]
    try:
        ff = _ffmpeg_exe()
        out = subprocess.run(
            [ff, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=12,
        )
        text = (out.stdout or "") + (out.stderr or "")
        for codec, qparam in candidates:
            if codec in text:
                _HW_CODEC_CACHE = (codec, qparam)
                return _HW_CODEC_CACHE
    except Exception:
        pass
    _HW_CODEC_CACHE = None
    return None


def hardware_encode_status() -> Dict[str, Any]:
    """Public status for ops / generation-health."""
    detected = detect_hardware_encoder()
    flag = (os.environ.get("GENERATOR_HW_ENCODE") or "auto").strip().lower()
    return {
        "enabled": flag not in ("0", "false", "off", "no"),
        "mode": flag,
        "codec": detected[0] if detected else None,
        "quality_param": detected[1] if detected else None,
    }


def resolve_encode_profile(config: Optional[Dict[str, Any]] = None) -> str:
    """Pick encode profile from explicit config, quality_mode, or MN2 tier."""
    cfg = dict(config or {})
    explicit = str(cfg.get("encode_profile") or "").strip().lower()
    if explicit in VALID_PROFILES:
        return explicit

    qm = str(cfg.get("quality_mode") or "").strip().lower()
    if qm == "fast":
        return "fast_ai"
    if qm == "high":
        return "premium"
    if qm in ("best", "max", "ultra"):
        return "ultra"

    tier = str(cfg.get("mn2_tier") or cfg.get("tier") or "").strip().lower()
    if tier == "express":
        return "fast_ai"
    if tier == "premium":
        return "premium"
    if tier == "ultra":
        return "ultra"

    is_prod = os.environ.get("FLASK_ENV", "").strip().lower() not in ("development", "dev", "")
    return "fast_ai" if is_prod else "standard"


def is_fast_encode_profile(profile: str) -> bool:
    return str(profile or "").strip().lower() in ("fast_ai", "standard")


def encode_profile_public() -> Dict[str, Any]:
    """Public table for ops / agent tools."""
    rows = []
    hw = hardware_encode_status()
    for key in ("fast_ai", "standard", "premium", "ultra"):
        rows.append({
            "profile": key,
            "crf": ENCODE_CRF[key],
            "preset": ENCODE_PRESET[key],
            "fps": ENCODE_FPS[key],
            "resolution_hint": "854x480" if is_fast_encode_profile(key) else "1280x768+",
        })
    return {
        "success": True,
        "profiles": rows,
        "default": "fast_ai",
        "hardware_encode": hw,
    }


def _apply_hardware_codec(kwargs: Dict[str, Any], profile: str) -> Dict[str, Any]:
    """Swap libx264 for NVENC/QSV when available (E1)."""
    hw = detect_hardware_encoder()
    if not hw:
        return kwargs
    codec, qparam = hw
    crf = ENCODE_CRF.get(profile, 28)
    out = dict(kwargs)
    out["codec"] = codec
    params = [qparam, str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    if codec == "h264_nvenc":
        params = ["-preset", "p4", qparam, str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    elif codec == "h264_qsv":
        params = ["-global_quality", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    out["ffmpeg_params"] = params
    out.pop("preset", None)
    out["hw_encode"] = codec
    return out


def moviepy_write_kwargs(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Strip internal keys before passing to MoviePy write_videofile."""
    return {k: v for k, v in raw.items() if k != "hw_encode"}


def build_write_kwargs(
    doc_id: str,
    profile: str,
    *,
    add_audio: bool = True,
    videos_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """MoviePy write_videofile kwargs with CRF mapped to encode_profile."""
    prof = str(profile or "fast_ai").strip().lower()
    if prof not in VALID_PROFILES:
        prof = "fast_ai"
    crf = ENCODE_CRF[prof]
    kwargs: Dict[str, Any] = {
        "fps": ENCODE_FPS[prof],
        "codec": "libx264",
        "audio": add_audio,
        "logger": None,
        "preset": ENCODE_PRESET[prof],
        "ffmpeg_params": [
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
        ],
    }
    if add_audio and videos_dir:
        kwargs["audio_codec"] = "aac"
        kwargs["temp_audiofile"] = os.path.join(videos_dir, f"{doc_id}_temp_audio.mp4")
    kwargs = _apply_hardware_codec(kwargs, prof)
    return kwargs
