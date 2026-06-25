"""Discord Linked Roles — verification URL, metadata, OAuth helpers."""
from __future__ import annotations

import json
import os
import tempfile

import pytest


def test_linked_role_verification_url_default(monkeypatch):
    monkeypatch.delenv("DISCORD_LINKED_ROLE_VERIFICATION_URL", raising=False)
    monkeypatch.setenv("SOCIAL_AUTH_BASE_URL", "https://masternoder.dk")

    from backend.services import discord_linked_roles_service as dlr

    assert dlr.linked_role_verification_url() == "https://masternoder.dk/api/discord/linked-role"
    assert dlr.linked_role_redirect_uri() == "https://masternoder.dk/api/discord/linked-role/callback"


def test_build_metadata_for_user_linked(monkeypatch):
    from backend.services import discord_link_service as dls
    from backend.services import discord_linked_roles_service as dlr

    with tempfile.TemporaryDirectory() as tmp:
        ident = os.path.join(tmp, "user_identifiers")
        os.makedirs(ident)
        with open(os.path.join(ident, "discord_123456789.json"), "w", encoding="utf-8") as f:
            json.dump({"user_id": "vip-user", "discord_id": "123456789", "linked": True}, f)

        old = dls._IDENT_DIR
        dls._IDENT_DIR = ident
        monkeypatch.setenv("CASINO_DISCORD_VIP_MIN_MN2", "100")
        try:
            meta = dlr.build_metadata_for_user("vip-user")
            assert meta["account_linked"] == 1
            assert "mn2_balance" in meta
            assert meta["casino_vip"] in (0, 1)
            assert meta["hosting_vip"] in (0, 1)
        finally:
            dls._IDENT_DIR = old


def test_build_oauth_start_requires_credentials(monkeypatch):
    monkeypatch.delenv("DISCORD_CLIENT_ID", raising=False)
    monkeypatch.delenv("DISCORD_CLIENT_SECRET", raising=False)

    from backend.services import discord_linked_roles_service as dlr

    assert dlr.build_oauth_start().get("success") is False


def test_build_oauth_start_returns_auth_url(monkeypatch):
    monkeypatch.setenv("DISCORD_CLIENT_ID", "app-client-id-12345678")
    monkeypatch.setenv("DISCORD_CLIENT_SECRET", "secret-value-12345678")
    monkeypatch.setenv("SOCIAL_AUTH_BASE_URL", "https://masternoder.dk")

    from backend.services import discord_linked_roles_service as dlr

    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, "oauth_state.json")
        old = dlr._STATE_PATH
        dlr._STATE_PATH = state_path
        try:
            result = dlr.build_oauth_start(user_id_hint="profile-user")
            assert result["success"] is True
            assert "role_connections.write" in result["auth_url"]
            assert result["redirect_uri"].endswith("/api/discord/linked-role/callback")
        finally:
            dlr._STATE_PATH = old


def test_linked_role_routes(app_client_factory=None):
    from flask import Flask
    from backend.routes.discord_routes import discord_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(discord_bp)
    with app.test_client() as c:
        r = c.get("/api/discord/linked-role/schema")
        assert r.status_code == 200
        body = r.get_json()
        assert body["success"] is True
        assert body["verification_url"].endswith("/api/discord/linked-role")
