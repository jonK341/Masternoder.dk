"""Film canvas registry: public websockets, secrets stay in the environment."""
from __future__ import annotations

import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.services import film_canvas_service as canvas


SECRET = "cloud-key-should-not-leak"


@pytest.fixture
def clean_env(monkeypatch):
    monkeypatch.setattr(canvas, "_ENV_FILES", ())
    canvas._fal_skip_until = 0.0
    for name in (
        "COMFY_CLOUD_API_KEY",
        "COMFYUI_BASE_URL",
        "COMFY_WORKFLOW_PATH",
        "COMFY_PROMPT_NODE",
        "FILM_CANVAS",
        "FAL_API_KEY",
        "DRAMACANVA_API_KEY",
        "DRAMACANVA_PROJECT_ID",
        "FAL_KREA_FRAMES",
        "FAL_KREA_FPS",
    ):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_provider_protocol_limits_match_current_services():
    assert canvas.FAL_TOKEN_EXPIRATION_SECONDS == 3600
    assert canvas.MCP_PROTOCOL_VERSION == "2025-11-25"


def test_fal_token_accepts_string_response(clean_env, monkeypatch):
    clean_env.setenv("FAL_API_KEY", SECRET)

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps("temporary-jwt").encode("utf-8")

    monkeypatch.setattr(canvas.urllib.request, "urlopen", lambda _req, timeout: FakeResponse())

    assert canvas._fal_token() == "temporary-jwt"


def test_public_listing_has_websockets_and_no_secret(clean_env):
    clean_env.setenv("COMFY_CLOUD_API_KEY", SECRET)
    clean_env.setenv("FAL_API_KEY", SECRET)
    rows = {row["id"]: row for row in canvas.list_canvases()}
    dumped = json.dumps(rows)

    assert SECRET not in dumped
    assert rows["comfy_local"]["websocket"].startswith("ws://127.0.0.1:8188/ws?clientId=")
    assert rows["comfy_cloud"]["websocket"].startswith("wss://cloud.comfy.org/ws?clientId=")
    assert "token=" not in rows["comfy_cloud"]["websocket"]
    assert rows["fal_krea"]["websocket"] == "wss://fal.run/fal-ai/krea-wan-14b/ws"
    assert rows["dramacanva"]["http_base"] == "https://dramacanva.com/api/mcp"
    assert rows["comfy_cloud"]["key_env"] == "COMFY_CLOUD_API_KEY"
    assert rows["comfy_cloud"]["key_configured"] is True
    assert rows["comfy_local"]["key_configured"] is True
    assert "film_render" in rows["fal_krea"]["uses"]
    assert "storyboard" in rows["dramacanva"]["uses"]


def test_cloud_socket_can_carry_the_token_for_a_connection(clean_env):
    clean_env.setenv("COMFY_CLOUD_API_KEY", SECRET)
    url = canvas.websocket_url("comfy_cloud", "abc", include_secret=True)
    assert "clientId=abc" in url
    assert "token=" + SECRET in url
    assert SECRET not in canvas.websocket_url("comfy_cloud", "abc", include_secret=False)


def test_local_base_url_switches_to_wss(clean_env):
    clean_env.setenv("COMFYUI_BASE_URL", "https://gpu.example:8188/")
    url = canvas.websocket_url("comfy_local", "abc", include_secret=False)
    assert url.startswith("wss://gpu.example:8188/ws?clientId=abc")


def test_apply_prompt_writes_the_text_node():
    workflow = {
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "old", "clip": ["4", 1]}},
        "9": {"class_type": "SaveImage", "inputs": {}},
    }
    graph = canvas.apply_prompt(workflow, "a night market", "6")
    assert graph["6"]["inputs"]["text"] == "a night market"
    assert workflow["6"]["inputs"]["text"] == "old"


