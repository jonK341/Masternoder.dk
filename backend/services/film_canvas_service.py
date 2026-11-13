"""
Film canvas providers.

One shape for every canvas that can make a film: an HTTP base, a websocket,
and an optional API key read from the environment. Keys are never written
into this file.

Canvases
  comfy_local   ComfyUI on your own machine. No key.
                ws://<host>/ws?clientId=<uuid>
  comfy_cloud   Comfy Cloud. Key from https://platform.comfy.org
                wss://cloud.comfy.org/ws?clientId=<uuid>&token=<COMFY_CLOUD_API_KEY>
                REST header: X-API-Key
  fal_krea      fal.ai Krea realtime canvas. Key from https://fal.ai/dashboard/keys
                wss://fal.run/fal-ai/krea-wan-14b/ws
                The socket takes a short-lived JWT minted from FAL_API_KEY, not the key itself.
  dramacanva    DramaCanvas film canvas over MCP (HTTP, not a raw socket).
                https://dramacanva.com/api/mcp
                REST header: Authorization: Bearer <DRAMACANVA_API_KEY>

Comfy generation needs an API-format workflow file (COMFY_WORKFLOW_PATH).
The prompt is written into COMFY_PROMPT_NODE (default "6", the text node in
ComfyUI's own websocket example).
"""
from __future__ import annotations

import io
import json
import os
import secrets
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, List, Optional

try:
    import imageio.v2 as imageio
except ImportError:
    imageio = None

try:
    import msgpack
except ImportError:
    msgpack = None

try:
    import websocket
except ImportError:
    websocket = None

try:
    from backend.services import heygen_service as _heygen_service
except Exception:  # pragma: no cover - optional provider package
    _heygen_service = None

try:
    from backend.services import modelslab_video_service as _modelslab_service
except Exception:  # pragma: no cover
    _modelslab_service = None

try:
    from backend.services import pika_service as _pika_service
except Exception:  # pragma: no cover
    _pika_service = None

try:
    from backend.services import replicate_video_service as _replicate_service
except Exception:  # pragma: no cover
    _replicate_service = None

try:
    from backend.services import runwayml_service as _runway_service
except Exception:  # pragma: no cover
    _runway_service = None

try:
    from backend.services import free_image_service as _free_image_service
except Exception:  # pragma: no cover
    _free_image_service = None

try:
    from backend.services import video_ai_bridge as _video_ai_bridge
except Exception:  # pragma: no cover
    _video_ai_bridge = None

try:
    from moviepy import ImageClip as _MoviePyImageClip
except ImportError:
    try:
        from moviepy.editor import ImageClip as _MoviePyImageClip
    except ImportError:
        _MoviePyImageClip = None

COMFY_CLOUD_HTTP = "https://cloud.comfy.org"
COMFY_CLOUD_WS = "wss://cloud.comfy.org/ws"
FAL_KREA_WS = "wss://fal.run/fal-ai/krea-wan-14b/ws"
FAL_TOKEN_HTTP = "https://rest.alpha.fal.ai/tokens/"
FAL_TOKEN_EXPIRATION_SECONDS = 3600
FAL_QUEUE_HTTP = "https://queue.fal.run"
FAL_DEFAULT_VIDEO_MODEL = "fal-ai/minimax/video-01-live"
DRAMACANVA_HTTP = "https://dramacanva.com/api/mcp"
MCP_PROTOCOL_VERSION = "2025-11-25"
_DEFAULT_LOCAL_HTTP = "http://127.0.0.1:8188"
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ENV_FILES = (
    os.path.join(_REPO_ROOT, ".env"),
    "/var/www/html/.env",
    "/var/www/html/vidgenerator/.env",
)

# Skip fal after exhausted-balance / locked account errors (shared across workers).
_fal_skip_until = 0.0
_FAL_SKIP_SECONDS = 6 * 3600
_FAL_SKIP_FILE = os.path.join(_REPO_ROOT, "instance", "film_canvas_fal_skip.json")

# External clip backends used when film canvases cannot render (e.g. fal balance gone).
_EXTERNAL_CLIP_BACKENDS = (
    "runway",
    "modelslab",
    "pika",
    "replicate",
    "heygen",
)

# id -> how to reach it. key_env None means the canvas has no secret.
CANVASES: Dict[str, Dict[str, Any]] = {
    "comfy_local": {
        "label": "ComfyUI local",
        "transport": "websocket",
        "key_env": None,
        "auth_header": None,
        "uses": ["film_render", "image_render", "workflow_automation"],
        "generates_mp4": True,
    },
    "comfy_cloud": {
        "label": "Comfy Cloud",
        "transport": "websocket",
        "key_env": "COMFY_CLOUD_API_KEY",
        "auth_header": "X-API-Key",
        "uses": ["film_render", "image_render", "workflow_automation"],
        "generates_mp4": True,
    },
    "fal_krea": {
        "label": "fal.ai Krea realtime",
        "transport": "websocket",
        "key_env": "FAL_API_KEY",
        "auth_header": None,
        "uses": ["realtime_preview", "prompt_iteration", "film_render"],
        "generates_mp4": True,
    },
    "dramacanva": {
        "label": "DramaCanvas",
        "transport": "http",
        "key_env": "DRAMACANVA_API_KEY",
        "auth_header": "Authorization",
        "uses": ["script_breakdown", "storyboard", "continuity", "project_workspace"],
        "generates_mp4": False,
    },
}

PREFERENCE_ALIASES = {
    "comfy": "comfy_cloud",
    "comfyui": "comfy_local",
    "comfy_local": "comfy_local",
    "comfy_cloud": "comfy_cloud",
    "fal": "fal_krea",
    "krea": "fal_krea",
    "fal_krea": "fal_krea",
    "dramacanva": "dramacanva",
    "drama": "dramacanva",
}


def provider_for_preference(preference: str) -> Optional[str]:
    """Map UI/config names to one provider id; auto and canvas mean best available."""
    normalized = str(preference or "").strip().lower()
    if normalized in ("", "auto", "canvas"):
        return None
    return PREFERENCE_ALIASES.get(normalized)


def _env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if val:
        return val
    for path in _ENV_FILES:
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                prefix = name + "="
                for line in handle:
                    line = line.strip()
                    if line.startswith(prefix):
                        found = line[len(prefix):].strip().strip("'\"")
                        if found:
                            os.environ[name] = found
                            return found
        except OSError:
            continue
    return ""


def _safe_error(error: Any, *extra_secrets: str) -> str:
    text = str(error)
    secrets_to_remove = list(extra_secrets)
    for spec in CANVASES.values():
        env_name = spec.get("key_env")
        if env_name:
            secrets_to_remove.append(_env(env_name))
    for secret in secrets_to_remove:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    return text[:300]


def _http_base(canvas_id: str) -> str:
    if canvas_id == "comfy_cloud":
        return COMFY_CLOUD_HTTP
    if canvas_id == "dramacanva":
        return DRAMACANVA_HTTP
    if canvas_id == "comfy_local":
        return (_env("COMFYUI_BASE_URL") or _DEFAULT_LOCAL_HTTP).rstrip("/")
    return ""


def _ws_from_http(http_base: str) -> str:
    if http_base.startswith("https://"):
        host = http_base[len("https://"):]
        scheme = "wss"
    elif http_base.startswith("http://"):
        host = http_base[len("http://"):]
        scheme = "ws"
    else:
        host = http_base
        scheme = "ws"
    return "%s://%s/ws" % (scheme, host.rstrip("/"))


def websocket_url(canvas_id: str, client_id: str, *, include_secret: bool = False) -> str:
    """
    Websocket for a canvas. include_secret=True appends the cloud token so a
    caller can connect. Public listings must leave it False.
    """
    if canvas_id not in CANVASES:
        raise KeyError(canvas_id)
    if canvas_id == "fal_krea":
        return FAL_KREA_WS
    if canvas_id == "dramacanva":
        return ""
    if canvas_id == "comfy_cloud":
        base = COMFY_CLOUD_WS
    else:
        base = _ws_from_http(_http_base(canvas_id))
    query = {"clientId": client_id}
    if include_secret and canvas_id == "comfy_cloud":
        token = _env("COMFY_CLOUD_API_KEY")
        if token:
            query["token"] = token
    return base + "?" + urllib.parse.urlencode(query)


def auth_headers(canvas_id: str) -> Dict[str, str]:
    """Headers for the REST call. The key stays in the header, not the URL."""
    spec = CANVASES[canvas_id]
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    env_name = spec.get("key_env")
    header = spec.get("auth_header")
    if not env_name or not header:
        return headers
    key = _env(env_name)
    if not key:
        return headers
    if header == "Authorization":
        headers[header] = "Bearer " + key
    else:
        headers[header] = key
    return headers


def list_canvases() -> List[Dict[str, Any]]:
    """Public description of every canvas. Secrets are not included."""
    rows: List[Dict[str, Any]] = []
    for canvas_id, spec in CANVASES.items():
        client_id = "public"
        key_env = spec.get("key_env")
        rows.append({
            "id": canvas_id,
            "label": spec["label"],
            "transport": spec["transport"],
            "http_base": _http_base(canvas_id),
            "websocket": websocket_url(canvas_id, client_id, include_secret=False),
            "key_env": key_env,
            "key_configured": bool(_env(key_env)) if key_env else True,
            "uses": list(spec.get("uses") or []),
            "generates_mp4": bool(spec.get("generates_mp4")),
        })
    return rows


