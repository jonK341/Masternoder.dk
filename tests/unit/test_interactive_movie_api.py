"""Mission Control interactive movie API (plan → render job)."""
from __future__ import annotations

import os
import sys
import time

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("FAL_API_KEY", "fal-test-key")
    monkeypatch.setenv("DRAMACANVA_API_KEY", "drama-test-key")
    monkeypatch.setenv("VIDEOS_DIR", str(tmp_path))
    monkeypatch.delenv("FILM_MONITOR_PROMO_STARTED_AT", raising=False)
    monkeypatch.setattr(
        "backend.services.film_monitor_billing_service._DATA_FILE",
        str(tmp_path / "film_monitor_billing.json"),
    )
    monkeypatch.setattr(
        "backend.services.film_canvas_service._ENV_FILES",
        (),
        raising=False,
    )
    monkeypatch.setattr(
        "backend.services.film_canvas_service._fal_dependencies_available",
        lambda: True,
    )

    def fake_compose(
        prompt,
        dest_dir=None,
        timeout=180,
        plan=True,
        render_provider=None,
        duration_sec=8,
        face_path=None,
    ):
        path = os.path.join(dest_dir or str(tmp_path), "interactive.mp4")
        with open(path, "wb") as handle:
            handle.write(b"\x00\x00\x00\x18ftypmp42" + b"0" * 64)
        return {
            "success": True,
            "planner": "all_llms+dramacanva",
            "renderer": "fal_krea",
            "prompt_used": prompt,
            "local_path": path,
            "canvas": "fal_krea",
            "duration_sec": duration_sec,
            "has_face": bool(face_path),
            "llm_plan": {"success": True, "providers": ["groq"], "count": 1},
        }

    monkeypatch.setattr(
        "backend.services.film_canvas_service.compose_interactive_movie",
        fake_compose,
    )

    from src.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_interactive_movie_job_completes_and_serves_video(client):
    started = client.post(
        "/api/film-canvas/interactive-movie",
        json={"prompt": "harbour control room film"},
    )
    assert started.status_code == 202
    body = started.get_json()
    assert body["success"] is True
    job_id = body["job_id"]
    assert job_id.startswith("im_")

    deadline = time.time() + 5
    status = None
    while time.time() < deadline:
        response = client.get("/api/film-canvas/interactive-movie/" + job_id)
        assert response.status_code == 200
        status = response.get_json()
        if status.get("status") in ("completed", "failed"):
            break
        time.sleep(0.05)

    assert status is not None
    assert status["status"] == "completed"
    assert status["planner"] == "all_llms+dramacanva"
    assert status["renderer"] == "fal_krea"
    assert status["video_url"].endswith("/video")

    video = client.get(status["video_url"])
    assert video.status_code == 200
    assert video.mimetype == "video/mp4"
    assert len(video.data) > 20


def test_interactive_movie_accepts_duration_and_face(client, tmp_path):
    # 1x1 PNG
    face = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    response = client.post(
        "/api/film-canvas/interactive-movie",
        json={
            "prompt": "harbour with a person",
            "duration_sec": 24,
            "face_image": face,
            "user_id": "face-tester",
        },
    )
    assert response.status_code == 202
    body = response.get_json()
    assert body["job_id"]
    assert body["duration_sec"] == 24
    assert body["has_face"] is True


def test_billing_status_is_free_program(client):
    response = client.get("/api/film-canvas/billing?user_id=film-tester")
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["always_free"] is True
    assert body["can_play"] is True
    assert body["pay_options"] == {}


def test_interactive_movie_stays_free_after_old_window(client, monkeypatch):
    from datetime import datetime, timedelta, timezone

    started = datetime.now(timezone.utc) - timedelta(hours=30)
    monkeypatch.setenv(
        "FILM_MONITOR_PROMO_STARTED_AT",
        started.isoformat().replace("+00:00", "Z"),
    )
    monkeypatch.setenv("FILM_MONITOR_ALWAYS_FREE", "1")
    response = client.post(
        "/api/film-canvas/interactive-movie",
        json={"prompt": "free scene", "user_id": "film-tester"},
    )
    assert response.status_code == 202
    body = response.get_json()
    assert body.get("job_id")
    assert body.get("billing", {}).get("free_active") is True


def test_interactive_movie_can_require_payment_when_paid_mode(client, monkeypatch):
    from datetime import datetime, timedelta, timezone

    started = datetime.now(timezone.utc) - timedelta(hours=30)
    monkeypatch.setenv(
        "FILM_MONITOR_PROMO_STARTED_AT",
        started.isoformat().replace("+00:00", "Z"),
    )
    monkeypatch.setenv("FILM_MONITOR_ALWAYS_FREE", "0")
    response = client.post(
        "/api/film-canvas/interactive-movie",
        json={"prompt": "paid scene", "user_id": "film-tester"},
    )
    assert response.status_code == 402
    body = response.get_json()
    assert body["code"] == "PAYMENT_REQUIRED"
    assert "mn2" in body["pay_options"]
    assert "paypal" in body["pay_options"]
