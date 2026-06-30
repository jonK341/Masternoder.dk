"""Progression quest system — 90 levels."""
import os
import tempfile

import pytest

import backend.services.quest_system as qs


@pytest.fixture
def prog_dir(monkeypatch):
    tmp = tempfile.mkdtemp()
    monkeypatch.setattr(qs, "_LEVEL_CACHE", None)
    orig = qs._progress_dir
    monkeypatch.setattr(qs, "_progress_dir", lambda: tmp)
    yield tmp
    qs._LEVEL_CACHE = None


def test_level_catalog_has_ninety_levels():
    levels = qs.get_all_levels()
    assert len(levels) == 90
    assert levels[0]["level"] == 1
    assert levels[-1]["level"] == 90
    assert levels[0]["chapter"] == 1
    assert levels[9]["chapter"] == 1
    assert levels[10]["chapter"] == 2


def test_chapters_nine_tiers(prog_dir):
    chapters = qs.get_chapters()
    assert len(chapters) == 9
    assert chapters[0]["level_start"] == 1
    assert chapters[-1]["level_end"] == 90


def test_level_one_unlocked_and_sync(prog_dir, monkeypatch):
    monkeypatch.setattr(qs, "_metric_value", lambda uid, metric, state: 0)
    out = qs.get_user_quests("prog_user_a")
    assert out["success"] is True
    assert out["total_levels"] == 90
    level1 = next(l for l in out["levels"] if l["level"] == 1)
    assert level1["locked"] is False
    level2 = next(l for l in out["levels"] if l["level"] == 2)
    assert level2["locked"] is True


def test_claim_level_one(prog_dir, monkeypatch):
    monkeypatch.setattr(qs, "_metric_value", lambda uid, metric, state: 999)
    uid = "prog_claim_user"
    qs.get_user_quests(uid)
    result = qs.claim_level_reward(uid, 1)
    assert result["success"] is True
    assert result["rewards"]["quest_points"] > 0

    out = qs.get_user_quests(uid)
    level1 = next(l for l in out["levels"] if l["level"] == 1)
    assert level1["claimed"] is True
    level2 = next(l for l in out["levels"] if l["level"] == 2)
    assert level2["locked"] is False


def test_update_quest_progress_increments(prog_dir):
    uid = "prog_action_user"
    r = qs.update_quest_progress(uid, "casino_bet", increment=3)
    assert r["success"] is True
    state = qs._load_state(uid)
    assert state.get("casino_bets") == 3


def test_quest_statistics(prog_dir, monkeypatch):
    monkeypatch.setattr(qs, "_metric_value", lambda uid, metric, state: 0)
    stats = qs.get_quest_statistics("stats_user")
    assert stats["total_levels"] == 90
    assert stats["completed"] == 0
    assert stats["quest_level"] == "beginner"
