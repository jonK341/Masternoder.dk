"""Account password protection — unlock progress, fast track, set/change."""
from __future__ import annotations

import json
import os
import tempfile

import pytest


@pytest.fixture
def pwd_env(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        protection_path = os.path.join(tmp, "user_password_protection.json")
        investigations_path = os.path.join(tmp, "star_map_25_investigations.json")
        with open(protection_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "users": {},
                    "unlock_rule": {"min_game_points": 50, "min_investigations": 1},
                    "reward_on_set": {"game_points": 10},
                },
                f,
            )
        import backend.services.password_protection_service as pwd

        monkeypatch.setattr(pwd, "PROTECTION_PATH", protection_path)
        monkeypatch.setattr(pwd, "INVESTIGATIONS_PATH", investigations_path)
        monkeypatch.setattr(pwd, "_user_game_points", lambda uid: 0.0)
        monkeypatch.setattr(pwd, "_user_investigations_count", lambda uid: 0)
        monkeypatch.setattr(pwd, "_profile_email", lambda uid: None)
        monkeypatch.setattr(pwd, "_linked_provider", lambda uid: None)
        monkeypatch.setattr(pwd, "_real_money_account", lambda uid: False)
        yield pwd


def test_status_locked_without_progress(pwd_env):
    status = pwd_env.get_password_status("alice")
    assert status["has_password"] is False
    assert status["can_set_password"] is False
    assert status["unlock_progress"]["overall_percent"] == 0


def test_fast_track_allows_set_without_points(pwd_env, monkeypatch):
    monkeypatch.setattr(pwd_env, "_profile_email", lambda uid: "alice@example.com")
    status = pwd_env.get_password_status("alice")
    assert status["fast_track"] is True
    assert status["can_set_password"] is True
    result = pwd_env.set_password("alice", "secret12")
    assert result["success"] is True
    assert pwd_env.verify_password("alice", "secret12")["success"] is True


def test_change_password_requires_current(pwd_env, monkeypatch):
    monkeypatch.setattr(pwd_env, "_profile_email", lambda uid: "alice@example.com")
    pwd_env.set_password("alice", "firstpass1")
    denied = pwd_env.set_password("alice", "newpass12")
    assert denied["success"] is False
    assert "Current password" in denied["error"]
    ok = pwd_env.set_password("alice", "newpass12", current_password="firstpass1")
    assert ok["success"] is True
    assert pwd_env.verify_password("alice", "newpass12")["success"] is True


def test_unlock_progress_when_points_met(pwd_env, monkeypatch):
    monkeypatch.setattr(pwd_env, "_user_game_points", lambda uid: 60.0)
    progress = pwd_env.get_unlock_progress("bob")
    assert progress["rule_met"] is True
    assert progress["overall_percent"] == 100
    status = pwd_env.get_password_status("bob")
    assert status["can_set_password"] is True
