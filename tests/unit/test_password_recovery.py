"""Password recovery — token flow, rate limit, forgot-by-email."""
from __future__ import annotations

import json
import os
import tempfile

import pytest


@pytest.fixture
def pwd_env(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        protection_path = os.path.join(tmp, "user_password_protection.json")
        rate_path = os.path.join(tmp, "password_recovery_rate_limit.json")
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
        monkeypatch.setattr(pwd, "_RECOVERY_RATE_PATH", rate_path)
        monkeypatch.setattr(pwd, "_user_game_points", lambda uid: 0.0)
        monkeypatch.setattr(pwd, "_user_investigations_count", lambda uid: 0)
        monkeypatch.setattr(pwd, "_profile_email", lambda uid: "alice@example.com")
        monkeypatch.setattr(pwd, "_linked_provider", lambda uid: None)
        monkeypatch.setattr(pwd, "_real_money_account", lambda uid: False)
        monkeypatch.setattr(pwd, "_send_recovery_email", lambda *args: False)
        monkeypatch.setattr(
            "backend.services.email_recovery_service.get_email_status",
            lambda uid: {"email_verified": True, "recovery_email_verified": False},
        )
        yield pwd


def test_recovery_token_reset_flow(pwd_env):
    req = pwd_env.request_password_recovery("alice")
    assert req["success"] is True
    token = req["reset_token"]
    assert token
    reset = pwd_env.reset_password_with_recovery("alice", token, "newpass1")
    assert reset["success"] is True
    assert pwd_env.verify_password("alice", "newpass1")["success"] is True
    again = pwd_env.reset_password_with_recovery("alice", token, "otherpass")
    assert again["success"] is False


def test_recovery_by_email_generic_response(pwd_env, monkeypatch):
    monkeypatch.setattr(
        "backend.services.email_recovery_service.lookup_user_id_by_email",
        lambda email: "alice" if email == "alice@example.com" else None,
    )
    found = pwd_env.request_password_recovery_by_email("alice@example.com")
    assert found["success"] is True
    missing = pwd_env.request_password_recovery_by_email("missing@example.com")
    assert missing["success"] is True
    assert "If an account exists" in missing["message"]
