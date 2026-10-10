"""C6 hosting VIP + B2 on-ramp/hosting bundle."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from backend.services.tier_b_monetization_service import (
    get_auto_hosting_promo,
    get_onramp_hosting_offer,
    user_has_paid_hosting,
    user_has_recent_onramp,
)


@pytest.fixture
def hosting_orders_path(tmp_path, monkeypatch):
    orders_file = tmp_path / "mn2_masternode_orders.json"
    orders_file.write_text(
        json.dumps({
            "mnq_paid1": {
                "order_id": "mnq_paid1",
                "user_id": "host_user",
                "status": "paid",
                "slots": 1,
                "usd_total": 4.99,
                "paid_at": datetime.now(timezone.utc).isoformat(),
            }
        }),
        encoding="utf-8",
    )
    import backend.services.mn2_masternode_hosting_service as hosting

    monkeypatch.setattr(hosting, "_ORDERS_FILE", "mn2_masternode_orders.json")

    def _data_path(name):
        return str(orders_file if name == "mn2_masternode_orders.json" else tmp_path / name)

    monkeypatch.setattr(hosting, "_data_path", _data_path)
    return orders_file


def test_user_has_paid_hosting(hosting_orders_path):
    assert user_has_paid_hosting("host_user") is True
    assert user_has_paid_hosting("other") is False


def test_onramp_offer_marks_hosting_done(hosting_orders_path, monkeypatch):
    monkeypatch.setattr(
        "backend.services.tier_b_monetization_service.user_has_recent_onramp",
        lambda uid, window_days=7: True,
    )
    offer = get_onramp_hosting_offer("host_user")
    assert offer["hosting_step_done"] is True
    assert offer["steps"][1]["done"] is True


def test_auto_hosting_promo_when_onramp_recent(monkeypatch):
    monkeypatch.setattr(
        "backend.services.tier_b_monetization_service.user_has_recent_onramp",
        lambda uid, window_days=7: True,
    )
    monkeypatch.setattr(
        "backend.services.tier_b_monetization_service.user_has_paid_hosting",
        lambda uid: False,
    )
    assert get_auto_hosting_promo("buyer_a") == "HOSTMN5"


def test_hosting_vip_eligibility(hosting_orders_path, monkeypatch):
    from backend.services import discord_hosting_vip_service as vip

    monkeypatch.setattr(
        "backend.services.discord_link_service.get_discord_id_for_user",
        lambda uid: "123456789" if uid == "host_user" else None,
    )
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-token")
    monkeypatch.setenv("DISCORD_GUILD_ID", "guild1")
    monkeypatch.setenv("DISCORD_HOSTING_VIP_ROLE_ID", "role1")

    st = vip.check_hosting_vip_eligibility("host_user")
    assert st["hosting_customer"] is True
    assert st["discord_linked"] is True
    assert st["eligible"] is True

    with patch.object(vip, "_discord_put_member_role", return_value={"success": True, "status": 204}):
        out = vip.grant_hosting_vip_role("host_user")
    assert out.get("granted") is True


def test_create_order_applies_auto_promo(hosting_orders_path, monkeypatch):
    import backend.services.mn2_masternode_hosting_service as hosting

    quote_id = "mnq_quote1"
    hosting_orders_path.write_text(
        json.dumps({
            quote_id: {
                "order_id": quote_id,
                "user_id": "buyer_a",
                "status": "quoted",
                "slots": 1,
                "usd_total": 4.99,
                "currency": "USD",
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            }
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "backend.services.tier_b_monetization_service.get_auto_hosting_promo",
        lambda uid: "HOSTMN5",
    )
    monkeypatch.setattr(
        hosting,
        "get_paypal_config",
        lambda: {
            "enabled": True,
            "return_path": "/shop?tab=mn2",
            "billing_label": "MN2 Hosting",
        },
    )

    def fake_pp_create(**kwargs):
        assert kwargs["amount"] < 4.99
        return {"success": True, "order_id": "PP123", "approve_url": "https://paypal.test/approve"}

    monkeypatch.setattr("backend.services.paypal_service.create_order", fake_pp_create)
    monkeypatch.setattr(
        "backend.services.shop_checkout_promo_service.apply_discounted_amount",
        lambda amt, code, uid: (round(amt * 0.95, 2), {"promo_applied": True, "code": code}),
    )

    out = hosting.create_order(quote_id, "buyer_a")
    assert out["success"] is True
    assert out.get("promo_applied") is True
