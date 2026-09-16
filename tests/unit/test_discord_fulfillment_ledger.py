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
    config = {
        "buyer_signal_threshold": 20,
        "buyer_signal_weights": {"discord_promo_redeem": 25, "payment_ledger": 30},
        "default_coin_pack_sku": "mn2-pack-s",
        "discord_promo_codes": ["DISCORD-STARTER"],
    }
    with open(data / "discord_fulfillment_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f)

    monetization = tmp_path / "logs" / "monetization"
    monetization.mkdir(parents=True)
    promos = data / "discord_promo_codes.json"
    with open(promos, "w", encoding="utf-8") as f:
        json.dump(
            {
                "codes": [
                    {
                        "code": "DISCORD-STARTER",
                        "redeemed_by": ["user-c"],
                        "max_redemptions": 100,
                    }
                ]
            },
            f,
        )

    import backend.services.discord_link_service as dls
    import backend.services.discord_fulfillment_ledger_service as dfl

    monkeypatch.setattr(dls, "_IDENT_DIR", str(ident))
    monkeypatch.setattr(dfl, "_IDENT_DIR", str(ident))
    monkeypatch.setattr(dfl, "_BASE", str(tmp_path))
    monkeypatch.setattr(dfl, "_MN2_CHANNEL_CONFIG", str(data / "discord_mn2_channel.json"))
    monkeypatch.setattr(dfl, "_DISCORD_PROMOS", str(promos))
    monkeypatch.setattr(dfl, "_PAYMENT_LEDGER", str(monetization / "payment_ledger.jsonl"))
    monkeypatch.setattr(dfl, "_DISCORD_CLICKS", str(tmp_path / "logs" / "discord_clicks.jsonl"))
    monkeypatch.setattr(dfl, "_ONRAMP_ORDERS", str(data / "mn2_onramp_orders.json"))
    monkeypatch.setattr(dfl, "_MN2_LEDGER", str(data / "mn2_ledger.json"))
    monkeypatch.setattr(dfl, "_data_dir", lambda: str(data))
    monkeypatch.setattr(dfl, "_config_path", lambda: str(data / "discord_fulfillment_config.json"))
    monkeypatch.setattr(dfl, "_ledger_path", lambda: str(data / "discord_fulfillment_ledger.json"))
    monkeypatch.setattr(dfl, "_order_list_path", lambda: str(data / "discord_order_list.json"))

    monkeypatch.setenv("CASINO_DISCORD_VIP_MIN_MN2", "100")

    def _balance(uid):
        return 150.0 if uid == "user-a" else 10.0

    def _discord_for_user(uid):
        return {"user-a": "111222333", "user-b": "444555666", "user-c": "777888999"}.get(uid)

    with patch("backend.services.discord_fulfillment_ledger_service._mn2_balance_for_user", side_effect=_balance):
        with patch("backend.services.discord_fulfillment_ledger_service._resolve_discord_id", side_effect=_discord_for_user):
            with patch("backend.services.discord_hosting_vip_service.check_hosting_vip_eligibility", return_value={"eligible": False}):
                yield data


def _no_api():
    return patch("backend.services.discord_fulfillment_ledger_service.fetch_discord_guild_members", return_value={"members": [], "api_used": False}), \
           patch("backend.services.discord_fulfillment_ledger_service.fetch_discord_channel_authors", return_value={"members": [], "api_used": False})


def test_build_order_list_from_linked_users(ledger_env):
    from backend.services.discord_fulfillment_ledger_service import build_order_list, get_order_list

    with _no_api()[0], _no_api()[1]:
        with patch("backend.services.discord_fulfillment_ledger_service.scan_purchase_intent_buyers", return_value=[]):
            result = build_order_list(use_local=True, use_discord_api=False, use_buyer_signals=False)

    assert result["success"] is True
    assert result["total"] == 2
    assert result["discord_api_used"] is False

    listing = get_order_list()
    alpha = next(r for r in listing["orders"] if r["discord_id"] == "111222333")
    assert alpha["user_id"] == "user-a"
    assert alpha["source"] == "local_linked"
    assert "local_linked" in alpha["sources"]


def test_build_order_list_merges_discord_api(ledger_env):
    from backend.services.discord_fulfillment_ledger_service import build_order_list

    api_members = [
        {"discord_id": "999888777", "discord_username": "gamma", "user_id": None, "source": "discord_api", "buyer_signals": [], "buyer_score": 0},
    ]
    with patch("backend.services.discord_fulfillment_ledger_service.fetch_discord_guild_members", return_value={"members": api_members, "api_used": True, "success": True}):
        with patch("backend.services.discord_fulfillment_ledger_service.fetch_discord_channel_authors", return_value={"members": [], "api_used": True, "success": True}):
            with patch("backend.services.discord_fulfillment_ledger_service.scan_purchase_intent_buyers", return_value=[]):
                result = build_order_list(use_local=True, use_discord_api=True, use_buyer_signals=False)

    assert result["total"] == 3
    assert result["discord_api_used"] is True
    assert result["sources"]["discord_api"] >= 1


def test_triple_source_merge_with_buyer_signal(ledger_env):
    from backend.services.discord_fulfillment_ledger_service import build_order_list, get_order_list

    buyer_row = {
        "discord_id": "777888999",
        "user_id": "user-c",
        "discord_username": None,
        "source": "purchase_intent",
        "buyer_signals": ["discord_promo_redeem"],
        "buyer_score": 25.0,
    }
    api_members = [
        {"discord_id": "111222333", "discord_username": "alpha_api", "user_id": None, "source": "discord_api", "buyer_signals": [], "buyer_score": 0},
    ]

    with patch("backend.services.discord_fulfillment_ledger_service.fetch_discord_guild_members", return_value={"members": api_members, "api_used": True, "success": True}):
        with patch("backend.services.discord_fulfillment_ledger_service.fetch_discord_channel_authors", return_value={"members": [], "api_used": True}):
            with patch("backend.services.discord_fulfillment_ledger_service.scan_purchase_intent_buyers", return_value=[buyer_row]):
                result = build_order_list(use_local=True, use_discord_api=True, use_buyer_signals=True)

    assert result["total"] == 3
    assert result["buyer_signal_count"] >= 1
    assert result["overlaps"]["local_and_api"] >= 1
    assert result["sources"]["purchase_intent"] >= 1

    orders = get_order_list()["orders"]
    alpha = next(r for r in orders if r["discord_id"] == "111222333")
    assert alpha["source"] in ("local_linked+discord_api", "all")
    assert "local_linked" in alpha["sources"]
    assert "discord_api" in alpha["sources"]

    buyer = next(r for r in orders if r["discord_id"] == "777888999")
    assert buyer["buyer_signal"] is True
    assert buyer["source"] == "purchase_intent"
    line_ids = [ln["id"] for ln in buyer["order_lines"]]
    assert "coin_pack_offer" in line_ids
    assert buyer["mn2_coin_offer_status"] == "pending"


def test_register_mn2_purchase_intent(ledger_env, tmp_path, monkeypatch):
    import backend.services.discord_fulfillment_ledger_service as dfl

    intent_path = tmp_path / "data" / "discord_mn2_purchase_intent.json"
    monkeypatch.setattr(dfl, "_INTENT_REGISTRY", str(intent_path))

    out = dfl.register_mn2_purchase_intent(user_id="user-a", channel="wallet", pack_id="mn2-pack-s")
    assert out["success"] is True
    assert out["discord_id"] == "111222333"

    rows = dfl.scan_purchase_intent_buyers()
    assert any(r["discord_id"] == "111222333" for r in rows)
    row = next(r for r in rows if r["discord_id"] == "111222333")
    assert "wallet_intent_register" in row.get("buyer_signals", [])


def test_scan_purchase_intent_from_payment_ledger(ledger_env, tmp_path, monkeypatch):
    import backend.services.discord_fulfillment_ledger_service as dfl

    ledger_path = tmp_path / "logs" / "monetization" / "payment_ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "user_id": "user-a",
            "item_id": "mn2-pack-m",
            "item_name": "MN2 Pack",
            "amount_usd": 9.99,
        }) + "\n")

    rows = dfl.scan_purchase_intent_buyers()
    alpha = next((r for r in rows if r["discord_id"] == "111222333"), None)
    assert alpha is not None
    assert "payment_ledger" in alpha["buyer_signals"] or "coin_pack_purchase" in alpha["buyer_signals"]


def test_fulfill_order_marks_lines(ledger_env):
    from backend.services.discord_fulfillment_ledger_service import build_order_list, fulfill_order, get_row_for_discord

    with _no_api()[0], _no_api()[1]:
        with patch("backend.services.discord_fulfillment_ledger_service.scan_purchase_intent_buyers", return_value=[]):
            build_order_list(use_local=True, use_discord_api=False, use_buyer_signals=False)

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
                    "source": "local_linked+purchase_intent",
                    "sources": ["local_linked", "purchase_intent"],
                    "buyer_signal": True,
                    "mn2_coin_offer_status": "pending",
                    "order_lines": [{"id": "coin_pack_offer", "status": "pending", "label": "MN2 coin pack offer"}],
                    "mn2_balance": 150.0,
                }
                r = client.get("/api/wallet/v2/discord/fulfillment-status")
    assert r.status_code == 200
    data = r.get_json()
    assert data["linked"] is True
    assert data["buyer_signal"] is True
    assert data["mn2_coin_offer_status"] == "pending"
