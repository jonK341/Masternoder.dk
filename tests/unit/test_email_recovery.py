"""Email verification and recovery email flows."""
from __future__ import annotations

import json
import os
import tempfile

import pytest


@pytest.fixture
def email_env(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        email_path = os.path.join(tmp, "user_email_recovery.json")
        profiles_dir = os.path.join(tmp, "profiles")
        os.makedirs(profiles_dir, exist_ok=True)
        import backend.services.email_recovery_service as email_svc

        monkeypatch.setattr(email_svc, "_EMAIL_PATH", email_path)
        monkeypatch.setattr(email_svc, "_BASE_DIR", tmp)
        monkeypatch.setattr(email_svc, "_send_verification_email", lambda *args: False)

        def fake_set_profile(user_id, email, verified=True):
            path = os.path.join(profiles_dir, f"{user_id}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"user_id": user_id, "preferences": {"email": email, "email_verified": verified}}, f)
            return {"success": True}

        monkeypatch.setattr(email_svc, "_set_profile_email", fake_set_profile)
        monkeypatch.setattr(email_svc, "_profile_primary_email", lambda uid: None)
        monkeypatch.setattr(email_svc, "_profile_preferences", lambda uid: {})
        yield email_svc


def test_verify_email_flow(email_env):
    req = email_env.request_email_verification("bob", "bob@example.com")
    assert req["success"] is True
    token = req["verification_token"]
    ok = email_env.confirm_email_verification("bob", token)
    assert ok["success"] is True
    status = email_env.get_email_status("bob")
    assert status["email_verified"] is True


def test_recovery_email_flow(email_env):
    req = email_env.request_recovery_email("carol", "backup@example.com")
    assert req["success"] is True
    token = req["recovery_token"]
    ok = email_env.confirm_recovery_email("carol", token)
    assert ok["success"] is True
    status = email_env.get_email_status("carol")
    assert status["recovery_email_verified"] is True
