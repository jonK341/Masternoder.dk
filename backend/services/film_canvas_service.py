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

import hashlib
import io
import json
import os
import re
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

# External clip backends — credit-blocked ones are deactivated via ai_provider_gate.
# Prefer story_gif_line / Pollinations stills over these wallets.
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
    try:
        from backend.services import ai_provider_gate as gate
        gate.ensure_defaults()
        if gate.is_blocked(backend):
            return False
    except Exception:
        pass
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
    if not out.get("success"):
        try:
            from backend.services import ai_provider_gate as gate
            gate.note_error(backend, out.get("error"))
        except Exception:
            pass
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
    """Always many distinct beats — denser storyboard for better motion/FX visuals."""
    seconds = max(2.0, float(duration or 8.0))
    if seconds <= 4:
        return 4
    if seconds <= 8:
        return 6
    if seconds <= 16:
        return 8
    if seconds <= 30:
        return 10
    if seconds <= 60:
        return 12
    return min(14, max(10, int(round(seconds / 8.0))))


# Story-supportive ambient pack — fewer meaningful FX, less color noise.
# (Previously 107 glitch/plasma overlays drowned the prompt picture.)
_FX_BACKGROUNDS = (
    "fog", "ocean", "rain", "ember", "chrome", "aurora",
)
_FX_SOUNDS = (
    "harbour", "storm", "rain", "ocean", "fog", "focus",
    "voice_soft", "voice_bright", "voice_deep", "drone", "stars", "market",
)
_FX_EFFECT_FAMILIES = (
    "mist", "dust", "bloom", "ripple", "wave", "drift",
    "beam", "veil", "frost", "heat", "echo", "trail",
)
_LIVE_FX_COUNT = 12


