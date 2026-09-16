import json
import os
from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_casino_social_opt_in_and_geo(tmp_path, monkeypatch):
    monkeypatch.setenv("CASINO_DISCORD_BLOCKED_COUNTRIES", "US")
    from backend.services import casino_social_service

    prefs_dir = tmp_path / "prefs"
    promos = tmp_path / "promos.json"
    monkeypatch.setattr(casino_social_service, "_PREFS_DIR", str(prefs_dir))
    monkeypatch.setattr(casino_social_service, "_PROMOS_PATH", str(promos))

    casino_social_service.set_preferences("user-a", share_wins=True, country_code="MT")
    assert casino_social_service.may_share_win("user-a") is True

    casino_social_service.set_preferences("user-b", share_wins=True, country_code="US")
    assert casino_social_service.may_share_win("user-b") is False

    casino_social_service.set_preferences("user-c", share_wins=False, country_code="MT")
    assert casino_social_service.may_share_win("user-c") is False


def test_casino_social_anonymize():
    from backend.services.casino_social_service import anonymize_user

    alias = anonymize_user("secret-user-id")
    assert alias.startswith("Player#")
    assert len(alias) == len("Player#") + 4


def test_casino_discord_fanout_skips_without_opt_in(tmp_path, monkeypatch):
    events = tmp_path / "activity_events.jsonl"
    cursor = tmp_path / "cursor.json"
    events.write_text(
        json.dumps({
            "ts": "2026-05-18T12:00:00Z",
            "type": "casino_big_win",
            "channel": "casino",
            "user_id": "u1",
            "payload": {"share_ok": False, "anonymized": "Player#abcd", "net": 5000, "currency": "coins", "game": "dice"},
        }) + "\n",
        encoding="utf-8",
    )

    from backend.services import casino_discord_fanout
    monkeypatch.setattr(casino_discord_fanout, "_EVENTS", str(events))
    monkeypatch.setattr(casino_discord_fanout, "_CURSOR", str(cursor))

    posted = []
    with patch("backend.services.discord_service.post_message", side_effect=lambda *a, **k: posted.append(a) or {"success": True}):
        result = casino_discord_fanout.run_fanout()

    assert result["processed"] == 1
    assert result["posted"] == 0
    assert result["skipped"] == 1
    assert not posted


def test_casino_discord_fanout_posts_with_opt_in(tmp_path, monkeypatch):
    events = tmp_path / "activity_events.jsonl"
    cursor = tmp_path / "cursor.json"
    events.write_text(
        json.dumps({
            "ts": "2026-05-18T12:00:00Z",
            "type": "casino_tournament_end",
            "channel": "casino",
            "payload": {"title": "Daily MN2", "pool": 100, "currency": "mn2"},
        }) + "\n",
        encoding="utf-8",
    )

    from backend.services import casino_discord_fanout
    monkeypatch.setattr(casino_discord_fanout, "_EVENTS", str(events))
    monkeypatch.setattr(casino_discord_fanout, "_CURSOR", str(cursor))

    with patch("backend.services.discord_service.post_message", return_value={"success": True}) as post:
        result = casino_discord_fanout.run_fanout()

    assert result["posted"] == 1
    post.assert_called_once()
    assert post.call_args[0][0] == "casino"


def test_casino_platform_news_route(tmp_path, monkeypatch):
    from flask import Flask
    from backend.routes.casino_routes import casino_bp

    news_path = tmp_path / "platform_news.json"
    news_path.write_text(
        json.dumps({
            "items": [
                {"id": "a", "title": "Casino jackpot", "channel": "casino", "date": "2026-05-18"},
                {"id": "b", "title": "Shop update", "channel": "shop", "date": "2026-05-18"},
            ]
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr("backend.routes.platform_news_routes._NEWS_PATH", str(news_path))

    app = Flask(__name__)
    app.register_blueprint(casino_bp)
    with app.test_client() as client:
        resp = client.get("/api/casino/news/platform?limit=5")
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["count"] == 1
    assert data["news"][0]["id"] == "a"
