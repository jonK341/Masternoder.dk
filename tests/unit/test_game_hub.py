"""Game Hub — story progress, claim streak, overview shape."""
import json
import os
import tempfile
from datetime import date, timedelta
from unittest.mock import patch

import pytest

import backend.services.trophy_quest_service as tqs
from backend.services.game_hub_service import get_overview, get_story_progress, mark_story_read


@pytest.fixture
def quest_state_dir():
    tmp = tempfile.mkdtemp()
    tqs._QUEST_DIR = tmp
    os.makedirs(tmp, exist_ok=True)
    yield tmp


def test_mark_story_read_and_progress(quest_state_dir):
    uid = "hub_test_user"
    with patch.object(tqs, "_stories_catalog_ids", return_value={"winter_wedding_1017", "story_b"}):
        r = mark_story_read(uid, "winter_wedding_1017")
        assert r["success"] is True
        assert r["read_count"] == 1
        assert "winter_wedding_1017" in r["read_ids"]
        p = get_story_progress(uid)
        assert p["read_count"] == 1
        assert p["continue"]["id"] == "story_b"
        r2 = mark_story_read(uid, "winter_wedding_1017")
        assert r2["success"] is True
        assert r2["read_count"] == 1


def test_claim_streak_increments(quest_state_dir, monkeypatch):
    uid = "streak_user"
    state = {}
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    state["claim_streak_last"] = yesterday
    state["claim_streak_days"] = 6
    tqs._save_state(uid, state)

    bonus = tqs._record_claim_streak(uid, state)
    assert state["claim_streak_days"] == 7
    assert state["claim_streak_last"] == today
    # MN2 credit may fail without full stack; streak still updates
    tqs._save_state(uid, state)
    loaded = tqs._load_state(uid)
    assert loaded["claim_streak_days"] == 7


def test_get_overview_shape(quest_state_dir, monkeypatch):
    monkeypatch.setattr(
        "backend.services.trophy_quest_service.get_unified_quests",
        lambda uid: {
            "quests": [],
            "trophy_quests": [],
            "platform_quests": [],
            "ai_quests": [],
            "casino_quests": [],
            "claim_streak": {"days": 0, "bonus_at_day": 7, "bonus_mn2": 0.007},
        },
    )
    monkeypatch.setattr(
        "backend.services.trophy_level_service.get_level_status",
        lambda uid: {"level": 1, "level_name": "Rookie", "pending_income": 0, "pending_income_mn2": 0},
    )
    monkeypatch.setattr("backend.services.trophies_db_service.get_user_trophies", lambda uid: [])
    monkeypatch.setattr(
        "backend.services.trophy_social_service.get_leaderboard",
        lambda limit=5, current_user=None: {"entries": [], "current_user_rank": None},
    )
    monkeypatch.setattr(
        "backend.routes.hunters_game.get_user_level_info",
        lambda uid: {"current_level": 1, "title": "Novice Hunter", "total_xp": 0},
    )
    monkeypatch.setattr(tqs, "_stories_catalog_ids", lambda: set())

    out = get_overview("overview_user")
    assert out["success"] is True
    assert "tabs" in out
    assert "summary" in out
    assert "claimable" in out["summary"]
    for key in ("trophies", "quests", "game", "battle", "story"):
        assert key in out["tabs"]
