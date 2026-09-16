"""Create App + Super Encoder nr. 1 + agent leaderboard MN2 rewards."""
from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


@pytest.fixture
def create_app_client(tmp_path, monkeypatch):
    apps_file = tmp_path / "create_apps.json"
    apps_file.write_text(json.dumps({"version": 1, "apps": []}), encoding="utf-8")
    rewards_file = tmp_path / "agent_leaderboard_rewards.json"
    rewards_file.write_text(json.dumps({"claims": {}, "cycles": []}), encoding="utf-8")

    monkeypatch.setattr("backend.services.create_app_service._APPS_FILE", str(apps_file))
    monkeypatch.setattr("backend.services.agent_leaderboard_rewards_service._REWARDS_FILE", str(rewards_file))

    from flask import Flask
    from backend.routes.create_app_routes import create_app_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(create_app_bp)
    return app.test_client()


def test_super_encoder_status():
    from backend.services.super_encoder_service import super_encoder_status

    st = super_encoder_status()
    assert st["success"] is True
    assert st["encoder_id"] == "new_encoder_nr_1"
    assert "e1_hardware" in st
    assert len(st.get("video_profiles") or []) >= 4


def test_heuristic_ai_optimize():
    from backend.services.super_encoder_service import ai_optimize_encode_plan

    plan = ai_optimize_encode_plan(target="podcast", quality_goal="ultra", duration_sec=300)
    assert plan.get("audio_profile") in ("ultra", "studio", "broadcast", "premium", "standard")
    assert "rationale" in plan


def test_finish_checks_count():
    from backend.services.create_app_finish_checks import run_finish_checks

    result = run_finish_checks("test_user")
    assert result["success"] is True
    assert result["total_checks"] == 100
    assert result["passed"] >= 80


def test_create_app_catalog_route(create_app_client):
    r = create_app_client.get("/api/create-app/catalog")
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert any(t["id"] == "playstore_podcast" for t in data["templates"])


