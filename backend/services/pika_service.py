"""
Pika 2.2 Text-to-Video Service
Generates cinematic video clips from text prompts.

API: https://api.pika.art
Key: PIKA_LABS_API_KEY (format: id:secret — stored as single env value)

Flow:
  1. POST /generate/2.2/t2v  → video_id
  2. Poll GET /videos/{video_id} until completed
  3. Download mp4 to local path

Cost: ~$0.20 / 5s clip at 720p
Docs: https://pika-827374fb.mintlify.app/api-reference/generate-2-2-t2v
"""
import os
import time
import json
import base64
import tempfile
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional, Dict, Any

BASE_URL       = "https://api.pika.art"
DEFAULT_RES    = "720p"           # 720p cheaper; use 1080p for premium
DEFAULT_DUR    = 5                # seconds (5 is cheapest)
POLL_INTERVAL  = 6                # seconds between status checks
MAX_POLL_SEC   = 150              # 2.5-minute ceiling

try:
    import requests as _requests
    _USE_REQUESTS = True
except ImportError:
    _USE_REQUESTS = False


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _get_api_key() -> str:
    key = os.environ.get("PIKA_LABS_API_KEY", "").strip()
    if key:
        return key
    for ef in ("/var/www/html/.env", "/var/www/html/vidgenerator/.env"):
        if os.path.exists(ef):
            try:
                with open(ef) as f:
                    for line in f:
                        if line.startswith("PIKA_LABS_API_KEY="):
                            v = line.split("=", 1)[1].strip().strip("'\"")
                            if v:
                                os.environ["PIKA_LABS_API_KEY"] = v
                                return v
            except Exception:
                pass
    return ""


def _auth_header(api_key: str) -> str:
    """Pika uses Basic auth with the full key:secret string."""
    b64 = base64.b64encode(api_key.encode("utf-8")).decode("utf-8")
    return f"Basic {b64}"


def is_available() -> bool:
    return bool(_get_api_key())


# ---------------------------------------------------------------------------
# Low-level HTTP
# ---------------------------------------------------------------------------

def _post_form(api_key: str, path: str, params: dict) -> Dict:
    url  = BASE_URL + path
    auth = _auth_header(api_key)
    if _USE_REQUESTS:
        r = _requests.post(url, data=params, headers={"Authorization": auth}, timeout=30)
        return r.json()
    body = urllib.parse.urlencode(params).encode("utf-8")
    req  = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", auth)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _get_json(api_key: str, path: str) -> Dict:
    url  = BASE_URL + path
    auth = _auth_header(api_key)
    if _USE_REQUESTS:
        r = _requests.get(url, headers={"Authorization": auth}, timeout=20)
        return r.json()
    req = urllib.request.Request(url)
    req.add_header("Authorization", auth)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def _download(video_url: str, dest_dir: Optional[str]) -> Optional[str]:
    try:
        if not dest_dir:
            dest_dir = os.environ.get("VIDEOS_DIR", tempfile.gettempdir())
        os.makedirs(dest_dir, exist_ok=True)
        fname = f"pika_{int(time.time())}_{os.getpid()}.mp4"
        path  = os.path.join(dest_dir, fname)
        if _USE_REQUESTS:
            r = _requests.get(video_url, timeout=90, stream=True)
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
        else:
            urllib.request.urlretrieve(video_url, path)
        return path if os.path.getsize(path) > 1000 else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_clip(
    prompt: str,
    duration: int = DEFAULT_DUR,
    resolution: str = DEFAULT_RES,
    aspect_ratio: Optional[float] = None,
    dest_dir: Optional[str] = None,
    timeout: int = MAX_POLL_SEC,
) -> Dict[str, Any]:
    """
    Generate a video clip from a text prompt using Pika 2.2.

    Returns {success, video_url, local_path, video_id, error}
    """
    api_key = _get_api_key()
    if not api_key:
        return {"success": False, "error": "PIKA_LABS_API_KEY not configured"}

    # Step 1: Submit generation job
    params: Dict[str, Any] = {
        "promptText": prompt[:500],
        "resolution": resolution,
        "duration":   max(1, min(10, duration)),
    }
    if aspect_ratio is not None:
        params["aspectRatio"] = round(max(0.4, min(2.5, aspect_ratio)), 3)

    try:
        data = _post_form(api_key, "/generate/2.2/t2v", params)
    except Exception as e:
        return {"success": False, "error": f"Submit failed: {e}"}

    video_id = data.get("video_id")
    if not video_id:
        return {"success": False, "error": f"No video_id in response: {str(data)[:200]}"}

    # Step 2: Poll for completion
    return _poll(api_key, video_id, dest_dir, timeout)


def _poll(api_key: str, video_id: str, dest_dir: Optional[str], timeout: int) -> Dict[str, Any]:
    start = time.monotonic()
    while (time.monotonic() - start) < timeout:
        time.sleep(POLL_INTERVAL)
        try:
            data = _get_json(api_key, f"/videos/{video_id}")
        except Exception:
            continue

        status = str(data.get("status") or "").lower()

        if status in ("completed", "succeeded", "success"):
            video_url = (
                data.get("video_url") or
                data.get("url") or
                data.get("result_url") or
                (data.get("result") or {}).get("url")
            )
            if not video_url:
                return {"success": False, "error": "Task succeeded but no video URL", "video_id": video_id}
            local_path = _download(video_url, dest_dir)
            return {
                "success": True,
                "video_url":  video_url,
                "local_path": local_path,
                "video_id":   video_id,
                "resolution": data.get("resolution", DEFAULT_RES),
            }

        if status in ("failed", "cancelled", "error"):
            failure = data.get("error") or data.get("message") or f"Pika {status}"
            return {"success": False, "error": str(failure), "video_id": video_id}

        # PENDING / PROCESSING — keep polling

    return {"success": False, "error": f"Timeout after {timeout}s", "video_id": video_id}


def generate_segment_clips(
    segments: list,
    max_clips: int = 1,
    duration: int = DEFAULT_DUR,
    timeout_per_clip: int = MAX_POLL_SEC,
) -> list:
    """
    Generate Pika 2.2 clips for visually rich segments without existing AI video.
    Adds 'pika_video_path', 'pika_video_url' and promotes to 'ai_video_path'.
    """
    if not is_available():
        return segments

    dest_dir   = os.environ.get("VIDEOS_DIR", tempfile.gettempdir())
    candidates = [
        (i, s) for i, s in enumerate(segments)
        if not s.get("ai_video_path") and not s.get("pika_video_path")
    ]
    candidates = sorted(candidates, key=lambda x: len(x[1].get("description", "")), reverse=True)[:max_clips]

    for idx, seg in candidates:
        title = seg.get("title", "")
        desc  = seg.get("description", "")
        mood  = seg.get("mood", "cinematic")
        prompt = f"{mood.capitalize()} {title}: {desc[:400]}"

        result = generate_clip(
            prompt=prompt,
            duration=duration,
            dest_dir=dest_dir,
            timeout=timeout_per_clip,
        )

        if result.get("success") and result.get("local_path"):
            segments[idx]["pika_video_path"] = result["local_path"]
            segments[idx]["pika_video_url"]  = result.get("video_url", "")
            segments[idx]["ai_video_path"]   = result["local_path"]

    return segments
