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

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, List, Optional

COMFY_CLOUD_HTTP = "https://cloud.comfy.org"
COMFY_CLOUD_WS = "wss://cloud.comfy.org/ws"
FAL_KREA_WS = "wss://fal.run/fal-ai/krea-wan-14b/ws"
DRAMACANVA_HTTP = "https://dramacanva.com/api/mcp"
_DEFAULT_LOCAL_HTTP = "http://127.0.0.1:8188"
_ENV_FILES = ("/var/www/html/.env", "/var/www/html/vidgenerator/.env")

# id -> how to reach it. key_env None means the canvas has no secret.
CANVASES: Dict[str, Dict[str, Any]] = {
    "comfy_local": {
        "label": "ComfyUI local",
        "transport": "websocket",
        "key_env": None,
        "auth_header": None,
        "generates_mp4": True,
    },
    "comfy_cloud": {
        "label": "Comfy Cloud",
        "transport": "websocket",
        "key_env": "COMFY_CLOUD_API_KEY",
        "auth_header": "X-API-Key",
        "generates_mp4": True,
    },
    "fal_krea": {
        "label": "fal.ai Krea realtime",
        "transport": "websocket",
        "key_env": "FAL_API_KEY",
        "auth_header": None,
        "generates_mp4": False,
    },
    "dramacanva": {
        "label": "DramaCanvas",
        "transport": "http",
        "key_env": "DRAMACANVA_API_KEY",
        "auth_header": "Authorization",
        "generates_mp4": False,
    },
}


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
            "generates_mp4": bool(spec.get("generates_mp4")),
        })
    return rows


def select_canvas() -> Optional[str]:
    """Which Comfy canvas can submit a workflow right now."""
    forced = _env("FILM_CANVAS").strip().lower()
    if forced in ("comfy_local", "comfy_cloud"):
        return forced
    if _env("COMFY_CLOUD_API_KEY"):
        return "comfy_cloud"
    if _env("COMFYUI_BASE_URL"):
        return "comfy_local"
    return None


def is_available() -> bool:
    """True when a Comfy canvas and an API-format workflow file are both set."""
    if select_canvas() is None:
        return False
    path = _env("COMFY_WORKFLOW_PATH")
    return bool(path) and os.path.isfile(path)


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


def generate_clip(
    prompt: str,
    dest_dir: Optional[str] = None,
    timeout: int = 180,
) -> Dict[str, Any]:
    """
    Submit the configured Comfy workflow and download the first output file.
    Returns {success, local_path, prompt_id, canvas, error}.
    """
    canvas_id = select_canvas()
    workflow_path = _env("COMFY_WORKFLOW_PATH")
    if canvas_id is None or not workflow_path or not os.path.isfile(workflow_path):
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
    base = _http_base(canvas_id)
    headers = auth_headers(canvas_id)
    try:
        queued = _http_json(
            "POST",
            base + "/prompt",
            headers,
            {"prompt": graph, "client_id": client_id},
            timeout=60,
        )
    except (RuntimeError, urllib.error.URLError, OSError) as exc:
        return {"success": False, "error": "Canvas submit failed: %s" % exc, "canvas": canvas_id}

    prompt_id = str(queued.get("prompt_id") or "")
    if not prompt_id:
        return {"success": False, "error": "Canvas did not return a prompt_id", "canvas": canvas_id}

    deadline = time.time() + max(5, timeout)
    entry: Dict[str, Any] = {}
    while time.time() < deadline:
        try:
            history = _http_json("GET", base + "/history/" + urllib.parse.quote(prompt_id), headers, None, timeout=30)
        except (RuntimeError, urllib.error.URLError, OSError):
            history = {}
        entry = history.get(prompt_id) if isinstance(history.get(prompt_id), dict) else history
        if not isinstance(entry, dict):
            entry = {}
        status = entry.get("status") if isinstance(entry.get("status"), dict) else {}
        if status.get("status_str") == "error":
            message = status.get("exception_message") or "execution error"
            return {"success": False, "error": str(message)[:300], "prompt_id": prompt_id, "canvas": canvas_id}
        if first_output_file(entry):
            break
        time.sleep(2)
    else:
        return {"success": False, "error": "Canvas job timed out", "prompt_id": prompt_id, "canvas": canvas_id}

    output = first_output_file(entry)
    if not output:
        return {"success": False, "error": "Canvas finished without a file", "prompt_id": prompt_id, "canvas": canvas_id}

    if dest_dir is None:
        dest_dir = os.environ.get("VIDEOS_DIR") or os.path.dirname(workflow_path)
    os.makedirs(dest_dir, exist_ok=True)
    ext = os.path.splitext(output["filename"])[1] or ".mp4"
    dest_path = os.path.join(dest_dir, "canvas_%s%s" % (prompt_id[:8], ext))
    view = base + "/view?" + urllib.parse.urlencode({
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


def generate_segment_clips(
    segments: list,
    max_clips: int = 1,
    timeout_per_clip: int = 180,
) -> list:
    """Fill ai_video_path on up to max_clips segments from the film canvas."""
    if not is_available():
        return segments
    dest_dir = os.environ.get("VIDEOS_DIR")
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
        result = generate_clip(prompt[:500], dest_dir=dest_dir, timeout=timeout_per_clip)
        if result.get("success") and result.get("local_path"):
            seg["ai_video_path"] = result["local_path"]
            seg["film_canvas"] = result.get("canvas")
            filled += 1
    return segments
