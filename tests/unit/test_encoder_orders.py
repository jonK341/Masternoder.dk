"""Encoder ledger orders + Discord customer ingest."""
from __future__ import annotations

import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


@pytest.fixture
def encoder_order_env(tmp_path, monkeypatch):
    orders = tmp_path / "encoder_orders.json"
    orders.write_text(json.dumps({"version": 1, "orders": []}), encoding="utf-8")
    discord_idx = tmp_path / "discord_customer_index.json"
    discord_idx.write_text(
        json.dumps({"version": 1, "customers": {}, "last_sync_at": None, "channel_id": None}),
        encoding="utf-8",
    )
    points = tmp_path / "points"
    points.mkdir()
    ident = tmp_path / "identifiers"
    ident.mkdir()
    monkeypatch.setattr("backend.services.encoder_order_service._ORDERS_FILE", str(orders))
    monkeypatch.setattr("backend.services.discord_customer_ingest_service._INDEX_FILE", str(discord_idx))
    monkeypatch.setattr("backend.services.discord_customer_ingest_service._POINTS_DIR", str(points))
    monkeypatch.setattr("backend.services.discord_customer_ingest_service._IDENT_DIR", str(ident))
    return tmp_path


def test_quote_encoder_v2_upgrade(encoder_order_env):
    from backend.services.encoder_order_service import quote_order

    q = quote_order("encoder_v2_unlock", {"upgrade_id": "v2_vid_001"})
    assert q["success"] is True
    assert q["upgrade_id"] == "v2_vid_001"
    assert q["price_mn2"] == 0.0


def test_create_free_encoder_order(encoder_order_env):
    from backend.services.encoder_order_service import create_balance_order, get_order

    res = create_balance_order(
        "_test_enc_order",
        "encoder_v2_unlock",
        {"upgrade_id": "v2_vid_001"},
        auto_fulfill=True,
    )
    assert res["success"] is True
    order = res.get("order") or {}
    assert order.get("status") == "fulfilled"
    assert get_order(order["order_id"]) is not None


def test_discord_customer_upsert(encoder_order_env):
    from backend.services.discord_customer_ingest_service import (
        _upsert_discord_customer,
        list_discord_customers,
    )

    row = _upsert_discord_customer(
        "123456789012345678",
        username="test_user",
        display_name="Test User",
        channel_id="999",
    )
    assert row["success"] is True
    listing = list_discord_customers()
    assert listing["total"] == 1
    assert listing["customers"][0]["username"] == "test_user"


def test_encoder_orders_routes(encoder_order_env):
    from flask import Flask
    from backend.routes.create_app_routes import create_app_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(create_app_bp)
    client = app.test_client()

    r = client.post(
        "/api/create-app/encoder-orders/quote",
        json={"kind": "encoder_v2_unlock", "upgrade_id": "v2_vid_001"},
    )
    assert r.status_code == 200
    assert r.get_json()["success"] is True

    r2 = client.get("/api/create-app/encoder-orders?user_id=_test_route_user")
    assert r2.status_code == 200
    assert r2.get_json()["success"] is True


def test_normalize_discord_channel_url():
    from backend.services.discord_customer_ingest_service import normalize_discord_channel_ref

    guild, channel = normalize_discord_channel_ref(
        "https://discord.com/channels/1111111111111111111/2222222222222222222"
    )
    assert guild == "1111111111111111111"
    assert channel == "2222222222222222222"
    _, only = normalize_discord_channel_ref("2222222222222222222")
    assert only == "2222222222222222222"


def test_discord_sync_without_channel_returns_error(encoder_order_env, monkeypatch):
    monkeypatch.delenv("DISCORD_CUSTOMER_CHANNEL_ID", raising=False)
    monkeypatch.setattr(
        "backend.services.discord_customer_ingest_service._config",
        lambda: {"enabled": True, "channel_id": "", "guild_id": "", "channel_url": ""},
    )
    from backend.services.discord_customer_ingest_service import sync_customers_from_channel

    res = sync_customers_from_channel(channel_id="")
    assert res["success"] is False
    assert res["error"] == "customer_channel_not_configured"
