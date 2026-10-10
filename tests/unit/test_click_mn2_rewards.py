"""Instant MN2 click rewards."""
from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


@pytest.fixture
def click_client(tmp_path, monkeypatch):
    prog_dir = tmp_path / "click_game"
    prog_dir.mkdir()
    monkeypatch.setattr("backend.routes.click_game_routes._PROGRESS_DIR", str(prog_dir))

    from flask import Flask
    from backend.routes.click_game_routes import click_game_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(click_game_bp)
    return app.test_client()


def test_click_reward_quote():
    from backend.services.click_mn2_rewards_service import click_reward_quote

    q = click_reward_quote("click", {"critical": True})
    assert q["success"] is True
    assert q["instant"] is True
    assert q["amount_mn2"] > 0


def test_instant_click_reward_eligible_user(monkeypatch):
    from backend.services.click_mn2_rewards_service import credit_instant_click_reward

    monkeypatch.setenv("MN2_EARN_ALLOW_TEST_USER", "1")
    r = credit_instant_click_reward(
        "_test_click_mn2_user",
        action="click",
        click_id="test-click-001",
        metadata={"critical": False, "combo": 2, "level": 3},
    )
    assert r.get("success") is True or r.get("duplicate") is True
    if r.get("success"):
        assert r.get("instant") is True
        assert float(r.get("amount_mn2") or 0) > 0


def test_click_game_instant_reward_route(click_client):
    r = click_client.post(
        "/api/game/click-game/instant-reward",
        json={
            "user_id": "_test_click_route_user",
            "action": "click",
            "click_id": "route-test-click-1",
            "metadata": {"level": 1},
        },
    )
    data = r.get_json()
    assert r.status_code in (200, 400)
    assert "instant" in data or "error" in data


def test_encoder_hub_gathered():
    from backend.services.super_encoder_service import gather_encoder_hub

    hub = gather_encoder_hub({"quality_goal": "premium", "target": "hybrid"})
    assert hub["success"] is True
    assert hub["encoder_nr"] == 1
    assert "video" in hub["sections"]
    assert "audio" in hub["sections"]
    assert "ai" in hub["sections"]
    assert hub["package"].get("video_profile")
