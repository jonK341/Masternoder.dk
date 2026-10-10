"""Account security — bind session, presets, purchase gate."""
from __future__ import annotations

import json
import os
import tempfile

import pytest


@pytest.fixture
def security_settings_path(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "account_security_settings.json")
        import backend.services.account_security_service as svc

        monkeypatch.setattr(svc, "_SETTINGS_PATH", path)
        yield path


def test_update_settings_persists_bind_session_and_preset(security_settings_path):
    from backend.services.account_security_service import (
        get_security_settings,
        update_security_settings,
    )

    update_security_settings(
        "user_a",
        {
            "require_password_bind_session": True,
            "require_password_purchases": True,
            "security_preset": "maximum",
        },
    )
    s = get_security_settings("user_a")
    assert s["require_password_bind_session"] is True
    assert s["require_password_purchases"] is True
    assert s["security_preset"] == "maximum"


def test_check_bind_session_requires_password_when_enabled(monkeypatch, security_settings_path):
    from backend.services import account_security_service as svc

    svc.update_security_settings("user_b", {"require_password_bind_session": True})
    monkeypatch.setattr(svc, "has_password", lambda _uid: True)
    monkeypatch.setattr(
        "backend.services.password_protection_service.verify_password",
        lambda _uid, _pw: {"success": True},
    )

    assert svc.check_bind_session_action("user_b", password=None) is not None
    assert "Password required" in svc.check_bind_session_action("user_b", password=None)
    assert svc.check_bind_session_action("user_b", password="secret") is None


def test_check_purchase_action_respects_token(monkeypatch, security_settings_path):
    from backend.services import account_security_service as svc

    svc.update_security_settings("user_c", {"require_password_purchases": True})
    monkeypatch.setattr(
        "backend.services.password_protection_service.get_password_status",
        lambda _uid: {"has_password": True},
    )
    monkeypatch.setattr(
        "backend.services.password_protection_service.verify_password",
        lambda _uid, _pw: {"success": True},
    )
    assert svc.check_purchase_action("user_c", verification_token=None, price_usd=9.99) is not None

    token = svc.issue_verification_token("user_c", "pw123")
    assert token.get("success")
    assert (
        svc.check_purchase_action(
            "user_c",
            verification_token=token["verification_token"],
            price_usd=9.99,
        )
        is None
    )
