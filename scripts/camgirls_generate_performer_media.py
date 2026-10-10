#!/usr/bin/env python3
"""Generate gallery stills (WebP + SVG fallback), icon/logo, preview webm, resell ZIPs."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.services.camgirls_media_render import (  # noqa: E402
    render_gallery_webp,
    render_icon_webp,
)
from backend.services.camgirls_media_service import (  # noqa: E402
    _MEDIA_ROOT,
    _PERFORMER_MEDIA_META,
    resell_pack_for_performer,
)


def _svg_gallery(slug: str, initials: str, c1: str, c2: str, variant: int) -> str:
    labels = ("Studio still", "Profile shot", "Stage look")
    label = labels[variant - 1] if 1 <= variant <= 3 else "Still"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480" viewBox="0 0 640 480" role="img">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
  </defs>
  <rect width="640" height="480" fill="#0d1117"/>
  <rect x="24" y="24" width="592" height="432" rx="20" fill="url(#g)" opacity="0.92"/>
  <circle cx="320" cy="200" r="72" fill="#0d1117" opacity="0.35"/>
  <text x="320" y="210" text-anchor="middle" fill="#fff" font-size="42" font-family="system-ui,sans-serif">{initials}</text>
  <text x="320" y="320" text-anchor="middle" fill="#f8fafc" font-size="22" font-family="system-ui,sans-serif">{label}</text>
  <text x="320" y="360" text-anchor="middle" fill="#e2e8f0" font-size="14" font-family="system-ui,sans-serif">{slug} · MN2 Camgirls</text>
</svg>
"""


