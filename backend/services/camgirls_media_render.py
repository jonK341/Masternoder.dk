"""Phase 2 — raster gallery stills (WebP) and helpers for preview encoding."""
from __future__ import annotations

import os
import struct
from typing import Tuple


def _hex_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = (hex_color or "#888888").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return struct.unpack(">BBB", bytes.fromhex(h[:6]))
    except (ValueError, struct.error):
        return (128, 128, 128)


def _blend(a: Tuple[int, int, int], b: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def render_gallery_webp(
    out_path: str,
    *,
    initials: str,
    c1: str,
    c2: str,
    variant: int,
    slug: str = "",
) -> bool:
    """Portrait-style still (640×480 WebP) — drop-in until real photos are added."""
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageFont
    except ImportError:
        return False

    w, h = 640, 480
    top = _hex_rgb(c1)
    bot = _hex_rgb(c2)
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        row = _blend(top, bot, t * 0.85 + 0.1)
        for x in range(w):
            px[x, y] = row

    draw = ImageDraw.Draw(img)
    # Bokeh orbs (variant shifts layout)
    orbs = [
        (120 + variant * 40, 80, 90),
        (480 - variant * 30, 120, 70),
        (360, 360, 110),
    ]
    for ox, oy, r in orbs:
        orb = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        od = ImageDraw.Draw(orb)
        od.ellipse((ox - r, oy - r, ox + r, oy + r), fill=(255, 255, 255, 35))
        orb = orb.filter(ImageFilter.GaussianBlur(radius=12))
        img = Image.alpha_composite(img.convert("RGBA"), orb).convert("RGB")
        draw = ImageDraw.Draw(img)

    # Vignette
    vig = Image.new("L", (w, h), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse((-80, -40, w + 80, h + 120), fill=220)
    vig = vig.filter(ImageFilter.GaussianBlur(radius=50))
    dark = Image.new("RGB", (w, h), (8, 10, 18))
    img = Image.composite(img, dark, vig)

    draw = ImageDraw.Draw(img)
    # Silhouette / portrait oval
    cx, cy = w // 2, int(h * 0.42) + variant * 6
    rx, ry = 95, 120
    skin = _blend((243, 213, 196), top, 0.15)
    draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=(18, 14, 24))
    draw.ellipse((cx - 54, cy - 70, cx + 54, cy + 78), fill=skin)
    hair = _blend((28, 16, 18), bot, 0.25)
    draw.pieslice((cx - 62, cy - 92, cx + 62, cy + 10), 200, 340, fill=hair)
    draw.ellipse((cx - 22, cy - 8, cx - 8, cy + 8), fill=(26, 18, 14))
    draw.ellipse((cx + 8, cy - 8, cx + 22, cy + 8), fill=(26, 18, 14))
    draw.arc((cx - 16, cy + 18, cx + 16, cy + 36), 20, 160, fill=(150, 70, 80), width=3)

    try:
        font = ImageFont.truetype("arial.ttf", 48)
        font_sm = ImageFont.truetype("arial.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
        font_sm = font

    labels = ("Studio still", "Profile shot", "Stage look", "Close-up")
    label = labels[variant - 1] if 1 <= variant <= len(labels) else "Still"
    init = (initials or "AI")[:3]
    bbox = draw.textbbox((0, 0), init, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((cx - tw // 2, cy - th // 2 - 4), init, fill=(245, 248, 255), font=font)
    draw.text((w // 2 - 60, h - 72), label, fill=(230, 235, 245), font=font_sm)
    if slug:
        draw.text((w // 2 - 70, h - 48), f"{slug} · MN2", fill=(180, 190, 210), font=font_sm)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    img.save(out_path, "WEBP", quality=82, method=4)
    return os.path.isfile(out_path) and os.path.getsize(out_path) > 200


def render_icon_webp(out_path: str, *, initials: str, c1: str, c2: str) -> bool:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False
    size = 128
    top, bot = _hex_rgb(c1), _hex_rgb(c2)
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        t = y / max(size - 1, 1)
        row = _blend(top, bot, t)
        for x in range(size):
            px[x, y] = row
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
    init = (initials or "AI")[:3]
    bbox = draw.textbbox((0, 0), init, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) // 2, (size - th) // 2 - 2), init, fill=(255, 255, 255), font=font)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    img.save(out_path, "WEBP", quality=85)
    return os.path.isfile(out_path)
