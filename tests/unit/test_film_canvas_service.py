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
    for name in (
        "COMFY_CLOUD_API_KEY",
        "COMFYUI_BASE_URL",
        "COMFY_WORKFLOW_PATH",
        "COMFY_PROMPT_NODE",
        "FILM_CANVAS",
        "FAL_API_KEY",
        "DRAMACANVA_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


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
        if method == "POST":
            assert body["prompt"]["6"]["inputs"]["text"] == "a quiet harbour"
            return {"prompt_id": "prompt-123"}
        return {
            "prompt-123": {
                "outputs": {
                    "12": {"videos": [{"filename": "film.mp4", "subfolder": "", "type": "output"}]}
                }
            }
        }

    def fake_download(url, headers, dest_path, timeout):
        assert "token=" not in url
        assert headers.get("X-API-Key") == SECRET
        with open(dest_path, "wb") as handle:
            handle.write(b"x" * 200)

    monkeypatch.setattr(canvas, "_http_json", fake_json)
    monkeypatch.setattr(canvas, "_download", fake_download)
    monkeypatch.setattr(canvas.time, "sleep", lambda _seconds: None)

    result = canvas.generate_clip("a quiet harbour", dest_dir=str(tmp_path), timeout=5)
    dumped = json.dumps(result)

    assert result["success"] is True
    assert result["canvas"] == "comfy_cloud"
    assert result["local_path"].endswith(".mp4")
    assert os.path.isfile(result["local_path"])
    assert SECRET not in dumped
    assert calls[0][0] == "POST"
    assert calls[0][1] == "https://cloud.comfy.org/prompt"
