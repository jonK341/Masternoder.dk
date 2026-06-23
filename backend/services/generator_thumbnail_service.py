"""Extract WebP poster/sprites from generated MP4s (encoder idea E6)."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from typing import Optional

from backend.services.video_generator_service import VIDEOS_DIR


def _ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg") or "ffmpeg"


def _video_duration_sec(path: str) -> float:
    try:
        from moviepy import VideoFileClip

        with VideoFileClip(path) as clip:
            return max(0.1, float(clip.duration or 0))
    except Exception:
        pass
    try:
        ff = _ffmpeg_exe()
        out = subprocess.run(
            [ff, "-i", path],
            capture_output=True,
            text=True,
            timeout=15,
        )
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", out.stderr or "")
        if m:
            h, mi, s = m.groups()
            return max(0.1, int(h) * 3600 + int(mi) * 60 + float(s))
    except Exception:
        pass
    return 5.0


def poster_path(doc_id: str) -> str:
    return os.path.join(VIDEOS_DIR, f"{doc_id}_poster.webp")


def sprite_path(doc_id: str) -> str:
    return os.path.join(VIDEOS_DIR, f"{doc_id}_thumb.webp")


def thumbnail_url(doc_id: str, kind: str = "poster") -> str:
    if kind == "sprite":
        return f"/api/documentary/thumbnail/{doc_id}?kind=sprite"
    return f"/api/documentary/thumbnail/{doc_id}"


def build_video_thumbnails(doc_id: str, video_path: Optional[str] = None) -> Optional[str]:
    """
    Extract 3 frames (10%, 50%, 90%) into a horizontal WebP sprite + middle-frame poster.
    Returns poster URL path on success.
    """
    path = video_path or os.path.join(VIDEOS_DIR, f"{doc_id}.mp4")
    if not os.path.isfile(path) or os.path.getsize(path) < 1024:
        return None

    poster_out = poster_path(doc_id)
    sprite_out = sprite_path(doc_id)
    if os.path.isfile(poster_out) and os.path.getsize(poster_out) > 64:
        return thumbnail_url(doc_id)

    ffmpeg = _ffmpeg_exe()
    dur = _video_duration_sec(path)
    stamps = [max(0.05, dur * p) for p in (0.1, 0.5, 0.9)]
    tmp_dir = tempfile.mkdtemp(prefix=f"thumb_{doc_id[:8]}_")
    frame_files = []
    try:
        for i, ts in enumerate(stamps):
            frame_path = os.path.join(tmp_dir, f"f{i}.png")
            subprocess.run(
                [ffmpeg, "-y", "-ss", f"{ts:.3f}", "-i", path, "-vframes", "1", "-q:v", "2", frame_path],
                capture_output=True,
                timeout=45,
            )
            if os.path.isfile(frame_path) and os.path.getsize(frame_path) > 32:
                frame_files.append(frame_path)
        if not frame_files:
            return None

        from PIL import Image

        images = [Image.open(f).convert("RGB") for f in frame_files]
        images[len(images) // 2].save(poster_out, "WEBP", quality=82)

        thumb_h = 120
        scaled = []
        for im in images:
            w = max(1, int(im.width * thumb_h / max(1, im.height)))
            scaled.append(im.resize((w, thumb_h)))
        total_w = sum(s.width for s in scaled)
        sprite = Image.new("RGB", (total_w, thumb_h))
        x = 0
        for s in scaled:
            sprite.paste(s, (x, 0))
            x += s.width
        sprite.save(sprite_out, "WEBP", quality=80)
        return thumbnail_url(doc_id)
    except Exception:
        return None
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def get_thumbnail_file(doc_id: str, kind: str = "poster") -> Optional[str]:
    """Return on-disk thumbnail path; build lazily if MP4 exists."""
    target = sprite_path(doc_id) if kind == "sprite" else poster_path(doc_id)
    if os.path.isfile(target) and os.path.getsize(target) > 64:
        return target
    mp4 = os.path.join(VIDEOS_DIR, f"{doc_id}.mp4")
    if os.path.isfile(mp4):
        build_video_thumbnails(doc_id, mp4)
    if os.path.isfile(target) and os.path.getsize(target) > 64:
        return target
    alt = poster_path(doc_id)
    return alt if os.path.isfile(alt) and os.path.getsize(alt) > 64 else None