def test_first_output_prefers_video_over_image():
    entry = {
        "outputs": {
            "9": {"images": [{"filename": "still.png", "subfolder": "", "type": "output"}]},
            "12": {"videos": [{"filename": "film.mp4", "subfolder": "clips", "type": "output"}]},
        }
    }
    found = canvas.first_output_file(entry)
    assert found["filename"] == "film.mp4"
    assert found["subfolder"] == "clips"


def test_generate_clip_downloads_without_putting_the_key_in_the_result(clean_env, tmp_path, monkeypatch):
    workflow = {"6": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}}}
    path = tmp_path / "workflow.json"
    path.write_text(json.dumps(workflow), encoding="utf-8")
    clean_env.setenv("COMFY_CLOUD_API_KEY", SECRET)
    clean_env.setenv("COMFY_WORKFLOW_PATH", str(path))
    clean_env.setenv("VIDEOS_DIR", str(tmp_path))

    calls = []

    def fake_json(method, url, headers, body, timeout):
        calls.append((method, url, headers, body))
        assert headers.get("X-API-Key") == SECRET
        assert method == "POST"
        assert body["prompt"]["6"]["inputs"]["text"] == "a quiet harbour"
        return {"prompt_id": "prompt-123"}

    class FakeSocket:
        def __init__(self):
            self.messages = [
                json.dumps({
                    "type": "executed",
                    "data": {
                        "prompt_id": "prompt-123",
                        "node": "12",
                        "output": {
                            "videos": [{
                                "filename": "film.mp4",
                                "subfolder": "",
                                "type": "output",
                            }]
                        },
                    },
                }),
                json.dumps({
                    "type": "execution_success",
                    "data": {"prompt_id": "prompt-123"},
                }),
            ]

        def recv(self):
            return self.messages.pop(0)

        def settimeout(self, _timeout):
            return None

        def close(self):
            return None

    fake_websocket = type(
        "FakeWebsocketModule",
        (),
        {"create_connection": staticmethod(lambda _url, timeout: FakeSocket())},
    )

    def fake_download(url, headers, dest_path, timeout):
        assert "token=" not in url
        assert headers.get("X-API-Key") == SECRET
        with open(dest_path, "wb") as handle:
            handle.write(b"x" * 200)

    monkeypatch.setattr(canvas, "_http_json", fake_json)
    monkeypatch.setattr(canvas, "_download", fake_download)
    monkeypatch.setattr(canvas, "websocket", fake_websocket)

    result = canvas.generate_clip("a quiet harbour", dest_dir=str(tmp_path), timeout=5)
    dumped = json.dumps(result)

    assert result["success"] is True, result
    assert result["canvas"] == "comfy_cloud"
    assert result["local_path"].endswith(".mp4")
    assert os.path.isfile(result["local_path"])
    assert SECRET not in dumped
    assert calls[0][0] == "POST"
    assert calls[0][1] == "https://cloud.comfy.org/api/prompt"


def test_connection_errors_redact_the_cloud_key(clean_env, tmp_path, monkeypatch):
    workflow = tmp_path / "workflow.json"
    workflow.write_text(
        json.dumps({"6": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}}}),
        encoding="utf-8",
    )
    clean_env.setenv("COMFY_CLOUD_API_KEY", SECRET)
    clean_env.setenv("COMFY_WORKFLOW_PATH", str(workflow))
    broken_websocket = type(
        "BrokenWebsocketModule",
        (),
        {
            "create_connection": staticmethod(
                lambda _url, timeout: (_ for _ in ()).throw(RuntimeError("failed " + SECRET))
            )
        },
    )
    monkeypatch.setattr(canvas, "websocket", broken_websocket)

    result = canvas.generate_clip("scene", provider="comfy_cloud")

    assert result["success"] is False
    assert SECRET not in json.dumps(result)
    assert "[REDACTED]" in result["error"]


