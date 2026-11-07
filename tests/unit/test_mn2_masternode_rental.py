"""Masternode inventory rental API."""
from __future__ import annotations


def test_rental_catalog_and_quote(monkeypatch, tmp_path):
    import backend.services.mn2_masternode_rental_service as rental
    import backend.services.mn2_masternode_service as mn

    monkeypatch.setattr(
        mn,
        "get_config",
        lambda: {
            "enabled": True,
            "collateral_mn2": 5000,
            "min_hosting_term_days": 30,
            "paypal": {"currency": "USD", "price_usd_per_slot": 5.0},
            "rental": {"enabled": True, "price_usd_monthly": 5.0},
        },
    )
    monkeypatch.setattr(
        rental,
        "list_rental_inventory",
        lambda **_: {
            "success": True,
            "assignable_count": 3,
            "active_count": 2,
            "hosts": [
                {"host_id": "platform-mn-1", "status": "active"},
                {"host_id": "platform-mn-2", "status": "active"},
            ],
        },
    )
    monkeypatch.setattr(
        mn,
        "get_service_status",
        lambda **_: {"slots_available": 0, "checkout_open": False},
    )

    cat = rental.rental_catalog()
    assert cat["price_usd_monthly"] == 5.0
    assert cat["inventory_available"] == 3

    orders: dict = {}

    def load_orders():
        return dict(orders)

    def save_orders(data):
        orders.clear()
        orders.update(data)

    import backend.services.mn2_masternode_hosting_service as hosting

    monkeypatch.setattr(hosting, "_load_orders", load_orders)
    monkeypatch.setattr(hosting, "_save_orders", save_orders)
    monkeypatch.setattr(hosting, "_data_path", lambda name: str(tmp_path / name))
    monkeypatch.setattr(hosting, "_audit", lambda *a, **k: None)
    monkeypatch.setattr(hosting, "pricing_for_slots", lambda n: {
        "coins_per_slot": 500,
        "coins_total": 500 * n,
        "mn2_total": 50 * n,
        "payment_rails": ["paypal"],
    })

    q = rental.create_rental_quote(2, "user_test")
    assert q["success"] is True
    assert q["product"] == rental.PRODUCT_INVENTORY_LEASE
    assert orders[q["quote_id"]]["product"] == rental.PRODUCT_INVENTORY_LEASE


def test_assign_rental_hosts(monkeypatch):
    import backend.services.mn2_masternode_rental_service as rental

    monkeypatch.setattr(
        rental,
        "list_rental_inventory",
        lambda **_: {
            "hosts": [
                {"host_id": "platform-mn-1", "status": "active", "collateral_txid": "a", "collateral_vout": 0},
            ]
        },
    )
    captured = []

    import backend.services.mn2_masternode_service as mn

    def fake_register(payload):
        captured.append(payload)
        return {"success": True, "host": payload}

    monkeypatch.setattr(mn, "register_host", fake_register)
    out = rental.assign_rental_hosts("renter_1", 1, "mnr_test")
    assert out["success"] is True
    assert captured[0]["owner_user_id"] == "renter_1"


def test_mark_paid_inventory_branch(monkeypatch):
    import backend.services.mn2_masternode_hosting_service as hosting
    import backend.services.mn2_masternode_rental_service as rental

    monkeypatch.setattr(
        rental,
        "assign_rental_hosts",
        lambda uid, slots, oid: {"success": True, "host_ids": ["platform-mn-1"], "message": "ok"},
    )
    monkeypatch.setattr(hosting, "_register_and_provision", lambda o: {"host_ids": ["new"], "provisions": []})
    monkeypatch.setattr(hosting, "_audit", lambda *a, **k: None)

    order = {"order_id": "mnr_x", "user_id": "u1", "slots": 1, "product": "masternode_inventory_lease"}
    out = hosting._mark_paid(order, "payref", "test", "paypal")
    assert out["success"] is True
    assert order["host_ids"] == ["platform-mn-1"]
