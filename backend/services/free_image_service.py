"""
Free Image Generation Service — zero cost, no API key required.

Primary:  Pollinations.ai  — completely free, unlimited, no signup
          GET https://image.pollinations.ai/prompt/{text}?width=1024&height=576&nologo=true

Fallback: Picsum Photos placeholder (instant, always available)

Used in video pipeline when Stability AI key is not configured.
"""
import os
import time
import tempfile
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any, List


_TIMEOUT = 30
_DEFAULT_W = 1024
_DEFAULT_H = 576  # 16:9


def generate_image(
    prompt: str,
    width: int = _DEFAULT_W,
    height: int = _DEFAULT_H,
    dest_dir: Optional[str] = None,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate an image from a text prompt at zero cost.
    Returns: {success, local_path, source, error}
    """
    result = _pollinations(prompt, width, height, dest_dir, seed)
    if result["success"]:
        return result
    return _picsum_placeholder(width, height, dest_dir)


def _pollinations(prompt, width, height, dest_dir, seed):
    try:
        encoded = urllib.parse.quote(prompt[:400], safe="")
        params = "width=%d&height=%d&nologo=true&enhance=true" % (width, height)
        if seed is not None:
            params += "&seed=%d" % seed
        url = "https://image.pollinations.ai/prompt/%s?%s" % (encoded, params)

        req = urllib.request.Request(url, headers={"User-Agent": "MasterNoder/1.0"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            img_bytes = resp.read()

        if len(img_bytes) < 1000:
            return {"success": False, "error": "Response too small"}

        path = _save(img_bytes, dest_dir, "pollinations", "jpg")
        return {"success": True, "local_path": path, "source": "pollinations"}
    except Exception as e:
        return {"success": False, "error": "pollinations: %s" % e}


def _picsum_placeholder(width, height, dest_dir):
    """Fast placeholder from picsum.photos — always works, no API key."""
    try:
        url = "https://picsum.photos/%d/%d" % (width, height)
        req = urllib.request.Request(url, headers={"User-Agent": "MasterNoder/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            img_bytes = resp.read()
        path = _save(img_bytes, dest_dir, "picsum", "jpg")
        return {"success": True, "local_path": path, "source": "picsum"}
    except Exception as e:
        return {"success": False, "error": "picsum: %s" % e}


def _save(img_bytes: bytes, dest_dir: Optional[str], prefix: str, ext: str) -> str:
    if dest_dir is None:
        dest_dir = os.environ.get("VIDEOS_DIR", tempfile.gettempdir())
    os.makedirs(dest_dir, exist_ok=True)
    filename = "%s_%d_%d.%s" % (prefix, int(time.time()), os.getpid(), ext)
    path = os.path.join(dest_dir, filename)
    with open(path, "wb") as f:
        f.write(img_bytes)
    return path


def is_available() -> bool:
    """Always True — Pollinations.ai needs no key."""
    return True


def generate_segment_images(
    segments: list,
    max_images: int = 6,
    width: int = _DEFAULT_W,
    height: int = _DEFAULT_H,
) -> list:
    """
    Generate free AI images for video segments.
    Adds 'image_path' to each segment dict.
    """
    dest_dir = os.environ.get("VIDEOS_DIR", tempfile.gettempdir())
    for i, seg in enumerate(segments[:max_images]):
        if seg.get("image_path") or seg.get("ai_video_path"):
            continue  # already has visual
        title = seg.get("title", "")
        desc = seg.get("description", "")
        mood = seg.get("mood", "cinematic")
        prompt = (
            "Cinematic widescreen scene, %s mood: %s. %s. "
            "Professional photography, dramatic lighting, 16:9 aspect ratio." % (mood, title, desc[:200])
        )
        result = generate_image(prompt, width=width, height=height, dest_dir=dest_dir, seed=i * 42)
        if result.get("success") and result.get("local_path"):
            segments[i]["image_path"] = result["local_path"]
    return segments


def get_status() -> Dict[str, Any]:
    return {
        "provider": "Pollinations.ai",
        "available": True,
        "cost": "free",
        "key_required": False,
        "url": "https://image.pollinations.ai",
        "limits": "Unlimited (community-funded)",
    }
