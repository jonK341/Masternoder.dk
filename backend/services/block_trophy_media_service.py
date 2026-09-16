"""Generate smiley PNG + animated GIF for block-height trophies (plan 004)."""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SMILEY_PALETTES: List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]] = [
    ((255, 214, 0), (255, 120, 0)),
    ((255, 235, 59), (255, 87, 34)),
    ((255, 193, 7), (244, 67, 54)),
    ((255, 238, 88), (255, 152, 0)),
    ((255, 241, 118), (255, 64, 129)),
    ((255, 213, 79), (156, 39, 176)),
    ((255, 202, 40), (63, 81, 181)),
]


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


def _palette_for_height(height: int) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    idx = int(hashlib.sha256(f"smiley-palette|{height}".encode()).hexdigest(), 16) % len(SMILEY_PALETTES)
    return SMILEY_PALETTES[idx]


def _palette_for_edition(
    edition_key: str,
    block_height: int,
    battle_stats: Optional[Dict[str, Any]] = None,
) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    mood = (battle_stats or {}).get("mood") or "neutral"
    rarity = (battle_stats or {}).get("rarity") or "common"
    seed = f"edition-palette|{edition_key}|{block_height}|{mood}|{rarity}"
    idx = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(SMILEY_PALETTES)
    base = SMILEY_PALETTES[idx]
    if rarity in ("legendary", "epic"):
        return ((min(255, base[0][0] + 20), base[0][1], base[0][2]), base[1])
    return base


def _safe_edition_filename(edition_key: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (edition_key or "edition"))
    return safe[:120] or "edition"


