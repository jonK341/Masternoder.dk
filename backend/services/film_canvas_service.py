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


def select_canvas(purpose: str = "render") -> Optional[str]:
    """Select a configured canvas for rendering or planning."""
    forced = _env("FILM_CANVAS").strip().lower()
    forced = PREFERENCE_ALIASES.get(forced, forced)
    if forced in CANVASES:
        return forced if is_available(forced, purpose=purpose) else None
    if purpose == "planning":
        return "dramacanva" if _env("DRAMACANVA_API_KEY") else None
    if _env("COMFYUI_BASE_URL") and _comfy_workflow_available():
        return "comfy_local"
    if _env("COMFY_CLOUD_API_KEY") and _comfy_workflow_available():
        return "comfy_cloud"
    if _env("FAL_API_KEY"):
        return "fal_krea"
    return None


def _comfy_workflow_available() -> bool:
    path = _env("COMFY_WORKFLOW_PATH")
    return bool(path) and os.path.isfile(path)


def _fal_dependencies_available() -> bool:
    return websocket is not None and msgpack is not None and imageio is not None


def is_available(canvas_id: Optional[str] = None, *, purpose: str = "render") -> bool:
    """Whether a canvas has the credentials, files, and local clients it needs."""
    if canvas_id is None:
        return select_canvas(purpose) is not None
    if canvas_id in ("comfy_local", "comfy_cloud"):
        if not _comfy_workflow_available():
            return False
        if canvas_id == "comfy_cloud":
            return bool(_env("COMFY_CLOUD_API_KEY"))
        return bool(_env("COMFYUI_BASE_URL"))
    if canvas_id == "fal_krea":
        # Queue HTTP works with only the key; realtime websocket needs extra deps.
        return bool(_env("FAL_API_KEY"))
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


def generate_clip(
    prompt: str,
    dest_dir: Optional[str] = None,
    timeout: int = 180,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a local clip with the selected renderer canvas."""
    canvas_id = provider or select_canvas("render")
    if canvas_id in ("comfy_local", "comfy_cloud"):
        return _generate_comfy_clip(prompt, dest_dir, timeout, canvas_id=canvas_id)
    if canvas_id == "fal_krea":
        return _generate_fal_clip(prompt, dest_dir, timeout)
    return {"success": False, "error": "No render-capable film canvas is configured"}


def compose_interactive_movie(
    prompt: str,
    *,
    dest_dir: Optional[str] = None,
    timeout: int = 180,
    plan: bool = True,
    render_provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Plan with DramaCanvas (when configured), then render with fal/Comfy.

    This is the monitor interactive-movie path: storyboard first, realtime
    canvas second, one local MP4 out.
    """
    brief = (prompt or "").strip()
    if not brief:
        return {"success": False, "error": "prompt is required"}

    planning: Optional[Dict[str, Any]] = None
    planner: Optional[str] = None
    render_prompt = brief
    if plan and is_available("dramacanva", purpose="planning"):
        planner = "dramacanva"
        # Keep planning short so the monitor can still render on time.
        planning = prepare_film_project(brief, timeout=min(45, max(15, timeout // 4)))
        if planning.get("success"):
            planned = _planning_text(planning.get("result"))
            if planned:
                render_prompt = (brief + "\n\nStoryboard direction:\n" + planned)[:2000]

    renderer = render_provider or select_canvas("render")
    if not renderer or not is_available(renderer, purpose="render"):
        return {
            "success": False,
            "error": "No render-capable film canvas is configured",
            "planner": planner,
            "renderer": None,
            "planning": planning,
            "prompt_used": render_prompt[:500],
        }

    render_timeout = max(90, timeout - 45) if planner else max(90, timeout)
    clip = generate_clip(
        render_prompt[:500],
        dest_dir=dest_dir,
        timeout=render_timeout,
        provider=renderer,
    )
    return {
        "success": bool(clip.get("success")),
        "planner": planner,
        "renderer": renderer,
        "planning": planning,
        "prompt_used": render_prompt[:500],
        "local_path": clip.get("local_path"),
        "canvas": clip.get("canvas") or renderer,
        "frame_count": clip.get("frame_count"),
        "fps": clip.get("fps"),
        "error": None if clip.get("success") else clip.get("error"),
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
