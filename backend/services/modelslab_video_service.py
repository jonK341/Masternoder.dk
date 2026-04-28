"""
ModelsLab Text-to-Video Service
Generates AI video clips from text prompts using the CogVideoX model.
Supports both v6 (standard) and v1/enterprise endpoints with async polling.
"""
import os
import time
import requests
import tempfile
from typing import Optional, Dict, Any, Tuple

BASE_V6 = "https://modelslab.com/api/v6/video"
BASE_ENTERPRISE = "https://modelslab.com/api/v1/enterprise/video"

FETCH_URL_V6 = "https://modelslab.com/api/v6/video/fetch/{request_id}"
FETCH_URL_ENTERPRISE = "https://modelslab.com/api/v1/enterprise/ultra_video/fetch/{request_id}"

DEFAULT_MODEL = "cogvideox"
DEFAULT_WIDTH = 512
DEFAULT_HEIGHT = 512
DEFAULT_NUM_FRAMES = 25
DEFAULT_FPS = 15
DEFAULT_STEPS = 20
DEFAULT_GUIDANCE = 7
DEFAULT_OUTPUT_TYPE = "mp4"

MAX_POLL_SECONDS = 180
POLL_INTERVAL = 5


def _get_api_key() -> str:
    key = os.environ.get("MODELSLAB_API_KEY", "").strip()
    if key:
        return key
    for env_path in ("/var/www/html/.env", "/var/www/html/vidgenerator/.env"):
        if os.path.exists(env_path):
            try:
                with open(env_path) as f:
                    for line in f:
                        if line.startswith("MODELSLAB_API_KEY="):
                            val = line.split("=", 1)[1].strip().strip("'\"")
                            if val:
                                os.environ["MODELSLAB_API_KEY"] = val
                                return val
            except Exception:
                pass
    return ""


def is_available() -> bool:
    return bool(_get_api_key())


def generate_clip(
    prompt: str,
    negative_prompt: str = "low quality, blurry, distorted, watermark",
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    num_frames: int = DEFAULT_NUM_FRAMES,
    fps: int = DEFAULT_FPS,
    steps: int = DEFAULT_STEPS,
    guidance_scale: float = DEFAULT_GUIDANCE,
    output_type: str = DEFAULT_OUTPUT_TYPE,
    use_enterprise: bool = False,
    timeout: int = MAX_POLL_SECONDS,
) -> Dict[str, Any]:
    """
    Generate a video clip from a text prompt.

    Returns dict with:
      success: bool
      video_url: str (remote URL of generated video)
      local_path: str (downloaded file path, if download succeeded)
      request_id: str
      eta: float (estimated time from API)
      error: str (on failure)
    """
    api_key = _get_api_key()
    if not api_key:
        return {"success": False, "error": "MODELSLAB_API_KEY not configured"}

    base = BASE_ENTERPRISE if use_enterprise else BASE_V6
    url = f"{base}/text2video"

    payload = {
        "key": api_key,
        "model_id": DEFAULT_MODEL,
        "prompt": prompt[:500],
        "negative_prompt": negative_prompt[:200],
        "height": min(512, max(256, height)),
        "width": min(512, max(256, width)),
        "num_frames": min(25, max(8, num_frames)),
        "num_inference_steps": min(50, max(10, steps)),
        "guidance_scale": min(8, max(1, guidance_scale)),
        "fps": min(16, max(8, fps)),
        "output_type": output_type,
        "upscale_height": 1024,
        "upscale_width": 1024,
        "upscale_strength": 0.6,
        "upscale_guidance_scale": 12,
        "upscale_num_inference_steps": 20,
        "temp": True,
        "instant_response": False,
        "webhook": None,
        "track_id": None,
    }

    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
        data = resp.json()
    except Exception as e:
        return {"success": False, "error": f"API request failed: {e}"}

    status = (data.get("status") or "").lower()
    request_id = data.get("id") or data.get("request_id") or ""

    if status == "error":
        return {"success": False, "error": data.get("message", "Unknown error"), "raw": data}

    video_url = _extract_video_url(data)
    if video_url and status == "success":
        local_path = _download_video(video_url)
        return {
            "success": True,
            "video_url": video_url,
            "local_path": local_path,
            "request_id": request_id,
            "eta": data.get("eta", 0),
        }

    if status in ("processing", "queued") or request_id:
        return _poll_for_result(request_id, use_enterprise, timeout)

    return {"success": False, "error": f"Unexpected response: {data}", "raw": data}


def _poll_for_result(
    request_id: str,
    use_enterprise: bool = False,
    timeout: int = MAX_POLL_SECONDS,
) -> Dict[str, Any]:
    if not request_id:
        return {"success": False, "error": "No request_id to poll"}

    fetch_tpl = FETCH_URL_ENTERPRISE if use_enterprise else FETCH_URL_V6
    fetch_url = fetch_tpl.format(request_id=request_id)

    start = time.monotonic()
    while (time.monotonic() - start) < timeout:
        time.sleep(POLL_INTERVAL)
        try:
            resp = requests.post(
                fetch_url,
                json={"key": _get_api_key()},
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            data = resp.json()
        except Exception:
            continue

        status = (data.get("status") or "").lower()
        video_url = _extract_video_url(data)

        if status == "success" and video_url:
            local_path = _download_video(video_url)
            return {
                "success": True,
                "video_url": video_url,
                "local_path": local_path,
                "request_id": request_id,
                "eta": 0,
            }

        if status == "error":
            return {"success": False, "error": data.get("message", "Generation failed"), "raw": data}

    return {"success": False, "error": f"Timeout after {timeout}s", "request_id": request_id}


def _extract_video_url(data: Dict) -> Optional[str]:
    output = data.get("output")
    if isinstance(output, list) and output:
        return str(output[0])
    if isinstance(output, str) and output.startswith("http"):
        return output
    future = data.get("future_links")
    if isinstance(future, list) and future:
        return str(future[0])
    return None


def _download_video(url: str, dest_dir: Optional[str] = None) -> Optional[str]:
    try:
        if dest_dir is None:
            dest_dir = os.environ.get("VIDEOS_DIR") or tempfile.gettempdir()
        os.makedirs(dest_dir, exist_ok=True)
        ext = "mp4" if ".mp4" in url else "gif"
        filename = f"modelslab_{int(time.time())}_{os.getpid()}.{ext}"
        local_path = os.path.join(dest_dir, filename)
        resp = requests.get(url, timeout=120, stream=True)
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        if os.path.getsize(local_path) > 100:
            return local_path
    except Exception:
        pass
    return None


def generate_segment_clips(
    segments: list,
    max_clips: int = 3,
    timeout_per_clip: int = 120,
) -> list:
    """
    Generate AI video clips for the most important segments.
    Returns the segments list with 'ai_video_path' added where successful.
    """
    if not is_available():
        return segments

    important = sorted(
        enumerate(segments),
        key=lambda x: len(x[1].get("description", "")),
        reverse=True,
    )[:max_clips]

    for idx, seg in important:
        title = seg.get("title", "")
        desc = seg.get("description", "")
        mood = seg.get("mood", "")
        prompt = f"Cinematic {mood} scene: {title}. {desc}"[:500]

        result = generate_clip(
            prompt=prompt,
            negative_prompt="low quality, blurry, text, watermark, distorted faces",
            width=512,
            height=512,
            num_frames=25,
            fps=15,
            output_type="mp4",
            timeout=timeout_per_clip,
        )

        if result.get("success") and result.get("local_path"):
            segments[idx]["ai_video_path"] = result["local_path"]
            segments[idx]["ai_video_url"] = result.get("video_url", "")

    return segments
