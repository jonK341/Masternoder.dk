"""
Stability AI Image Generation Service
Generates AI images from text prompts for video segment backgrounds.
Uses the v1 REST API (stable-diffusion-xl-1024-v1-0) for text-to-image.
Falls back to v2beta stable-image/generate/core if v1 fails.
"""
import os
import time
import requests
from typing import Optional, Dict, Any

V1_URL = "https://api.stability.ai/v1/generation/{engine}/text-to-image"
V2_URL = "https://api.stability.ai/v2beta/stable-image/generate/core"
DEFAULT_ENGINE = "stable-diffusion-xl-1024-v1-0"
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 576  # 16:9 widescreen for video
DEFAULT_STEPS = 30


def _get_api_key() -> str:
    for env_var in ("STABILITY_AI_API_KEY", "STABLE_API_KEY", "STABLE_VIDEO_API_KEY"):
        key = os.environ.get(env_var, "").strip()
        if key:
            return key
    for env_path in ("/var/www/html/.env", "/var/www/html/vidgenerator/.env"):
        if os.path.exists(env_path):
            try:
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        for prefix in ("STABILITY_AI_API_KEY=", "STABLE_API_KEY="):
                            if line.startswith(prefix):
                                val = line[len(prefix):].strip().strip("'\"")
                                if val:
                                    return val
            except Exception:
                pass
    return ""


def is_available() -> bool:
    return bool(_get_api_key())


def generate_image(
    prompt: str,
    negative_prompt: str = "low quality, blurry, distorted, watermark, text overlay",
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    steps: int = DEFAULT_STEPS,
    cfg_scale: float = 7.0,
    style_preset: Optional[str] = None,
    dest_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate an image from text prompt.
    Returns: {success, local_path, error}
    """
    api_key = _get_api_key()
    if not api_key:
        return {"success": False, "error": "No Stability AI API key configured"}

    result = _try_v1(api_key, prompt, negative_prompt, width, height, steps, cfg_scale, style_preset, dest_dir)
    if result["success"]:
        return result

    result2 = _try_v2(api_key, prompt, negative_prompt, style_preset, dest_dir)
    if result2["success"]:
        return result2

    return {"success": False, "error": f"v1: {result.get('error')} | v2: {result2.get('error')}"}


def _try_v1(api_key, prompt, negative_prompt, width, height, steps, cfg_scale, style_preset, dest_dir):
    url = V1_URL.format(engine=DEFAULT_ENGINE)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = {
        "text_prompts": [
            {"text": prompt[:1000], "weight": 1.0},
        ],
        "cfg_scale": cfg_scale,
        "height": height,
        "width": width,
        "steps": steps,
        "samples": 1,
    }
    if negative_prompt:
        body["text_prompts"].append({"text": negative_prompt[:500], "weight": -1.0})
    if style_preset:
        body["style_preset"] = style_preset

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=60)
        if resp.status_code != 200:
            return {"success": False, "error": f"v1 HTTP {resp.status_code}: {resp.text[:200]}"}
        data = resp.json()
        artifacts = data.get("artifacts", [])
        if not artifacts:
            return {"success": False, "error": "v1: no artifacts returned"}
        import base64
        img_data = base64.b64decode(artifacts[0]["base64"])
        path = _save_image(img_data, dest_dir)
        return {"success": True, "local_path": path}
    except Exception as e:
        return {"success": False, "error": f"v1: {e}"}


def _try_v2(api_key, prompt, negative_prompt, style_preset, dest_dir):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "image/*",
    }
    form_data = {
        "prompt": (None, prompt[:1000]),
        "output_format": (None, "png"),
    }
    if negative_prompt:
        form_data["negative_prompt"] = (None, negative_prompt[:500])
    if style_preset:
        form_data["style_preset"] = (None, style_preset)

    try:
        resp = requests.post(V2_URL, headers=headers, files=form_data, timeout=60)
        if resp.status_code != 200:
            return {"success": False, "error": f"v2 HTTP {resp.status_code}: {resp.text[:200]}"}
        path = _save_image(resp.content, dest_dir, ext="png")
        return {"success": True, "local_path": path}
    except Exception as e:
        return {"success": False, "error": f"v2: {e}"}


def _save_image(img_bytes: bytes, dest_dir: Optional[str], ext: str = "png") -> str:
    if dest_dir is None:
        dest_dir = os.environ.get("VIDEOS_DIR", "/tmp")
    os.makedirs(dest_dir, exist_ok=True)
    filename = f"stability_{int(time.time())}_{os.getpid()}.{ext}"
    path = os.path.join(dest_dir, filename)
    with open(path, "wb") as f:
        f.write(img_bytes)
    return path


def generate_segment_images(
    segments: list,
    max_images: int = 6,
    style_preset: Optional[str] = "cinematic",
) -> list:
    """
    Generate AI images for segments. Adds 'image_path' to each segment.
    Returns segments with image_path populated where generation succeeded.
    """
    if not is_available():
        return segments

    dest_dir = os.environ.get("VIDEOS_DIR", "/tmp")

    for i, seg in enumerate(segments[:max_images]):
        title = seg.get("title", "")
        desc = seg.get("description", "")
        mood = seg.get("mood", "")
        tagline = seg.get("tagline", "")

        prompt = (
            f"Cinematic widescreen scene, {mood} mood: {title}. "
            f"{desc[:200]}. {tagline}. "
            "Professional photography, high detail, dramatic lighting, 16:9 aspect ratio."
        )[:1000]

        result = generate_image(
            prompt=prompt,
            style_preset=style_preset,
            width=1024,
            height=576,
            dest_dir=dest_dir,
        )

        if result.get("success") and result.get("local_path"):
            segments[i]["image_path"] = result["local_path"]

    return segments