def _build_fx_effect_catalog(count: int = _LIVE_FX_COUNT) -> tuple:
    """Build a small catalog of story-supportive live effects."""
    names: List[str] = []
    index = 0
    while len(names) < max(1, int(count)):
        family = _FX_EFFECT_FAMILIES[index % len(_FX_EFFECT_FAMILIES)]
        generation = (index // len(_FX_EFFECT_FAMILIES)) + 1
        names.append("%s_%02d" % (family, generation))
        index += 1
    return tuple(names)


_FX_EFFECTS = _build_fx_effect_catalog(_LIVE_FX_COUNT)
_FX_PALETTES = (
    ("#94a3b8", "#38bdf8", "#e2e8f0"),
    ("#f97316", "#22d3ee", "#fde68a"),
    ("#34d399", "#818cf8", "#fda4af"),
    ("#7cf5ff", "#3d7cff", "#c8ff6a"),
    ("#ff9a3c", "#ff5e7a", "#ffe08a"),
    ("#67e8f9", "#a78bfa", "#fb7185"),
)


def _build_fx_pack(run_id: str, style: str = "", mood: str = "") -> Dict[str, Any]:
    """Invent a light story-supportive FX pack — picture and story stay dominant."""
    salt = int(
        hashlib.sha1(
            ("%s|%s|%s|%s" % (run_id, style, mood, secrets.token_hex(4))).encode("utf-8")
        ).hexdigest()[:8],
        16,
    )
    background = _FX_BACKGROUNDS[salt % len(_FX_BACKGROUNDS)]
    sound = _FX_SOUNDS[(salt // 3) % len(_FX_SOUNDS)]
    palette = list(_FX_PALETTES[(salt // 11) % len(_FX_PALETTES)])
    rotated = list(_FX_EFFECTS)
    start = salt % len(rotated)
    effects = rotated[start:] + rotated[:start]
    return {
        "background": background,
        "sound": sound,
        "effects": effects[:_LIVE_FX_COUNT],
        "live_count": min(len(effects), _LIVE_FX_COUNT),
        "palette": palette,
        # Soft ambient only — never overpower story picture.
        "intensity": round(0.22 + (salt % 12) / 100.0, 2),
        "run_id": run_id,
        "sfx_bank": "shop",
        "voice_profile": (
            "performer_nova", "performer_luna", "performer_ember", "performer_storm",
            "performer_velvet", "performer_jade", "performer_rio", "performer_mist",
        )[salt % 8],
        "story_first": True,
    }


def _normalize_fx_pack(raw: Any, run_id: str, style: str = "", mood: str = "") -> Dict[str, Any]:
    """Validate AI fx_pack or fall back to a light story-supportive pack."""
    base = _build_fx_pack(run_id, style=style, mood=mood)
    if not isinstance(raw, dict):
        return base
    bg = str(raw.get("background") or "").strip().lower()
    if bg in _FX_BACKGROUNDS:
        base["background"] = bg
    snd = str(raw.get("sound") or "").strip().lower()
    if snd in _FX_SOUNDS:
        base["sound"] = snd
    voice = str(raw.get("voice_profile") or "").strip()
    if voice.startswith("performer_"):
        base["voice_profile"] = voice
    effects = raw.get("effects") if isinstance(raw.get("effects"), list) else []
    cleaned = []
    for item in effects:
        name = str(item or "").strip().lower()
        if name in _FX_EFFECTS and name not in cleaned:
            cleaned.append(name)
    for name in _FX_EFFECTS:
        if name not in cleaned:
            cleaned.append(name)
    base["effects"] = cleaned[:_LIVE_FX_COUNT]
    base["live_count"] = len(base["effects"])
    base["story_first"] = True
    palette = raw.get("palette") if isinstance(raw.get("palette"), list) else []
    colors = [str(c).strip()[:9] for c in palette if str(c).strip().startswith("#")]
    if len(colors) >= 2:
        while len(colors) < 3:
            colors.append(base["palette"][len(colors) % len(base["palette"])])
        base["palette"] = colors[:3]
    try:
        intensity = float(raw.get("intensity"))
        if 0.1 <= intensity <= 1.2:
            # Clamp soft — overlays must not wash out the story picture.
            base["intensity"] = round(max(0.18, min(0.38, intensity)), 2)
    except (TypeError, ValueError):
        pass
    return base


def _scene_bible(brief: str) -> str:
    """Locked continuity line so every still stays on the user prompt."""
    core = (brief or "").split("[face reference")[0].strip()
    core = core.split("\n\nStoryboard direction:")[0].strip()[:180]
    if not core:
        core = "cinematic real-world scene"
    return (
        "LOCKED REAL SCENE (must match exactly): %s. "
        "Photoreal photograph, real people, real clothing, natural skin, "
        "same location and lighting in every frame, documentary realism, "
        "no cartoon, no text, no watermark."
    ) % core


def _build_story_bundle(
    brief: str,
    beats: List[Dict[str, Any]],
    style: str,
    mood: str,
    run_id: str,
) -> Dict[str, Any]:
    """Mix a short coherent story + narration lines for voice playback."""
    core = (brief or "").split("[face reference")[0].strip()[:160] or "the scene"
    titles = [str(b.get("title") or ("Beat %s" % (i + 1))) for i, b in enumerate(beats)]
    story = (
        "In %s, a %s story unfolds in %s light: first %s, then %s, "
        "and finally %s — people move and act inside the same real place."
        % (
            core,
            mood or "vivid",
            style or "cinematic",
            titles[0] if titles else "the opening",
            titles[len(titles) // 2] if len(titles) > 2 else (titles[-1] if titles else "the turn"),
            titles[-1] if titles else "the close",
        )
    )[:420]
    narration: List[str] = []
    for index, beat in enumerate(beats):
        line = str(
            beat.get("narration")
            or beat.get("description")
            or beat.get("title")
            or ("Moment %s of %s" % (index + 1, core))
        ).strip()
        narration.append(
            ("Scene %s. %s. Stay with %s." % (index + 1, line[:140], core[:80]))[:220]
        )
    return {
        "story": story,
        "narration": narration,
        "run_id": run_id,
    }


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
    ai_pipeline: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Full storyboard: prefer a fresh AI pipeline; otherwise parse direction / templates."""
    want = _beat_count_for_duration(duration)
    seconds = max(2.0, float(duration or 8.0))
    if ai_pipeline and ai_pipeline.get("success") and isinstance(ai_pipeline.get("beats"), list):
        ai_beats = [dict(b) for b in ai_pipeline["beats"] if isinstance(b, dict)]
        if len(ai_beats) >= 2:
            # Re-fit durations to the requested runtime while keeping AI creative content.
            remaining = seconds
            for index, beat in enumerate(ai_beats):
                left = len(ai_beats) - index
                beat_sec = remaining if left == 1 else max(1.2, round(remaining / left, 2))
                remaining = max(0.0, round(remaining - beat_sec, 2))
                beat["index"] = index
                beat["duration_sec"] = beat_sec
                if not beat.get("seed"):
                    beat["seed"] = (secrets.randbelow(900000) + 1000 + index * 97) % 999999
                if not beat.get("motion"):
                    beat["motion"] = (
                        "zoom_in", "pan_right", "zoom_out", "pan_left",
                    )[index % 4]
            return ai_beats

    parsed = _parse_direction_beats(direction or "", want)
    brief = (prompt or "cinematic scene").strip()
    brief_core = brief.split("\n\nStoryboard direction:")[0].strip()
    brief_core = brief_core.split("[face reference")[0].strip() or brief_core
    # Shuffle template order each clip so fallbacks are not identical.
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
    start = secrets.randbelow(len(templates))
    templates = templates[start:] + templates[:start]
    run_salt = uuid.uuid4().hex[:6]

    beats: List[Dict[str, Any]] = []
    for index in range(want):
        shot_type, prompt_fmt, title_fallback = templates[index % len(templates)]
        if index < len(parsed):
            description = parsed[index]["description"]
            title = parsed[index].get("title") or title_fallback
        else:
            description = prompt_fmt % brief_core[:160]
            title = title_fallback
        seed = (secrets.randbelow(900000) + 1000 + index * 97) % 999999
        beats.append({
            "index": index,
            "title": str(title)[:48],
            "description": str(description)[:280],
            "shot_type": shot_type,
            "seed": seed,
            "prompt": (
                "%s. Shot type: %s. Scene: %s. Unique clip salt %s. "
                "Cinematic film still, detailed, 16:9, dramatic lighting."
            ) % (description[:160], shot_type, brief_core[:120], run_salt),
            "image_prompt": (
                "Photoreal cinematic still of %s, %s, unique variation %s"
            ) % (description[:160], brief_core[:100], run_salt),
        })

    remaining = seconds
    for index, beat in enumerate(beats):
        left = len(beats) - index
        beat_sec = remaining if left == 1 else max(1.2, round(remaining / left, 2))
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


def _try_free_beat_image(prompt: str, dest_dir: str, seed: int, timeout: int = 12) -> Optional[str]:
    """Best-effort prompt-matched AI still via Pollinations free models."""
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, "ai_beat_%s_%s.jpg" % (seed, uuid.uuid4().hex[:6]))
    models = ("flux", "z-image-turbo", "gptimage")
    try:
        from backend.services import ai_provider_gate as gate
        models = tuple(gate.POLLINATIONS_IMAGE_MODELS) or models
    except Exception:
        pass
    model = models[int(seed) % len(models)]
    try:
        encoded = urllib.parse.quote((prompt or "photoreal film still")[:420], safe="")
        url = (
            "https://image.pollinations.ai/prompt/%s"
            "?width=1280&height=720&nologo=true&enhance=true&model=%s&seed=%d"
        ) % (encoded, urllib.parse.quote(str(model)), int(seed) % 999999)
        req = urllib.request.Request(url, headers={"User-Agent": "MasterNoder/1.0"})
        with urllib.request.urlopen(req, timeout=max(8, int(timeout))) as resp:
            img_bytes = resp.read()
        if len(img_bytes) < 1000:
            return None
        with open(path, "wb") as handle:
            handle.write(img_bytes)
        return path
    except Exception:
        return None


def _prompt_matched_still_prompt(beat: Dict[str, Any], base_prompt: str) -> str:
    """Build a still prompt that stays close to the user's scene and shows people acting."""
    shot = str(beat.get("shot_type") or "establishing")
    detail = str(beat.get("description") or beat.get("title") or "").strip()
    bible = _scene_bible(base_prompt)
    action = {
        "establishing": "wide photoreal establishing shot, real environment first, people walking naturally in distance",
        "character": "medium photoreal shot of a real person acting in the locked scene, expressive face, eye contact",
        "action": "dynamic photoreal action, person mid-stride walking or gesturing, clear body motion",
        "detail": "close photoreal insert of hands or props from the locked scene while a person acts nearby",
        "reaction": "reaction close-up, real person turns and reacts emotionally in the locked scene",
        "closing": "closing wide photoreal shot, person walks away through the same locked place",
    }.get(shot, "photoreal shot with people moving naturally in the locked scene")
    return (
        "%s %s. Story beat: %s. Keep identity and place identical, 16:9."
    ) % (bible, action, detail[:140])


def _acting_pose_prompts(beat: Dict[str, Any], base_prompt: str) -> List[str]:
    """Three pose prompts so people appear to move/act across the beat."""
    bible = _scene_bible(base_prompt)
    custom = beat.get("pose_prompts") if isinstance(beat.get("pose_prompts"), list) else []
    custom = [str(p).strip()[:420] for p in custom if str(p).strip()]
    if len(custom) >= 2:
        reinforced = []
        for pose in custom[:3]:
            if "LOCKED REAL SCENE" in pose:
                reinforced.append(pose[:420])
            else:
                reinforced.append(("%s %s" % (bible, pose))[:420])
        while len(reinforced) < 3:
            reinforced.append(reinforced[-1])
        return reinforced[:3]
    base = beat.get("image_prompt") or _prompt_matched_still_prompt(beat, base_prompt)
    if "LOCKED REAL SCENE" not in str(base):
        base = ("%s %s" % (bible, base))[:420]
    shot = str(beat.get("shot_type") or "action")
    if shot in ("establishing", "detail", "closing"):
        suffixes = (
            "same place, ambient people shift slightly, photoreal",
            "same place, stronger foreground walkers crossing, photoreal",
            "same place, figures farther into the scene, photoreal",
        )
    else:
        suffixes = (
            "same person standing ready, facing camera, photoreal skin",
            "same person mid-stride, body turned, arm gesturing, photoreal",
            "same person acting: turning head, expressive hands, stepping forward, photoreal",
        )
    return [("%s. %s." % (base, suffix))[:420] for suffix in suffixes]


def _composite_face_onto_still(still_path: str, face_path: str, dest_path: str) -> Optional[str]:
    """Paste the user face onto a prompt still so the actor stays recognizable."""
    if not (still_path and face_path and os.path.isfile(still_path) and os.path.isfile(face_path)):
        return None
    try:
        from PIL import Image, ImageDraw

        scene = Image.open(still_path).convert("RGB").resize((1280, 720))
        face = Image.open(face_path).convert("RGB")
        face.thumbnail((260, 260))
        fx, fy = 920, 180
        mask = Image.new("L", face.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((2, 2, face.size[0] - 2, face.size[1] - 2), fill=255)
        scene.paste(face, (fx, fy), mask)
        scene.save(dest_path, format="JPEG", quality=90)
        return dest_path
    except Exception:
        return None


def _collect_acting_pose_images(
    beat: Dict[str, Any],
    base_prompt: str,
    dest_dir: str,
    face_path: Optional[str] = None,
) -> List[str]:
    """Fetch/paint several prompt-matched poses for one beat (people acting)."""
    poses: List[str] = []
    try:
        seed0 = int(beat.get("seed") or 0)
    except (TypeError, ValueError):
        seed0 = 0
    if seed0 <= 0:
        seed0 = 2200 + int(beat.get("index") or 0) * 131 + secrets.randbelow(5000)
    for i, pose_prompt in enumerate(_acting_pose_prompts(beat, base_prompt)):
        path = _try_free_beat_image(pose_prompt, dest_dir, seed=seed0 + i * 17, timeout=10)
        if not path:
            painted = _write_beat_scene_image(
                dest_dir,
                {
                    **beat,
                    "index": int(beat.get("index") or 0) * 10 + i,
                    "title": "%s · pose %s" % (beat.get("title") or "Beat", i + 1),
                    "description": pose_prompt[:180],
                },
                face_path=face_path if i == 0 else None,
            )
            path = painted
        if path and face_path and os.path.isfile(face_path) and str(beat.get("shot_type")) in (
            "character", "action", "reaction", "closing",
        ):
            composited = os.path.join(
                dest_dir, "facepose_%s_%s.jpg" % (beat.get("index"), i)
            )
            path = _composite_face_onto_still(path, face_path, composited) or path
        if path and os.path.isfile(path):
            poses.append(path)
    # Deduplicate identical paths; keep order.
    unique: List[str] = []
    for path in poses:
        if path not in unique:
            unique.append(path)
    return unique


def _ffmpeg_acting_clip(
    image_paths: List[str],
    dest_path: str,
    duration: float = 3.0,
    motion: str = "zoom_in",
) -> Dict[str, Any]:
    """Morph between pose stills so people appear to move and act."""
    seconds = max(1.2, min(60.0, float(duration or 3.0)))
    paths = [p for p in image_paths if p and os.path.isfile(p)]
    if not paths:
        return {"success": False, "error": "no acting poses"}
    if len(paths) == 1:
        return _ffmpeg_kenburns_movie(paths[0], dest_path, duration=seconds, motion=motion)

    n = len(paths)
    fade = min(0.4, max(0.2, seconds / (n * 4.0)))
    hold = max(fade + 0.4, (seconds + fade * (n - 1)) / float(n))
    cmd: List[str] = ["ffmpeg", "-y"]
    for path in paths:
        cmd.extend(["-loop", "1", "-t", ("%.3f" % hold), "-i", path])

    # Normalize each input, then xfade through the pose chain.
    parts: List[str] = []
    for i in range(n):
        parts.append(
            "[%d:v]scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25[s%d]"
            % (i, i)
        )
    current = "[s0]"
    offset = hold - fade
    for i in range(1, n):
        label = "[x%d]" % i
        parts.append(
            "%s[s%d]xfade=transition=fade:duration=%.3f:offset=%.3f%s"
            % (current, i, fade, max(0.05, offset), label)
        )
        current = label
        offset += hold - fade
    parts.append(
        "%seq=contrast=1.06:saturation=1.1,format=yuv420p[vout]" % current
    )
    cmd.extend([
        "-filter_complex", ";".join(parts),
        "-map", "[vout]",
        "-t", ("%.3f" % seconds),
        "-r", "25",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        dest_path,
    ])
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(60, int(seconds) + 45),
            check=False,
        )
    except Exception as exc:
        return {"success": False, "error": "acting ffmpeg failed: %s" % exc}
    if proc.returncode != 0 or not os.path.isfile(dest_path):
        return _ffmpeg_kenburns_movie(paths[0], dest_path, duration=seconds, motion=motion)
    return {
        "success": True,
        "local_path": dest_path,
        "fps": 25,
        "duration_sec": seconds,
        "mode": "acting_morph",
        "poses": len(paths),
    }


def _ffmpeg_gif_strip_clip(
    image_paths: List[str],
    dest_path: str,
    duration: float = 4.5,
    motion: str = "zoom_in",
) -> Dict[str, Any]:
    """Side-by-side story GIF panels — sellable path feeds 4–5s per strip."""
    seconds = max(1.2, min(60.0, float(duration or 4.5)))
    paths = [p for p in image_paths if p and os.path.isfile(p)]
    if not paths:
        return {"success": False, "error": "no gif-strip poses"}
    while len(paths) < 3:
        paths.append(paths[-1])
    paths = paths[:3]
    panel_w, panel_h = 426, 720
    frames = max(30, int(round(seconds * 25)))
    zoom_map = {
        "zoom_in": "min(1.0+0.08*(on/%d),1.12)" % max(1, frames),
        "zoom_out": "max(1.12-0.08*(on/%d),1.0)" % max(1, frames),
        "pan_left": "1.08",
        "pan_right": "1.08",
    }
    zoom = zoom_map.get(str(motion or "zoom_in"), zoom_map["zoom_in"])
    x_exprs = {
        "pan_left": "'iw/2-(iw/zoom/2)-(on*0.35)'",
        "pan_right": "'iw/2-(iw/zoom/2)+(on*0.35)'",
        "zoom_in": "'iw/2-(iw/zoom/2)'",
        "zoom_out": "'iw/2-(iw/zoom/2)'",
    }
    y_expr = "'ih/2-(ih/zoom/2)'"
    cmd: List[str] = ["ffmpeg", "-y"]
    for path in paths:
        cmd.extend(["-loop", "1", "-t", ("%.3f" % seconds), "-i", path])
    parts: List[str] = []
    for i in range(3):
        # Slight phase offset per panel so the strip feels like three GIFs.
        phase = i * 7
        z = zoom if i == 1 else ("min(1.0+0.06*((on+%d)/%d),1.1)" % (phase, max(1, frames)))
        x_expr = x_exprs.get(str(motion or "zoom_in"), x_exprs["zoom_in"])
        if i == 0:
            x_expr = "'iw/2-(iw/zoom/2)-(8*sin(2*PI*(on+%d)/60))'" % phase
        elif i == 2:
            x_expr = "'iw/2-(iw/zoom/2)+(8*sin(2*PI*(on+%d)/55))'" % phase
        parts.append(
            "[%d:v]scale=%d:%d:force_original_aspect_ratio=increase,"
            "crop=%d:%d,zoompan=z=%s:x=%s:y=%s:d=%d:s=%dx%d:fps=25[p%d]"
            % (i, panel_w, panel_h, panel_w, panel_h, z, x_expr, y_expr, frames, panel_w, panel_h, i)
        )
    parts.append(
        "[p0][p1][p2]hstack=inputs=3,"
        "scale=1280:720,setsar=1,eq=contrast=1.05:saturation=1.08,format=yuv420p[vout]"
    )
    cmd.extend([
        "-filter_complex", ";".join(parts),
        "-map", "[vout]",
        "-t", ("%.3f" % seconds),
        "-r", "25",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        dest_path,
    ])
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(60, int(seconds) + 50),
            check=False,
        )
    except Exception as exc:
        return {"success": False, "error": "gif-strip ffmpeg failed: %s" % exc}
    if proc.returncode != 0 or not os.path.isfile(dest_path):
        # Fall back to pose morph if zoompan/hstack fails on this host.
        return _ffmpeg_acting_clip(paths, dest_path, duration=seconds, motion=motion)
    return {
        "success": True,
        "local_path": dest_path,
        "fps": 25,
        "duration_sec": seconds,
        "mode": "gif_strip",
        "poses": len(paths),
        "panels": 3,
    }


def _ffmpeg_encode_xvid(mp4_path: str, dest_path: Optional[str] = None) -> Dict[str, Any]:
    """Re-encode an MP4 into an Xvid AVI clip for download/playback compatibility."""
    if not mp4_path or not os.path.isfile(mp4_path):
        return {"success": False, "error": "mp4 missing for xvid encode"}
    if dest_path is None:
        base, _ = os.path.splitext(mp4_path)
        dest_path = base + "_xvid.avi"
    cmd = [
        "ffmpeg", "-y",
        "-i", mp4_path,
        "-c:v", "libxvid",
        "-qscale:v", "4",
        "-an",
        dest_path,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False)
    except Exception as exc:
        return {"success": False, "error": "xvid encode failed: %s" % exc}
    if proc.returncode != 0 or not os.path.isfile(dest_path):
        err = (proc.stderr or proc.stdout or "xvid failed")[-300:]
        return {"success": False, "error": "xvid encode failed: %s" % err}
    return {"success": True, "local_path": dest_path, "format": "xvid"}


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
    ai_pipeline: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Gather prompt-matched acting poses per storyboard beat."""
    beats = _build_storyboard_beats(
        prompt, duration, direction=direction, ai_pipeline=ai_pipeline,
    )
    stills: List[Dict[str, Any]] = []
    style = ""
    mood = ""
    if isinstance(ai_pipeline, dict):
        style = str(ai_pipeline.get("style") or "")
        mood = str(ai_pipeline.get("mood") or "")
    for beat in beats:
        poses = _collect_acting_pose_images(
            beat, prompt, dest_dir, face_path=face_path,
        )
        source = "acting_poses" if len(poses) > 1 else ("free_ai" if poses else "beat_scene")
        if not poses:
            path = _write_beat_scene_image(dest_dir, beat, face_path=face_path)
            if not path:
                continue
            poses = [path]
            source = "beat_scene"
        stills.append({
            "path": poses[0],
            "poses": poses,
            "source": source,
            "title": str(beat.get("title") or ""),
            "shot_type": str(beat.get("shot_type") or ""),
            "motion": str(beat.get("motion") or "zoom_in"),
            "duration_sec": float(beat.get("duration_sec") or 2.0),
            "description": str(beat.get("description") or ""),
            "prompt": beat.get("image_prompt") or _prompt_matched_still_prompt(beat, prompt),
            "seed": beat.get("seed"),
            "style": style,
            "mood": mood,
        })
    return stills


def _generate_free_still_movie(
    prompt: str,
    dest_dir: Optional[str] = None,
    duration: float = 6.0,
    face_path: Optional[str] = None,
    direction: Optional[str] = None,
    ai_pipeline: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a prompt-matched multi-scene movie with people acting across poses."""
    if dest_dir is None:
        dest_dir = os.environ.get("VIDEOS_DIR") or os.getcwd()
    os.makedirs(dest_dir, exist_ok=True)
    errors: List[str] = []
    duration = max(2.0, min(120.0, float(duration or 6.0)))
    storyboard = _build_storyboard_beats(
        prompt, duration, direction=direction, ai_pipeline=ai_pipeline,
    )

    stills = _collect_movie_stills(
        prompt,
        dest_dir,
        duration,
        face_path=face_path,
        direction=direction,
        ai_pipeline=ai_pipeline,
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
    # Primary still path per beat for adjacent GIF-strip panels.
    beat_faces: List[str] = []
    for still in stills:
        poses = [p for p in (still.get("poses") or []) if p and os.path.isfile(p)]
        face = poses[0] if poses else still.get("path")
        if face and os.path.isfile(str(face)):
            beat_faces.append(str(face))
        elif still.get("path") and os.path.isfile(str(still.get("path"))):
            beat_faces.append(str(still["path"]))
    for index, still in enumerate(stills):
        beat_sec = float(still.get("duration_sec") or (duration / max(1, len(stills))))
        part = os.path.join(dest_dir, "beat_%s_%s.mp4" % (uuid.uuid4().hex[:8], index))
        poses = list(still.get("poses") or [still.get("path")])
        # Adjacent story panels: previous / current / next moving like GIFs side by side.
        left = beat_faces[index - 1] if index > 0 else (poses[0] if poses else beat_faces[0])
        mid = beat_faces[index] if index < len(beat_faces) else (poses[0] if poses else left)
        right = (
            beat_faces[index + 1]
            if index + 1 < len(beat_faces)
            else (poses[-1] if poses else mid)
        )
        strip_paths = [p for p in (left, mid, right) if p and os.path.isfile(str(p))]
        encoded = _ffmpeg_gif_strip_clip(
            strip_paths or poses,
            part,
            duration=beat_sec,
            motion=str(still.get("motion") or "zoom_in"),
        )
        if not (encoded.get("success") and encoded.get("local_path")):
            encoded = _ffmpeg_acting_clip(
                poses,
                part,
                duration=beat_sec,
                motion=str(still.get("motion") or "zoom_in"),
            )
        if not (encoded.get("success") and encoded.get("local_path")):
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
                "narration": still.get("narration") or still.get("description"),
                "poses": len(poses),
                "mode": encoded.get("mode"),
                "panels": encoded.get("panels") or 1,
                "seed": still.get("seed"),
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
    xvid_path = None
    pipeline_meta = {
        "pipeline_run_id": (ai_pipeline or {}).get("run_id") if isinstance(ai_pipeline, dict) else None,
        "pipeline_style": (ai_pipeline or {}).get("style") if isinstance(ai_pipeline, dict) else None,
        "pipeline_mood": (ai_pipeline or {}).get("mood") if isinstance(ai_pipeline, dict) else None,
        "pipeline_provider": (ai_pipeline or {}).get("provider") if isinstance(ai_pipeline, dict) else None,
        "pipeline_title": (ai_pipeline or {}).get("title") if isinstance(ai_pipeline, dict) else None,
        "fx_pack": (ai_pipeline or {}).get("fx_pack") if isinstance(ai_pipeline, dict) else None,
    }
    if merged.get("success") and merged.get("local_path"):
        xvid = _ffmpeg_encode_xvid(merged["local_path"])
        if xvid.get("success"):
            xvid_path = xvid.get("local_path")
        out = {
            "success": True,
            "local_path": merged["local_path"],
            "xvid_path": xvid_path,
            "canvas": "free_still",
            "source_image": ",".join(sources) or "storyboard",
            "fps": 25,
            "duration_sec": int(round(duration)),
            "beats": len(beat_paths),
            "beat_plan": beat_meta or storyboard,
            "mode": "gif_storyboard",
            "ai_pipeline": ai_pipeline if isinstance(ai_pipeline, dict) else None,
            "story": (ai_pipeline or {}).get("story") if isinstance(ai_pipeline, dict) else None,
            "narration": (ai_pipeline or {}).get("narration") if isinstance(ai_pipeline, dict) else None,
        }
        out.update(pipeline_meta)
        return out

    if beat_paths:
        xvid = _ffmpeg_encode_xvid(beat_paths[0])
        out = {
            "success": True,
            "local_path": beat_paths[0],
            "xvid_path": xvid.get("local_path") if xvid.get("success") else None,
            "canvas": "free_still",
            "source_image": ",".join(sources) or "storyboard",
            "fps": 25,
            "duration_sec": int(round(duration)),
            "beats": len(beat_paths),
            "beat_plan": beat_meta,
            "mode": "gif_storyboard",
            "concat_error": merged.get("error"),
            "ai_pipeline": ai_pipeline if isinstance(ai_pipeline, dict) else None,
            "story": (ai_pipeline or {}).get("story") if isinstance(ai_pipeline, dict) else None,
            "narration": (ai_pipeline or {}).get("narration") if isinstance(ai_pipeline, dict) else None,
        }
        out.update(pipeline_meta)
        return out
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
    run_token = uuid.uuid4().hex[:10]
    system = (
        "You invent a brand-new multi-shot storyboard for a short interactive monitor film. "
        "Never reuse a generic template. Return 3-6 numbered beats. Each beat must be a "
        "DIFFERENT shot (establishing / character / action / detail / reaction / closing) "
        "with concrete visual detail, camera move, people acting, and mood. No preamble."
    )
    user = (
        "Unique run id: %s (make this storyboard original for this id only).\n"
        "Scene brief:\n%s\n\n"
        "Write a fresh storyboard as numbered beats the renderer can follow. "
        "Every beat must describe different material and different character action."
    ) % (run_token, brief[:800])
    try:
        multi = _video_ai_bridge.complete_multi_provider(
            "interactive_movie",
            user,
            system_prompt=system,
            max_providers=None,
            temperature=0.95,
            max_tokens=520,
            timeout=min(25, max(8, timeout)),
            extra_context={"use_all_ais": True, "quality_mode": "best", "run_id": run_token},
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
        "run_id": run_token,
    }


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    raw = (text or "").strip()
    if not raw:
        return None
    if "```" in raw:
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL | re.IGNORECASE)
        if fence:
            raw = fence.group(1)
        else:
            raw = raw.replace("```json", "").replace("```", "").strip()
    start = raw.find("{")
    if start < 0:
        return None
    chunk = raw[start:]
    for candidate in (chunk, chunk[: chunk.rfind("}") + 1] if "}" in chunk else ""):
        if not candidate:
            continue
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    # Keep only complete beat objects if the array was cut off.
    beats_match = re.search(r'"beats"\s*:\s*\[(.*)', chunk, re.DOTALL)
    title = re.search(r'"title"\s*:\s*"([^"]*)"', chunk)
    style = re.search(r'"style"\s*:\s*"([^"]*)"', chunk)
    mood = re.search(r'"mood"\s*:\s*"([^"]*)"', chunk)
    beats: List[Dict[str, Any]] = []
    if beats_match:
        for obj_text in re.findall(r'\{[^{}]*\}', beats_match.group(1)):
            try:
                item = json.loads(obj_text)
            except Exception:
                continue
            if isinstance(item, dict) and (item.get("description") or item.get("image_prompt")):
                beats.append(item)
    if title or style or beats:
        return {
            "title": title.group(1) if title else "AI pipeline",
            "style": style.group(1) if style else "ai-directed",
            "mood": mood.group(1) if mood else "fresh",
            "color_grade": "",
            "camera_language": "",
            "people_direction": "people act differently each beat",
            "beats": beats,
        }
    repaired = chunk.rstrip()
    if repaired.count('"') % 2 == 1:
        repaired += '"'
    repaired += "]" * max(0, repaired.count("[") - repaired.count("]"))
    repaired += "}" * max(0, repaired.count("{") - repaired.count("}"))
    try:
        obj = json.loads(repaired)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _gemini_rest_complete(prompt: str, system: str = "", timeout: int = 25) -> Dict[str, Any]:
    """Direct Gemini REST call — bypasses broken openai-compatible client paths."""
    api_key = (
        os.environ.get("GOOGLE_AI_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or ""
    ).strip()
    if not api_key:
        for env_path in _ENV_FILES:
            if not os.path.isfile(env_path):
                continue
            try:
                with open(env_path, encoding="utf-8") as handle:
                    for line in handle:
                        if line.startswith("GOOGLE_AI_API_KEY=") or line.startswith("GEMINI_API_KEY="):
                            api_key = line.split("=", 1)[1].strip().strip("'\"")
                            if api_key:
                                break
            except Exception:
                continue
            if api_key:
                break
    if not api_key:
        return {"success": False, "error": "GOOGLE_AI_API_KEY missing"}

    text = (("System:\n%s\n\n" % system) if system else "") + prompt
    body = json.dumps({
        "contents": [{"parts": [{"text": text[:6000]}]}],
        "generationConfig": {
            "temperature": 1.05,
            "maxOutputTokens": 1400,
            "responseMimeType": "application/json",
        },
    }).encode("utf-8")
    last_err = ""
    for model in (
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-2.5-flash-lite",
        "gemini-3.8-flash",
    ):
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s"
            % (model, urllib.parse.quote(api_key))
        )
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": "MasterNoder/1.0"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=max(8, int(timeout))) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception as exc:
            last_err = str(exc)[:180]
            continue
        try:
            content = payload["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            last_err = "gemini response missing text"
            continue
        if content and str(content).strip():
            return {"success": True, "content": str(content).strip(), "provider": "gemini_rest", "model": model}
    return {"success": False, "error": last_err or "gemini rest failed"}


def _procedural_unique_pipeline(
    brief: str,
    duration_sec: int,
    beat_count: int,
    run_id: str,
) -> Dict[str, Any]:
    """Always-new local pipeline when remote LLMs throttle — still unique per clip."""
    want = max(4, min(14, int(beat_count or 6)))
    seconds = max(2, min(120, int(duration_sec or 8)))
    salt = int(hashlib.sha1(("%s|%s|%s" % (run_id, brief, secrets.token_hex(4))).encode("utf-8")).hexdigest()[:8], 16)
    styles = (
        "neon noir", "wet chrome", "fog pastel", "amber documentary",
        "cyber rain", "steel dawn", "violet night", "salt-spray realism",
        "ember dusk", "signal green", "harbour steel", "plasma bloom",
    )
    moods = (
        "urgent", "lonely", "hopeful", "tense", "dreamlike", "gritty", "serene", "chaotic",
        "electric", "melancholy", "fierce", "quiet",
    )
    style = styles[salt % len(styles)]
    mood = moods[(salt // 7) % len(moods)]
    fx_pack = _build_fx_pack(run_id, style=style, mood=mood)
    core = (brief or "cinematic scene").split("[face reference")[0].strip()[:160]
    words = [w for w in core.replace(",", " ").split() if len(w) > 2]
    beats: List[Dict[str, Any]] = []
    order = list(_SHOT_TYPES)
    start = salt % len(order)
    order = order[start:] + order[:start]
    motions = ("zoom_in", "pan_right", "zoom_out", "pan_left")
    for index in range(want):
        shot = order[index % len(order)]
        spice = words[(salt + index * 3) % len(words)] if words else "scene"
        # Lead with the user brief so the prompt picture stays strongest.
        bible = _scene_bible(brief)
        description = (
            "%s %s shot — clearly show %s, focus on %s, style %s, mood %s (%s)"
            % (bible, shot, core[:90], spice, style, mood, run_id[-6:])
        )[:420]
        seed = (salt * 13 + index * 97 + secrets.randbelow(5000)) % 999999
        narration = (
            "Scene %s: in %s, %s — people move and act."
            % (index + 1, core[:70], shot)
        )[:180]
        beats.append({
            "index": index,
            "title": ("%s · %s" % (shot.title(), spice))[:48],
            "description": description,
            "narration": narration,
            "shot_type": shot,
            "prompt": description,
            "image_prompt": description,
            "pose_prompts": [
                ("%s — ready pose, keep the same scene subject" % description)[:420],
                ("%s — mid motion, keep the same scene subject" % description)[:420],
                ("%s — acting turn, keep the same scene subject" % description)[:420],
            ],
            "motion": motions[index % 4],
            "seed": seed,
            "duration_sec": 0,
        })
    remaining = float(seconds)
    for index, beat in enumerate(beats):
        left = len(beats) - index
        beat_sec = remaining if left == 1 else max(0.9, round(remaining / left, 2))
        remaining = max(0.0, round(remaining - beat_sec, 2))
        beat["duration_sec"] = beat_sec
    story_bundle = _build_story_bundle(brief, beats, style, mood, run_id)
    return {
        "success": True,
        "run_id": run_id,
        "provider": "procedural_unique",
        "title": ("%s · %s" % (style, mood))[:80],
        "style": style,
        "mood": mood,
        "color_grade": style,
        "camera_language": "invented handheld for %s" % run_id[-6:],
        "people_direction": "people act differently each beat (%s)" % mood,
        "fx_pack": fx_pack,
        "story": story_bundle["story"],
        "narration": story_bundle["narration"],
        "beats": beats,
        "direction": "\n".join(
            "%s. [%s] %s" % (i + 1, b["shot_type"], b["description"])
            for i, b in enumerate(beats)
        ),
    }


def _ai_design_clip_pipeline(
    brief: str,
    duration_sec: int,
    beat_count: int,
    timeout: int = 25,
) -> Dict[str, Any]:
    """Ask AI to invent a brand-new flexible render pipeline for this one clip only."""
    run_id = "pipe_%s" % uuid.uuid4().hex[:12]
    want = max(4, min(14, int(beat_count or 6)))
    seconds = max(2, min(120, int(duration_sec or 8)))

    system = (
        "You are the film pipeline architect. For EVERY request invent a NEW pipeline. "
        "Never copy a previous layout. Reply with ONLY one compact JSON object on a single "
        "logical response (no markdown fences, no commentary) matching:\n"
        "{"
        "\"title\":str,\"style\":str,\"mood\":str,\"color_grade\":str,"
        "\"camera_language\":str,\"people_direction\":str,"
        "\"story\":str,"
        "\"fx_pack\":{\"background\":str,\"sound\":str,\"voice_profile\":str,"
        "\"palette\":[str,str,str],\"intensity\":float},"
        "\"beats\":[{\"title\":str,\"shot_type\":str,\"description\":str,"
        "\"narration\":str,\"image_prompt\":str,\"pose_prompts\":[str,str,str],"
        "\"motion\":\"zoom_in|zoom_out|pan_left|pan_right\",\"seed\":int}]"
        "}\n"
        "Invent a NEW short coherent story every time that stays inside the user brief. "
        "Keep strings short. shot_type must be one of "
        "establishing,character,action,detail,reaction,closing. "
        "fx_pack.background one of fog,ocean,rain,ember,chrome,aurora. "
        "fx_pack.sound one of harbour,storm,rain,ocean,fog,focus,voice_soft,voice_bright,voice_deep,drone,stars,market. "
        "fx_pack.voice_profile one of performer_nova,performer_luna,performer_ember,performer_storm,performer_velvet. "
        "Keep fx_pack light and story-supportive (max 12 soft effects, low intensity); never invent loud color/glitch FX. "
        "Each image_prompt MUST start with the user scene brief, then add short shot detail. "
        "The brief subject must dominate the frame — photoreal, real people, same place every beat. "
        "Each narration line is spoken aloud and must advance the story. "
        "People must act differently in each pose_prompt."
    )
    user = (
        "Fresh pipeline run_id=%s\n"
        "Duration seconds=%s\n"
        "Required beat count=%s\n"
        "User scene brief:\n%s\n\n"
        "Invent a unique pipeline and exactly %s original beats for this run only. "
        "Return compact JSON only."
    ) % (run_id, seconds, want, brief[:700], want)

    content = ""
    provider = None
    # 1) Direct Gemini REST — reliable even when openai-compatible clients are broken.
    gem = _gemini_rest_complete(user, system=system, timeout=min(28, max(10, timeout)))
    if gem.get("success") and gem.get("content"):
        content = str(gem["content"]).strip()
        provider = gem.get("provider") or "gemini_rest"

    # 2) Bridge / multi-provider fallback.
    if not content:
        try:
            if _video_ai_bridge is not None and hasattr(_video_ai_bridge, "complete_for_stage"):
                response = _video_ai_bridge.complete_for_stage(
                    "interactive_movie",
                    user,
                    system_prompt=system,
                    temperature=1.05,
                    max_tokens=1400,
                    timeout=min(28, max(10, timeout)),
                    use_best=True,
                    extra_context={"run_id": run_id, "quality_mode": "best"},
                )
                if response is not None and getattr(response, "success", False):
                    content = (getattr(response, "content", None) or "").strip()
                    provider = getattr(response, "provider", None) or "llm"
        except Exception:
            content = ""

    if not content and _video_ai_bridge is not None and hasattr(_video_ai_bridge, "complete_multi_provider"):
        try:
            multi = _video_ai_bridge.complete_multi_provider(
                "interactive_movie",
                user,
                system_prompt=system,
                max_providers=2,
                temperature=1.0,
                max_tokens=1400,
                timeout=min(28, max(10, timeout)),
                extra_context={"run_id": run_id, "use_all_ais": True},
            )
            for pname, response in multi or []:
                text = (getattr(response, "content", None) or "").strip()
                if text:
                    content = text
                    provider = pname
                    break
        except Exception as exc:
            return {"success": False, "run_id": run_id, "error": str(exc)[:200]}

    # 3) Retry with a simpler JSON shape if the first creative reply was empty/truncated.
    if not content or not _extract_json_object(content):
        time.sleep(1.2)
        simple = (
            "run_id=%s brief=%s beats=%s. "
            "Return JSON:"
            "{\"title\":str,\"style\":str,\"mood\":str,\"beats\":[str,str,str]}"
        ) % (run_id, brief[:240], want)
        gem2 = _gemini_rest_complete(
            simple,
            system="Return compact JSON only. Invent a NEW style and NEW beat strings every time.",
            timeout=min(28, max(10, timeout)),
        )
        if gem2.get("success") and gem2.get("content"):
            content = str(gem2["content"]).strip()
            provider = gem2.get("provider") or "gemini_rest"

    parsed = _extract_json_object(content)
    if not parsed:
        # Last resort: turn freeform AI direction into beats so every clip still gets AI novelty.
        parsed_beats = _parse_direction_beats(content or "", want)
        if len(parsed_beats) >= 2:
            parsed = {
                "title": "AI freeform pipeline",
                "style": "ai-directed",
                "mood": "fresh",
                "color_grade": "",
                "camera_language": "",
                "people_direction": "people act differently each beat",
                "beats": [
                    {
                        "title": b.get("title") or ("Beat %s" % (i + 1)),
                        "shot_type": _SHOT_TYPES[i % len(_SHOT_TYPES)],
                        "description": b.get("description"),
                        "image_prompt": b.get("description"),
                        "pose_prompts": [
                            "%s — ready pose" % b.get("description"),
                            "%s — mid motion" % b.get("description"),
                            "%s — acting turn" % b.get("description"),
                        ],
                        "motion": ("zoom_in", "pan_right", "zoom_out", "pan_left")[i % 4],
                        "seed": secrets.randbelow(900000) + 1000,
                    }
                    for i, b in enumerate(parsed_beats[:want])
                ],
            }
        else:
            fallback = _procedural_unique_pipeline(brief, seconds, want, run_id)
            fallback["error"] = "AI pipeline JSON missing — used unique procedural fallback"
            fallback["raw"] = (content or "")[:400]
            fallback["provider"] = "procedural_unique"
            return fallback

    raw_beats = parsed.get("beats") if isinstance(parsed.get("beats"), list) else []
    # Gemini sometimes returns beats as plain strings — normalize to objects.
    normalized_raw: List[Dict[str, Any]] = []
    for item in raw_beats:
        if isinstance(item, dict):
            normalized_raw.append(item)
        elif isinstance(item, str) and item.strip():
            normalized_raw.append({
                "title": item.strip().split(".")[0][:48],
                "description": item.strip()[:280],
                "image_prompt": item.strip()[:420],
            })
    beats: List[Dict[str, Any]] = []
    motions = ("zoom_in", "pan_right", "zoom_out", "pan_left")
    style = str(parsed.get("style") or "cinematic").strip()[:80]
    mood = str(parsed.get("mood") or "dramatic").strip()[:80]
    for index, item in enumerate(normalized_raw[:want]):
        shot = str(item.get("shot_type") or _SHOT_TYPES[index % len(_SHOT_TYPES)]).strip().lower()
        if shot not in _SHOT_TYPES:
            shot = _SHOT_TYPES[index % len(_SHOT_TYPES)]
        pose_prompts = item.get("pose_prompts") if isinstance(item.get("pose_prompts"), list) else []
        pose_prompts = [str(p).strip()[:420] for p in pose_prompts if str(p).strip()]
        image_prompt = str(item.get("image_prompt") or item.get("description") or "").strip()[:420]
        description = str(item.get("description") or image_prompt).strip()[:320]
        brief_core = (brief or "").split("[face reference")[0].strip()[:140]
        # Reinforce user brief at the front when the model drifted.
        if brief_core and image_prompt and brief_core.lower()[:24] not in image_prompt.lower():
            image_prompt = ("%s. %s" % (brief_core, image_prompt))[:420]
        if brief_core and description and brief_core.lower()[:24] not in description.lower():
            description = ("%s. %s" % (brief_core, description))[:320]
        title = str(item.get("title") or ("Beat %s" % (index + 1))).strip()[:48]
        try:
            seed = int(item.get("seed") or 0) % 999999
        except (TypeError, ValueError):
            seed = 0
        if seed <= 0:
            seed = (secrets.randbelow(900000) + 1000 + index * 97) % 999999
        motion = str(item.get("motion") or motions[index % 4]).strip().lower()
        if motion not in motions:
            motion = motions[index % 4]
        if len(pose_prompts) < 3:
            base = image_prompt or description or brief
            pose_prompts = [
                ("%s — person standing, ready pose, same scene" % base)[:420],
                ("%s — same person mid-stride, gesturing, same scene" % base)[:420],
                ("%s — same person turning and acting, same scene" % base)[:420],
            ]
        narration = str(item.get("narration") or description or title).strip()[:220]
        beats.append({
            "index": index,
            "title": title,
            "description": description or image_prompt,
            "narration": narration,
            "shot_type": shot,
            "prompt": image_prompt or description,
            "image_prompt": image_prompt or description,
            "pose_prompts": pose_prompts[:3],
            "motion": motion,
            "seed": seed,
        })

    # Expand a short/truncated AI reply into a full unique beat list for this run.
    while len(beats) < want:
        index = len(beats)
        basis = beats[index % max(1, len(beats))]["description"] if beats else brief[:160]
        shot = _SHOT_TYPES[index % len(_SHOT_TYPES)]
        description = (
            "%s — fresh %s angle, style %s, mood %s, run %s"
            % (basis[:140], shot, style or "cinematic", mood or "dramatic", run_id[-6:])
        )[:280]
        beats.append({
            "index": index,
            "title": ("%s %s" % (shot.title(), index + 1))[:48],
            "description": description,
            "narration": ("Scene %s. %s" % (index + 1, description[:140]))[:220],
            "shot_type": shot,
            "prompt": description,
            "image_prompt": description,
            "pose_prompts": [
                ("%s — ready pose" % description)[:420],
                ("%s — mid motion" % description)[:420],
                ("%s — acting turn" % description)[:420],
            ],
            "motion": motions[index % 4],
            "seed": (secrets.randbelow(900000) + 1000 + index * 97) % 999999,
        })

    if len(beats) < 2:
        fallback = _procedural_unique_pipeline(brief, seconds, want, run_id)
        fallback["error"] = "AI returned too few beats — used unique procedural fallback"
        fallback["raw"] = (content or "")[:400]
        return fallback

    # Fill duration across AI beats.
    remaining = float(seconds)
    for index, beat in enumerate(beats):
        left = len(beats) - index
        beat_sec = remaining if left == 1 else max(0.9, round(remaining / left, 2))
        remaining = max(0.0, round(remaining - beat_sec, 2))
        beat["duration_sec"] = beat_sec

    fx_pack = _normalize_fx_pack(
        parsed.get("fx_pack"),
        run_id,
        style=style or "cinematic",
        mood=mood or "dramatic",
    )
    story_bundle = _build_story_bundle(brief, beats, style, mood, run_id)
    ai_story = str(parsed.get("story") or "").strip()[:420]
    if ai_story:
        story_bundle["story"] = ai_story

    return {
        "success": True,
        "run_id": run_id,
        "provider": provider,
        "title": str(parsed.get("title") or "Interactive film")[:80],
        "style": style or "cinematic",
        "mood": mood or "dramatic",
        "color_grade": str(parsed.get("color_grade") or "")[:80],
        "camera_language": str(parsed.get("camera_language") or "")[:120],
        "people_direction": str(parsed.get("people_direction") or "")[:160],
        "fx_pack": fx_pack,
        "story": story_bundle["story"],
        "narration": story_bundle["narration"],
        "beats": beats,
        "direction": "\n".join(
            "%s. [%s] %s" % (i + 1, b["shot_type"], b["description"])
            for i, b in enumerate(beats)
        ),
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
    ai_pipeline: Optional[Dict[str, Any]] = None
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

    # Always invent a brand-new AI pipeline for this clip before rendering.
    if plan:
        ai_pipeline = _ai_design_clip_pipeline(
            render_prompt,
            duration_sec=duration_sec,
            beat_count=_beat_count_for_duration(float(duration_sec)),
            timeout=min(28, max(10, timeout // 5)),
        )
        if ai_pipeline.get("success"):
            planner = "ai_pipeline:%s" % (ai_pipeline.get("provider") or "llm")
            if ai_pipeline.get("direction"):
                direction_blocks.append(str(ai_pipeline["direction"]))
            style_line = " | ".join(
                part for part in (
                    ai_pipeline.get("title"),
                    ai_pipeline.get("style"),
                    ai_pipeline.get("mood"),
                    ai_pipeline.get("color_grade"),
                ) if part
            )
            if style_line:
                direction_blocks.append("Pipeline look: %s" % style_line)
            if ai_pipeline.get("people_direction"):
                direction_blocks.append("People: %s" % ai_pipeline["people_direction"])
        else:
            llm_plan = _plan_with_all_llms(render_prompt, timeout=min(30, max(10, timeout // 6)))
            if llm_plan.get("success") and llm_plan.get("direction"):
                direction_blocks.append(str(llm_plan["direction"]))
                planner = "all_llms"
        if is_available("dramacanva", purpose="planning"):
            planning = prepare_film_project(render_prompt, timeout=min(45, max(15, timeout // 4)))
            if planning.get("success"):
                planned = _planning_text(planning.get("result"))
                if planned:
                    direction_blocks.append(planned)
                if planner and "dramacanva" not in str(planner):
                    planner = "%s+dramacanva" % planner
                elif not planner:
                    planner = "dramacanva"
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
        ai_pipeline=ai_pipeline,
    )

    if render_provider:
        candidates = [render_provider] if is_available(render_provider, purpose="render") else []
    else:
        candidates = list_render_canvases()

    # Full pipeline: try a short canvas/external clip per storyboard beat, then stitch.
    # If paid canvases are exhausted we still assemble the detailed multi-beat movie locally.
    def _finish(clip: Dict[str, Any], renderer: str) -> Dict[str, Any]:
        local_path = clip.get("local_path")
        xvid_path = clip.get("xvid_path")
        if local_path and not xvid_path:
            xvid = _ffmpeg_encode_xvid(str(local_path))
            if xvid.get("success"):
                xvid_path = xvid.get("local_path")
        fx_pack = None
        if ai_pipeline and isinstance(ai_pipeline.get("fx_pack"), dict):
            fx_pack = ai_pipeline.get("fx_pack")
        elif isinstance(clip.get("fx_pack"), dict):
            fx_pack = clip.get("fx_pack")
        else:
            fx_pack = _build_fx_pack(
                str((ai_pipeline or {}).get("run_id") or clip.get("pipeline_run_id") or ("pipe_%s" % uuid.uuid4().hex[:8])),
                style=str((ai_pipeline or {}).get("style") or clip.get("pipeline_style") or ""),
                mood=str((ai_pipeline or {}).get("mood") or clip.get("pipeline_mood") or ""),
            )
        return {
            "success": True,
            "planner": planner,
            "llm_plan": llm_plan,
            "ai_pipeline": ai_pipeline,
            "pipeline_run_id": (ai_pipeline or {}).get("run_id") if ai_pipeline else clip.get("pipeline_run_id"),
            "pipeline_style": (ai_pipeline or {}).get("style") if ai_pipeline else clip.get("pipeline_style"),
            "pipeline_mood": (ai_pipeline or {}).get("mood") if ai_pipeline else clip.get("pipeline_mood"),
            "fx_pack": fx_pack,
            "story": (
                (ai_pipeline or {}).get("story")
                if ai_pipeline and ai_pipeline.get("story")
                else clip.get("story")
            ),
            "narration": (
                (ai_pipeline or {}).get("narration")
                if ai_pipeline and isinstance(ai_pipeline.get("narration"), list)
                else clip.get("narration")
            ),
            "renderer": renderer,
            "planning": planning,
            "prompt_used": render_prompt[:500],
            "local_path": local_path,
            "xvid_path": xvid_path,
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

        # Guaranteed full-detail local storyboard movie from this clip's AI pipeline.
        clip = _generate_free_still_movie(
            brief[:400],
            dest_dir=dest_dir,
            duration=float(duration_sec),
            face_path=face_path,
            direction=direction_text or None,
            ai_pipeline=ai_pipeline,
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
