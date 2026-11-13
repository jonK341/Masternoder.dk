"""Film canvases appear in /api/ai/video-providers without leaking secrets."""
from __future__ import annotations

import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("FAL_API_KEY", "fal-test-key")
    monkeypatch.setenv("DRAMACANVA_API_KEY", "drama-test-key")
    monkeypatch.delenv("COMFY_CLOUD_API_KEY", raising=False)
    monkeypatch.delenv("COMFYUI_BASE_URL", raising=False)
    monkeypatch.delenv("COMFY_WORKFLOW_PATH", raising=False)
    monkeypatch.setattr(
        "backend.services.film_canvas_service._ENV_FILES",
        (),
        raising=False,
    )
    from src.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_video_providers_lists_configured_film_canvases(client):
    response = client.get("/api/ai/video-providers")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    rows = {row.get("id"): row for row in payload["providers"] if row.get("type") == "film_canvas"}
    dumped = json.dumps(payload)

    assert "fal-test-key" not in dumped
    assert "drama-test-key" not in dumped
    assert rows["fal_krea"]["configured"] is True
    assert rows["fal_krea"]["available"] is True
    assert rows["dramacanva"]["configured"] is True
    assert rows["dramacanva"]["available"] is True
    assert rows["film_canvas_auto"]["selected_renderer"] == "fal_krea"
    assert rows["film_canvas_auto"]["selected_planner"] == "dramacanva"
