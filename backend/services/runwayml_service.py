"""
RunwayML Gen-4 Turbo Video Service
Generates cinematic AI video clips from text prompts.

Flow:
  1. Generate a starting frame image via Pollinations.ai (free, instant)
  2. Encode image as base64 data URI
  3. POST to RunwayML /v1/image_to_video with model=gen4_turbo
  4. Poll task until complete
  5. Download and save mp4

API docs: https://docs.dev.runwayml.com/api
Key env:  RUNWAYML_API_KEY
"""
import os
import time
import base64
import tempfile
import urllib.request
import urllib.parse
import json
from typing import Optional, Dict, Any

try:
    import requests as _requests
    _USE_REQUESTS = True
except ImportError:
    _USE_REQUESTS = False

BASE_URL        = "https://api.dev.runwayml.com/v1"
API_VERSION     = "2024-11-06"
DEFAULT_MODEL   = "gen4_turbo"
DEFAULT_RATIO   = "1280:720"
DEFAULT_DURATION = 5          # seconds (2–10 allowed)
POLL_INTERVAL   = 5           # seconds between status checks
MAX_POLL_SEC    = 180         # 3-minute ceiling


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------

def _get_api_key() -> str:
    key = os.environ.get("RUNWAYML_API_KEY", "").strip()
    if key:
        return key
    for ef in ("/var/www/html/.env", "/var/www/html/vidgenerator/.env"):
        if os.path.exists(ef):
            try:
                with open(ef) as f:
                    for line in f:
                        if line.startswith("RUNWAYML_API_KEY="):
                            v = line.split("=", 1)[1].strip().strip("'\"")
                            if v:
                                os.environ["RUNWAYML_API_KEY"] = v
                                return v
            except Exception:
                pass
    return ""


def is_available() -> bool:
    return bool(_get_api_key())


# ---------------------------------------------------------------------------
# Image helper — fetch start frame from Pollinations.ai
# ---------------------------------------------------------------------------

def _fetch_start_frame(prompt: str) -> Optional[str]:
    """
    Download a 1280x720 image from Pollinations.ai and return as
    base64 data URI (data:image/jpeg;base64,...).
    """
    try:
        encoded = urllib.parse.quote(prompt[:400], safe="")
        url = "https://image.pollinations.ai/prompt/%s?width=1280&height=720&nologo=true" % encoded
        req = urllib.request.Request(url, headers={"User-Agent": "MasterNoder/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            img_bytes = resp.read()
        if len(img_bytes) < 1000:
            return None
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        return "data:image/jpeg;base64," + b64
    except Exception:
        return None


# ---------------------------------------------------------------------------
# RunwayML REST calls
# ---------------------------------------------------------------------------

def _headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": "Bearer " + api_key,
        "X-Runway-Version": API_VERSION,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _post(api_key: str, path: str, payload: dict) -> Dict:
    url = BASE_URL + path
    if _USE_REQUESTS:
        r = _requests.post(url, headers=_headers(api_key), json=payload, timeout=60)
        return r.json()
    else:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=body, method="POST")
        for k, v in _headers(api_key).items():
            req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())


def _get_task(api_key: str, task_id: str) -> Dict:
    url = BASE_URL + "/tasks/" + task_id
    if _USE_REQUESTS:
        r = _requests.get(url, headers=_headers(api_key), timeout=30)
        return r.json()
    else:
        req = urllib.request.Request(url)
        for k, v in _headers(api_key).items():
            req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())


