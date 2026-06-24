"""Casino v14 MultiPlay + Facebook casino bot."""
from __future__ import annotations

import json
import os
import tempfile

import pytest


@pytest.fixture
def multiplay_config(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        cfg = {
            "room_boost": {"min_mult": 1.05, "max_mult": 1.2, "players_for_max": 40},
            "community_pot": {"enabled": False},
            "categories": [{"id": "party_blast", "label": "Party"}],
            "games": [
                {
                    "id": "mp_test_coin",
                    "title": "Test Coin",
                    "category": "party_blast",
                    "engine": "coin_flip",
                    "min_bet": 5,
                    "max_bet": 100,
                    "min_players": 2,
                    "max_players": 20,
                    "engine_params": {"choice": "heads"},
                }
            ],
        }
        path = os.path.join(tmp, "multiplay.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        import backend.services.casino_multiplay_service as mp
        monkeypatch.setattr(mp, "_CONFIG_PATH", path)
        yield mp


@pytest.fixture
def facebook_bot(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        import backend.services.facebook_casino_bot_service as fb
        monkeypatch.setattr(fb, "_STATE_DIR", tmp)
        monkeypatch.setattr(fb, "_USERS_PATH", os.path.join(tmp, "users.json"))
        monkeypatch.setattr(fb, "_CODES_PATH", os.path.join(tmp, "codes.json"))
        monkeypatch.setattr(fb, "_BASE", tmp)
        yield fb


def test_multiplay_catalog_has_30_games():
    import backend.services.casino_multiplay_service as mp
    cat = mp.get_multiplay_catalog()
    assert cat["success"] is True
    assert len(cat.get("games") or []) >= 30
    assert cat["stats"]["games_count"] >= 30


def test_multiplay_catalog_players_online(multiplay_config):
    mp = multiplay_config
    cat = mp.get_multiplay_catalog()
    g = cat["games"][0]
    assert g.get("players_online", 0) >= 2


def test_messenger_casino_command(facebook_bot):
    fb = facebook_bot
    resp = fb.handle_messenger_text("psid_123", "CASINO")
    assert resp["success"] is True
    assert "MultiPlay" in resp["messages"][0]["text"] or "multiplay" in resp["messages"][0]["text"].lower()


def test_facebook_link_flow(facebook_bot):
    fb = facebook_bot
    code_out = fb.create_link_code("user_fb_1")
    assert code_out["success"] is True
    link = fb.complete_link_with_code("psid_999", code_out["code"])
    assert link["success"] is True
    st = fb.get_facebook_status(facebook_psid="psid_999")
    assert st["linked"] is True


def test_multiplay_play_delegates(multiplay_config, monkeypatch):
    mp = multiplay_config
    monkeypatch.setattr(
        "backend.services.casino_service.play_coin_flip",
        lambda uid, bet, choice, currency="coins": {
            "success": True, "outcome": "win", "net": 10, "payout": 15, "bet": bet,
        },
    )
    out = mp.play_multiplay("player1", "mp_test_coin", 10, "coins")
    assert out["success"] is True
    assert out.get("multiplay_tier") is True
    assert out.get("players_in_room", 0) > 0
