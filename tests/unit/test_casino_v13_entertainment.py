"""Casino v13 — AI hosts, uber games, network rewards, discord play site."""
from __future__ import annotations

import json
import os
import tempfile

import pytest


@pytest.fixture
def ai_config(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        cfg = {
            "hosts": [
                {"id": "nova", "name": "Nova", "persona": "Hype host", "min_level": 1, "greeting": "Hey!"},
            ],
            "tip_packs_coins": [25, 50],
        }
        path = os.path.join(tmp, "casino_ai_hosts.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        import backend.services.casino_ai_entertainment_service as ai

        monkeypatch.setattr(ai, "_CONFIG_PATH", path)
        yield ai


@pytest.fixture
def uber_config(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        cfg = {
            "preferred_currency_order": ["usd", "mn2"],
            "network_bonus": {"daily_cap_mn2": 0.5, "mn2_per_usd_win": 0.002, "min_bet_usd": 1},
            "games": [
                {
                    "id": "uber_crash",
                    "title": "Uber Crash",
                    "engine": "crash",
                    "min_bet_usd": 5,
                    "max_bet_usd": 500,
                    "min_bet_mn2": 0.1,
                    "max_bet_mn2": 50,
                }
            ],
            "discord_venues": [{"id": "uber", "name": "Uber Lounge", "description": "Premium"}],
        }
        path = os.path.join(tmp, "casino_uber_games.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        import backend.services.casino_uber_games_service as uber

        monkeypatch.setattr(uber, "_CONFIG_PATH", path)
        yield uber


def test_list_ai_hosts(ai_config, monkeypatch):
    monkeypatch.setattr(
        "backend.services.casino_progression_service.get_user_progression",
        lambda uid: {"level": 3},
    )
    out = ai_config.list_hosts("user1")
    assert out["success"] is True
    assert out["hosts"][0]["id"] == "nova"
    assert out["hosts"][0]["unlocked"] is True


def test_uber_catalog(uber_config):
    cat = uber_config.get_uber_catalog(venue="uber")
    assert cat["success"] is True
    assert len(cat["games"]) == 1
    assert cat["venues"][0]["id"] == "uber"


def test_play_session_token(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        tok_path = os.path.join(tmp, "tokens.json")
        import backend.services.discord_play_site_service as dps

        monkeypatch.setattr(dps, "_TOKENS_PATH", tok_path)
        sess = dps.create_play_session("player_x", discord_id="d1", venue="uber", currency="usd")
        assert sess["success"] is True
        assert "discord-play" in sess["play_url"]
        valid = dps.validate_play_token(sess["token"])
        assert valid["success"] is True
        assert valid["user_id"] == "player_x"


def test_network_bonus_cap(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        state = os.path.join(tmp, "users.json")
        ledger = os.path.join(tmp, "anchors.jsonl")
        uber_path = os.path.join(tmp, "uber.json")
        with open(uber_path, "w", encoding="utf-8") as f:
            json.dump({"network_bonus": {"daily_cap_mn2": 0.01, "mn2_per_usd_win": 0.01}}, f)
        import backend.services.casino_network_rewards_service as net

        monkeypatch.setattr(net, "_STATE_PATH", state)
        monkeypatch.setattr(net, "_LEDGER_PATH", ledger)
        monkeypatch.setattr(net, "_UBER_PATH", uber_path)
        monkeypatch.setattr(
            "backend.services.unified_points_database.unified_points_db.add_points",
            lambda *a, **k: {"success": True},
        )
        b1 = net.apply_uber_win_bonus("u1", currency="usd", net=100)
        assert b1["mn2_bonus"] > 0
        b2 = net.apply_uber_win_bonus("u1", currency="usd", net=100)
        assert b2.get("capped") is True or b2.get("mn2_bonus", 0) == 0


def test_slash_playnow(monkeypatch):
    import backend.services.discord_controller_service as svc

    monkeypatch.setattr(
        svc,
        "get_controller_status",
        lambda **kw: {"linked": True, "user_id": "site_u", "discord_id": "d99"},
    )
    monkeypatch.setattr(
        "backend.services.discord_play_site_service.create_play_session",
        lambda uid, **kw: {"success": True, "play_url": "https://masternoder.dk/discord-play/?token=abc"},
    )
    resp = svc.handle_slash_command("playnow", "d99", {})
    assert resp["type"] == 4
    assert "discord-play" in resp["data"]["content"]
