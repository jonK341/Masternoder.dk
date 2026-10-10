#!/usr/bin/env python3
"""Generate small animated GIF badges for nav category buttons."""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "img" / "nav" / "categories"
OUT.mkdir(parents=True, exist_ok=True)

SPECS = {
    "play": {"colors": [(0, 255, 136), (0, 212, 255), (124, 92, 255)], "shape": "diamond"},
    "account": {"colors": [(255, 215, 0), (255, 140, 0), (255, 90, 120)], "shape": "bag"},
    "finance": {"colors": [(0, 212, 255), (0, 120, 255), (0, 255, 200)], "shape": "coin"},
    "create": {"colors": [(200, 120, 255), (255, 100, 200), (0, 212, 255)], "shape": "star"},
    "intel": {"colors": [(100, 255, 180), (0, 255, 136), (56, 189, 248)], "shape": "hex"},
    "social": {"colors": [(255, 120, 200), (255, 180, 100), (0, 255, 136)], "shape": "bubble"},
}

SIZE = 56
FRAMES = 10


def draw_shape(draw: ImageDraw.ImageDraw, shape: str, cx: int, cy: int, r: int, fill):
    if shape == "diamond":
        draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)
    elif shape == "bag":
        draw.rounded_rectangle([cx - r, cy - r + 4, cx + r, cy + r], radius=8, fill=fill)
        draw.arc([cx - r // 2, cy - r, cx + r // 2, cy - r // 2 + 8], 180, 0, fill=fill, width=3)
    elif shape == "coin":
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
        draw.ellipse([cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2], outline=(255, 255, 255), width=2)
    elif shape == "star":
        pts = []
        for i in range(10):
            ang = i * 36 - 90
            rad = r if i % 2 == 0 else r // 2
            import math

            pts.append((cx + rad * math.cos(math.radians(ang)), cy + rad * math.sin(math.radians(ang))))
        draw.polygon(pts, fill=fill)
    elif shape == "hex":
        import math

        pts = [
            (cx + r * math.cos(math.radians(60 * i - 30)), cy + r * math.sin(math.radians(60 * i - 30)))
            for i in range(6)
        ]
        draw.polygon(pts, fill=fill)
    else:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
        draw.ellipse([cx - r + 6, cy - r + 6, cx - r + 14, cy - r + 14], fill=(255, 255, 255, 180))


def frame_image(spec: dict, frame_idx: int) -> Image.Image:
    colors = spec["colors"]
    c1 = colors[frame_idx % len(colors)]
    c2 = colors[(frame_idx + 1) % len(colors)]
    t = frame_idx / FRAMES
    blend = tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pulse = 18 + int(4 * (1 if frame_idx % 2 == 0 else 0))
    draw_shape(draw, spec["shape"], SIZE // 2, SIZE // 2, pulse, blend + (230,))
    glow = tuple(max(0, c - 40) for c in blend)
    draw.ellipse([4, 4, SIZE - 4, SIZE - 4], outline=glow + (120,), width=2)
    return img


def main():
    for key, spec in SPECS.items():
        frames = [frame_image(spec, i) for i in range(FRAMES)]
        path = OUT / f"{key}.gif"
        frames[0].save(
            path,
            save_all=True,
            append_images=frames[1:],
            duration=90,
            loop=0,
            disposal=2,
            optimize=True,
        )
        print("wrote", path)


if __name__ == "__main__":
    main()