def test_select_canvas_uses_capabilities(clean_env, tmp_path):
    workflow = tmp_path / "workflow.json"
    workflow.write_text("{}", encoding="utf-8")
    clean_env.setenv("COMFY_WORKFLOW_PATH", str(workflow))
    clean_env.setenv("COMFYUI_BASE_URL", "http://gpu:8188")
    clean_env.setenv("COMFY_CLOUD_API_KEY", SECRET)
    clean_env.setenv("DRAMACANVA_API_KEY", SECRET)

    assert canvas.select_canvas("render") == "comfy_local"
    assert canvas.select_canvas("planning") == "dramacanva"
    clean_env.setenv("FILM_CANVAS", "comfy_cloud")
    assert canvas.select_canvas("render") == "comfy_cloud"


@pytest.mark.parametrize(
    ("preference", "provider"),
    [
        ("auto", None),
        ("canvas", None),
        ("comfyui", "comfy_local"),
        ("comfy_cloud", "comfy_cloud"),
        ("fal", "fal_krea"),
        ("krea", "fal_krea"),
        ("drama", "dramacanva"),
    ],
)
def test_pipeline_preferences_map_to_provider_capabilities(preference, provider):
    assert canvas.provider_for_preference(preference) == provider


def test_fal_queue_fallback_downloads_mp4(clean_env, tmp_path, monkeypatch):
    clean_env.setenv("FAL_API_KEY", SECRET)
    clean_env.setenv("FAL_FORCE_QUEUE", "1")
    calls = []

    def fake_http(method, url, body=None, timeout=60):
        calls.append((method, url, body))
        if method == "POST":
            return {
                "status": "IN_QUEUE",
                "request_id": "req-1",
                "status_url": "https://queue.fal.run/status/req-1",
                "response_url": "https://queue.fal.run/response/req-1",
            }
        if "status" in url:
            return {"status": "COMPLETED"}
        return {"video": {"url": "https://cdn.example/video.mp4"}}

    def fake_download(url, dest_path, timeout=120):
        assert url.endswith(".mp4")
        with open(dest_path, "wb") as handle:
            handle.write(b"mp4" * 40)

    monkeypatch.setattr(canvas, "_fal_http_json", fake_http)
    monkeypatch.setattr(canvas, "_download_url_to_path", fake_download)
    result = canvas.generate_clip("harbour night", dest_dir=str(tmp_path), provider="fal_krea")
    assert result["success"] is True, result
    assert result["mode"] == "queue"
    assert os.path.isfile(result["local_path"])
    assert calls[0][0] == "POST"


def test_fal_realtime_frames_are_encoded_as_a_local_clip(clean_env, tmp_path, monkeypatch):
    clean_env.setenv("FAL_API_KEY", SECRET)
    clean_env.setenv("FAL_KREA_FRAMES", "2")
    clean_env.setenv("FAL_KREA_FPS", "8")
    clean_env.delenv("FAL_FORCE_QUEUE", raising=False)

    class FakeSocket:
        def __init__(self):
            self.messages = ['{"status":"ready"}', b"frame-1" * 20, b"frame-2" * 20]
            self.sent = []
            self.closed = False

        def recv(self):
            return self.messages.pop(0)

        def send_binary(self, payload):
            self.sent.append(payload)

        def settimeout(self, _timeout):
            return None

        def close(self):
            self.closed = True

    fake_socket = FakeSocket()
    fake_websocket = type(
        "FakeWebsocketModule",
        (),
        {"create_connection": staticmethod(lambda _url, timeout: fake_socket)},
    )

    def fake_write(frames, path, fps):
        assert len(frames) == 2
        assert fps == 8
        with open(path, "wb") as handle:
            handle.write(b"mp4" * 100)

    monkeypatch.setattr(canvas, "websocket", fake_websocket)
    monkeypatch.setattr(canvas, "_fal_token", lambda: "temporary-jwt")
    monkeypatch.setattr(canvas, "_write_frame_video", fake_write)

    result = canvas.generate_clip(
        "a moving camera through a forest",
        dest_dir=str(tmp_path),
        provider="fal_krea",
    )

    assert result["success"] is True, result
    assert result["canvas"] == "fal_krea"
    assert result["mode"] == "realtime"
    assert result["frame_count"] == 2
    assert os.path.isfile(result["local_path"])
    assert fake_socket.sent
    assert fake_socket.closed is True


