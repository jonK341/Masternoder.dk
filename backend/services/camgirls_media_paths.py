"""Resolve on-disk performer media URLs (Phase 2 raster preferred over SVG)."""
from __future__ import annotations

import os
from typing import List, Optional

_RASTER_EXT = ("webp", "png", "jpg", "jpeg")
_VECTOR_EXT = ("svg",)


def pick_media_url(media_dir: str, url_base: str, stem: str) -> str:
    for ext in _RASTER_EXT + _VECTOR_EXT:
        if os.path.isfile(os.path.join(media_dir, f"{stem}.{ext}")):
            return f"{url_base}/{stem}.{ext}"
    return f"{url_base}/{stem}.svg"


def gallery_urls(media_dir: str, url_base: str) -> List[str]:
    urls: List[str] = []
    for i in (1, 2, 3):
        urls.append(pick_media_url(media_dir, url_base, f"gallery-{i}"))
    return urls


def preview_video_url(media_dir: str, url_base: str) -> Optional[str]:
    path = os.path.join(media_dir, "preview.webm")
    if os.path.isfile(path) and os.path.getsize(path) > 100:
        return f"{url_base}/preview.webm"
    return None


def preview_video_mp4_url(media_dir: str, url_base: str) -> Optional[str]:
    path = os.path.join(media_dir, "preview.mp4")
    if os.path.isfile(path) and os.path.getsize(path) > 100:
        return f"{url_base}/preview.mp4"
    return None
