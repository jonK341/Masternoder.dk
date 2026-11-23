"""
Big-win vertical clip export for TikTok / Reels (9:16 still → short MP4).

Renders a poster with Pillow, then encodes a few-second loop with ffmpeg
(system binary or imageio-ffmpeg). SVG vertical cards stay available via
casino_social_service.build_big_win_svg(aspect='vertical').
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CLIPS_DIR = os.path.join(
    os.environ.get("OUTPUT_DIR") or os.path.join(_BASE, "output"),
    "casino_clips",
)
_WIDTH = 1080
_HEIGHT = 1920
_DURATION_SEC = 4.0


def _iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _find_ffmpeg() -> Optional[str]:
    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _format_amount(net: float, currency: str) -> str:
    cur = (currency or "coins").lower()
    if cur == "coins":
        return f"{int(net):,} coins"
    if cur == "mn2":
        return f"{net:.4f} MN2"
    if cur == "usd":
        return f"${net:,.2f}"
    return f"{net:g} {cur}"


def render_vertical_poster(
    *,
    game: Optional[str] = None,
    net: float = 0,
    currency: str = "coins",
    multiplier: Optional[float] = None,
    handle: str = "Player",
) -> "Any":
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (_WIDTH, _HEIGHT), "#0b1020")
    draw = ImageDraw.Draw(img)
    # atmosphere
    for i, color in enumerate(("#141a33", "#1a0f2e", "#0d1a14")):
        y0 = int(_HEIGHT * (0.15 + i * 0.22))
        draw.rectangle([0, y0, _WIDTH, y0 + 180], fill=color)
    draw.rectangle([48, 48, _WIDTH - 48, _HEIGHT - 48], outline="#21d07a", width=6)

    def font(size: int):
        for name in ("Segoe UI Bold", "Segoe UI", "Arial", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                continue
        return ImageFont.load_default()

    game_label = (game or "casino").replace("_", " ").replace("-", " ").title()
    amount = _format_amount(float(net or 0), currency) if net else "Big win"
    mult_line = f"{float(multiplier):.1f}×" if multiplier and float(multiplier) >= 1 else "MasterNoder2"

    draw.text((90, 160), "BIG WIN CLIP", fill="#8ea0c8", font=font(42))
    draw.text((90, 280), "TIKTOK / REELS", fill="#7c5cff", font=font(36))
    draw.text((90, 520), str(handle)[:28], fill="#ffffff", font=font(72))
    draw.text((90, 720), amount[:36], fill="#21d07a", font=font(64))
    draw.text((90, 880), f"{game_label} · {mult_line}"[:40], fill="#c8d4ff", font=font(48))
    draw.text((90, 1600), "masternoder.dk/casino", fill="#8ea0c8", font=font(40))
    draw.text((90, 1700), "virtual coins · entertainment", fill="#64748B", font=font(32))
    # accent orb
    draw.ellipse([720, 1100, 980, 1360], fill="#21d07a")
    draw.text((790, 1190), "7×", fill="#0b1020", font=font(72))
    return img


def export_big_win_clip(
    *,
    user_id: str = "",
    game: Optional[str] = None,
    net: float = 0,
    currency: str = "coins",
    multiplier: Optional[float] = None,
    handle: Optional[str] = None,
    duration_sec: float = _DURATION_SEC,
) -> Dict[str, Any]:
    from backend.services import casino_social_service

    player = handle or (casino_social_service.anonymize_user(user_id) if user_id else "Player")
    digest = hashlib.sha256(
        f"{user_id}|{game}|{net}|{currency}|{multiplier}|{player}".encode("utf-8")
    ).hexdigest()[:12]
    stamp = _iso()
    os.makedirs(_CLIPS_DIR, exist_ok=True)
    stem = f"bigwin_{digest}_{stamp}"
    png_path = os.path.join(_CLIPS_DIR, f"{stem}.png")
    mp4_path = os.path.join(_CLIPS_DIR, f"{stem}.mp4")

    img = render_vertical_poster(
        game=game,
        net=float(net or 0),
        currency=currency or "coins",
        multiplier=float(multiplier) if multiplier is not None else None,
        handle=player,
    )
    img.save(png_path, "PNG")

    svg = casino_social_service.build_big_win_svg(
        game=game,
        net=net,
        currency=currency,
        multiplier=multiplier,
        handle=player,
        aspect="vertical",
    )
    svg_path = os.path.join(_CLIPS_DIR, f"{stem}.svg")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)

    ffmpeg = _find_ffmpeg()
    encoded = False
    encode_error = None
    if ffmpeg:
        cmd = [
            ffmpeg,
            "-y",
            "-loop",
            "1",
            "-i",
            png_path,
            "-t",
            str(max(2.0, min(float(duration_sec or _DURATION_SEC), 12.0))),
            "-vf",
            f"scale={_WIDTH}:{_HEIGHT}:force_original_aspect_ratio=decrease,pad={_WIDTH}:{_HEIGHT}:(ow-iw)/2:(oh-ih)/2",
            "-r",
            "30",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-movflags",
            "+faststart",
            mp4_path,
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
            encoded = proc.returncode == 0 and os.path.isfile(mp4_path)
            if not encoded:
                encode_error = (proc.stderr or proc.stdout or "ffmpeg_failed")[:400]
        except Exception as exc:
            encode_error = str(exc)[:400]
    else:
        encode_error = "ffmpeg_not_found"

    rel_png = f"/api/casino/share/big-win/clip/file/{os.path.basename(png_path)}"
    rel_mp4 = f"/api/casino/share/big-win/clip/file/{os.path.basename(mp4_path)}" if encoded else None
    rel_svg = f"/api/casino/share/big-win/card.svg?aspect=vertical&game={game or 'casino'}&net={net or 0}&currency={currency or 'coins'}"
    if multiplier:
        rel_svg += f"&mult={multiplier}"

    base = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")
    return {
        "success": True,
        "format": "tiktok",
        "width": _WIDTH,
        "height": _HEIGHT,
        "duration_sec": float(duration_sec or _DURATION_SEC),
        "poster_path": png_path,
        "mp4_path": mp4_path if encoded else None,
        "svg_path": svg_path,
        "poster_url": rel_png,
        "mp4_url": rel_mp4,
        "svg_url": rel_svg,
        "download_name": f"{stem}.mp4" if encoded else f"{stem}.png",
        "encoded": encoded,
        "encode_error": encode_error,
        "share_hint": "Post the MP4 to TikTok or Instagram Reels (9:16).",
        "absolute_mp4_url": f"{base}{rel_mp4}" if rel_mp4 else None,
    }


def resolve_clip_file(filename: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (absolute_path, mimetype) for a safe clip basename."""
    name = os.path.basename(filename or "")
    if not name or ".." in name or "/" in name or "\\" in name:
        return None, None
    path = os.path.join(_CLIPS_DIR, name)
    if not os.path.isfile(path):
        return None, None
    if name.endswith(".mp4"):
        return path, "video/mp4"
    if name.endswith(".png"):
        return path, "image/png"
    if name.endswith(".svg"):
        return path, "image/svg+xml"
    return None, None