def _download_video(video_url: str, dest_dir: Optional[str]) -> Optional[str]:
    try:
        if dest_dir is None:
            dest_dir = os.environ.get("VIDEOS_DIR", tempfile.gettempdir())
        os.makedirs(dest_dir, exist_ok=True)
        filename = "runway_%d_%d.mp4" % (int(time.time()), os.getpid())
        path = os.path.join(dest_dir, filename)
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_clip(
    prompt: str,
    duration: int = DEFAULT_DURATION,
    ratio: str = DEFAULT_RATIO,
    model: str = DEFAULT_MODEL,
    dest_dir: Optional[str] = None,
    timeout: int = MAX_POLL_SEC,
) -> Dict[str, Any]:
    """
    Generate a video clip from a text prompt using RunwayML Gen-4 Turbo.

    Returns:
      {success, video_url, local_path, task_id, eta, error}
    """
    api_key = _get_api_key()
    if not api_key:
        return {"success": False, "error": "RUNWAYML_API_KEY not configured"}

    # Step 1 — get a starting frame image
    start_frame = _fetch_start_frame(prompt)
    if not start_frame:
        return {"success": False, "error": "Could not generate starting frame image"}

    # Step 2 — submit task
    try:
        payload = {
            "model": model,
            "promptText": prompt[:1000],
            "promptImage": start_frame,
            "ratio": ratio,
            "duration": max(2, min(10, duration)),
        }
        data = _post(api_key, "/image_to_video", payload)
    except Exception as e:
        return {"success": False, "error": "Submit failed: %s" % e}

    if "error" in data or data.get("status") == "FAILED":
        return {"success": False, "error": str(data.get("error") or data.get("message") or data), "raw": data}

    task_id = data.get("id") or data.get("task_id") or data.get("taskId")
    if not task_id:
        return {"success": False, "error": "No task ID in response: %s" % str(data)[:200]}

    # Step 3 — poll for completion
    return _poll(api_key, task_id, dest_dir, timeout)


def _poll(api_key: str, task_id: str, dest_dir: Optional[str], timeout: int) -> Dict[str, Any]:
    start = time.monotonic()
    while (time.monotonic() - start) < timeout:
        time.sleep(POLL_INTERVAL)
        try:
            data = _get_task(api_key, task_id)
        except Exception:
            continue

        status = str(data.get("status") or "").upper()

        if status == "SUCCEEDED":
            output = data.get("output") or []
            video_url = output[0] if isinstance(output, list) and output else None
            if not video_url:
                return {"success": False, "error": "Task succeeded but no output URL", "task_id": task_id}
            local_path = _download_video(video_url, dest_dir)
            return {
                "success": True,
                "video_url": video_url,
                "local_path": local_path,
                "task_id": task_id,
                "eta": 0,
            }

        if status in ("FAILED", "CANCELLED"):
            failure = data.get("failure") or data.get("error") or "Task failed"
            return {"success": False, "error": str(failure), "task_id": task_id}

        # PENDING / RUNNING — keep polling

    return {"success": False, "error": "Timeout after %ds" % timeout, "task_id": task_id}


def generate_segment_clips(
    segments: list,
    max_clips: int = 2,
    duration: int = DEFAULT_DURATION,
    timeout_per_clip: int = MAX_POLL_SEC,
) -> list:
    """
    Generate RunwayML Gen-4 video clips for the most visually descriptive segments.
    Adds 'runway_video_path' and 'runway_video_url' to successful segments.
    Skips segments that already have a ModelsLab clip.
    """
    if not is_available():
        return segments

    dest_dir = os.environ.get("VIDEOS_DIR", tempfile.gettempdir())

    # Pick segments without existing AI video, prioritise by description richness
    candidates = [
        (i, s) for i, s in enumerate(segments)
        if not s.get("ai_video_path") and not s.get("runway_video_path")
    ]
    candidates = sorted(candidates, key=lambda x: len(x[1].get("description", "")), reverse=True)[:max_clips]

    for idx, seg in candidates:
        title = seg.get("title", "")
        desc  = seg.get("description", "")
        mood  = seg.get("mood", "cinematic")
        prompt = "Cinematic %s scene: %s. %s" % (mood, title, desc[:300])

        result = generate_clip(
            prompt=prompt,
            duration=duration,
            dest_dir=dest_dir,
            timeout=timeout_per_clip,
        )

        if result.get("success") and result.get("local_path"):
            segments[idx]["runway_video_path"] = result["local_path"]
            segments[idx]["runway_video_url"]  = result.get("video_url", "")
            # Promote to primary ai_video_path so the pipeline uses it
            segments[idx]["ai_video_path"]      = result["local_path"]

    return segments
