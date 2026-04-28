"""
HeyGen Avatar Video Service (V2)
Generates up to ~30s talking-avatar videos from script text.

Flow:
  1. Resolve avatar_id and voice_id (env HEYGEN_AVATAR_ID / HEYGEN_VOICE_ID or list API)
  2. POST /v2/video/generate with video_inputs (character + voice text)
  3. Poll GET /v1/video_status.get?video_id=... until status completed
  4. Download video_url to local path

API docs: https://docs.heygen.com/reference/create-an-avatar-video-v2
Key env:  HEYGEN_API_KEY
Optional: HEYGEN_AVATAR_ID, HEYGEN_VOICE_ID (else first from list is used)
"""
import os
import time
import tempfile
from typing import Optional, Dict, Any, List

try:
    import requests as _requests
    _USE_REQUESTS = True
except ImportError:
    _USE_REQUESTS = False

BASE_URL = "https://api.heygen.com"
POLL_INTERVAL = 8
MAX_POLL_SEC = 300  # 5 min for 30s avatar
MAX_SCRIPT_LEN = 4500  # stay under 5000


def _get_api_key() -> str:
    key = os.environ.get("HEYGEN_API_KEY", "").strip()
    if key:
        return key
    for ef in ("/var/www/html/.env", "/var/www/html/vidgenerator/.env"):
        if os.path.exists(ef):
            try:
                with open(ef) as f:
                    for line in f:
                        if line.startswith("HEYGEN_API_KEY="):
                            v = line.split("=", 1)[1].strip().strip("'\"")
                            if v:
                                os.environ["HEYGEN_API_KEY"] = v
                                return v
            except Exception:
                pass
    return ""


def _headers(api_key: str) -> Dict[str, str]:
    return {"x-api-key": api_key, "Content-Type": "application/json"}


def _get(api_key: str, path: str, params: Optional[Dict] = None) -> Dict:
    url = BASE_URL + path
    if _USE_REQUESTS:
        r = _requests.get(url, headers=_headers(api_key), params=params or {}, timeout=30)
        return r.json()
    import urllib.request
    q = "&".join(f"{k}={v}" for k, v in (params or {}).items())
    full = url + ("?" + q if q else "")
    req = urllib.request.Request(full)
    for k, v in _headers(api_key).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=30) as resp:
        import json
        return json.loads(resp.read())


def _post(api_key: str, path: str, payload: dict) -> Dict:
    url = BASE_URL + path
    if _USE_REQUESTS:
        r = _requests.post(url, headers=_headers(api_key), json=payload, timeout=60)
        return r.json()
    import urllib.request
    import json
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    for k, v in _headers(api_key).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def _resolve_avatar_and_voice(api_key: str) -> tuple:
    """Return (avatar_id, voice_id). Use env if set, else first from list APIs."""
    aid = os.environ.get("HEYGEN_AVATAR_ID", "").strip()
    vid = os.environ.get("HEYGEN_VOICE_ID", "").strip()
    if aid and vid:
        return (aid, vid)
    try:
        if not aid:
            data = _get(api_key, "/v2/avatars")
            avatars = (data.get("data") or {}).get("avatars") or data.get("avatars") or []
            if avatars:
                a = avatars[0] if isinstance(avatars[0], dict) else {"avatar_id": avatars[0]}
                aid = a.get("avatar_id") or a.get("id") or str(avatars[0])
        if not vid:
            data = _get(api_key, "/v2/voices")
            voices = (data.get("data") or {}).get("voices") or data.get("voices") or []
            if voices:
                v = voices[0] if isinstance(voices[0], dict) else {"voice_id": voices[0]}
                vid = v.get("voice_id") or v.get("id") or str(voices[0])
    except Exception:
        pass
    return (aid or "", vid or "")


def is_available() -> bool:
    if not _get_api_key():
        return False
    api_key = _get_api_key()
    avatar_id, voice_id = _resolve_avatar_and_voice(api_key)
    return bool(avatar_id and voice_id)


def _download_video(video_url: str, dest_dir: Optional[str]) -> Optional[str]:
    try:
        if dest_dir is None:
            dest_dir = os.environ.get("VIDEOS_DIR", tempfile.gettempdir())
        os.makedirs(dest_dir, exist_ok=True)
        path = os.path.join(dest_dir, "heygen_%d_%d.mp4" % (int(time.time()), os.getpid()))
        if _USE_REQUESTS:
            r = _requests.get(video_url, timeout=120, stream=True)
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
        else:
            import urllib.request
            urllib.request.urlretrieve(video_url, path)
        return path if os.path.getsize(path) > 1000 else None
    except Exception:
        return None


