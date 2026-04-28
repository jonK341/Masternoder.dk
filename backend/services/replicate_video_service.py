"""
Replicate Stable Video Diffusion Service
Generates short video clips from images via Replicate API (image-to-video).

Flow:
  1. Get start frame from Pollinations.ai (URL)
  2. POST to Replicate API to create prediction (stable-video-diffusion)
  3. Poll until status=succeeded
  4. Download output video to local path

API: https://api.replicate.com/v1/predictions
Key: REPLICATE_API_TOKEN
Model: christophy/stable-video-diffusion (or aicapcut/stable-video-diffusion-img2vid-xt-optimized)
"""
import os
import time
import tempfile
import urllib.parse
import urllib.request
from typing import Optional, Dict, Any, List

try:
    import requests as _requests
    _USE_REQUESTS = True
except ImportError:
    _USE_REQUESTS = False

REPLICATE_API = "https://api.replicate.com/v1"
MODEL_VERSION = "christophy/stable-video-diffusion:43b6ee89028ca4ded3497f711e814ae5a0d619287136763c5616968194aff574"
POLL_INTERVAL = 10
MAX_POLL_SEC = 300


def _get_api_key() -> str:
    key = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if key:
        return key
    for ef in ("/var/www/html/.env", "/var/www/html/vidgenerator/.env"):
        if os.path.exists(ef):
            try:
                with open(ef) as f:
                    for line in f:
                        if line.startswith("REPLICATE_API_TOKEN="):
                            v = line.split("=", 1)[1].strip().strip("'\"")
                            if v:
                                os.environ["REPLICATE_API_TOKEN"] = v
                                return v
            except Exception:
                pass
    return ""


def _headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _post(api_key: str, path: str, payload: dict) -> Dict:
    url = REPLICATE_API + path
    if _USE_REQUESTS:
        r = _requests.post(url, headers=_headers(api_key), json=payload, timeout=60)
        return r.json()
    import json
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    for k, v in _headers(api_key).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def _get(api_key: str, path: str) -> Dict:
    url = REPLICATE_API + path
    if _USE_REQUESTS:
        r = _requests.get(url, headers=_headers(api_key), timeout=30)
        return r.json()
    req = urllib.request.Request(url)
    for k, v in _headers(api_key).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=30) as resp:
        import json
        return json.loads(resp.read())


def _pollinations_image_url(prompt: str) -> str:
    """Return Pollinations image URL for the prompt (1024x576 for SVD)."""
    encoded = urllib.parse.quote(prompt[:400], safe="")
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=576&nologo=true"


def _download_video(video_url: str, dest_dir: Optional[str]) -> Optional[str]:
    try:
        if dest_dir is None:
            dest_dir = os.environ.get("VIDEOS_DIR", tempfile.gettempdir())
        os.makedirs(dest_dir, exist_ok=True)
        path = os.path.join(dest_dir, "replicate_%d_%d.mp4" % (int(time.time()), os.getpid()))
        if _USE_REQUESTS:
            r = _requests.get(video_url, timeout=120, stream=True)
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
        else:
            urllib.request.urlretrieve(video_url, path)
        return path if os.path.getsize(path) > 1000 else None
    except Exception:
        return None


def is_available() -> bool:
    return bool(_get_api_key())


def generate_clip(
    prompt: str,
    dest_dir: Optional[str] = None,
    timeout: int = MAX_POLL_SEC,
) -> Dict[str, Any]:
    """
    Generate a video clip from a text prompt using Replicate Stable Video Diffusion.

    Returns:
      {success, video_url, local_path, prediction_id, error}
    """
    api_key = _get_api_key()
    if not api_key:
        return {"success": False, "error": "REPLICATE_API_TOKEN not configured"}

    image_url = _pollinations_image_url(prompt)
    payload = {
        "version": MODEL_VERSION,
        "input": {
            "input_image": image_url,
            "video_length": "14_frames_with_svd",
            "frames_per_second": 14,
        },
    }

    try:
        data = _post(api_key, "/predictions", payload)
    except Exception as e:
        return {"success": False, "error": "Replicate submit failed: %s" % e}

    pred_id = data.get("id")
    if not pred_id:
        err = data.get("error") or data.get("detail") or str(data)[:200]
        return {"success": False, "error": "No prediction ID: %s" % err}

    start = time.monotonic()
    while (time.monotonic() - start) < timeout:
        time.sleep(POLL_INTERVAL)
        try:
            status_data = _get(api_key, "/predictions/" + pred_id)
        except Exception:
            continue
        status = (status_data.get("status") or "").lower()
        if status == "succeeded":
            output = status_data.get("output")
            video_url = None
            if isinstance(output, str):
                video_url = output
            elif isinstance(output, list) and output:
                video_url = output[0] if isinstance(output[0], str) else output[0].get("url")
            elif isinstance(output, dict):
                video_url = output.get("url") or output.get("video")
            if not video_url:
                return {"success": False, "error": "No video URL in output", "prediction_id": pred_id}
            local_path = _download_video(video_url, dest_dir)
            return {
                "success": True,
                "video_url": video_url,
                "local_path": local_path,
                "prediction_id": pred_id,
            }
        if status == "failed" or status == "canceled":
            err = status_data.get("error") or status_data.get("logs") or "Unknown error"
            return {"success": False, "error": "Replicate failed: %s" % str(err)[:200], "prediction_id": pred_id}

    return {"success": False, "error": "Replicate timeout after %ds" % timeout, "prediction_id": pred_id}


def generate_segment_clips(
    segments: List[Dict],
    max_clips: int = 1,
    timeout_per_clip: int = MAX_POLL_SEC,
) -> List[Dict]:
    """Generate Replicate SVD clips for segments. Adds replicate_video_path and ai_video_path."""
    if not is_available():
        return segments

    dest_dir = os.environ.get("VIDEOS_DIR", tempfile.gettempdir())
    candidates = [
        (i, s)
        for i, s in enumerate(segments)
        if not s.get("ai_video_path") and not s.get("replicate_video_path")
    ]
    candidates = sorted(
        candidates,
        key=lambda x: len(x[1].get("description", "")),
        reverse=True,
    )[:max_clips]

    for idx, seg in candidates:
        title = seg.get("title", "")
        desc = seg.get("description", "")
        mood = seg.get("mood", "cinematic")
        prompt = "Cinematic %s scene: %s. %s" % (mood, title, desc[:300])
        result = generate_clip(prompt=prompt, dest_dir=dest_dir, timeout=timeout_per_clip)
        if result.get("success") and result.get("local_path"):
            segments[idx]["replicate_video_path"] = result["local_path"]
            segments[idx]["ai_video_path"] = result["local_path"]
    return segments
