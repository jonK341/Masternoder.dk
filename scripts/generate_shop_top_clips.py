#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build ~3s MP4 + animated GIF from existing shop hero JPGs for the "best" catalog rows.

Selection: items that already have image_url in data/shop_item_media.json, ranked by
rarity (legendary > epic > rare > common) then coin price.

Requires ffmpeg on PATH (libx264 + palette filters for GIF).

  python scripts/generate_shop_top_clips.py --count 8
  python scripts/generate_shop_top_clips.py --count 10 --duration 3
  python scripts/generate_shop_top_clips.py --count 26 --tag media_priority

Writes:
  static/shop/clips/<id>.mp4
  static/shop/clips/<id>.gif
Updates data/shop_item_media.json with clip_url and gif_url.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_RARITY = {"legendary": 4, "epic": 3, "rare": 2, "common": 1}


def _ffmpeg() -> str:
    try:
        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except Exception:
        pass
    w = shutil.which("ffmpeg")
    return w or "ffmpeg"


def _ffprobe() -> str:
    return shutil.which("ffprobe") or "ffprobe"


def _coin_price(item: dict) -> int:
    p = item.get("price")
    if isinstance(p, (int, float)):
        return int(p)
    return 0


def _select_best(items: list, manifest: dict, count: int) -> list:
    rows = []
    for it in items:
        iid = it.get("id")
        if not iid or iid not in manifest:
            continue
        m = manifest.get(iid) or {}
        if not m.get("image_url"):
            continue
        img_rel = m.get("image_url", "").lstrip("/")
        img_disk = os.path.join(_ROOT, img_rel.replace("/", os.sep))
        if not os.path.isfile(img_disk):
            continue
        r = (it.get("rarity") or "common").lower()
        rows.append((-_RARITY.get(r, 0), -_coin_price(it), iid, img_disk))
    rows.sort()
    out = []
    seen = set()
    for _, _, iid, path in rows:
        if iid in seen:
            continue
        seen.add(iid)
        out.append((iid, path))
        if len(out) >= count:
            break
    return out


def _run_mp4(ffmpeg: str, image_path: str, out_mp4: str, duration: float, fps: int) -> bool:
    frames = int(max(1, round(duration * fps)))
    # Slow zoom on still — 16:9
    vf = (
        f"scale=1280:720:force_original_aspect_ratio=decrease,"
        f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
        f"zoompan=z='min(zoom+0.0015,1.4)':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps={fps}"
    )
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-loop",
        "1",
        "-i",
        image_path,
        "-vf",
        vf,
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        out_mp4,
    ]
    try:
        subprocess.run(cmd, check=True, timeout=120)
        if os.path.isfile(out_mp4) and os.path.getsize(out_mp4) > 100:
            return True
    except Exception:
        pass
    # Fallback: still frame encoded as short video (no zoom)
    cmd2 = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-loop",
        "1",
        "-i",
        image_path,
        "-vf",
        "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        out_mp4,
    ]
    try:
        subprocess.run(cmd2, check=True, timeout=120)
        return os.path.isfile(out_mp4) and os.path.getsize(out_mp4) > 100
    except Exception:
        return False


def _run_gif(ffmpeg: str, mp4_path: str, out_gif: str) -> bool:
    # Palette pipeline — compact GIF for web
    vf = "fps=12,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen=stats_mode=single[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5"
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        mp4_path,
        "-vf",
        vf,
        "-loop",
        "0",
        out_gif,
    ]
    try:
        subprocess.run(cmd, check=True, timeout=120)
        return os.path.isfile(out_gif) and os.path.getsize(out_gif) > 100
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=8, help="How many top items (5–10 typical)")
    ap.add_argument("--duration", type=float, default=3.0, help="Clip length in seconds")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Only consider items with any of these tags (OR). E.g. --tag media_priority",
    )
    args = ap.parse_args()
    count = max(5, min(10, args.count))
    os.chdir(_ROOT)

    ffmpeg = _ffmpeg()
    if not os.path.isfile(ffmpeg) and not shutil.which(ffmpeg):
        print("ffmpeg not found (install imageio-ffmpeg: pip install imageio-ffmpeg, or add ffmpeg to PATH).")
        return 1

    from backend.routes.shop_routes import _get_shop_items
    from backend.services.shop_media_service import load_manifest, manifest_path, save_manifest

    items = _filter_by_tags(_get_shop_items() or [], args.tag)
    manifest = load_manifest()
    selected = _select_best(items, manifest, count)
    if not selected:
        print("No items with existing hero images in manifest. Run generate_shop_item_media.py first.")
        return 1

    out_dir = os.path.join(_ROOT, "static", "shop", "clips")
    os.makedirs(out_dir, exist_ok=True)

    for iid, img_path in selected:
        stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", iid).strip("_") or "item"
        mp4_name = stem + ".mp4"
        gif_name = stem + ".gif"
        out_mp4 = os.path.join(out_dir, mp4_name)
        out_gif = os.path.join(out_dir, gif_name)
        print(f"Clip: {iid} …")
        if not _run_mp4(ffmpeg, img_path, out_mp4, args.duration, args.fps):
            print(f"  [FAIL] mp4 for {iid}")
            continue
        if not _run_gif(ffmpeg, out_mp4, out_gif):
            print(f"  [WARN] gif failed for {iid}")
        entry = manifest.get(iid) or {}
        entry["clip_url"] = f"/static/shop/clips/{mp4_name}"
        if os.path.isfile(out_gif):
            entry["gif_url"] = f"/static/shop/clips/{gif_name}"
        entry["clip_duration_s"] = args.duration
        entry["clip_generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        manifest[iid] = entry
        save_manifest(manifest)
        print(f"  [OK] {entry.get('clip_url')} {entry.get('gif_url', '')}")

    print()
    print(f"Manifest: {manifest_path()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
