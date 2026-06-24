"""Casino social hub — feed, challenges, hub aggregate."""
from __future__ import annotations

import os
import tempfile

import pytest


@pytest.fixture
def social_state(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        social_path = os.path.join(tmp, "social_structure.json")
        data = {
            "friends": {"alice": ["bob"], "bob": ["alice"]},
            "crews": [{"id": "crew1", "name": "High Rollers", "member_ids": ["alice"]}],
            "user_crews": {"alice": "crew1"},
            "activity_feed": [
                {
                    "id": "a1",
                    "user_id": "bob",
                    "action_type": "casino_win",
                    "label": "Won crash",
                    "ts": "2026-06-24T12:00:00Z",
                    "extra": {"channel": "casino"},
                },
                {
                    "id": "a2",
                    "user_id": "bob",
                    "action_type": "battle",
                    "label": "Quick battle",
                    "ts": "2026-06-24T11:00:00Z",
                    "extra": {},
                },
            ],
            "challenges": [],
        }
        import json

        with open(social_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        import backend.routes.social_routes as social_routes

        monkeypatch.setattr(social_routes, "SOCIAL_DATA_PATH", social_path)
        yield social_routes


def test_casino_feed_filters_non_casino(social_state):
    import backend.services.casino_social_hub_service as hub

    out = hub.get_casino_feed("alice", friends_only=False, limit=10)
    assert out["success"] is True
    assert len(out["feed"]) == 1
    assert out["feed"][0]["action_type"] == "casino_win"


def test_casino_challenge_friends_only(social_state):
    import backend.services.casino_social_hub_service as hub

    ok = hub.send_casino_challenge("alice", "bob", "casino_bets_race", target=5)
    assert ok["success"] is True
    blocked = hub.send_casino_challenge("alice", "stranger", "casino_bets_race", target=5)
    assert blocked["success"] is False


def test_push_casino_bet_activity_win(social_state):
    import backend.services.casino_social_hub_service as hub

    hub.push_casino_bet_activity("alice", "crash", "win", 50.0, 75.0, "coins", None)
    feed = hub.get_casino_feed("alice", limit=5)
    assert any(row.get("action_type") == "casino_win" for row in feed.get("feed") or [])
