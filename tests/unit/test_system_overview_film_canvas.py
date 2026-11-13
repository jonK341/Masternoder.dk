"""Mission Control overview includes film canvases without leaking secrets."""
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
    monkeypatch.setenv("FAL_API_KEY", "fal-monitor-key")
    monkeypatch.setenv("DRAMACANVA_API_KEY", "drama-monitor-key")
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


def test_system_overview_lists_film_canvases(client):
    response = client.get("/api/system/overview?compact=1")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    rows = {row.get("id") or row.get("name"): row for row in payload["video_providers"]}
    dumped = json.dumps(payload)

    assert "fal-monitor-key" not in dumped
    assert "drama-monitor-key" not in dumped
    assert rows["fal_krea"]["available"] is True
    assert rows["dramacanva"]["available"] is True
    assert rows["film_canvas_auto"]["selected_renderer"] == "fal_krea"
    assert rows["film_canvas_auto"]["selected_planner"] == "dramacanva"
    assert payload["health"]["video_providers_ready"] >= 2