def test_create_app_flow(create_app_client, monkeypatch):
    monkeypatch.setenv("MN2_EARN_ALLOW_TEST_USER", "1")

    r = create_app_client.post(
        "/api/create-app/apps",
        json={
            "user_id": "_test_create_app_user",
            "title": "Test Podcast Play App",
            "template_id": "playstore_podcast",
            "quality_goal": "premium",
            "content_hint": "hardware encode test",
        },
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    app = data["app"]
    assert app["id"].startswith("capp_")
    assert app["super_encoder"]["encoder_id"] in ("encoder_v2", "new_encoder_nr_1")
    assert app["super_encoder"].get("encoder_version") == 2 or "v2_tuning" in app["super_encoder"]
    assert data["finish_checks"]["total_checks"] == 100


def test_agent_leaderboard():
    from backend.services.agent_leaderboard_rewards_service import build_agent_leaderboard

    board = build_agent_leaderboard(limit=5)
    assert board["success"] is True
    assert board["reward_currency"] == "MN2"
    assert len(board["leaderboard"]) >= 1


def test_encoder_hub_route(create_app_client):
    r = create_app_client.get("/api/create-app/encoder-hub?quality_goal=premium")
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert data["hub_id"] == "encoder_hub_unified"
    assert "sections" in data


def test_lab_projects_catalog():
    from flask import Flask
    from backend.routes.lab_routes import lab_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(lab_bp)
    with app.test_client() as c:
        r = c.get("/api/lab/projects/catalog")
        assert r.status_code == 200
        data = r.get_json()
        assert data["success"] is True
        assert data["super_encoder_id"] == "new_encoder_nr_1"
        ids = [p["id"] for p in data.get("seed_projects") or []]
        assert "lseed_create_app_super_encoder" in ids


def test_finish_checks_all_pass():
    from backend.services.create_app_finish_checks import run_finish_checks

    result = run_finish_checks("audit_user")
    assert result["total_checks"] == 100
    assert result["passed"] == 100
    assert result["product_finished"] is True


def test_join_reward_once_per_user(create_app_client, monkeypatch):
    monkeypatch.setenv("MN2_EARN_ALLOW_TEST_USER", "1")
    body = {
        "user_id": "_test_join_once_user",
        "title": "First App",
        "template_id": "podcast_only",
    }
    r1 = create_app_client.post("/api/create-app/apps", json=body)
    r2 = create_app_client.post("/api/create-app/apps", json={**body, "title": "Second App"})
    j1 = r1.get_json()["join_reward"]
    j2 = r2.get_json()["join_reward"]
    assert j1.get("success") is True
    assert j2.get("duplicate") or j2.get("skipped") or j2.get("success") is False


def test_finish_blocked_until_checks_pass(create_app_client, monkeypatch):
    monkeypatch.setenv("MN2_EARN_ALLOW_TEST_USER", "1")
    from backend.services.create_app_finish_checks import run_finish_checks

    create_app_client.post(
        "/api/create-app/apps",
        json={"user_id": "_test_finish_gate", "title": "Gate Test App"},
    )
    apps = create_app_client.get("/api/create-app/apps?user_id=_test_finish_gate").get_json()["apps"]
    app_id = apps[0]["id"]

    monkeypatch.setattr(
        "backend.services.create_app_finish_checks.run_finish_checks",
        lambda user_id: {**run_finish_checks(user_id), "product_finished": False, "passed": 50},
    )
    bad = create_app_client.post(
        f"/api/create-app/apps/{app_id}/finish?user_id=_test_finish_gate",
        json={"user_id": "_test_finish_gate"},
    ).get_json()
    assert bad["success"] is False
    assert bad["error"] == "finish_checks_incomplete"


def test_template_agents_assigned(create_app_client, monkeypatch):
    monkeypatch.setenv("MN2_EARN_ALLOW_TEST_USER", "1")
    r = create_app_client.post(
        "/api/create-app/apps",
        json={
            "user_id": "_test_template_agents",
            "title": "Podcast Only App",
            "template_id": "podcast_only",
        },
    )
    agents = r.get_json()["app"]["assigned_agents"]
    assert "podcast_producer_agent" in agents
    assert "content_generator_agent" in agents


def test_create_app_starts_encode_jobs(create_app_client, monkeypatch):
    monkeypatch.setenv("MN2_EARN_ALLOW_TEST_USER", "1")

    podcast_calls = []
    video_calls = []

    def fake_podcast(user_id, app, **kwargs):
        podcast_calls.append(app.get("super_encoder", {}).get("audio_profile"))
        return {
            "success": True,
            "job_id": "pod-test123",
            "status": "queued",
            "encode_profile": "ultra",
        }

    def fake_video(user_id, app, **kwargs):
        video_calls.append(app.get("super_encoder", {}).get("video_profile"))
        return {
            "success": True,
            "documentary_id": "doc-test-uuid",
            "status": "processing",
            "encode_profile": "premium",
        }

    monkeypatch.setattr(
        "backend.services.create_app_encode_service.start_podcast_encode_job",
        fake_podcast,
    )
    monkeypatch.setattr(
        "backend.services.create_app_encode_service.start_video_encode_job",
        fake_video,
    )
    monkeypatch.setattr(
        "backend.services.create_app_encode_service.refresh_encode_jobs",
        lambda jobs: jobs or {},
    )

    r = create_app_client.post(
        "/api/create-app/apps",
        json={
            "user_id": "_test_encode_jobs",
            "title": "Encode Jobs App",
            "quality_goal": "premium",
            "content_hint": "podcast + play store encode",
        },
    )
    data = r.get_json()
    assert data["success"] is True
    assert "encode_jobs" in data
    assert podcast_calls
    assert video_calls
    assert data["app"]["encode_jobs"].get("podcast", {}).get("job_id") == "pod-test123"


def test_encode_jobs_status_route(create_app_client, monkeypatch):
    monkeypatch.setenv("MN2_EARN_ALLOW_TEST_USER", "1")
    monkeypatch.setattr(
        "backend.services.create_app_encode_service.refresh_podcast_job_status",
        lambda job: {**job, "status": "completed", "episode_id": "gen-abc"},
    )
    monkeypatch.setattr(
        "backend.services.create_app_encode_service.refresh_video_job_status",
        lambda job: {**job, "status": "processing", "progress": 42},
    )
    monkeypatch.setattr(
        "backend.services.create_app_encode_service.start_podcast_encode_job",
        lambda user_id, app, **kw: {
            "success": True,
            "job_id": "pod-enc001",
            "status": "queued",
            "encode_profile": "ultra",
        },
    )
    monkeypatch.setattr(
        "backend.services.create_app_encode_service.start_video_encode_job",
        lambda user_id, app, **kw: {
            "success": True,
            "documentary_id": "00000000-0000-0000-0000-000000000099",
            "status": "processing",
            "encode_profile": "premium",
        },
    )

    create_app_client.post(
        "/api/create-app/apps",
        json={"user_id": "_test_encode_status", "title": "Status App", "include_playstore": True},
    )
    app_id = create_app_client.get("/api/create-app/apps?user_id=_test_encode_status").get_json()["apps"][0]["id"]
    r = create_app_client.get(f"/api/create-app/apps/{app_id}/encode-jobs?user_id=_test_encode_status")
    data = r.get_json()
    assert data["success"] is True
    assert "encode_jobs" in data
    assert data["encode_jobs"].get("podcast", {}).get("status") == "completed"


def test_encoder_v2_catalog_count():
    from backend.services.encoder_v2_service import load_catalog, catalog_upgrades

    cat = load_catalog()
    assert cat.get("upgrade_count") == 250
    assert len(catalog_upgrades()) == 250


def test_encoder_v2_status_and_free_unlocks():
    from backend.services.encoder_v2_service import encoder_v2_status, ensure_free_unlocks

    ensure_free_unlocks("_test_v2_user")
    st = encoder_v2_status("_test_v2_user")
    assert st["success"] is True
    assert st["upgrade_count"] == 250
    assert st["unlocked_count"] >= 12


def test_encoder_v2_hub_route(create_app_client):
    r = create_app_client.get("/api/create-app/encoder-v2/hub?user_id=_test_v2_hub&quality_goal=premium")
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert data["hub_id"] == "encoder_v2_hub"
    assert data["status"]["upgrade_count"] == 250


def test_encoder_v2_catalog_route(create_app_client):
    r = create_app_client.get("/api/create-app/encoder-v2/catalog?user_id=_test_v2_cat&limit=10")
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert len(data["upgrades"]) == 10
    assert data["total"] == 250


def test_encoder_v2_build_package():
    from backend.services.encoder_v2_service import build_v2_encode_package

    pkg = build_v2_encode_package({"user_id": "_test_v2_pkg", "quality_goal": "premium"})
    assert pkg.get("success") is True
    assert pkg.get("encoder_version") == 2
    assert "v2_tuning" in pkg


def test_super_encode_rerun(create_app_client, monkeypatch):
    monkeypatch.setenv("MN2_EARN_ALLOW_TEST_USER", "1")
    create_app_client.post(
        "/api/create-app/apps",
        json={"user_id": "_test_reencode", "title": "Reencode App"},
    )
    app_id = create_app_client.get("/api/create-app/apps?user_id=_test_reencode").get_json()["apps"][0]["id"]
    r = create_app_client.post(
        f"/api/create-app/apps/{app_id}/super-encode?user_id=_test_reencode",
        json={"user_id": "_test_reencode", "quality_goal": "ultra"},
    )
    data = r.get_json()
    assert data["success"] is True
    assert data["super_encoder"]["encoder_id"] in ("encoder_v2", "new_encoder_nr_1")
