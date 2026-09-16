"""Unit tests for ledger coin sales service."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest


@pytest.fixture
def sales_env(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    sales = data / "ledger_coin_sales.json"
    assigns = data / "ledger_sales_assignments.json"
    ledger = data / "discord_fulfillment_ledger.json"
    ledger.write_text(
        json.dumps(
            {
                "version": 3,
                "rows": [
                    {
                        "ledger_row_id": "discord:lead1",
                        "discord_id": "lead1",
                        "user_id": "user-lead-1",
                        "display_name": "Lead One",
                        "priority_score": 50,
                        "buyer_score": 25,
                        "sources": ["purchase_intent"],
                        "fulfillment_status": "pending",
                        "ledger_rank": 1,
                        "order_lines": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (data / "camgirls_catalog.json").write_text(
        json.dumps({"performers": [{"id": "cg_wallet_nova", "name": "Nova"}]}),
        encoding="utf-8",
    )

    import backend.services.ledger_coin_sales_service as lcs
    import backend.services.discord_fulfillment_ledger_service as dfl

    monkeypatch.setattr(lcs, "_BASE", str(tmp_path))
    monkeypatch.setattr(lcs, "_SALES_FILE", str(sales))
    monkeypatch.setattr(lcs, "_ASSIGNMENT_FILE", str(assigns))
    monkeypatch.setattr(dfl, "_BASE", str(tmp_path))
    monkeypatch.setattr(dfl, "_data_dir", lambda: str(data))
    monkeypatch.setattr(dfl, "_ledger_path", lambda: str(ledger))
    yield data


def test_create_offer(sales_env):
    from backend.services.ledger_coin_sales_service import create_offer, list_offers

    out = create_offer(ledger_row_id="discord:lead1", mn2_amount=100, price_usd=9.99, rail="paypal")
    assert out["success"] is True
    assert out["offer"]["rail"] == "paypal"
    assert out["offer"]["camgirl_id"] == "cg_wallet_nova"
    listed = list_offers("discord:lead1")
    assert listed["total"] == 1


def test_fulfill_offer_usdt_mock(sales_env):
    from backend.services.ledger_coin_sales_service import create_offer, fulfill_offer

    created = create_offer(ledger_row_id="discord:lead1", mn2_amount=50, price_usd=5.0, rail="usdt")
    offer_id = created["offer"]["offer_id"]
    with patch("backend.services.unified_points_database.unified_points_db.add_points", return_value={"success": True}):
        result = fulfill_offer(offer_id, payment_ref="mock-usdt-1")
    assert result["success"] is True
    assert result["mn2_credited"] == 50


def test_sales_queue(sales_env):
    from backend.services.ledger_coin_sales_service import get_sales_queue

    q = get_sales_queue(limit=10)
    assert q["success"] is True
    assert q["total"] >= 1
    assert q["queue"][0]["ledger_row_id"] == "discord:lead1"