def _draw_smiley_frame(
    size: int,
    face: Tuple[int, int, int],
    accent: Tuple[int, int, int],
    *,
    frame_idx: int,
    block_height: int,
    edition_label: str = "",
    mood: str = "neutral",
) -> "Any":
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (13, 27, 42, 255))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    radius = int(size * 0.34)

    draw.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        fill=face + (255,),
        outline=accent + (255,),
        width=max(3, size // 80),
    )

    eye_y = cy - radius // 3
    eye_dx = radius // 2
    eye_r = max(6, radius // 8)
    wink = frame_idx % 8 == 3

    if wink:
        draw.line((cx - eye_dx - eye_r, eye_y, cx - eye_dx + eye_r, eye_y), fill=(40, 30, 20, 255), width=max(3, eye_r // 2))
        draw.ellipse((cx + eye_dx - eye_r, eye_y - eye_r, cx + eye_dx + eye_r, eye_y + eye_r), fill=(40, 30, 20, 255))
    else:
        for ex in (cx - eye_dx, cx + eye_dx):
            draw.ellipse((ex - eye_r, eye_y - eye_r, ex + eye_r, eye_y + eye_r), fill=(40, 30, 20, 255))

    mood_modes = {
        "happy": ("smile", "grin", "beam", "smile"),
        "fierce": ("grin", "open", "grin", "flat"),
        "calm": ("flat", "smile", "flat", "smile"),
        "lucky": ("beam", "open", "grin", "smile"),
    }
    mouth_modes = mood_modes.get(mood, ("smile", "grin", "open", "smile", "flat", "grin", "smile", "beam"))
    mouth = mouth_modes[frame_idx % len(mouth_modes)]
    mouth_y = cy + radius // 3
    mouth_w = radius
    if mouth == "grin":
        draw.arc(
            (cx - mouth_w, mouth_y - mouth_w // 2, cx + mouth_w, mouth_y + mouth_w),
            start=10,
            end=170,
            fill=(40, 30, 20, 255),
            width=max(4, radius // 10),
        )
        draw.rectangle((cx - mouth_w // 2, mouth_y, cx + mouth_w // 2, mouth_y + mouth_w // 3), fill=(180, 60, 60, 220))
    elif mouth == "open":
        draw.ellipse(
            (cx - mouth_w // 2, mouth_y - mouth_w // 4, cx + mouth_w // 2, mouth_y + mouth_w // 2),
            fill=(120, 30, 30, 255),
        )
    elif mouth == "flat":
        draw.line((cx - mouth_w // 2, mouth_y, cx + mouth_w // 2, mouth_y), fill=(40, 30, 20, 255), width=max(3, radius // 12))
    else:
        draw.arc(
            (cx - mouth_w, mouth_y - mouth_w // 2, cx + mouth_w, mouth_y + mouth_w),
            start=15,
            end=165,
            fill=(40, 30, 20, 255),
            width=max(4, radius // 10),
        )

    label = edition_label or f"#{block_height}"
    draw.text((12, size - 28), label[:18], fill=(200, 230, 255, 220))
    badge = "AI"
    draw.rectangle((size - 44, 10, size - 10, 34), fill=accent + (200,))
    draw.text((size - 38, 12), badge, fill=(255, 255, 255, 255))
    return img


def _edition_paths(edition_key: str) -> Dict[str, str]:
    stem = _safe_edition_filename(edition_key)
    img_dir = os.path.join(_BASE, "static", "img", "trophies", "editions")
    os.makedirs(img_dir, exist_ok=True)
    return {
        "png": os.path.join(img_dir, f"{stem}.png"),
        "gif": os.path.join(img_dir, f"{stem}.gif"),
        "png_url": f"/static/img/trophies/editions/{stem}.png",
        "gif_url": f"/static/img/trophies/editions/{stem}.gif",
    }


def _generate_edition_gif_pil(
    edition_key: str,
    block_height: int,
    gif_path: str,
    png_path: str,
    *,
    battle_stats: Optional[Dict[str, Any]] = None,
    license_number: str = "",
    frames: int = 8,
) -> bool:
    try:
        from PIL import Image
    except ImportError:
        return False

    face, accent = _palette_for_edition(edition_key, block_height, battle_stats)
    mood = (battle_stats or {}).get("mood") or "neutral"
    serial = (battle_stats or {}).get("serial_number") or ""
    label = serial or (license_number[:14] if license_number else f"#{block_height}")
    size = 480
    images: List[Image.Image] = []
    for i in range(frames):
        frame = _draw_smiley_frame(
            size,
            face,
            accent,
            frame_idx=i,
            block_height=block_height,
            edition_label=label,
            mood=mood,
        )
        images.append(frame.convert("P", palette=Image.ADAPTIVE))

    if not images:
        return False

    images[0].save(png_path, format="PNG")
    images[0].save(
        gif_path,
        save_all=True,
        append_images=images[1:],
        duration=120,
        loop=0,
        disposal=2,
    )
    return os.path.isfile(gif_path) and os.path.isfile(png_path)


def ensure_edition_media(
    edition_key: str,
    block_height: int,
    *,
    battle_stats: Optional[Dict[str, Any]] = None,
    license_number: str = "",
    edition_no: int = 1,
    force: bool = False,
) -> Dict[str, Any]:
    """Create a unique AI smiley GIF per trophy edition (not shared per block)."""
    ekey = (edition_key or "").strip()
    if not ekey:
        return {"success": False, "error": "missing_edition_key"}

    h = int(block_height)
    paths = _edition_paths(ekey)
    if not force and os.path.isfile(paths["gif"]) and os.path.isfile(paths["png"]):
        return {
            "success": True,
            "edition_key": ekey,
            "block_height": h,
            "gif_url": paths["gif_url"],
            "image_url": paths["png_url"],
            "skipped": True,
            "per_edition": True,
            "ai_generated": True,
        }

    ok = _generate_edition_gif_pil(
        ekey,
        h,
        paths["gif"],
        paths["png"],
        battle_stats=battle_stats,
        license_number=license_number,
    )
    if not ok:
        fallback = ensure_block_media(h, force=False)
        if fallback.get("success"):
            return {
                "success": True,
                "edition_key": ekey,
                "block_height": h,
                "gif_url": fallback.get("gif_url"),
                "image_url": fallback.get("image_url"),
                "skipped": True,
                "per_edition": False,
                "fallback_block_media": True,
            }
        return {"success": False, "error": "edition_media_generation_failed", "edition_key": ekey}

    return {
        "success": True,
        "edition_key": ekey,
        "edition_no": edition_no,
        "block_height": h,
        "gif_url": paths["gif_url"],
        "image_url": paths["png_url"],
        "skipped": False,
        "per_edition": True,
        "ai_generated": True,
        "mood": (battle_stats or {}).get("mood"),
        "rarity": (battle_stats or {}).get("rarity"),
    }


def _generate_smiley_gif_pil(height: int, gif_path: str, png_path: str, *, frames: int = 8) -> bool:
    try:
        from PIL import Image
    except ImportError:
        return False

    face, accent = _palette_for_height(height)
    size = 480
    images: List[Image.Image] = []
    for i in range(frames):
        frame = _draw_smiley_frame(size, face, accent, frame_idx=i, block_height=height)
        images.append(frame.convert("P", palette=Image.ADAPTIVE))

    if not images:
        return False

    images[0].save(
        png_path,
        format="PNG",
    )
    images[0].save(
        gif_path,
        save_all=True,
        append_images=images[1:],
        duration=130,
        loop=0,
        disposal=2,
    )
    return os.path.isfile(gif_path) and os.path.isfile(png_path)


def ensure_block_media(height: int, *, duration: float = 3.0, force: bool = False) -> Dict[str, Any]:
    """Create AI smiley poster PNG and animated GIF; update shop_item_media.json."""
    h = int(height)
    iid = block_item_id(h)
    paths = _paths(h)

    from backend.services.shop_media_service import load_manifest, save_manifest

    manifest = load_manifest()
    existing = manifest.get(iid) or {}
    if not force and existing.get("gif_url") and existing.get("image_url"):
        if os.path.isfile(os.path.join(_BASE, existing["image_url"].lstrip("/"))):
            return {"success": True, "item_id": iid, "skipped": True, "media": existing}

    gif_ok = _generate_smiley_gif_pil(h, paths["gif"], paths["png"])
    if not gif_ok:
        ffmpeg = _ffmpeg()
        if not ffmpeg:
            return {"success": False, "error": "media_generation_unavailable", "item_id": iid}
        label = f"Block #{h} :-)"
        vf_still = (
            "drawtext=text='" + label + "':fontsize=48:fontcolor=yellow:"
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
        if not png_ok:
            return {"success": False, "error": "png_generation_failed", "item_id": iid}
        gif_ok = False

    mp4_ok = False
    ffmpeg = _ffmpeg()
    if ffmpeg and os.path.isfile(paths["png"]):
        frames = int(max(1, round(duration * 30)))
        vf_zoom = (
            f"scale=640:640,format=rgba,"
            f"zoompan=z='min(zoom+0.002,1.2)':d={frames}:"
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
        if not gif_ok and mp4_ok:
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
    entry["media_kind"] = "block_smiley_trophy"
    entry["ai_generated"] = True
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
        "ai_smiley": True,
    }