def _read_fal_skip_until() -> float:
    global _fal_skip_until
    latest = float(_fal_skip_until or 0)
    try:
        if os.path.isfile(_FAL_SKIP_FILE):
            with open(_FAL_SKIP_FILE, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            latest = max(latest, float((data or {}).get("until") or 0))
            _fal_skip_until = latest
    except Exception:
        pass
    return latest


def _fal_is_skipped() -> bool:
    return time.time() < _read_fal_skip_until()


def _note_fal_error(error: Any) -> None:
    """Skip fal for a while when the account is locked / balance exhausted."""
    global _fal_skip_until
    text = str(error or "").lower()
    markers = (
        "exhausted balance",
        "user is locked",
        "top up your balance",
        "insufficient balance",
        "payment required",
        "fal http 403",
    )
    if not any(marker in text for marker in markers):
        return
    until = time.time() + _FAL_SKIP_SECONDS
    _fal_skip_until = until
    try:
        os.makedirs(os.path.dirname(_FAL_SKIP_FILE), exist_ok=True)
        tmp = _FAL_SKIP_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump({"until": until, "reason": str(error or "")[:300]}, handle)
        os.replace(tmp, _FAL_SKIP_FILE)
    except Exception:
        pass


def list_render_canvases() -> List[str]:
    """Configured render canvases in preference order (skips locked fal)."""
    forced = _env("FILM_CANVAS").strip().lower()
    forced = PREFERENCE_ALIASES.get(forced, forced)
    if forced in CANVASES and CANVASES[forced].get("generates_mp4"):
        return [forced] if is_available(forced, purpose="render") else []

    order = ("comfy_local", "comfy_cloud", "fal_krea")
    return [canvas_id for canvas_id in order if is_available(canvas_id, purpose="render")]


def select_canvas(purpose: str = "render") -> Optional[str]:
    """Select a configured canvas for rendering or planning."""
    forced = _env("FILM_CANVAS").strip().lower()
    forced = PREFERENCE_ALIASES.get(forced, forced)
    if forced in CANVASES:
        return forced if is_available(forced, purpose=purpose) else None
    if purpose == "planning":
        return "dramacanva" if is_available("dramacanva", purpose="planning") else None
    candidates = list_render_canvases()
    return candidates[0] if candidates else None


def _comfy_workflow_available() -> bool:
    path = _env("COMFY_WORKFLOW_PATH")
    return bool(path) and os.path.isfile(path)


def _fal_dependencies_available() -> bool:
    return websocket is not None and msgpack is not None and imageio is not None


def is_available(canvas_id: Optional[str] = None, *, purpose: str = "render") -> bool:
    """Whether a canvas has the credentials, files, and local clients it needs."""
    if canvas_id is None:
        if purpose == "planning":
            return is_available("dramacanva", purpose="planning")
        return bool(list_render_canvases())
    if canvas_id in ("comfy_local", "comfy_cloud"):
        if not _comfy_workflow_available():
            return False
        if canvas_id == "comfy_cloud":
            return bool(_env("COMFY_CLOUD_API_KEY"))
        return bool(_env("COMFYUI_BASE_URL"))
    if canvas_id == "fal_krea":
        # Queue HTTP works with only the key; skip when balance is exhausted.
        return bool(_env("FAL_API_KEY")) and not _fal_is_skipped()
    if canvas_id == "dramacanva":
        return bool(_env("DRAMACANVA_API_KEY"))
    return False


def apply_prompt(workflow: Dict[str, Any], prompt: str, node_id: str) -> Dict[str, Any]:
    """Copy a workflow and write the scene prompt into the text node."""
    graph = json.loads(json.dumps(workflow))
    node = graph.get(node_id)
    if not isinstance(node, dict):
        raise KeyError("workflow has no node %s" % node_id)
    inputs = node.get("inputs")
    if not isinstance(inputs, dict):
        inputs = {}
        node["inputs"] = inputs
    if "text" in inputs or "prompt" not in inputs:
        inputs["text"] = prompt
    else:
        inputs["prompt"] = prompt
    return graph


def first_output_file(history_entry: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """First video, gif, or image file recorded on a finished Comfy history entry."""
    outputs = history_entry.get("outputs") or {}
    if not isinstance(outputs, dict):
        return None
    for kind in ("videos", "gifs", "images"):
        for node_out in outputs.values():
            if not isinstance(node_out, dict):
                continue
            items = node_out.get(kind) or []
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict) and item.get("filename"):
                    return {
                        "filename": str(item["filename"]),
                        "subfolder": str(item.get("subfolder") or ""),
                        "type": str(item.get("type") or "output"),
                    }
    return None


def _http_json(method: str, url: str, headers: Dict[str, str], body: Optional[Dict[str, Any]], timeout: int) -> Dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError("HTTP %s from canvas: %s" % (exc.code, detail)) from exc
    if not raw:
        return {}
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise RuntimeError("canvas returned a non-object JSON body")
    return parsed


def _comfy_url(canvas_id: str, path: str) -> str:
    prefix = "/api" if canvas_id == "comfy_cloud" else ""
    return _http_base(canvas_id) + prefix + path


def _wait_comfy_outputs(sock: Any, prompt_id: str, timeout: int) -> Dict[str, Any]:
    outputs: Dict[str, Any] = {}
    deadline = time.time() + max(5, timeout)
    while time.time() < deadline:
        sock.settimeout(max(1, deadline - time.time()))
        message = sock.recv()
        if not isinstance(message, str):
            continue
        event = json.loads(message)
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        if data.get("prompt_id") != prompt_id:
            continue
        event_type = event.get("type")
        if event_type == "executed" and data.get("node") and isinstance(data.get("output"), dict):
            outputs[str(data["node"])] = data["output"]
        elif event_type == "execution_error":
            detail = data.get("exception_message") or data.get("exception_type") or "execution error"
            raise RuntimeError(str(detail))
        elif event_type == "execution_success":
            return outputs
        elif event_type == "executing" and data.get("node") is None:
            return outputs
    raise RuntimeError("Canvas job timed out")


def _download(url: str, headers: Dict[str, str], dest_path: str, timeout: int) -> None:
    # View downloads are binary. Drop the JSON content type.
    view_headers = {k: v for k, v in headers.items() if k.lower() != "content-type"}
    req = urllib.request.Request(url, headers=view_headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = resp.read()
    if len(payload) < 100:
        raise RuntimeError("canvas file was empty")
    with open(dest_path, "wb") as handle:
        handle.write(payload)


def _generate_comfy_clip(
    prompt: str,
    dest_dir: Optional[str] = None,
    timeout: int = 180,
    canvas_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Submit the configured Comfy workflow and download the first output file.
    Returns {success, local_path, prompt_id, canvas, error}.
    """
    canvas_id = canvas_id or select_canvas()
    workflow_path = _env("COMFY_WORKFLOW_PATH")
    if canvas_id not in ("comfy_local", "comfy_cloud") or not workflow_path or not os.path.isfile(workflow_path):
        return {"success": False, "error": "Comfy canvas or COMFY_WORKFLOW_PATH is not configured"}
    try:
        with open(workflow_path, encoding="utf-8") as handle:
            workflow = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        return {"success": False, "error": "Could not read workflow: %s" % exc}
    if not isinstance(workflow, dict):
        return {"success": False, "error": "Workflow file must be a JSON object"}

    node_id = _env("COMFY_PROMPT_NODE") or "6"
    try:
        graph = apply_prompt(workflow, prompt[:2000], node_id)
    except KeyError as exc:
        return {"success": False, "error": str(exc)}

    client_id = str(uuid.uuid4())
    headers = auth_headers(canvas_id)
    sock = None
    try:
        if websocket is None:
            raise RuntimeError("websocket-client is not installed")
        sock = websocket.create_connection(
            websocket_url(canvas_id, client_id, include_secret=True),
            timeout=min(30, timeout),
        )
        queued = _http_json(
            "POST",
            _comfy_url(canvas_id, "/prompt"),
            headers,
            {"prompt": graph, "client_id": client_id},
            timeout=60,
        )
    except (RuntimeError, urllib.error.URLError, OSError) as exc:
        if sock is not None:
            sock.close()
        return {
            "success": False,
            "error": "Canvas submit failed: %s" % _safe_error(exc),
            "canvas": canvas_id,
        }

    prompt_id = str(queued.get("prompt_id") or "")
    if not prompt_id:
        if sock is not None:
            sock.close()
        return {"success": False, "error": "Canvas did not return a prompt_id", "canvas": canvas_id}

    try:
        outputs = _wait_comfy_outputs(sock, prompt_id, timeout)
    except Exception as exc:
        return {
            "success": False,
            "error": "Canvas execution failed: %s" % _safe_error(exc),
            "prompt_id": prompt_id,
            "canvas": canvas_id,
        }
    finally:
        if sock is not None:
            sock.close()

    output = first_output_file({"outputs": outputs})
    if not output:
        return {"success": False, "error": "Canvas finished without a file", "prompt_id": prompt_id, "canvas": canvas_id}

    if dest_dir is None:
        dest_dir = os.environ.get("VIDEOS_DIR") or os.path.dirname(workflow_path)
    os.makedirs(dest_dir, exist_ok=True)
    ext = os.path.splitext(output["filename"])[1] or ".mp4"
    dest_path = os.path.join(dest_dir, "canvas_%s%s" % (prompt_id[:8], ext))
    view = _comfy_url(canvas_id, "/view") + "?" + urllib.parse.urlencode({
        "filename": output["filename"],
        "subfolder": output["subfolder"],
        "type": output["type"],
    })
    try:
        _download(view, headers, dest_path, timeout=120)
    except (RuntimeError, urllib.error.URLError, OSError) as exc:
        return {"success": False, "error": "Canvas download failed: %s" % exc, "prompt_id": prompt_id, "canvas": canvas_id}

    return {
        "success": True,
        "local_path": dest_path,
        "prompt_id": prompt_id,
        "canvas": canvas_id,
    }


def _fal_token(timeout: int = 30) -> str:
    key = _env("FAL_API_KEY")
    if not key:
        raise RuntimeError("FAL_API_KEY is not configured")
    payload = json.dumps({
        "allowed_apps": ["krea-wan-14b"],
        "token_expiration": FAL_TOKEN_EXPIRATION_SECONDS,
    }).encode("utf-8")
    req = urllib.request.Request(
        FAL_TOKEN_HTTP,
        data=payload,
        headers={
            "Accept": "application/json",
            "Authorization": "Key " + key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("fal token request failed: %s" % exc) from exc
    if isinstance(data, str):
        token = data
    elif isinstance(data, dict):
        token = data.get("token") or data.get("jwt") or data.get("access_token")
    else:
        token = None
    if not isinstance(token, str) or not token:
        raise RuntimeError("fal token response did not include a token")
    return token


def _write_frame_video(frames: List[bytes], path: str, fps: int) -> None:
    if imageio is None:
        raise RuntimeError("imageio is not installed")
    writer = imageio.get_writer(path, fps=fps, codec="libx264", pixelformat="yuv420p")
    try:
        for frame in frames:
            writer.append_data(imageio.imread(io.BytesIO(frame)))
    finally:
        writer.close()


def _fal_auth_headers() -> Dict[str, str]:
    key = _env("FAL_API_KEY")
    if not key:
        raise RuntimeError("FAL_API_KEY is not configured")
    return {
        "Accept": "application/json",
        "Authorization": "Key " + key,
        "Content-Type": "application/json",
    }


def _fal_http_json(method: str, url: str, body: Optional[Dict[str, Any]] = None, timeout: int = 60) -> Dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_fal_auth_headers(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError("fal HTTP %s: %s" % (exc.code, detail)) from exc
    except (urllib.error.URLError, OSError) as exc:
        raise RuntimeError("fal HTTP failed: %s" % exc) from exc
    if not raw.strip():
        return {}
    value = json.loads(raw)
    return value if isinstance(value, dict) else {"result": value}


def _download_url_to_path(url: str, dest_path: str, timeout: int = 120) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "MasterNoder/1.0"}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest_path, "wb") as handle:
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            handle.write(chunk)


def _generate_fal_queue_clip(
    prompt: str,
    dest_dir: Optional[str] = None,
    timeout: int = 180,
) -> Dict[str, Any]:
    """HTTP queue fallback when the Krea realtime websocket is unavailable."""
    model = (_env("FAL_VIDEO_MODEL") or FAL_DEFAULT_VIDEO_MODEL).strip().strip("/")
    submit_url = FAL_QUEUE_HTTP + "/" + model
    try:
        submitted = _fal_http_json(
            "POST",
            submit_url,
            {"prompt": prompt[:2000]},
            timeout=min(60, timeout),
        )
    except RuntimeError as exc:
        return {"success": False, "error": str(exc), "canvas": "fal_krea", "mode": "queue"}

    status_url = submitted.get("status_url")
    response_url = submitted.get("response_url")
    request_id = submitted.get("request_id")
    if not status_url or not response_url:
        return {
            "success": False,
            "error": "fal queue submit did not return status/response URLs",
            "canvas": "fal_krea",
            "mode": "queue",
        }

    deadline = time.time() + max(20, timeout)
    status = str(submitted.get("status") or "IN_QUEUE")
    while time.time() < deadline and status in ("IN_QUEUE", "IN_PROGRESS"):
        time.sleep(2)
        try:
            payload = _fal_http_json("GET", status_url, timeout=30)
        except RuntimeError as exc:
            return {"success": False, "error": str(exc), "canvas": "fal_krea", "mode": "queue"}
        status = str(payload.get("status") or "")
        if status in ("FAILED", "ERROR", "CANCELLED"):
            return {
                "success": False,
                "error": "fal queue %s: %s" % (status, payload.get("error") or payload.get("detail") or "failed"),
                "canvas": "fal_krea",
                "mode": "queue",
                "request_id": request_id,
            }

    if status != "COMPLETED":
        return {
            "success": False,
            "error": "fal queue timed out with status %s" % (status or "unknown"),
            "canvas": "fal_krea",
            "mode": "queue",
            "request_id": request_id,
        }

    try:
        result = _fal_http_json("GET", response_url, timeout=60)
    except RuntimeError as exc:
        return {"success": False, "error": str(exc), "canvas": "fal_krea", "mode": "queue"}

    video = result.get("video") if isinstance(result.get("video"), dict) else {}
    video_url = video.get("url") or result.get("video_url") or result.get("url")
    if not isinstance(video_url, str) or not video_url.startswith("http"):
        return {
            "success": False,
            "error": "fal queue completed without a video URL",
            "canvas": "fal_krea",
            "mode": "queue",
            "request_id": request_id,
        }

    if dest_dir is None:
        dest_dir = os.environ.get("VIDEOS_DIR") or os.getcwd()
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, "fal_queue_%s.mp4" % uuid.uuid4().hex[:8])
    try:
        _download_url_to_path(video_url, path, timeout=120)
    except Exception as exc:
        return {
            "success": False,
            "error": "fal queue download failed: %s" % _safe_error(exc),
            "canvas": "fal_krea",
            "mode": "queue",
        }
    return {
        "success": True,
        "local_path": path,
        "canvas": "fal_krea",
        "mode": "queue",
        "model": model,
        "request_id": request_id,
    }


def _generate_fal_clip(
    prompt: str,
    dest_dir: Optional[str] = None,
    timeout: int = 90,
) -> Dict[str, Any]:
    """Try Krea realtime websocket frames; fall back to fal HTTP queue video."""
    force_queue = (_env("FAL_FORCE_QUEUE") or "").strip().lower() in ("1", "true", "yes", "on")
    if force_queue or not _fal_dependencies_available():
        return _generate_fal_queue_clip(prompt, dest_dir=dest_dir, timeout=max(timeout, 120))

    try:
        token = _fal_token()
    except RuntimeError as exc:
        return _generate_fal_queue_clip(prompt, dest_dir=dest_dir, timeout=max(timeout, 120)) or {
            "success": False,
            "error": str(exc),
            "canvas": "fal_krea",
        }

    fps = max(1, min(30, int(_env("FAL_KREA_FPS") or 12)))
    frame_target = max(2, min(300, int(_env("FAL_KREA_FRAMES") or 48)))
    width = max(64, int(_env("FAL_KREA_WIDTH") or 768))
    height = max(64, int(_env("FAL_KREA_HEIGHT") or 432))
    width = round(width / 8) * 8
    height = round(height / 8) * 8
    ws_url = FAL_KREA_WS + "?fal_jwt_token=" + urllib.parse.quote(token, safe="")
    frames: List[bytes] = []
    sock = None
    ws_error: Optional[str] = None
    try:
        sock = websocket.create_connection(ws_url, timeout=min(30, timeout))
        deadline = time.time() + max(10, timeout)
        ready = False
        while time.time() < deadline and len(frames) < frame_target:
            remaining = max(1, deadline - time.time())
            sock.settimeout(remaining)
            message = sock.recv()
            if isinstance(message, str):
                event = json.loads(message)
                if event.get("error"):
                    raise RuntimeError("fal Krea error: %s" % event["error"])
                if event.get("status") == "ready" and not ready:
                    ready = True
                    sock.send_binary(msgpack.packb({
                        "prompt": prompt[:2000],
                        "num_blocks": max(10, min(50, int(_env("FAL_KREA_BLOCKS") or 20))),
                        "num_denoising_steps": 4,
                        "strength": 0.8,
                        "width": width,
                        "height": height,
                        "seed": secrets.randbelow(1 << 24),
                    }, use_bin_type=True))
            elif ready and isinstance(message, (bytes, bytearray)) and len(message) > 100:
                frames.append(bytes(message))
    except Exception as exc:
        ws_error = _safe_error(exc, token)
    finally:
        if sock is not None:
            sock.close()

    if len(frames) >= 2:
        if dest_dir is None:
            dest_dir = os.environ.get("VIDEOS_DIR") or os.getcwd()
        os.makedirs(dest_dir, exist_ok=True)
        path = os.path.join(dest_dir, "fal_krea_%s.mp4" % uuid.uuid4().hex[:8])
        try:
            _write_frame_video(frames, path, fps)
        except Exception as exc:
            return {"success": False, "error": "fal Krea encode failed: %s" % exc, "canvas": "fal_krea"}
        return {
            "success": True,
            "local_path": path,
            "canvas": "fal_krea",
            "mode": "realtime",
            "frame_count": len(frames),
            "fps": fps,
        }

    # Realtime app may be offline/unavailable for this account — use queue video.
    fallback = _generate_fal_queue_clip(prompt, dest_dir=dest_dir, timeout=max(timeout, 120))
    if fallback.get("success"):
        fallback["realtime_error"] = ws_error or "fewer than two realtime frames"
        return fallback
    return {
        "success": False,
        "error": "fal realtime failed (%s); queue fallback: %s"
        % (ws_error or "no frames", fallback.get("error") or "failed"),
        "canvas": "fal_krea",
    }


def _mcp_payload(raw: bytes, content_type: str) -> Dict[str, Any]:
    text = raw.decode("utf-8", errors="replace")
    if not text.strip():
        return {}
    if "text/event-stream" in content_type:
        for line in reversed(text.splitlines()):
            if line.startswith("data:"):
                value = json.loads(line[5:].strip())
                if isinstance(value, dict):
                    return value
        return {}
    value = json.loads(text)
    return value if isinstance(value, dict) else {}


def _mcp_post(
    body: Dict[str, Any],
    *,
    session_id: Optional[str] = None,
    timeout: int = 60,
) -> tuple[Dict[str, Any], Optional[str]]:
    headers = auth_headers("dramacanva")
    headers["Accept"] = "application/json, text/event-stream"
    headers["MCP-Protocol-Version"] = MCP_PROTOCOL_VERSION
    headers["User-Agent"] = "MasterNoder/1.0"
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    req = urllib.request.Request(
        DRAMACANVA_HTTP,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = _mcp_payload(resp.read(), resp.headers.get("Content-Type", ""))
            returned_session = resp.headers.get("Mcp-Session-Id") or session_id
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError("DramaCanvas HTTP %s: %s" % (exc.code, detail)) from exc
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("DramaCanvas request failed: %s" % exc) from exc
    return payload, returned_session


def _dramacanva_arguments(tool: Dict[str, Any], prompt: str) -> Dict[str, Any]:
    schema = tool.get("inputSchema") if isinstance(tool.get("inputSchema"), dict) else {}
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    required = schema.get("required") if isinstance(schema.get("required"), list) else []
    args: Dict[str, Any] = {}
    for name in ("prompt", "task", "instruction", "goal", "message"):
        if name in properties:
            args[name] = prompt
            break
    if "idempotencyKey" in properties:
        args["idempotencyKey"] = "masternoder-" + uuid.uuid4().hex
    project_id = _env("DRAMACANVA_PROJECT_ID")
    for name in ("projectId", "project_id"):
        if name in properties and project_id:
            args[name] = project_id
    unsupported = [name for name in required if name not in args]
    if unsupported:
        raise RuntimeError(
            "DramaCanvas tool %s also needs: %s"
            % (tool.get("name"), ", ".join(str(name) for name in unsupported))
        )
    return args


def prepare_film_project(prompt: str, timeout: int = 90) -> Dict[str, Any]:
    """Send a film brief to the DramaCanvas Agent for storyboard planning."""
    if not is_available("dramacanva", purpose="planning"):
        return {"success": False, "error": "DRAMACANVA_API_KEY is not configured"}
    request_id = uuid.uuid4().hex
    initialize = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "initialize",
        "params": {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "MasterNoder film pipeline", "version": "1"},
        },
    }
    try:
        _initialized, session_id = _mcp_post(initialize, timeout=timeout)
        _mcp_post(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            session_id=session_id,
            timeout=timeout,
        )
        listed, session_id = _mcp_post(
            {"jsonrpc": "2.0", "id": uuid.uuid4().hex, "method": "tools/list", "params": {}},
            session_id=session_id,
            timeout=timeout,
        )
        result = listed.get("result") if isinstance(listed.get("result"), dict) else {}
        tools = result.get("tools") if isinstance(result.get("tools"), list) else []
        tool = next(
            (item for item in tools if isinstance(item, dict) and item.get("name") == "agent_start"),
            None,
        )
        if tool is None:
            return {"success": False, "error": "DramaCanvas did not advertise agent_start", "canvas": "dramacanva"}
        arguments = _dramacanva_arguments(tool, prompt)
        called, _session_id = _mcp_post(
            {
                "jsonrpc": "2.0",
                "id": uuid.uuid4().hex,
                "method": "tools/call",
                "params": {"name": "agent_start", "arguments": arguments},
            },
            session_id=session_id,
            timeout=timeout,
        )
    except RuntimeError as exc:
        return {"success": False, "error": _safe_error(exc), "canvas": "dramacanva"}
    if called.get("error"):
        return {"success": False, "error": str(called["error"])[:300], "canvas": "dramacanva"}
    return {
        "success": True,
        "canvas": "dramacanva",
        "stage": "planning",
        "result": called.get("result"),
    }


def _planning_text(result: Any) -> str:
    """Pull human-readable storyboard text from a DramaCanvas MCP result."""
    if result is None:
        return ""
    if isinstance(result, str):
        return result.strip()
    if isinstance(result, list):
        parts = [_planning_text(item) for item in result]
        return "\n".join(part for part in parts if part).strip()[:2000]
    if isinstance(result, dict):
        content = result.get("content")
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("text"):
                    parts.append(str(item["text"]))
                elif isinstance(item, str):
                    parts.append(item)
            if parts:
                return "\n".join(parts).strip()[:2000]
        for key in ("text", "message", "summary", "storyboard", "brief", "output"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:2000]
            nested = _planning_text(value)
            if nested:
                return nested
        try:
            return json.dumps(result)[:2000]
        except (TypeError, ValueError):
            return str(result)[:2000]
    return str(result)[:2000]


def _generate_one_canvas_clip(
    prompt: str,
    canvas_id: str,
    dest_dir: Optional[str] = None,
    timeout: int = 180,
) -> Dict[str, Any]:
    if canvas_id in ("comfy_local", "comfy_cloud"):
        return _generate_comfy_clip(prompt, dest_dir, timeout, canvas_id=canvas_id)
    if canvas_id == "fal_krea":
        if _fal_is_skipped():
            return {
                "success": False,
                "error": "fal skipped (exhausted/locked balance)",
                "canvas": "fal_krea",
            }
        clip = _generate_fal_clip(prompt, dest_dir, timeout)
        if not clip.get("success"):
            _note_fal_error(clip.get("error"))
        return clip
    return {"success": False, "error": "Unknown film canvas %s" % canvas_id, "canvas": canvas_id}


def generate_clip(
    prompt: str,
    dest_dir: Optional[str] = None,
    timeout: int = 180,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a local clip; auto mode walks every available renderer."""
    if provider:
        if not is_available(provider, purpose="render"):
            return {
                "success": False,
                "error": "Film canvas %s is not available" % provider,
                "canvas": provider,
            }
        return _generate_one_canvas_clip(prompt, provider, dest_dir, timeout)

    candidates = list_render_canvases()
    if not candidates:
        return {"success": False, "error": "No render-capable film canvas is configured"}

    errors: List[str] = []
    for canvas_id in candidates:
        clip = _generate_one_canvas_clip(prompt, canvas_id, dest_dir, timeout)
        if clip.get("success") and clip.get("local_path"):
            if errors:
                clip["fallbacks_tried"] = list(errors)
            return clip
        err = clip.get("error") or ("%s failed" % canvas_id)
        errors.append("%s: %s" % (canvas_id, err))
    return {
        "success": False,
        "error": "All film canvases failed: " + " | ".join(errors)[:500],
        "attempts": errors,
    }


def _external_backend_module(backend: str):
    return {
        "runway": _runway_service,
        "modelslab": _modelslab_service,
        "pika": _pika_service,
        "replicate": _replicate_service,
        "heygen": _heygen_service,
    }.get(backend)


def _external_backend_available(backend: str) -> bool:
    mod = _external_backend_module(backend)
    if mod is None or not hasattr(mod, "is_available"):
        return False
    try:
        return bool(mod.is_available())
    except Exception:
        return False


def _generate_external_clip(
    backend: str,
    prompt: str,
    dest_dir: Optional[str] = None,
    timeout: int = 120,
) -> Dict[str, Any]:
    """Try a non-canvas video backend (Runway / ModelsLab / Pika / …)."""
    mod = _external_backend_module(backend)
    if mod is None or not hasattr(mod, "generate_clip"):
        return {"success": False, "error": "%s unavailable" % backend, "canvas": backend}
    if not _external_backend_available(backend):
        return {"success": False, "error": "%s not configured" % backend, "canvas": backend}

    try:
        if backend == "modelslab":
            out = mod.generate_clip(prompt, timeout=min(timeout, 120))
        elif backend == "runway":
            out = mod.generate_clip(prompt, dest_dir=dest_dir, timeout=min(timeout, 120))
        elif backend == "pika":
            out = mod.generate_clip(prompt, dest_dir=dest_dir, timeout=min(timeout, 120))
        elif backend == "replicate":
            out = mod.generate_clip(prompt, dest_dir=dest_dir, timeout=min(timeout, 180))
        elif backend == "heygen":
            out = mod.generate_clip(prompt, dest_dir=dest_dir, timeout=min(timeout, 180))
        else:
            return {"success": False, "error": "Unknown backend %s" % backend, "canvas": backend}
    except Exception as exc:
        return {"success": False, "error": "%s: %s" % (backend, _safe_error(exc)), "canvas": backend}

    if not isinstance(out, dict):
        return {"success": False, "error": "%s returned no result" % backend, "canvas": backend}
    out = dict(out)
    out["canvas"] = backend
    if out.get("success") and out.get("local_path"):
        return out
    # Some backends return only a remote URL — download when possible.
    url = out.get("video_url") or out.get("url")
    if out.get("success") and isinstance(url, str) and url.startswith("http") and not out.get("local_path"):
        if dest_dir is None:
            dest_dir = os.environ.get("VIDEOS_DIR") or os.getcwd()
        os.makedirs(dest_dir, exist_ok=True)
        path = os.path.join(dest_dir, "%s_%s.mp4" % (backend, uuid.uuid4().hex[:8]))
        try:
            _download_url_to_path(url, path, timeout=120)
            out["local_path"] = path
            return out
        except Exception as exc:
            return {
                "success": False,
                "error": "%s download failed: %s" % (backend, _safe_error(exc)),
                "canvas": backend,
            }
    return {
        "success": False,
        "error": out.get("error") or ("%s failed" % backend),
        "canvas": backend,
    }


def _write_local_standby_image(dest_dir: str, prompt: str) -> Optional[str]:
    """Network-free standby frame so Play Movie still works offline."""
    beat = {
        "index": 0,
        "title": "STANDBY",
        "description": (prompt or "FILM CANVAS").strip()[:120],
        "shot_type": "establishing",
        "prompt": prompt or "FILM CANVAS",
    }
    return _write_beat_scene_image(dest_dir, beat, face_path=None)


_BEAT_PALETTES = (
    ((2, 18, 28), (0, 210, 255), (180, 240, 255)),      # teal night
    ((28, 8, 4), (255, 120, 40), (255, 220, 180)),      # amber fire
    ((8, 4, 28), (160, 80, 255), (220, 200, 255)),      # violet noir
    ((4, 24, 12), (0, 255, 140), (180, 255, 210)),      # emerald
    ((24, 16, 4), (255, 200, 60), (255, 240, 180)),     # gold dawn
    ((4, 12, 24), (80, 160, 255), (200, 230, 255)),     # steel blue
    ((22, 4, 14), (255, 60, 120), (255, 190, 210)),     # crimson
    ((12, 12, 12), (220, 220, 220), (255, 255, 255)),   # mono
)

_SHOT_TYPES = (
    "establishing",
    "character",
    "action",
    "detail",
    "reaction",
    "closing",
)


def _beat_count_for_duration(duration: float) -> int:
    """Always multiple distinct beats — never a single still pan for a whole movie."""
    seconds = max(2.0, float(duration or 8.0))
    if seconds <= 4:
        return 2
    if seconds <= 8:
        return 3
    if seconds <= 16:
        return 4
    if seconds <= 30:
        return 5
    if seconds <= 60:
        return 6
    return min(8, max(6, int(round(seconds / 12.0))))


def _parse_direction_beats(direction: str, want: int) -> List[Dict[str, str]]:
    """Pull numbered / bulleted visual beats from LLM / DramaCanvas direction."""
    text = (direction or "").strip()
    if not text:
        return []
    lines = []
    for raw in text.replace("\r", "\n").split("\n"):
        line = raw.strip().lstrip("-*•").strip()
        if not line:
            continue
        # Strip leading "1." / "Beat 2:" / "[groq]" noise when useful.
        if line.startswith("[") and "]" in line[:24]:
            continue
        cleaned = line
        for prefix in ("Beat ", "Shot ", "Scene ", "BEAT ", "SHOT "):
            if cleaned.upper().startswith(prefix.upper()):
                cleaned = cleaned[len(prefix):].lstrip("0123456789.:)- ").strip()
                break
        else:
            if len(cleaned) > 2 and cleaned[0].isdigit():
                cleaned = cleaned.lstrip("0123456789.:)- ").strip()
        if len(cleaned) < 8:
            continue
        lines.append(cleaned[:220])
    # Also split on semicolons / " | " if we still have too few lines.
    if len(lines) < want:
        for chunk in text.replace("|", "\n").split("\n"):
            piece = chunk.strip()
            if len(piece) >= 12 and piece not in lines:
                lines.append(piece[:220])
            if len(lines) >= want * 2:
                break
    return [{"description": line, "title": line.split(".")[0][:42]} for line in lines[:want]]


def _build_storyboard_beats(
    prompt: str,
    duration: float,
    direction: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Full storyboard: N distinct shots covering the whole runtime."""
    want = _beat_count_for_duration(duration)
    seconds = max(2.0, float(duration or 8.0))
    parsed = _parse_direction_beats(direction or "", want)
    brief = (prompt or "cinematic scene").strip()
    # Drop meta "Storyboard direction" / face-reference lines from the brief.
    brief_core = brief.split("\n\nStoryboard direction:")[0].strip()
    brief_core = brief_core.split("[face reference")[0].strip() or brief_core

    templates = [
        ("establishing", "Wide establishing shot of %s", "Open on the world"),
        ("character", "Hero / subject close-up inside %s", "Meet the subject"),
        ("action", "Dynamic mid shot — motion and tension in %s", "Conflict rises"),
        ("detail", "Insert detail / prop / screen readout from %s", "Key detail"),
        ("reaction", "Reaction shot — stakes land in %s", "Emotional beat"),
        ("closing", "Closing wide / pull-back finale of %s", "Resolution"),
        ("action", "Secondary action angle through %s", "Escalate"),
        ("detail", "Atmospheric texture pass over %s", "Atmosphere"),
    ]

    beats: List[Dict[str, Any]] = []
    for index in range(want):
        shot_type, prompt_fmt, title_fallback = templates[index % len(templates)]
        if index < len(parsed):
            description = parsed[index]["description"]
            title = parsed[index].get("title") or title_fallback
        else:
            description = prompt_fmt % brief_core[:160]
            title = title_fallback
        beats.append({
            "index": index,
            "title": str(title)[:48],
            "description": str(description)[:280],
            "shot_type": shot_type,
            "prompt": (
                "%s. Shot type: %s. Scene: %s. Cinematic film still, detailed, "
                "16:9, dramatic lighting."
            ) % (description[:180], shot_type, brief_core[:120]),
        })

    # Distribute duration across beats (min ~1.2s each).
    remaining = seconds
    for index, beat in enumerate(beats):
        left = len(beats) - index
        if left == 1:
            beat_sec = remaining
        else:
            beat_sec = max(1.2, round(remaining / left, 2))
        remaining = max(0.0, round(remaining - beat_sec, 2))
        beat["duration_sec"] = beat_sec
        beat["motion"] = (
            "zoom_in", "pan_right", "zoom_out", "pan_left",
            "zoom_in", "pan_right", "zoom_out", "pan_left",
        )[index % 8]
    return beats


def _write_beat_scene_image(
    dest_dir: str,
    beat: Dict[str, Any],
    face_path: Optional[str] = None,
) -> Optional[str]:
    """Paint a distinct storyboard frame per beat (different material each shot)."""
    os.makedirs(dest_dir, exist_ok=True)
    index = int(beat.get("index") or 0)
    palette = _BEAT_PALETTES[index % len(_BEAT_PALETTES)]
    bg, accent, text_color = palette
    shot = str(beat.get("shot_type") or _SHOT_TYPES[index % len(_SHOT_TYPES)])
    path = os.path.join(
        dest_dir,
        "beat_scene_%s_%s.jpg" % (index, uuid.uuid4().hex[:8]),
    )
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (1280, 720), bg)
        draw = ImageDraw.Draw(img)

        # Unique geometry per shot type so beats never look identical.
        if shot == "establishing":
            for y in range(0, 720, 6):
                shade = tuple(min(255, c + (y % 50) // 3) for c in bg)
                draw.line([(0, y), (1280, y)], fill=shade)
            draw.polygon([(0, 520), (420, 360), (900, 560), (1280, 480), (1280, 720), (0, 720)], fill=accent)
            draw.rectangle([(0, 0), (1280, 90)], fill=(0, 0, 0))
        elif shot == "character":
            draw.ellipse([(720, 80), (1180, 640)], outline=accent, width=8)
            draw.rectangle([(40, 80), (640, 640)], outline=accent, width=4)
            for y in range(100, 620, 18):
                draw.line([(60, y), (620, y)], fill=tuple(min(255, c + 30) for c in bg))
        elif shot == "action":
            for i in range(0, 12):
                y0 = 40 + i * 55
                draw.polygon(
                    [(80 + i * 30, y0), (380 + i * 40, y0 + 40), (60 + i * 20, y0 + 80)],
                    outline=accent,
                )
            draw.rectangle([(900, 40), (1240, 680)], fill=tuple(min(255, c + 18) for c in bg), outline=accent, width=3)
        elif shot == "detail":
            draw.rectangle([(160, 120), (1120, 600)], outline=accent, width=6)
            draw.rectangle([(220, 180), (1060, 540)], fill=tuple(min(255, c + 22) for c in bg))
            for x in range(260, 1020, 40):
                draw.line([(x, 200), (x, 520)], fill=accent)
        elif shot == "reaction":
            draw.ellipse([(340, 80), (940, 680)], outline=accent, width=10)
            draw.ellipse([(440, 180), (840, 580)], fill=tuple(min(255, c + 14) for c in bg))
        else:  # closing
            for i in range(8):
                inset = 30 + i * 40
                draw.rectangle(
                    [(inset, inset), (1280 - inset, 720 - inset)],
                    outline=tuple(min(255, accent[j] - i * 8) for j in range(3)),
                    width=2,
                )

        draw.rectangle([(36, 36), (1244, 684)], outline=accent, width=3)
        badge = "SHOT %02d · %s" % (index + 1, shot.upper())
        title = str(beat.get("title") or "Beat")[:48]
        desc = str(beat.get("description") or beat.get("prompt") or "")[:90]
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((70, 58), badge, fill=accent, font=font)
        draw.text((70, 620), title, fill=text_color, font=font)
        draw.text((70, 650), desc, fill=tuple(max(0, c - 40) for c in text_color), font=font)

        if face_path and os.path.isfile(face_path) and shot in ("character", "reaction", "closing"):
            try:
                face = Image.open(face_path).convert("RGB")
                face.thumbnail((280, 280))
                fx, fy = (860, 220) if shot != "closing" else (500, 220)
                img.paste(face, (fx, fy))
                draw.rectangle(
                    [(fx - 4, fy - 4), (fx + face.size[0] + 4, fy + face.size[1] + 4)],
                    outline=accent,
                    width=3,
                )
            except Exception:
                pass

        img.save(path, format="JPEG", quality=90)
        return path
    except Exception:
        if imageio is not None:
            try:
                import numpy as np
                frame = np.zeros((720, 1280, 3), dtype="uint8")
                frame[:, :] = bg
                frame[40:80, :] = accent
                imageio.imwrite(path, frame)
                return path
            except Exception:
                return None
        return None


def _try_free_beat_image(prompt: str, dest_dir: str, seed: int) -> Optional[str]:
    """Best-effort unique AI still per beat with a short timeout (never block the movie)."""
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, "ai_beat_%s_%s.jpg" % (seed, uuid.uuid4().hex[:6]))
    try:
        encoded = urllib.parse.quote((prompt or "cinematic film still")[:320], safe="")
        url = (
            "https://image.pollinations.ai/prompt/%s"
            "?width=1280&height=720&nologo=true&enhance=true&seed=%d"
        ) % (encoded, int(seed) % 999999)
        req = urllib.request.Request(url, headers={"User-Agent": "MasterNoder/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            img_bytes = resp.read()
        if len(img_bytes) < 1000:
            return None
        with open(path, "wb") as handle:
            handle.write(img_bytes)
        return path
    except Exception:
        return None


def _ffmpeg_color_movie(dest_dir: str, duration: float = 5.0) -> Dict[str, Any]:
    """Guaranteed local MP4 via ffmpeg lavfi (no API keys, no network images)."""
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, "ffmpeg_still_%s.mp4" % uuid.uuid4().hex[:8])
    seconds = max(3, int(round(float(duration) or 5)))
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "color=c=0x02140c:s=1280x720:d=%s" % seconds,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        path,
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(20, seconds + 15),
            check=False,
        )
    except Exception as exc:
        return {"success": False, "error": "ffmpeg still failed: %s" % exc, "canvas": "free_still"}
    if proc.returncode != 0 or not os.path.isfile(path):
        err = (proc.stderr or proc.stdout or "ffmpeg failed")[-300:]
        return {"success": False, "error": "ffmpeg still failed: %s" % err, "canvas": "free_still"}
    return {
        "success": True,
        "local_path": path,
        "canvas": "free_still",
        "source_image": "ffmpeg_lavfi",
        "fps": 25,
    }


def _ffmpeg_kenburns_movie(
    image_path: str,
    dest_path: str,
    duration: float = 8.0,
    fps: int = 25,
    motion: str = "zoom_in",
) -> Dict[str, Any]:
    """Animate one still with a chosen camera move (different per storyboard beat)."""
    seconds = max(1, min(120, int(round(float(duration) or 8))))
    frames = max(seconds * fps, fps)
    motion = (motion or "zoom_in").strip().lower()
    if motion == "zoom_out":
        z = "if(eq(on,1),1.45,max(1.0,1.45-0.0012*on))"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif motion == "pan_left":
        z = "1.25"
        x = "max(0,iw-iw/zoom)-on*2.2"
        y = "ih/2-(ih/zoom/2)"
    elif motion == "pan_right":
        z = "1.25"
        x = "min(iw-iw/zoom,on*2.2)"
        y = "ih/2-(ih/zoom/2)"
    else:  # zoom_in
        z = "min(1.0+0.0014*on,1.55)"
        x = "iw/2-(iw/zoom/2)+12*sin(on/70)"
        y = "ih/2-(ih/zoom/2)+8*cos(on/90)"
    vf = (
        "scale=8000:-1,"
        "zoompan=z='%s':x='%s':y='%s':d=%d:s=1280x720:fps=%d,"
        "eq=contrast=1.06:saturation=1.1,"
        "format=yuv420p"
    ) % (z, x, y, frames, fps)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-vf", vf,
        "-t", str(seconds),
        "-r", str(fps),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        dest_path,
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(45, seconds + 30),
            check=False,
        )
    except Exception as exc:
        return {"success": False, "error": "kenburns ffmpeg failed: %s" % exc}
    if proc.returncode != 0 or not os.path.isfile(dest_path):
        err = (proc.stderr or proc.stdout or "ffmpeg failed")[-400:]
        return {"success": False, "error": "kenburns ffmpeg failed: %s" % err}
    return {
        "success": True,
        "local_path": dest_path,
        "fps": fps,
        "duration_sec": seconds,
        "mode": "kenburns",
        "motion": motion,
    }


def _ffmpeg_concat_movies(paths: List[str], dest_path: str) -> Dict[str, Any]:
    if not paths:
        return {"success": False, "error": "no clips to concat"}
    if len(paths) == 1:
        try:
            os.replace(paths[0], dest_path)
            return {"success": True, "local_path": dest_path}
        except Exception:
            return {"success": True, "local_path": paths[0]}
    list_path = dest_path + ".txt"
    try:
        with open(list_path, "w", encoding="utf-8") as handle:
            for path in paths:
                handle.write("file '%s'\n" % path.replace("'", "'\\''"))
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_path,
            "-c", "copy",
            "-movflags", "+faststart",
            dest_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
        if proc.returncode != 0 or not os.path.isfile(dest_path):
            # Re-encode fallback when stream copy fails.
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_path,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                dest_path,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False)
        if proc.returncode != 0 or not os.path.isfile(dest_path):
            err = (proc.stderr or proc.stdout or "concat failed")[-300:]
            return {"success": False, "error": "concat failed: %s" % err}
        return {"success": True, "local_path": dest_path}
    except Exception as exc:
        return {"success": False, "error": "concat failed: %s" % exc}
    finally:
        try:
            if os.path.isfile(list_path):
                os.remove(list_path)
        except Exception:
            pass


def _encode_image_to_mp4(
    image_path: str,
    dest_path: str,
    duration: float = 6.0,
    motion: str = "zoom_in",
) -> Dict[str, Any]:
    """Encode a still into a motion MP4 (ffmpeg camera move, moviepy fallback)."""
    kb = _ffmpeg_kenburns_movie(
        image_path, dest_path, duration=duration, fps=25, motion=motion,
    )
    if kb.get("success"):
        return kb

    if _MoviePyImageClip is None:
        return {"success": False, "error": kb.get("error") or "moviepy unavailable for free movie"}
    clip = None
    try:
        seconds = max(1.0, min(120.0, float(duration or 6.0)))
        clip = _MoviePyImageClip(image_path, duration=seconds)
        if hasattr(clip, "resized"):
            clip = clip.resized(new_size=(1280, 720))
        elif hasattr(clip, "resize"):
            clip = clip.resize(new_size=(1280, 720))
        write_kwargs = {"codec": "libx264", "audio": False, "fps": 24}
        try:
            clip.write_videofile(dest_path, logger=None, **write_kwargs)
        except TypeError:
            clip.write_videofile(dest_path, verbose=False, logger=None, **write_kwargs)
    except Exception as exc:
        return {
            "success": False,
            "error": "movie encode failed: %s | %s" % (_safe_error(exc), kb.get("error") or ""),
        }
    finally:
        try:
            if clip is not None:
                clip.close()
        except Exception:
            pass
    if not os.path.isfile(dest_path):
        return {"success": False, "error": "movie mp4 missing"}
    return {"success": True, "local_path": dest_path, "fps": 24, "mode": "moviepy_still", "motion": motion}


def _collect_movie_stills(
    prompt: str,
    dest_dir: str,
    duration: float,
    face_path: Optional[str] = None,
    direction: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Gather one unique still per storyboard beat (AI image or painted scene)."""
    beats = _build_storyboard_beats(prompt, duration, direction=direction)
    stills: List[Dict[str, str]] = []
    for beat in beats:
        source = "beat_scene"
        path = _try_free_beat_image(
            beat.get("prompt") or beat.get("description") or prompt,
            dest_dir,
            seed=1000 + int(beat.get("index") or 0) * 97,
        )
        if path:
            source = "free_ai"
        else:
            path = _write_beat_scene_image(dest_dir, beat, face_path=face_path)
        if not path:
            continue
        stills.append({
            "path": path,
            "source": source,
            "title": str(beat.get("title") or ""),
            "shot_type": str(beat.get("shot_type") or ""),
            "motion": str(beat.get("motion") or "zoom_in"),
            "duration_sec": float(beat.get("duration_sec") or 2.0),
            "description": str(beat.get("description") or ""),
        })
    return stills


def _generate_free_still_movie(
    prompt: str,
    dest_dir: Optional[str] = None,
    duration: float = 6.0,
    face_path: Optional[str] = None,
    direction: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a multi-scene storyboard movie: distinct material per beat, full runtime."""
    if dest_dir is None:
        dest_dir = os.environ.get("VIDEOS_DIR") or os.getcwd()
    os.makedirs(dest_dir, exist_ok=True)
    errors: List[str] = []
    duration = max(2.0, min(120.0, float(duration or 6.0)))
    storyboard = _build_storyboard_beats(prompt, duration, direction=direction)

    stills = _collect_movie_stills(
        prompt,
        dest_dir,
        duration,
        face_path=face_path,
        direction=direction,
    )
    if not stills:
        errors.append("no still frames available")
        ffmpeg_clip = _ffmpeg_color_movie(dest_dir, duration=duration)
        if ffmpeg_clip.get("success"):
            ffmpeg_clip["prior_errors"] = errors
            return ffmpeg_clip
        return {
            "success": False,
            "error": "free movie failed: " + " | ".join(errors + [ffmpeg_clip.get("error") or ""])[:400],
            "canvas": "free_still",
        }

    beat_paths: List[str] = []
    beat_meta: List[Dict[str, Any]] = []
    for index, still in enumerate(stills):
        beat_sec = float(still.get("duration_sec") or (duration / max(1, len(stills))))
        part = os.path.join(dest_dir, "beat_%s_%s.mp4" % (uuid.uuid4().hex[:8], index))
        encoded = _encode_image_to_mp4(
            still["path"],
            part,
            duration=beat_sec,
            motion=str(still.get("motion") or "zoom_in"),
        )
        if encoded.get("success") and encoded.get("local_path"):
            beat_paths.append(encoded["local_path"])
            beat_meta.append({
                "index": index,
                "title": still.get("title"),
                "shot_type": still.get("shot_type"),
                "source": still.get("source"),
                "motion": still.get("motion"),
                "duration_sec": beat_sec,
                "description": still.get("description"),
            })
        else:
            errors.append(str(encoded.get("error") or "beat encode failed"))

    if not beat_paths:
        ffmpeg_clip = _ffmpeg_color_movie(dest_dir, duration=duration)
        if ffmpeg_clip.get("success"):
            ffmpeg_clip["prior_errors"] = errors[:5]
            return ffmpeg_clip
        return {
            "success": False,
            "error": "free movie failed: " + " | ".join(errors)[:400],
            "canvas": "free_still",
        }

    dest = os.path.join(dest_dir, "movie_%s.mp4" % uuid.uuid4().hex[:8])
    merged = _ffmpeg_concat_movies(beat_paths, dest)
    sources = sorted({str(s.get("source") or "") for s in stills if s.get("source")})
    if merged.get("success") and merged.get("local_path"):
        return {
            "success": True,
            "local_path": merged["local_path"],
            "canvas": "free_still",
            "source_image": ",".join(sources) or "storyboard",
            "fps": 25,
            "duration_sec": int(round(duration)),
            "beats": len(beat_paths),
            "beat_plan": beat_meta or storyboard,
            "mode": "storyboard_movie",
        }

    if beat_paths:
        return {
            "success": True,
            "local_path": beat_paths[0],
            "canvas": "free_still",
            "source_image": ",".join(sources) or "storyboard",
            "fps": 25,
            "duration_sec": int(round(duration)),
            "beats": len(beat_paths),
            "beat_plan": beat_meta,
            "mode": "storyboard_movie",
            "concat_error": merged.get("error"),
        }
    errors.append(str(merged.get("error") or "concat failed"))
    return {
        "success": False,
        "error": "free movie failed: " + " | ".join(errors)[:400],
        "canvas": "free_still",
    }


def pipeline_render_available() -> bool:
    """True when interactive movie can produce an MP4 via any backend."""
    if list_render_canvases():
        return True
    if any(_external_backend_available(backend) for backend in _EXTERNAL_CLIP_BACKENDS):
        return True
    if _free_image_service is not None and hasattr(_free_image_service, "is_available"):
        try:
            return bool(_free_image_service.is_available())
        except Exception:
            return _MoviePyImageClip is not None
    return _MoviePyImageClip is not None


def _plan_with_all_llms(brief: str, timeout: int = 25) -> Dict[str, Any]:
    """Ask every configured LLM for interactive-movie direction and merge."""
    if _video_ai_bridge is None or not hasattr(_video_ai_bridge, "complete_multi_provider"):
        return {"success": False, "providers": [], "direction": ""}
    system = (
        "You write a complete multi-shot storyboard for a short interactive monitor film. "
        "Return 3-6 numbered beats. Each beat must be a DIFFERENT shot "
        "(establishing / character / action / detail / reaction / closing) with concrete "
        "visual detail, camera move, and mood. No preamble."
    )
    user = (
        "Scene brief:\n%s\n\n"
        "Write the full storyboard as numbered beats the renderer can follow. "
        "Every beat must describe different material on screen — not the same picture."
    ) % brief[:800]
    try:
        multi = _video_ai_bridge.complete_multi_provider(
            "interactive_movie",
            user,
            system_prompt=system,
            max_providers=None,
            temperature=0.7,
            max_tokens=420,
            timeout=min(25, max(8, timeout)),
            extra_context={"use_all_ais": True, "quality_mode": "best"},
        )
    except Exception as exc:
        return {"success": False, "providers": [], "direction": "", "error": str(exc)[:200]}

    parts: List[str] = []
    providers: List[str] = []
    for pname, response in multi or []:
        content = (getattr(response, "content", None) or "").strip()
        if not content:
            continue
        providers.append(pname)
        parts.append("[%s]\n%s" % (pname, content[:700]))
    direction = "\n\n".join(parts).strip()[:1800]
    return {
        "success": bool(direction),
        "providers": providers,
        "direction": direction,
        "count": len(providers),
    }


def compose_interactive_movie(
    prompt: str,
    *,
    dest_dir: Optional[str] = None,
    timeout: int = 180,
    plan: bool = True,
    render_provider: Optional[str] = None,
    duration_sec: int = 8,
    face_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Plan with all configured LLMs + DramaCanvas, then render across the full pipeline.

    Order: multi-LLM direction → DramaCanvas → film canvases → Runway/ModelsLab/Pika/
    Replicate/HeyGen → free still. fal exhausted-balance errors skip fal and continue.
    """
    brief = (prompt or "").strip()
    if not brief:
        return {"success": False, "error": "prompt is required"}
    try:
        duration_sec = int(round(float(duration_sec)))
    except (TypeError, ValueError):
        duration_sec = 8
    duration_sec = max(2, min(120, duration_sec))
    face_path = face_path if face_path and os.path.isfile(face_path) else None

    planning: Optional[Dict[str, Any]] = None
    planner: Optional[str] = None
    llm_plan: Optional[Dict[str, Any]] = None
    extras: List[str] = ["Target length: %s seconds." % duration_sec]
    if face_path:
        extras.append(
            "Keep continuity with the attached face reference of a person; "
            "the same face should remain recognizable."
        )
    render_prompt = brief
    if extras:
        render_prompt = (brief + "\n\n" + " ".join(extras)).strip()
    direction_blocks: List[str] = []

    if plan:
        llm_plan = _plan_with_all_llms(render_prompt, timeout=min(30, max(10, timeout // 6)))
        if llm_plan.get("success") and llm_plan.get("direction"):
            direction_blocks.append(str(llm_plan["direction"]))
            planner = "all_llms"
        if is_available("dramacanva", purpose="planning"):
            # Keep DramaCanvas short so the monitor can still render on time.
            planning = prepare_film_project(render_prompt, timeout=min(45, max(15, timeout // 4)))
            if planning.get("success"):
                planned = _planning_text(planning.get("result"))
                if planned:
                    direction_blocks.append(planned)
                planner = "all_llms+dramacanva" if planner == "all_llms" else "dramacanva"
        if direction_blocks:
            render_prompt = (
                render_prompt + "\n\nStoryboard direction:\n" + "\n\n".join(direction_blocks)
            )[:2000]

    render_timeout = max(60, timeout - 45) if planner else max(60, timeout)
    attempts: List[str] = []
    direction_text = "\n\n".join(direction_blocks).strip()
    storyboard = _build_storyboard_beats(
        brief,
        float(duration_sec),
        direction=direction_text or None,
    )

    if render_provider:
        candidates = [render_provider] if is_available(render_provider, purpose="render") else []
    else:
        candidates = list_render_canvases()

    # Full pipeline: try a short canvas/external clip per storyboard beat, then stitch.
    # If paid canvases are exhausted we still assemble the detailed multi-beat movie locally.
    def _finish(clip: Dict[str, Any], renderer: str) -> Dict[str, Any]:
        return {
            "success": True,
            "planner": planner,
            "llm_plan": llm_plan,
            "renderer": renderer,
            "planning": planning,
            "prompt_used": render_prompt[:500],
            "local_path": clip.get("local_path"),
            "canvas": clip.get("canvas") or renderer,
            "frame_count": clip.get("frame_count"),
            "fps": clip.get("fps"),
            "duration_sec": duration_sec,
            "has_face": bool(face_path),
            "beats": clip.get("beats") or len(storyboard),
            "beat_plan": clip.get("beat_plan") or storyboard,
            "mode": clip.get("mode"),
            "attempts": attempts,
            "error": None,
        }

    # Explicit provider: still render multi-beat when possible, else one canvas clip.
    if render_provider and candidates:
        canvas_id = candidates[0]
        if len(storyboard) >= 2 and dest_dir:
            paths: List[str] = []
            meta: List[Dict[str, Any]] = []
            for beat in storyboard:
                beat_clip = _generate_one_canvas_clip(
                    str(beat.get("prompt") or render_prompt)[:500],
                    canvas_id,
                    dest_dir=dest_dir,
                    timeout=min(90, render_timeout),
                )
                if not (beat_clip.get("success") and beat_clip.get("local_path")):
                    attempts.append(
                        "%s@beat%s: %s"
                        % (canvas_id, beat.get("index"), beat_clip.get("error") or "failed")
                    )
                    paths = []
                    break
                paths.append(beat_clip["local_path"])
                meta.append({
                    "index": beat.get("index"),
                    "title": beat.get("title"),
                    "shot_type": beat.get("shot_type"),
                    "source": canvas_id,
                    "duration_sec": beat.get("duration_sec"),
                    "description": beat.get("description"),
                })
            if len(paths) >= 2:
                dest = os.path.join(dest_dir, "movie_%s.mp4" % uuid.uuid4().hex[:8])
                merged = _ffmpeg_concat_movies(paths, dest)
                if merged.get("success") and merged.get("local_path"):
                    return _finish(
                        {
                            "local_path": merged["local_path"],
                            "canvas": canvas_id,
                            "fps": 24,
                            "beats": len(paths),
                            "beat_plan": meta,
                            "mode": "pipeline_storyboard",
                        },
                        canvas_id,
                    )
        clip = _generate_one_canvas_clip(
            render_prompt[:500],
            canvas_id,
            dest_dir=dest_dir,
            timeout=render_timeout,
        )
        if clip.get("success") and clip.get("local_path"):
            return _finish(clip, canvas_id)
        attempts.append("%s: %s" % (canvas_id, clip.get("error") or "failed"))

    if not render_provider:
        # Try stitching distinct canvas/external clips per beat when providers still work.
        per_beat_paths: List[str] = []
        per_beat_meta: List[Dict[str, Any]] = []
        paid_ok = bool(candidates) and not _fal_is_skipped()
        if paid_ok and dest_dir and len(storyboard) >= 2:
            for beat in storyboard[: min(4, len(storyboard))]:
                beat_prompt = str(beat.get("prompt") or render_prompt)[:500]
                beat_clip = None
                for canvas_id in candidates[:2]:
                    beat_clip = _generate_one_canvas_clip(
                        beat_prompt,
                        canvas_id,
                        dest_dir=dest_dir,
                        timeout=min(90, render_timeout),
                    )
                    if beat_clip.get("success") and beat_clip.get("local_path"):
                        break
                    attempts.append(
                        "%s@beat%s: %s"
                        % (canvas_id, beat.get("index"), beat_clip.get("error") or "failed")
                    )
                    beat_clip = None
                if beat_clip and beat_clip.get("local_path"):
                    per_beat_paths.append(beat_clip["local_path"])
                    per_beat_meta.append({
                        "index": beat.get("index"),
                        "title": beat.get("title"),
                        "shot_type": beat.get("shot_type"),
                        "source": beat_clip.get("canvas") or "canvas",
                        "duration_sec": beat.get("duration_sec"),
                        "description": beat.get("description"),
                    })
                else:
                    # Stop paid multi-beat early once credits fail; finish locally.
                    if any("403" in (a or "") or "exhausted" in (a or "").lower() for a in attempts[-3:]):
                        break
            if len(per_beat_paths) >= 2:
                dest = os.path.join(dest_dir, "movie_%s.mp4" % uuid.uuid4().hex[:8])
                merged = _ffmpeg_concat_movies(per_beat_paths, dest)
                if merged.get("success") and merged.get("local_path"):
                    return _finish(
                        {
                            "local_path": merged["local_path"],
                            "canvas": "pipeline_storyboard",
                            "fps": 24,
                            "beats": len(per_beat_paths),
                            "beat_plan": per_beat_meta,
                            "mode": "pipeline_storyboard",
                        },
                        "pipeline_storyboard",
                    )

        # Guaranteed full-detail local storyboard movie (distinct material every beat).
        clip = _generate_free_still_movie(
            brief[:400],
            dest_dir=dest_dir,
            duration=float(duration_sec),
            face_path=face_path,
            direction=direction_text or None,
        )
        if clip.get("success") and clip.get("local_path"):
            return _finish(clip, "free_still")
        attempts.append("free_still: %s" % (clip.get("error") or "failed"))

        for backend in _EXTERNAL_CLIP_BACKENDS:
            clip = _generate_external_clip(
                backend,
                render_prompt[:500],
                dest_dir=dest_dir,
                timeout=min(45, render_timeout),
            )
            if clip.get("success") and clip.get("local_path"):
                return _finish(clip, backend)
            attempts.append("%s: %s" % (backend, clip.get("error") or "failed"))

    return {
        "success": False,
        "error": "All pipeline renderers failed: " + (" | ".join(attempts)[:500] or "none available"),
        "planner": planner,
        "llm_plan": llm_plan,
        "renderer": None,
        "planning": planning,
        "prompt_used": render_prompt[:500],
        "duration_sec": duration_sec,
        "has_face": bool(face_path),
        "beat_plan": storyboard,
        "attempts": attempts,
    }


def generate_segment_clips(
    segments: list,
    max_clips: int = 1,
    timeout_per_clip: int = 180,
    provider: Optional[str] = None,
) -> list:
    """Fill segment clips from film canvases.

    provider=None (auto): DramaCanvas plans, then fal/Comfy renders.
    provider=dramacanva: planning metadata only.
    provider=fal_krea/comfy_*: render only.
    """
    dest_dir = os.environ.get("VIDEOS_DIR")
    if provider is None:
        filled = 0
        for seg in segments:
            if filled >= max_clips:
                break
            if seg.get("ai_video_path"):
                continue
            title = seg.get("title", "")
            desc = seg.get("description", "")
            mood = seg.get("mood", "cinematic")
            prompt = "Cinematic %s scene: %s. %s" % (mood, title, desc)
            result = compose_interactive_movie(
                prompt[:500],
                dest_dir=dest_dir,
                timeout=timeout_per_clip,
                plan=True,
            )
            if result.get("planning"):
                seg["film_canvas_planning"] = result.get("planning")
            if result.get("success") and result.get("local_path"):
                seg["ai_video_path"] = result["local_path"]
                seg["film_canvas"] = result.get("canvas")
                seg["film_canvas_planner"] = result.get("planner")
                filled += 1
        return segments

    canvas_id = provider
    if canvas_id == "dramacanva":
        brief = "\n".join(
            "%s: %s" % (seg.get("title", ""), seg.get("description", ""))
            for seg in segments
        )[:4000]
        result = prepare_film_project(brief, timeout=timeout_per_clip)
        if segments:
            segments[0]["film_canvas_planning"] = result
        return segments
    if not is_available(canvas_id):
        return segments
    filled = 0
    for seg in segments:
        if filled >= max_clips:
            break
        if seg.get("ai_video_path"):
            continue
        title = seg.get("title", "")
        desc = seg.get("description", "")
        mood = seg.get("mood", "cinematic")
        prompt = "Cinematic %s scene: %s. %s" % (mood, title, desc)
        result = generate_clip(
            prompt[:500],
            dest_dir=dest_dir,
            timeout=timeout_per_clip,
            provider=canvas_id,
        )
        if result.get("success") and result.get("local_path"):
            seg["ai_video_path"] = result["local_path"]
            seg["film_canvas"] = result.get("canvas")
            filled += 1
    return segments
