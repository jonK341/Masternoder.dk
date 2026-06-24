#!/usr/bin/env python3
"""Build Discord Developer Portal assets (icon + banner PNG/GIF)."""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "discord-branding"
OUT.mkdir(parents=True, exist_ok=True)

# MasterNoder palette
PRIMARY = (0, 255, 136)
SECONDARY = (0, 212, 255)
GOLD = (255, 215, 0)
ACCENT = (255, 107, 157)
BG_TOP = (12, 14, 28)
BG_BOTTOM = (4, 32, 36)


def _load_font(size: int, *, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates += [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    else:
        candidates += [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _radial_bg(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), BG_TOP)
    draw = ImageDraw.Draw(img)
    cx = cy = size // 2
    for r in range(size // 2, 0, -2):
        t = r / (size // 2)
        color = (
            int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * (1 - t)),
            int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * (1 - t)),
            int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * (1 - t)),
            255,
        )
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    return img


def _draw_glow_ring(base: Image.Image, cx: int, cy: int, radius: int, color: tuple[int, int, int], width: int = 8) -> None:
    ring = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(ring)
    draw.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        outline=(*color, 180),
        width=width,
    )
    blurred = ring.filter(ImageFilter.GaussianBlur(radius=12))
    base.alpha_composite(blurred)
    draw2 = ImageDraw.Draw(base)
    draw2.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        outline=(*color, 255),
        width=max(4, width // 2),
    )


def _draw_chip(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    r: int,
    fill: tuple[int, int, int],
    *,
    stripes: bool = True,
) -> None:
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill, outline=(255, 255, 255, 240), width=max(3, r // 18))
    inner = int(r * 0.72)
    draw.ellipse((cx - inner, cy - inner, cx + inner, cy + inner), outline=(255, 255, 255, 90), width=max(2, r // 24))
    if stripes:
        for i in range(8):
            ang = i * math.pi / 4
            x1 = cx + int(math.cos(ang) * r * 0.55)
            y1 = cy + int(math.sin(ang) * r * 0.55)
            x2 = cx + int(math.cos(ang) * r * 0.92)
            y2 = cy + int(math.sin(ang) * r * 0.92)
            draw.line((x1, y1, x2, y2), fill=(255, 255, 255, 70), width=max(2, r // 20))


def render_icon_frame(t: float) -> Image.Image:
    size = 1024
    pulse = 0.5 + 0.5 * math.sin(t * math.pi * 2)
    img = _radial_bg(size)
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, int(size * 0.46)
    main_r = int(200 + 14 * pulse)
    _draw_glow_ring(img, cx, cy, main_r + 36, PRIMARY)
    _draw_chip(draw, cx, cy, main_r, PRIMARY)

    _draw_chip(draw, cx - 150, cy + 120, 72, GOLD)
    _draw_chip(draw, cx + 150, cy + 120, 72, SECONDARY)

    # MN2 monogram on main chip
    font_big = _load_font(int(main_r * 0.62))
    draw.text((cx, cy - 8), "MN2", fill=(8, 16, 20, 255), anchor="mm", font=font_big)

    font_sub = _load_font(52, bold=False)
    draw.text((cx, cy + main_r + 58), "CASINO STREAM", fill=(255, 255, 255, 235), anchor="mm", font=font_sub)

    # Corner accent dots
    for i, col in enumerate((ACCENT, GOLD, SECONDARY)):
        ang = math.pi * 0.25 + i * (math.pi * 2 / 3) + t * math.pi * 2
        px = cx + int(math.cos(ang) * (main_r + 110))
        py = cy + int(math.sin(ang) * (main_r + 110))
        pr = 16 + int(4 * pulse)
        draw.ellipse((px - pr, py - pr, px + pr, py + pr), fill=(*col, 220))

    return img.convert("RGB")


def render_banner_frame(t: float) -> Image.Image:
    w, h = 680, 240
    img = Image.new("RGB", (w, h), BG_TOP)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        tgrad = y / max(h - 1, 1)
        row = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * tgrad) for i in range(3))
        draw.line([(0, y), (w, y)], fill=row)
    shift = int(10 * math.sin(t * math.pi * 2))
    _draw_chip(draw, 100 + shift, 120, 56, PRIMARY)
    _draw_chip(draw, 200, 120, 40, GOLD)
    _draw_chip(draw, 280, 120, 40, SECONDARY)
    font = _load_font(34)
    font_sm = _load_font(20, bold=False)
    draw.text((340, 95), "MasterNoder Casino Stream", fill=(255, 255, 255), font=font)
    draw.text((340, 140), "PayPal + MN2  ·  /playnow  /casino  /hosting", fill=(184, 255, 217), font=font_sm)
    return img


def save_png_gif(name: str, frame_fn, *, gif_frames: int = 24) -> None:
    frames = [frame_fn(i / gif_frames) for i in range(gif_frames)]
    icon_path = OUT / f"{name}.png"
    frames[0].save(icon_path, "PNG", optimize=True)
    frames[0].save(
        OUT / f"{name}.gif",
        save_all=True,
        append_images=frames[1:],
        duration=80,
        loop=0,
        disposal=2,
    )
    if name == "discord-app-icon":
        # Discord accepts 1024x1024 PNG; also ship a copy for docs/profile
        copy = OUT / "discord-app-icon-1024.png"
        frames[0].save(copy, "PNG", optimize=True)


def main() -> None:
    save_png_gif("discord-app-icon", render_icon_frame)
    save_png_gif("discord-app-banner", render_banner_frame)
    print("Wrote assets to", OUT)
    print("  Upload discord-app-icon.png (1024x1024) to Developer Portal -> Bot -> Icon")


if __name__ == "__main__":
    main()