def generate_clip(
    script_text: str,
    dest_dir: Optional[str] = None,
    timeout: int = MAX_POLL_SEC,
    avatar_id: Optional[str] = None,
    voice_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate one talking-avatar video from script text (up to ~30s / 4500 chars).

    Returns:
      {success, video_url, local_path, video_id, error}
    """
    api_key = _get_api_key()
    if not api_key:
        return {"success": False, "error": "HEYGEN_API_KEY not configured"}

    aid = (avatar_id or os.environ.get("HEYGEN_AVATAR_ID", "").strip())
    vid = (voice_id or os.environ.get("HEYGEN_VOICE_ID", "").strip())
    if not aid or not vid:
        aid, vid = _resolve_avatar_and_voice(api_key)
    if not aid or not vid:
        return {"success": False, "error": "No avatar/voice (set HEYGEN_AVATAR_ID and HEYGEN_VOICE_ID or use account defaults)"}

    text = (script_text or "")[:MAX_SCRIPT_LEN].strip()
    if not text:
        return {"success": False, "error": "script_text is empty"}

    payload = {
        "video_inputs": [
            {
                "character": {"type": "avatar", "avatar_id": aid},
                "voice": {"type": "text", "voice_id": vid, "input_text": text},
                "background": {"type": "color", "value": "#1a1a2e"},
            }
        ],
        "dimension": {"width": 1280, "height": 720},
    }

    try:
        data = _post(api_key, "/v2/video/generate", payload)
    except Exception as e:
        return {"success": False, "error": "HeyGen submit failed: %s" % e}

    err = data.get("error")
    if err:
        msg = err.get("message", err) if isinstance(err, dict) else str(err)
        return {"success": False, "error": "HeyGen: %s" % msg}

    inner = data.get("data") or {}
    video_id = inner.get("video_id")
    if not video_id:
        return {"success": False, "error": "No video_id in HeyGen response"}

    # Poll status
    start = time.monotonic()
    while (time.monotonic() - start) < timeout:
        time.sleep(POLL_INTERVAL)
        try:
            status_data = _get(api_key, "/v1/video_status.get", {"video_id": video_id})
        except Exception:
            continue
        code = status_data.get("code")
        body = status_data.get("data") or {}
        status = (body.get("status") or "").lower()

        if status == "completed":
            video_url = body.get("video_url")
            if not video_url:
                return {"success": False, "error": "Completed but no video_url", "video_id": video_id}
            local_path = _download_video(video_url, dest_dir)
            return {
                "success": True,
                "video_url": video_url,
                "local_path": local_path,
                "video_id": video_id,
            }
        if status == "failed":
            err = body.get("error") or {}
            msg = err.get("message") or err.get("detail") or str(err) if isinstance(err, dict) else str(err)
            return {"success": False, "error": "HeyGen failed: %s" % msg, "video_id": video_id}

    return {"success": False, "error": "HeyGen timeout after %ds" % timeout, "video_id": video_id}


def generate_segment_clips(
    segments: List[Dict],
    max_clips: int = 1,
    timeout_per_clip: int = MAX_POLL_SEC,
) -> List[Dict]:
    """
    Generate HeyGen avatar clips for segments that have narration/description.
    Adds heygen_video_path and ai_video_path to the segment when successful.
    """
    if not is_available():
        return segments

    dest_dir = os.environ.get("VIDEOS_DIR", tempfile.gettempdir())
    # Prefer segments with rich text (opening_hook, tagline, or description)
    candidates = [
        (i, s)
        for i, s in enumerate(segments)
        if not s.get("ai_video_path") and not s.get("heygen_video_path")
    ]
    candidates = sorted(
        candidates,
        key=lambda x: len((x[1].get("opening_hook") or "") + (x[1].get("tagline") or "") + (x[1].get("description") or "")),
        reverse=True,
    )[:max_clips]

    for idx, seg in candidates:
        script = (
            seg.get("opening_hook")
            or seg.get("tagline")
            or seg.get("description")
            or seg.get("title")
            or ""
        )
        script = (script or "")[:MAX_SCRIPT_LEN].strip()
        if not script:
            continue
        result = generate_clip(script_text=script, dest_dir=dest_dir, timeout=timeout_per_clip)
        if result.get("success") and result.get("local_path"):
            segments[idx]["heygen_video_path"] = result["local_path"]
            segments[idx]["ai_video_path"] = result["local_path"]
    return segments
