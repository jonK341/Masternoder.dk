"""Social auth and account security expansion tests."""
from __future__ import annotations

import json
import os
import shutil
import tempfile

import pytest

from backend.services import social_auth_service as sas
from backend.services.account_security_service import (
    SECURITY_PRESETS,
    apply_security_preset,
    bind_session_requires_password,
    get_security_settings,
    update_security_settings,
)


@pytest.fixture
def oauth_state_file(monkeypatch):
    tmp_dir = tempfile.mkdtemp(prefix="oauth_state_")
    path = os.path.join(tmp_dir, "oauth_state.json")
    monkeypatch.setattr(sas, "_STATE_PATH", path)
    try:
        yield path
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_oauth_state_persists_to_file(oauth_state_file):
    sas._store_state("state123", {"provider": "google", "nonce": "n"})
    assert os.path.isfile(oauth_state_file)
    payload = sas._consume_state("state123")
    assert payload is not None
    assert payload.get("provider") == "google"
    assert sas._consume_state("state123") is None


def test_allowed_providers_include_facebook_discord():
    assert "facebook" in sas.ALLOWED_OAUTH_PROVIDERS
    assert "discord" in sas.ALLOWED_OAUTH_PROVIDERS
    ids = {p["id"] for p in sas.list_providers()["providers"]}
    assert "facebook" in ids
    assert "discord" in ids


def test_security_preset_maximum(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="sec_settings_")
    path = os.path.join(tmp, "settings.json")
    monkeypatch.setattr("backend.services.account_security_service._SETTINGS_PATH", path)
    try:
        out = update_security_settings("u_sec", {"security_preset": "maximum"})
        assert out["success"] is True
        s = get_security_settings("u_sec")
        assert s["security_preset"] == "maximum"
        assert s["require_password_login"] is True
        assert s["require_password_bind_session"] is True
        assert s["require_password_purchases"] is True
        assert apply_security_preset("secure")["require_password_bind_session"] is True
        assert bind_session_requires_password("u_sec") is True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_placeholder_credentials_not_configured(monkeypatch):
    monkeypatch.setenv("FACEBOOK_CLIENT_ID", "...")
    monkeypatch.setenv("FACEBOOK_CLIENT_SECRET", "...")
    fb = next(p for p in sas.list_providers()["providers"] if p["id"] == "facebook")
    assert fb["configured"] is False
    assert fb["enabled"] is False
    out = sas.build_start_url("facebook")
    assert out.get("success") is False


def test_append_linked_provider():
    prefs = {}
    out = sas._append_linked_provider(prefs, "google")
    assert out["linked_providers"] == ["google"]
    out = sas._append_linked_provider(out, "google")
    assert out["linked_providers"] == ["google"]
