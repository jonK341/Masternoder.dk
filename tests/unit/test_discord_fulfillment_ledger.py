"""Unit tests for Discord fulfillment ledger service and routes."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch

import pytest
from flask import Flask


@pytest.fixture
def ledger_env(tmp_path, monkeypatch):
    ident = tmp_path / "user_identifiers"
    ident.mkdir()
    with open(ident / "discord_111222333.json", "w", encoding="utf-8") as f:
        json.dump(
            {"user_id": "user-a", "discord_id": "111222333", "linked": True, "discord_username": "alpha"},
            f,
        )
    with open(ident / "discord_444555666.json", "w", encoding="utf-8") as f:
        json.dump(
            {"user_id": "user-b", "discord_id": "444555666", "linked": True},
            f,
        )

    data = tmp_path / "data"
    data.mkdir()

    import backend.services.discord_link_service as dls
    import backend.services.discord_fulfillment_ledger_service as dfl

    monkeypatch.setattr(dls, "_IDENT_DIR", str(ident))
    monkeypatch.setattr(dfl, "_IDENT_DIR", str(ident))
    monkeypatch.setattr(dfl, "_BASE", str(tmp_path))
    monkeypatch.setattr(dfl, "_MN2_CHANNEL_CONFIG", str(data / "discord_mn2_channel.json"))
    monkeypatch.setattr(dfl, "_data_dir", lambda: str(data))
    monkeypatch.setattr(dfl, "_ledger_path", lambda: str(data / "discord_fulfillment_ledger.json"))
    monkeypatch.setattr(dfl, "_order_list_path", lambda: str(data / "discord_order_list.json"))

    monkeypatch.setenv("CASINO_DISCORD_VIP_MIN_MN2", "100")

    def _balance(uid):
        return 150.0 if uid == "user-a" else 10.0

    with patch("backend.services.discord_fulfillment_ledger_service._mn2_balance_for_user", side_effect=_balance):
        with patch("backend.services.discord_hosting_vip_service.check_hosting_vip_eligibility", return_value={"eligible": False}):
            yield data


def test_build_order_list_from_linked_users(ledger_env):
    from backend.services.discord_fulfillment_ledger_service import build_order_list, get_order_list

    with patch("backend.services.discord_fulfillment_ledger_service.fetch_discord_guild_members", return_value={"members": [], "api_used": False}):
        with patch("backend.services.discord_fulfillment_ledger_service.fetch_discord_channel_authors", return_value={"members": [], "api_used": False}):
            result = build_order_list(use_discord_api=False)

    assert result["success"] is True
    assert result["total"] == 2
    assert result["discord_api_used"] is False

    listing = get_order_list()
    assert listing["total"] == 2
    alpha = next(r for r in listing["orders"] if r["discord_id"] == "111222333")
    assert alpha["user_id"] == "user-a"
    assert alpha["mn2_balance"] == 150.0
    assert alpha["discord_username"] == "alpha"
    line_ids = [ln["id"] for ln in alpha["order_lines"]]
    assert "account_link" in line_ids
    assert "trophy_grant" in line_ids
    account_link = next(ln for ln in alpha["order_lines"] if ln["id"] == "account_link")
    assert account_link["status"] == "fulfilled"


def test_build_order_list_merges_discord_api(ledger_env):
    from backend.services.discord_fulfillment_ledger_service import build_order_list

    api_members = [
        {"discord_id": "999888777", "discord_username": "gamma", "user_id": None, "source": "discord_api_guild"},
    ]
    with patch("backend.services.discord_fulfillment_ledger_service.fetch_discord_guild_members", return_value={"members": api_members, "api_used": True, "success": True}):
        with patch("backend.services.discord_fulfillment_ledger_service.fetch_discord_channel_authors", return_value={"members": [], "api_used": True, "success": True}):
            result = build_order_list(use_discord_api=True)

    assert result["total"] == 3
    assert result["discord_api_used"] is True
    assert result["sources"]["discord_api_guild"] == 1


def test_fulfill_order_marks_lines(ledger_env):
    from backend.services.discord_fulfillment_ledger_service import build_order_list, fulfill_order, get_row_for_discord

    with patch("backend.services.discord_fulfillment_ledger_service.fetch_discord_guild_members", return_value={"members": [], "api_used": False}):
        with patch("backend.services.discord_fulfillment_ledger_service.fetch_discord_channel_authors", return_value={"members": [], "api_used": False}):
            build_order_list(use_discord_api=False)

    with patch("backend.services.unified_points_database.unified_points_db.add_points", return_value={"success": True}):
        out = fulfill_order("444555666", ["mn2_credit"], operator="test")
    assert out["success"] is True
    assert "mn2_credit" in out["applied"]
    row = get_row_for_discord("444555666")
    credit_line = next(ln for ln in row["order_lines"] if ln["id"] == "mn2_credit")
    assert credit_line["status"] == "fulfilled"


def test_fulfillment_order_list_route_requires_ops(ledger_env):
    from backend.routes.discord_routes import discord_bp

    app = Flask(__name__)
    app.register_blueprint(discord_bp)
    client = app.test_client()

    r = client.get("/api/discord/fulfillment/order-list")
    assert r.status_code == 403

    with patch("backend.services.discord_fulfillment_ledger_service.get_order_list", return_value={"success": True, "total": 2, "orders": []}):
        r2 = client.get("/api/discord/fulfillment/order-list", headers={"X-Ops-Secret": os.environ.get("DISCORD_OPS_SECRET", "test")})
    if os.environ.get("DISCORD_OPS_SECRET"):
        assert r2.status_code == 200
    else:
        assert r2.status_code == 403


def test_wallet_fulfillment_status_route(ledger_env):
    from backend.routes.wallet_v2_routes import wallet_v2_bp

    app = Flask(__name__)
    app.register_blueprint(wallet_v2_bp)
    client = app.test_client()

    with patch("backend.routes.wallet_v2_routes.resolve_user_id", return_value="user-a"):
        with patch("backend.services.discord_link_service.get_discord_id_for_user", return_value="111222333"):
            with patch("backend.services.discord_fulfillment_ledger_service.get_row_for_discord") as mock_row:
                mock_row.return_value = {
                    "discord_id": "111222333",
                    "fulfillment_status": "pending",
                    "order_lines": [{"id": "trophy_grant", "status": "pending"}],
                    "mn2_balance": 150.0,
                }
                r = client.get("/api/wallet/v2/discord/fulfillment-status")
    assert r.status_code == 200
    data = r.get_json()
    assert data["linked"] is True
    assert data["in_order_list"] is True
    assert data["fulfillment_status"] == "pending"