def _svg_icon(initials: str, c1: str, c2: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="{c1}"/><stop offset="100%" stop-color="{c2}"/>
  </linearGradient></defs>
  <rect width="64" height="64" rx="14" fill="url(#g)"/>
  <text x="32" y="38" text-anchor="middle" fill="#fff" font-size="18" font-family="system-ui,sans-serif">{initials}</text>
</svg>
"""


def _svg_logo(name: str, c1: str, c2: str) -> str:
    short = (name or "Studio")[:18]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="240" height="64" viewBox="0 0 240 64">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="{c1}"/><stop offset="100%" stop-color="{c2}"/>
  </linearGradient></defs>
  <rect width="240" height="64" rx="12" fill="#0d1117"/>
  <rect x="4" y="4" width="232" height="56" rx="10" fill="url(#g)" opacity="0.9"/>
  <text x="120" y="40" text-anchor="middle" fill="#fff" font-size="16" font-weight="600" font-family="system-ui,sans-serif">{short}</text>
</svg>
"""


def _ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def _ffmpeg_ok() -> bool:
    exe = _ffmpeg_exe()
    try:
        subprocess.run([exe, "-version"], capture_output=True, check=True, timeout=10)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def _poster_still(out_dir: str) -> str | None:
    for stem in ("gallery-1", "gallery-2", "gallery-3"):
        for ext in ("webp", "png", "jpg", "jpeg"):
            path = os.path.join(out_dir, f"{stem}.{ext}")
            if os.path.isfile(path) and os.path.getsize(path) > 200:
                return path
    return None


def _try_preview_webm(out_path: str, poster_path: str) -> bool:
    if not _ffmpeg_ok():
        return False
    vf = "scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2,format=yuv420p"
    cmd = [
        _ffmpeg_exe(),
        "-y",
        "-loop",
        "1",
        "-i",
        poster_path,
        "-vf",
        vf,
        "-c:v",
        "libvpx-vp9",
        "-b:v",
        "140k",
        "-an",
        "-t",
        "3",
        out_path,
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=120)
        return os.path.isfile(out_path) and os.path.getsize(out_path) > 100
    except (OSError, subprocess.SubprocessError):
        return False


def _try_preview_mp4(out_path: str, poster_path: str) -> bool:
    if not _ffmpeg_ok():
        return False
    vf = "scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2"
    cmd = [
        _ffmpeg_exe(),
        "-y",
        "-loop",
        "1",
        "-i",
        poster_path,
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-an",
        "-t",
        "3",
        out_path,
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=120)
        return os.path.isfile(out_path) and os.path.getsize(out_path) > 100
    except (OSError, subprocess.SubprocessError):
        return False


def _user_raster_exists(out_dir: str, stem: str) -> bool:
    for ext in ("webp", "png", "jpg", "jpeg"):
        path = os.path.join(out_dir, f"{stem}.{ext}")
        if os.path.isfile(path) and os.path.getsize(path) > 200:
            return True
    return False


def _write_if_allowed(
    path: str,
    content: str,
    *,
    force: bool,
    protect_raster: bool,
    stem: str,
    out_dir: str,
) -> None:
    if protect_raster and _user_raster_exists(out_dir, stem):
        return
    if not force and os.path.isfile(path) and os.path.getsize(path) > 50:
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description="Camgirls performer media generator (Phase 2 raster)")
    parser.add_argument("--no-raster", action="store_true", help="Skip WebP generation (SVG only)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing generated files")
    parser.add_argument("--skip-preview", action="store_true", help="Do not run ffmpeg preview encode")
    args = parser.parse_args()

    from backend.services.camgirls_service import _load_performers_from_json

    performers = _load_performers_from_json()
    made = 0
    for p in performers:
        pid = str(p.get("id") or "")
        meta = _PERFORMER_MEDIA_META.get(pid)
        if not meta:
            continue
        slug = meta["slug"]
        name = str(p.get("display_name") or slug)
        out_dir = os.path.join(_MEDIA_ROOT, slug)
        os.makedirs(out_dir, exist_ok=True)

        if not args.no_raster:
            for i in (1, 2, 3):
                stem = f"gallery-{i}"
                webp_path = os.path.join(out_dir, f"{stem}.webp")
                if args.force or not _user_raster_exists(out_dir, stem):
                    render_gallery_webp(
                        webp_path,
                        initials=meta["initials"],
                        c1=meta["c1"],
                        c2=meta["c2"],
                        variant=i,
                        slug=slug,
                    )
            icon_webp = os.path.join(out_dir, "icon.webp")
            if args.force or not _user_raster_exists(out_dir, "icon"):
                render_icon_webp(
                    icon_webp,
                    initials=meta["initials"],
                    c1=meta["c1"],
                    c2=meta["c2"],
                )

        for i in (1, 2, 3):
            svg_path = os.path.join(out_dir, f"gallery-{i}.svg")
            if args.no_raster or args.force or not os.path.isfile(svg_path):
                _write_if_allowed(
                    svg_path,
                    _svg_gallery(slug, meta["initials"], meta["c1"], meta["c2"], i),
                    force=args.force,
                    protect_raster=not args.no_raster,
                    stem=f"gallery-{i}",
                    out_dir=out_dir,
                )
        _write_if_allowed(
            os.path.join(out_dir, "icon.svg"),
            _svg_icon(meta["initials"], meta["c1"], meta["c2"]),
            force=args.force,
            protect_raster=not args.no_raster,
            stem="icon",
            out_dir=out_dir,
        )
        logo_path = os.path.join(out_dir, "logo.svg")
        if args.force or not os.path.isfile(logo_path):
            with open(logo_path, "w", encoding="utf-8") as f:
                f.write(_svg_logo(name, meta["c1"], meta["c2"]))

        preview_svg = os.path.join(out_dir, "preview-loop.svg")
        if args.force or not os.path.isfile(preview_svg):
            with open(preview_svg, "w", encoding="utf-8") as f:
                f.write(
                    f"""<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180" viewBox="0 0 320 180">
  <style>@keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:.75}} }}</style>
  <rect width="320" height="180" fill="{meta['c2']}"/>
  <rect width="320" height="180" fill="{meta['c1']}" opacity="0.5" style="animation:pulse 2s ease-in-out infinite"/>
  <text x="160" y="95" text-anchor="middle" fill="#fff" font-size="28" font-family="system-ui,sans-serif">{meta['initials']}</text>
</svg>"""
                )

        if not args.skip_preview:
            poster = _poster_still(out_dir)
            webm = os.path.join(out_dir, "preview.webm")
            if poster and (args.force or not os.path.isfile(webm) or os.path.getsize(webm) < 100):
                _try_preview_webm(webm, poster)
            mp4 = os.path.join(out_dir, "preview.mp4")
            if poster and (args.force or not os.path.isfile(mp4) or os.path.getsize(mp4) < 100):
                _try_preview_mp4(mp4, poster)

        pack = resell_pack_for_performer(pid, name)
        with open(os.path.join(out_dir, "resell-pack.json"), "w", encoding="utf-8") as f:
            json.dump(pack, f, indent=2)
        zip_dir = os.path.join(ROOT, "content", "digital_goods", "camgirls")
        os.makedirs(zip_dir, exist_ok=True)
        zip_path = os.path.join(zip_dir, f"{slug}-brand-pack.zip")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for fn in os.listdir(out_dir):
                full = os.path.join(out_dir, fn)
                if fn.endswith(".webm") and os.path.getsize(full) < 100:
                    continue
                if fn.endswith(".mp4") and os.path.getsize(full) < 100:
                    continue
                zf.write(full, arcname=fn)
            readme = (
                f"# {name} brand pack\n\n"
                "Includes icon, logo, gallery stills (WebP), preview clip, resell-pack.json.\n"
                "Drop your own gallery-*.webp|png|jpg in this folder and re-run the generator.\n"
                "Affiliate use requires disclosure per MasterNoder camgirls license.\n"
            )
            zf.writestr("README.md", readme)
        made += 1
        print(f"  OK {slug} ({pid})")
    _write_mega_zip(ROOT, made)
    print(f"Generated media for {made} performers under static/camgirls/media/")
    return 0 if made else 1


def _write_mega_zip(root: str, count: int) -> None:
    if count < 1:
        return
    zip_dir = os.path.join(root, "content", "digital_goods", "camgirls")
    mega = os.path.join(zip_dir, "all-performers-brand-pack.zip")
    with zipfile.ZipFile(mega, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fn in sorted(os.listdir(zip_dir)):
            if fn.endswith("-brand-pack.zip") and fn != "all-performers-brand-pack.zip":
                zf.write(os.path.join(zip_dir, fn), arcname=fn)
        zf.writestr(
            "README.md",
            "All camgirls performer brand ZIPs. Each contains icons, logos, gallery WebP, preview, manifest.\n",
        )


if __name__ == "__main__":
    raise SystemExit(main())
