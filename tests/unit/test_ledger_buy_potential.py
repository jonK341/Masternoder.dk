"""Ledger buy potential scoring tests."""
import json
import pytest


def test_classify_funded_never_bought():
    from backend.services.ledger_buy_potential_service import classify_buy_tier

    tier = classify_buy_tier(
        spendable_mn2=0.25,
        buy_spend_mn2=0,
        buy_count=0,
        has_bought=False,
        has_funding=True,
    )
    assert tier == "funded_never_bought"


def test_classify_high_spender():
    from backend.services.ledger_buy_potential_service import classify_buy_tier

    tier = classify_buy_tier(
        spendable_mn2=1.0,
        buy_spend_mn2=0.75,
        buy_count=3,
        has_bought=True,
        has_funding=True,
    )
    assert tier == "high_spender"


def test_summarize_entries_buy_channels():
    from backend.services.mn2_ledger import _summarize_entries_for_user

    entries = [
        {"user_id": "buyer_a", "type": "deposit", "amount": 1.0, "created_at": "2026-09-01T10:00:00Z"},
        {"user_id": "buyer_a", "type": "shop_payment", "amount": 0.1, "created_at": "2026-09-02T10:00:00Z"},
        {"user_id": "buyer_a", "type": "encoder_payment", "amount": 0.05, "created_at": "2026-09-03T10:00:00Z"},
    ]
    row = _summarize_entries_for_user("buyer_a", entries)
    assert row["has_bought"] is True
    assert row["buy_count"] == 2
    assert "shop_payment" in row["buy_channels"]
    assert row["buy_potential"]["tier"] in ("active_buyer", "repeat_buyer", "high_spender")


def test_list_buy_opportunities_route(tmp_path, monkeypatch):
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)
    monkeypatch.delenv("DISCORD_OPS_SECRET", raising=False)
    monkeypatch.delenv("YOUR_OPS_SECRET", raising=False)

    import backend.services.ledger_customer_aggregator_service as lca
    index_file = tmp_path / "ledger_customer_index.json"
    customers = [
        {
            "user_id": "funded_user",
            "ledger_net_mn2": 0.2,
            "buy_spend_mn2": 0,
            "buy_count": 0,
            "has_bought": False,
            "has_funding": True,
            "buy_channels": [],
            "entry_count": 1,
            "last_activity": "2026-09-16T10:00:00Z",
            "buy_potential": {
                "tier": "funded_never_bought",
                "spendable_mn2": 0.2,
                "buy_spend_mn2": 0,
                "buy_count": 0,
                "has_bought": False,
                "buy_channels": [],
                "suggested_purchases": [],
            },
        }
    ]
    index_file.write_text(
        json.dumps({"version": 1, "total": 1, "customers": customers}),
        encoding="utf-8",
    )
    monkeypatch.setattr(lca, "_INDEX_FILE", str(index_file))

    from flask import Flask
    from backend.routes.customer_aggregator_routes import customer_aggregator_bp

    app = Flask(__name__)
    app.register_blueprint(customer_aggregator_bp)
    c = app.test_client()
    r = c.get(
        "/api/customers/buy-potential?tier=funded_never_bought&limit=10",
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("total") == 1
    assert data["customers"][0]["user_id"] == "funded_user"