def test_dramacanva_planning_uses_advertised_agent_schema(clean_env, monkeypatch):
    clean_env.setenv("DRAMACANVA_API_KEY", SECRET)
    clean_env.setenv("DRAMACANVA_PROJECT_ID", "project-7")
    calls = []

    def fake_mcp(body, session_id=None, timeout=60):
        calls.append(body)
        method = body["method"]
        if method == "initialize":
            return {"result": {}}, "session-1"
        if method == "tools/list":
            return {
                "result": {
                    "tools": [{
                        "name": "agent_start",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "task": {"type": "string"},
                                "projectId": {"type": "string"},
                                "idempotencyKey": {"type": "string"},
                            },
                            "required": ["task", "projectId", "idempotencyKey"],
                        },
                    }]
                }
            }, session_id
        if method == "tools/call":
            return {"result": {"content": [{"type": "text", "text": "Agent queued"}]}}, session_id
        return {}, session_id

    monkeypatch.setattr(canvas, "_mcp_post", fake_mcp)
    result = canvas.prepare_film_project("Make a six-shot harbour film")

    assert result["success"] is True
    assert result["stage"] == "planning"
    tool_call = next(call for call in calls if call["method"] == "tools/call")
    args = tool_call["params"]["arguments"]
    assert args["task"] == "Make a six-shot harbour film"
    assert args["projectId"] == "project-7"
    assert args["idempotencyKey"].startswith("masternoder-")


def test_dramacanva_pipeline_attaches_planning_result(clean_env, monkeypatch):
    clean_env.setenv("DRAMACANVA_API_KEY", SECRET)
    monkeypatch.setattr(
        canvas,
        "prepare_film_project",
        lambda prompt, timeout: {
            "success": True,
            "canvas": "dramacanva",
            "brief": prompt,
        },
    )
    segments = [{"title": "Opening", "description": "A harbour at night"}]

    result = canvas.generate_segment_clips(segments, provider="dramacanva")

    prep = result[0]["film_canvas_planning"]
    assert prep["success"] is True
    assert "Opening: A harbour at night" in prep["brief"]


def test_planning_text_reads_mcp_content_blocks():
    text = canvas._planning_text({
        "content": [{"type": "text", "text": "Shot 1: harbour lights"}],
    })
    assert text == "Shot 1: harbour lights"


def test_fal_exhausted_is_skipped_and_compose_falls_back(clean_env, tmp_path, monkeypatch):
    clean_env.setenv("FAL_API_KEY", SECRET)
    clean_env.setenv("DRAMACANVA_API_KEY", SECRET)
    canvas._fal_skip_until = 0.0
    monkeypatch.setattr(canvas, "_fal_dependencies_available", lambda: True)
    monkeypatch.setattr(
        canvas,
        "_plan_with_all_llms",
        lambda brief, timeout=25: {"success": False, "providers": [], "direction": ""},
    )
    monkeypatch.setattr(
        canvas,
        "prepare_film_project",
        lambda prompt, timeout: {"success": True, "result": {"text": "Wide shot"}},
    )

    def fake_fal(prompt, dest_dir=None, timeout=90):
        return {
            "success": False,
            "error": 'fal HTTP 403: {"detail":"User is locked. Reason: Exhausted balance."}',
            "canvas": "fal_krea",
        }

    def fake_free(prompt, dest_dir=None, duration=6.0):
        path = os.path.join(dest_dir or str(tmp_path), "fallback.mp4")
        with open(path, "wb") as handle:
            handle.write(b"mp4" * 30)
        return {"success": True, "local_path": path, "canvas": "free_still", "fps": 12}

    monkeypatch.setattr(canvas, "_generate_fal_clip", fake_fal)
    monkeypatch.setattr(canvas, "_generate_external_clip", lambda *a, **k: {"success": False, "error": "skip"})
    monkeypatch.setattr(canvas, "_generate_free_still_movie", fake_free)

    result = canvas.compose_interactive_movie("harbour", dest_dir=str(tmp_path), timeout=30)
    assert result["success"] is True
    assert result["renderer"] == "free_still"
    assert canvas._fal_is_skipped() is True
    assert canvas.is_available("fal_krea") is False
    assert "fal_krea" not in canvas.list_render_canvases()


