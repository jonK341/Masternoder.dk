"""
Free Image Generation Service — zero cost, no API key required.

Primary:  Pollinations.ai free models (researched replacements for
          Stability / OpenAI image / Gemini imagen which are credit-blocked):
            - flux            (best photoreal baseline)
            - z-image-turbo   (fast Tongyi stills)
            - gptimage        (alternate composition)

          GET https://image.pollinations.ai/prompt/{text}
              ?width=1280&height=720&nologo=true&model=flux&seed=N

Fallback: Picsum Photos placeholder (instant, always available)

Used in video / sellable film pipeline when paid image wallets are empty.
"""
import os
import time
import tempfile
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any, List

from backend.services import ai_provider_gate as gate


_TIMEOUT = 30
_DEFAULT_W = 1280
_DEFAULT_H = 720  # 16:9


def generate_image(
    prompt: str,
    width: int = _DEFAULT_W,
    height: int = _DEFAULT_H,
    dest_dir: Optional[str] = None,
    seed: Optional[int] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate an image from a text prompt at zero cost.
    Returns: {success, local_path, source, model, error}
    """
    models = [model] if model else list(gate.POLLINATIONS_IMAGE_MODELS)
    errors: List[str] = []
    for name in models:
        if not name:
            continue
        result = _pollinations(prompt, width, height, dest_dir, seed, str(name))
        if result.get("success"):
            return result
        errors.append("%s: %s" % (name, result.get("error") or "fail"))
    placeholder = _picsum_placeholder(width, height, dest_dir)
    if placeholder.get("success"):
        placeholder["prior_errors"] = errors[:4]
        return placeholder
    return {
        "success": False,
        "error": " | ".join(errors + [placeholder.get("error") or "picsum fail"])[:400],
    }


def _pollinations(prompt, width, height, dest_dir, seed, model):
    try:
        encoded = urllib.parse.quote(prompt[:400], safe="")
        params = (
            "width=%d&height=%d&nologo=true&enhance=true&model=%s"
            % (width, height, urllib.parse.quote(str(model)))
        )
        if seed is not None:
            params += "&seed=%d" % int(seed)
        url = "https://image.pollinations.ai/prompt/%s?%s" % (encoded, params)

        req = urllib.request.Request(url, headers={"User-Agent": "MasterNoder/1.0"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            img_bytes = resp.read()

        if len(img_bytes) < 1000:
            return {"success": False, "error": "Response too small"}

        source = "pollinations_%s" % str(model).replace("-", "_").replace(".", "_")
        path = _save(img_bytes, dest_dir, source, "jpg")
        return {
            "success": True,
            "local_path": path,
            "source": source,
            "model": model,
            "provider": "pollinations",
        }
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
        return {"success": True, "local_path": path, "source": "picsum", "model": "picsum"}
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
    """Always True — Pollinations.ai free models need no key."""
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
    models = list(gate.POLLINATIONS_IMAGE_MODELS)
    for i, seg in enumerate(segments[:max_images]):
        if seg.get("image_path") or seg.get("ai_video_path"):
            continue  # already has visual
        title = seg.get("title", "")
        desc = seg.get("description", "")
        mood = seg.get("mood", "cinematic")
        prompt = (
            "Cinematic widescreen scene, %s mood: %s. %s. "
            "Professional photography, dramatic lighting, 16:9 aspect ratio."
            % (mood, title, desc[:200])
        )
        model = models[i % len(models)]
        result = generate_image(
            prompt,
            width=width,
            height=height,
            dest_dir=dest_dir,
            seed=i * 42,
            model=model,
        )
        if result.get("success") and result.get("local_path"):
            segments[i]["image_path"] = result["local_path"]
            segments[i]["image_source"] = result.get("source")
    return segments


def get_status() -> Dict[str, Any]:
    return {
        "provider": "Pollinations.ai",
        "models": list(gate.POLLINATIONS_IMAGE_MODELS),
        "cost": 0,
        "api_key_required": False,
        "available": True,
        "replacements_for": list(gate._DEFAULT_BLOCKED.keys()),
    }
