"""Generate PNG + GIF media for block-height trophies (plan 001 BM-U2)."""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _ffmpeg() -> Optional[str]:
    try:
        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except Exception:
        pass
    return shutil.which("ffmpeg")


def block_item_id(height: int) -> str:
    return f"block-{int(height)}"


def _paths(height: int) -> Dict[str, str]:
    stem = block_item_id(height)
    img_dir = os.path.join(_BASE, "static", "img", "trophies")
    clip_dir = os.path.join(_BASE, "static", "shop", "clips")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(clip_dir, exist_ok=True)
    return {
        "png": os.path.join(img_dir, f"{stem}.png"),
        "gif": os.path.join(img_dir, f"{stem}.gif"),
        "mp4": os.path.join(clip_dir, f"{stem}.mp4"),
        "png_url": f"/static/img/trophies/{stem}.png",
        "gif_url": f"/static/img/trophies/{stem}.gif",
        "clip_url": f"/static/shop/clips/{stem}.mp4",
    }


def _run(cmd: list, timeout: int = 120) -> bool:
    try:
        subprocess.run(cmd, check=True, timeout=timeout, capture_output=True)
        return True
    except Exception:
        return False


def ensure_block_media(height: int, *, duration: float = 3.0, force: bool = False) -> Dict[str, Any]:
    """Create block trophy poster PNG and ~3s GIF; update shop_item_media.json."""
    h = int(height)
    iid = block_item_id(h)
    paths = _paths(h)
    ffmpeg = _ffmpeg()

    from backend.services.shop_media_service import load_manifest, save_manifest

    manifest = load_manifest()
    existing = manifest.get(iid) or {}
    if not force and existing.get("gif_url") and existing.get("image_url"):
        if os.path.isfile(os.path.join(_BASE, existing["image_url"].lstrip("/"))):
            return {"success": True, "item_id": iid, "skipped": True, "media": existing}

    if not ffmpeg:
        return {"success": False, "error": "ffmpeg_not_available", "item_id": iid}

    label = f"Block #{h}"
    # Poster still — dark gradient + height label
    vf_still = (
        "drawtext=text='" + label + "':fontsize=48:fontcolor=white:"
        "x=(w-text_w)/2:y=(h-text_h)/2"
    )
    png_ok = _run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x0d1b2a:s=640x640:d=1",
            "-vf",
            vf_still,
            "-frames:v",
            "1",
            paths["png"],
        ],
        timeout=60,
    )
    if not png_ok or not os.path.isfile(paths["png"]):
        return {"success": False, "error": "png_generation_failed", "item_id": iid}

    frames = int(max(1, round(duration * 30)))
    vf_zoom = (
        f"scale=640:640,format=rgba,"
        f"zoompan=z='min(zoom+0.002,1.35)':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=640x640:fps=30"
    )
    mp4_ok = _run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-loop",
            "1",
            "-i",
            paths["png"],
            "-vf",
            vf_zoom,
            "-t",
            str(duration),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            paths["mp4"],
        ],
        timeout=120,
    )

    gif_ok = False
    if mp4_ok and os.path.isfile(paths["mp4"]):
        vf_gif = (
            "fps=12,scale=480:-1:flags=lanczos,split[s0][s1];"
            "[s0]palettegen=stats_mode=single[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5"
        )
        gif_ok = _run(
            [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                paths["mp4"],
                "-vf",
                vf_gif,
                "-loop",
                "0",
                paths["gif"],
            ],
            timeout=120,
        )

    entry = dict(existing)
    entry["image_url"] = paths["png_url"]
    entry["poster_url"] = paths["png_url"]
    if gif_ok and os.path.isfile(paths["gif"]):
        entry["gif_url"] = paths["gif_url"]
    if mp4_ok and os.path.isfile(paths["mp4"]):
        entry["clip_url"] = paths["clip_url"]
    entry["clip_duration_s"] = duration
    entry["block_height"] = h
    entry["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    manifest[iid] = entry
    save_manifest(manifest)

    return {
        "success": True,
        "item_id": iid,
        "height": h,
        "image_url": entry.get("image_url"),
        "gif_url": entry.get("gif_url"),
        "clip_url": entry.get("clip_url"),
        "skipped": False,
    }