def test_compose_interactive_movie_plans_then_renders(clean_env, tmp_path, monkeypatch):
    clean_env.setenv("DRAMACANVA_API_KEY", SECRET)
    clean_env.setenv("FAL_API_KEY", SECRET)
    monkeypatch.setattr(canvas, "_fal_dependencies_available", lambda: True)
    monkeypatch.setattr(
        canvas,
        "_plan_with_all_llms",
        lambda brief, timeout=25: {
            "success": True,
            "providers": ["groq", "openai"],
            "direction": "Neon rim light on the console",
            "count": 2,
        },
    )
    monkeypatch.setattr(
        canvas,
        "prepare_film_project",
        lambda prompt, timeout: {
            "success": True,
            "canvas": "dramacanva",
            "result": {"content": [{"type": "text", "text": "Keep the camera low"}]},
        },
    )

    def fake_one(prompt, canvas_id, dest_dir=None, timeout=180):
        path = os.path.join(dest_dir or str(tmp_path), "compose.mp4")
        with open(path, "wb") as handle:
            handle.write(b"mp4" * 40)
        return {
            "success": True,
            "local_path": path,
            "canvas": canvas_id,
            "frame_count": 4,
            "fps": 12,
            "prompt": prompt,
        }

    monkeypatch.setattr(canvas, "_generate_one_canvas_clip", fake_one)
    monkeypatch.setattr(
        canvas,
        "_generate_external_clip",
        lambda *a, **k: {"success": False, "error": "unused"},
    )
    result = canvas.compose_interactive_movie(
        "harbour night",
        dest_dir=str(tmp_path),
        timeout=30,
    )

    assert result["success"] is True
    assert result["planner"] == "all_llms+dramacanva"
    assert result["renderer"] == "fal_krea"
    assert "Keep the camera low" in result["prompt_used"]
    assert "Neon rim light" in result["prompt_used"]
    assert result["llm_plan"]["count"] == 2
    assert os.path.isfile(result["local_path"])


def test_auto_segment_clips_use_compose_pipeline(clean_env, tmp_path, monkeypatch):
    clean_env.setenv("DRAMACANVA_API_KEY", SECRET)
    clean_env.setenv("FAL_API_KEY", SECRET)
    monkeypatch.setattr(canvas, "_fal_dependencies_available", lambda: True)

    def fake_compose(prompt, dest_dir=None, timeout=180, plan=True, render_provider=None):
        path = os.path.join(dest_dir or str(tmp_path), "auto.mp4")
        with open(path, "wb") as handle:
            handle.write(b"mp4" * 20)
        return {
            "success": True,
            "local_path": path,
            "canvas": "fal_krea",
            "planner": "dramacanva",
            "planning": {"success": True},
        }

    monkeypatch.setattr(canvas, "compose_interactive_movie", fake_compose)
    segments = [{"title": "Dock", "description": "Fog rolls in", "mood": "noir"}]
    result = canvas.generate_segment_clips(segments, provider=None)

    assert result[0]["ai_video_path"].endswith("auto.mp4")
    assert result[0]["film_canvas"] == "fal_krea"
    assert result[0]["film_canvas_planner"] == "dramacanva"
    assert result[0]["film_canvas_planning"]["success"] is True
