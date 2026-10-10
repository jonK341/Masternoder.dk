"""Game Hub routes — progression quest API shape."""
import tempfile
from unittest.mock import patch

import pytest

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


@pytest.fixture
def hub_app(monkeypatch):
    from flask import Flask
    import backend.services.quest_system as qs
    from backend.routes.game_hub_routes import game_hub_bp

    tmp = tempfile.mkdtemp()
    monkeypatch.setattr(qs, "_LEVEL_CACHE", None)
    monkeypatch.setattr(qs, "_progress_dir", lambda: tmp)

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(game_hub_bp)
    return app


def test_game_hub_quests_includes_ninety_levels(hub_app, monkeypatch):
    monkeypatch.setattr(
        "backend.services.trophy_quest_service.get_unified_quests",
        lambda uid: {
            "success": True,
            "quests": [],
            "trophy_quests": [],
            "platform_quests": [],
            "ai_quests": [],
            "casino_quests": [],
            "claim_streak": {"days": 0, "bonus_at_day": 7, "bonus_mn2": 0.007},
        },
    )
    monkeypatch.setattr(
        "backend.services.quest_system._metric_value",
        lambda uid, metric, state: 0,
    )

    with hub_app.test_client() as client:
        r = client.get("/api/game-hub/quests?user_id=route_test_user")

    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert data["total_progression_levels"] == 90
    assert len(data["progression_levels"]) == 90
    assert len(data["chapters"]) == 9
    assert data["progression"]["total_levels"] == 90


def test_quest_page_user_endpoint(hub_app, monkeypatch):
    from flask import Flask
    from backend.routes.quest_page import quest_page_bp

    monkeypatch.setattr(
        "backend.services.quest_system._metric_value",
        lambda uid, metric, state: 0,
    )

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(quest_page_bp)

    with app.test_client() as client:
        r = client.get("/api/quests/user/page_user?chapter=1")

    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert data["total_levels"] == 90
    assert len(data["levels"]) == 10
    assert all(l["chapter"] == 1 for l in data["levels"])
