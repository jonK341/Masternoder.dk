"""Plan 001 U2 — server-priced PayPal trophy checkout, editions, idempotent capture."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

from flask import Flask


def _paypal_app():
    from backend.routes.paypal_routes import paypal_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(paypal_bp)
    return app


@patch("backend.services.trophy_pricing_service.get_effective_price")
@patch("backend.services.trophy_fulfillment_service.is_trophy_item", return_value=True)
@patch("backend.services.paypal_service.create_order")
@patch("backend.services.paypal_service.get_access_token", return_value="tok")
def test_create_order_uses_server_trophy_price(mock_token, mock_create, mock_is_trophy, mock_price):
    mock_price.return_value = {
        "success": True,
        "item_id": "top25-01",
        "name": "Genesis Node Sigil",
        "effective_price_usd": 2.10,
        "on_chain_mint": False,
    }
    mock_create.return_value = {
        "success": True,
        "order_id": "ORD-T1",
        "approve_url": "https://paypal.test/approve",
    }

    client = _paypal_app().test_client()
    r = client.post(
        "/api/paypal/create-order",
        json={
            "amount": 0.01,
            "item_id": "top25-01",
            "item_name": "Wrong client name",
            "user_id": "buyer-a",
            "return_surface": "exchange",
        },
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["amount_usd"] == 2.10
    assert data["kind"] == "trophy"
    assert mock_create.call_args[1]["amount"] == 2.10
    assert "Licensed digital collectible trophy" in mock_create.call_args[1]["item_name"]
    assert "/exchange?" in mock_create.call_args[1]["return_url"]


def test_create_order_guest_blocked():
    client = _paypal_app().test_client()
    r = client.post(
        "/api/paypal/create-order",
        json={"amount": 1.0, "item_id": "top25-01", "user_id": "default_user"},
    )
    assert r.status_code == 400
    assert r.get_json().get("code") == "ACCOUNT_REQUIRED"


@patch("backend.services.trophy_fulfillment_service.fulfill_trophy_paypal")
@patch("backend.services.trophy_fulfillment_service.is_trophy_item", return_value=True)
@patch("backend.services.paypal_service.capture_order")
@patch("backend.services.paypal_service.get_access_token", return_value="tok")
def test_capture_trophy_edition(mock_token, mock_capture, mock_is_trophy, mock_fulfill):
    mock_capture.return_value = {
        "success": True,
        "order_id": "ORD-C1",
        "capture_id": "CAP-C1",
        "amount": "2.10",
        "currency": "USD",
    }
    mock_fulfill.return_value = {
        "success": True,
        "duplicate": False,
        "item_granted": "top25-01",
        "edition_no": 1,
        "edition_key": "TRO-top25-01-1",
        "edition": {
            "edition_no": 1,
            "edition_key": "TRO-top25-01-1",
            "hold_until": "2026-10-01T00:00:00Z",
            "proof_hash": "abc123",
        },
    }

    client = _paypal_app().test_client()
    with patch("backend.services.purchase_notification_service.notify_purchase"):
        r = client.post(
            "/api/paypal/capture",
            json={"order_id": "ORD-C1", "item_id": "top25-01", "user_id": "buyer-a"},
        )
    assert r.status_code == 200
    data = r.get_json()
    assert data["item_granted"] == "top25-01"
    assert data["edition_no"] == 1
    assert data["edition_key"] == "TRO-top25-01-1"
    assert data["on_chain_mint"] is False
    mock_fulfill.assert_called_once()


def test_fulfill_trophy_idempotent(tmp_path, monkeypatch):
    import backend.services.trophy_fulfillment_service as tfs

    monkeypatch.setattr(tfs, "_CAPTURES_PATH", str(tmp_path / "captures.json"))
    monkeypatch.setattr(tfs, "_EDITION_COUNTERS_PATH", str(tmp_path / "counters.json"))

    inv_root = tmp_path / "shop_file_mode"
    (inv_root / "inventory").mkdir(parents=True)
    (inv_root / "trophy_editions").mkdir(parents=True)
    monkeypatch.setattr("backend.services.shop_db_service._shop_file_root", lambda: str(inv_root))
    monkeypatch.setattr("backend.services.shop_db_service.shop_tables_exist", lambda: False)

    with patch("backend.services.trophy_pricing_service.get_effective_price") as mock_price:
        mock_price.return_value = {
            "success": True,
            "name": "Genesis",
            "effective_price_usd": 2.10,
        }
        with patch("backend.services.shop_db_service.fulfill_shop_purchase", return_value=1):
            with patch("backend.routes.shop_routes._apply_shop_item_effects"):
                with patch("backend.routes.shop_routes._get_shop_items", return_value=[{"id": "top25-01", "name": "Genesis"}]):
                    with patch("backend.services.mn2_ledger.append_entry"):
                        r1 = tfs.fulfill_trophy_paypal(
                            user_id="buyer-a",
                            item_id="top25-01",
                            item_name="Genesis",
                            order_id="ORD-1",
                            capture_id="CAP-DUP",
                            amount_usd=2.10,
                        )
                        r2 = tfs.fulfill_trophy_paypal(
                            user_id="buyer-a",
                            item_id="top25-01",
                            item_name="Genesis",
                            order_id="ORD-1",
                            capture_id="CAP-DUP",
                            amount_usd=2.10,
                        )

    assert r1["success"] is True
    assert r1["edition_no"] == 1
    assert r1["edition_key"] == "TRO-top25-01-1"
    assert r2["success"] is True
    assert r2.get("duplicate") is True
    assert r2["edition_no"] == 1

    editions = tfs.get_trophy_editions("buyer-a", "top25-01")
    assert len(editions) == 1
    assert editions[0]["proof_hash"]
    assert editions[0]["hold_until"]


def test_pricing_unknown_item():
    from backend.services.trophy_pricing_service import get_effective_price

    with patch("backend.services.trophy_pricing_service._catalog_item", return_value=None):
        out = get_effective_price("missing-trophy")
    assert out["success"] is False
