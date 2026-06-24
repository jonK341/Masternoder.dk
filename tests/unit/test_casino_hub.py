"""Tests for GET /api/casino/hub super-experience payload."""
import json
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _app(tmp_path, monkeypatch):
    from flask import Flask
    import backend.services.casino_service as casino
    from backend.routes.casino_routes import casino_bp

    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path / "logs"))
    cfg = tmp_path / "casino_config.json"
    cfg.write_text(
        '{"currency":"coins","min_bet":5,"max_bet":500,"max_bets_per_day":50,'
        '"jackpot":{"enabled":true,"rails":{"coins":{"seed":1000,"contribution_rate":0.01,'
        '"win_chance":0,"reseed":1000}}},'
        '"games":{"coin_flip":{"label":"Coin flip","payout_multiplier":1.9,"choices":["heads","tails"]}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg))

    hub_cfg = tmp_path / "casino_hub_config.json"
    hub_cfg.write_text(
        json.dumps({
            "hero": {"title": "Test Casino", "subtitle": "Test sub", "tagline": "Play"},
            "featured_games": [{"id": "crash", "label": "Crash", "tag": "Hot"}],
            "categories": [{"id": "all", "label": "All", "icon": "🎮"}],
            "events": [{"id": "ev1", "title": "Event", "enabled": True}],
            "cross_links": [{"id": "shop", "label": "Shop", "href": "/shop/"}],
        }),
        encoding="utf-8",
    )
    import backend.services.casino_hub_service as hub_svc
    monkeypatch.setattr(hub_svc, "_CONFIG_PATH", str(hub_cfg))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    app.register_blueprint(casino_bp)
    return app


def test_casino_hub_returns_super_experience_payload(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 200, "mn2_balance": 1.5}}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_service.unified_points_db", mock_points, create=True):
                with patch("backend.services.social_platform_fanout_service.get_platform_hub") as mock_social:
                    mock_social.return_value = {"success": True, "platforms": [{"id": "discord", "label": "Discord"}]}
                    resp = client.get("/api/casino/hub?user_id=hub-user")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["hero"]["title"] == "Test Casino"
    assert "online_players_feel" in data["hero"]
    assert data["featured_games"][0]["id"] == "crash"
    assert data["events"][0]["id"] == "ev1"
    assert data["cross_links"][0]["id"] == "shop"
    assert data["user"]["balance"]["coins"] == 200
    assert "social_platforms" in data
    assert data["social_sidebar"]["discord_deep_link"]


def test_casino_hub_includes_jackpots_and_wins(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 50}}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_service.unified_points_db", mock_points, create=True):
                with patch("backend.services.social_platform_fanout_service.get_platform_hub") as mock_social:
                    mock_social.return_value = {"success": True, "platforms": []}
                    with patch("backend.services.casino_ledger.recent_wins") as mock_wins:
                        mock_wins.return_value = [
                            {"user_id": "a", "game": "crash", "currency": "mn2", "net": 0.5, "created_at": "2026-06-24T12:00:00Z"},
                        ]
                        resp = client.get("/api/casino/hub?user_id=a")

    data = resp.get_json()
    assert data["success"] is True
    assert len(data["recent_wins"]) == 1
    assert "jackpots" in data
