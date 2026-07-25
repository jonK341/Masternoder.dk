"""Phase 2 wallet routes: refresh, connect, addresses, address-book, transfer."""
from __future__ import annotations

from flask import Flask


def _app():
    from backend.routes.mn2_routes import mn2_bp

    app = Flask(__name__)
    app.register_blueprint(mn2_bp)
    return app


def test_wallet_addresses_list(tmp_path, monkeypatch):
    from backend.routes import mn2_routes as routes

    monkeypatch.setattr(routes, "resolve_user_id", lambda **k: "user_w")
    monkeypatch.setattr(
        routes,
        "list_user_addresses",
        lambda uid: {
            "success": True,
            "user_id": uid,
            "wallet_type": "core",
            "addresses": [{"label": "primary", "address": "JTestAddr111111111111111111111", "active": True}],
        },
    )
    monkeypatch.setattr(routes, "_explorer_base_url", lambda: "https://example.test")

    c = _app().test_client()
    r = c.get("/api/mn2/wallet/addresses")
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert data["addresses"][0]["address"].startswith("JTest")
    assert "explorer_address_url" in data["addresses"][0]


def test_wallet_refresh_rotates(tmp_path, monkeypatch):
    from backend.routes import mn2_routes as routes

    monkeypatch.setattr(routes, "resolve_user_id", lambda **k: "user_r")
    monkeypatch.setattr(
        routes,
        "refresh_deposit_address",
        lambda uid: {"success": True, "user_id": uid, "deposit_address": "JRotatedAddr22222222222222222"},
    )
    monkeypatch.setattr(
        routes,
        "list_user_addresses",
        lambda uid: {
            "success": True,
            "addresses": [
                {"label": "legacy", "address": "JOld", "active": False},
                {"label": "primary", "address": "JRotatedAddr22222222222222222", "active": True},
            ],
        },
    )
    monkeypatch.setattr(routes, "_explorer_base_url", lambda: "https://example.test")
    monkeypatch.setattr(
        "backend.services.mn2_deposit_scanner.run_scanner",
        lambda: {"success": True},
    )

    c = _app().test_client()
    r = c.post("/api/mn2/wallet/refresh", json={"user_id": "user_r"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert data["deposit_address"].startswith("JRotated")
    assert data["rescanned"] is True
    assert len(data["addresses"]) == 2


def test_wallet_connect_external(monkeypatch):
    from backend.routes import mn2_routes as routes

    monkeypatch.setattr(routes, "resolve_user_id", lambda **k: "user_c")
    monkeypatch.setattr(
        routes,
        "connect_external_wallet",
        lambda uid, addr, wallet_type="watch": {
            "success": True,
            "user_id": uid,
            "address": addr,
            "wallet_type": wallet_type,
        },
    )
    monkeypatch.setattr(
        routes,
        "list_user_addresses",
        lambda uid: {"success": True, "addresses": [{"label": "watch", "address": "JWatchAddr33333333333333333", "external": True}]},
    )

    c = _app().test_client()
    r = c.post(
        "/api/mn2/wallet/connect",
        json={"address": "JWatchAddr33333333333333333", "wallet_type": "extension"},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert data["wallet_type"] == "extension"
    assert data["addresses"]


def test_address_book_get_and_add(tmp_path, monkeypatch):
    from backend.services import mn2_address_book as book
    from backend.routes import mn2_routes as routes

    monkeypatch.setattr(book, "_PATH", str(tmp_path / "book.json"))
    monkeypatch.setattr(routes, "resolve_user_id", lambda **k: "user_ab")
    monkeypatch.setattr(
        "backend.services.password_protection_service.get_password_status",
        lambda uid: {"has_password": False},
    )

    c = _app().test_client()
    r = c.get("/api/mn2/address-book")
    assert r.status_code == 200
    assert r.get_json()["addresses"] == []

    r2 = c.post("/api/mn2/address-book", json={"address": "JBookAddr44444444444444444", "label": "cold"})
    assert r2.status_code == 200
    assert r2.get_json()["success"] is True
    listed = book.list_addresses("user_ab")
    assert len(listed) == 1
    assert listed[0]["label"] == "cold"


def test_transfer_route(monkeypatch):
    from backend.routes import mn2_routes as routes

    monkeypatch.setattr(routes, "resolve_user_id", lambda **k: "user_from")
    monkeypatch.setattr(
        "backend.services.mn2_gift_service.transfer",
        lambda sender, to, amount, note="": {
            "success": True,
            "amount_mn2": amount,
            "from_user": sender,
            "to_user": "user_to",
        },
    )
    c = _app().test_client()
    r = c.post("/api/mn2/transfer", json={"to": "user_to", "amount": 1.5})
    assert r.status_code == 200
    assert r.get_json()["amount_mn2"] == 1.5
