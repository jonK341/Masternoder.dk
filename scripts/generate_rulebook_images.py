"""Generate static rulebook cover PNGs for compendium thumbnails and viewer headers."""
from __future__ import annotations

import os
from typing import Iterable, Tuple

from PIL import Image, ImageDraw, ImageFont

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_OUT = os.path.join(_BASE, "static", "img")

# (filename, version badge, title, accent rgb)
RULEBOOK_COVERS: Tuple[Tuple[str, str, str, Tuple[int, int, int]], ...] = (
    ("rulebook-compendium-v15.png", "V15", "Master Index", (255, 215, 0)),
    ("rulebook-v1-core.png", "V1", "Core Rules", (100, 180, 255)),
    ("rulebook-v2-hunters.png", "V2", "Trophy Hunters", (255, 140, 60)),
    ("rulebook-v3-comm-psych.png", "V3", "Comm. Psychology", (180, 120, 255)),
    ("rulebook-v3-2-systemic.png", "V3.2", "Systemic Protocols", (160, 200, 255)),
    ("rulebook-v4-star-map.png", "V4", "Star Map", (120, 220, 255)),
    ("rulebook-v5-effect-clusters.png", "V5", "Effect Clusters", (255, 100, 180)),
    ("rulebook-v6-electric-magnet.png", "V6", "Electric Magnet", (80, 255, 200)),
    ("rulebook-v7-unified-points.png", "V7", "Unified Points", (255, 215, 0)),
    ("rulebook-v8-agents.png", "V8", "Agents", (140, 255, 140)),
    ("rulebook-v9-shop.png", "V9", "Shop", (255, 180, 80)),
    ("rulebook-v10-battle.png", "V10", "Battle", (255, 80, 80)),
    ("rulebook-v11-dna.png", "V11", "DNA Theory", (120, 255, 160)),
    ("rulebook-v12-generator.png", "V12", "Generator", (255, 120, 220)),
    ("rulebook-v13-geo-session.png", "V13", "Geo & Session", (100, 200, 255)),
    ("rulebook-v14-analytics.png", "V14", "Analytics", (200, 160, 255)),
    ("rulebook-v16-sync.png", "V16", "Sync Mechanisms", (255, 215, 100)),
    ("rulebook-lab-v2.png", "Lab", "Lab V2", (180, 255, 120)),
)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for path in candidates:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render_cover(filename: str, version: str, title: str, accent: Tuple[int, int, int]) -> str:
    w, h = 800, 450
    img = Image.new("RGB", (w, h), (10, 10, 15))
    draw = ImageDraw.Draw(img)

    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(10 + (26 - 10) * t)
        g = int(10 + (26 - 10) * t)
        b = int(15 + (46 - 15) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    draw.rounded_rectangle((24, 24, w - 24, h - 24), radius=20, outline=accent + (255,), width=3)
    draw.rounded_rectangle((40, 40, 180, 100), radius=14, fill=accent + (40,), outline=accent + (200,), width=2)

    vfont = _font(34, bold=True)
    tfont = _font(42, bold=True)
    sfont = _font(22)

    draw.text((52, 52), version, fill=accent, font=vfont)
    draw.text((40, 130), title, fill=(255, 255, 255), font=tfont)
    draw.text((40, h - 70), "MasterNoder Compendium", fill=(180, 180, 200), font=sfont)

    cx, cy = w - 120, h // 2
    draw.ellipse((cx - 70, cy - 70, cx + 70, cy + 70), outline=accent + (120,), width=2)
    draw.ellipse((cx - 48, cy - 48, cx + 48, cy + 48), fill=accent + (30,))

    out_path = os.path.join(_OUT, filename)
    img.save(out_path, format="PNG", optimize=True)
    return out_path


def generate_all(covers: Iterable[Tuple[str, str, str, Tuple[int, int, int]]] = RULEBOOK_COVERS) -> list[str]:
    os.makedirs(_OUT, exist_ok=True)
    written = []
    for row in covers:
        written.append(render_cover(*row))
    return written


if __name__ == "__main__":
    paths = generate_all()
    print(f"Wrote {len(paths)} rulebook images to {_OUT}")
