"""On-chain chrome balance: create deposit address + UTXO sum (no ledger)."""
from __future__ import annotations

from flask import Flask


def _app_with_lifecycle():
    from backend.middleware.ai_user_lifecycle_middleware import register_ai_user_lifecycle_middleware
    from backend.routes.mn2_routes import mn2_bp

    app = Flask(__name__)
    app.secret_key = "test-mn2-balance-onchain"
    app.register_blueprint(mn2_bp)
    register_ai_user_lifecycle_middleware(app)
    return app


def test_onchain_chrome_creates_address_and_returns_utxo(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_onchain_wallet.ensure_user_address",
        lambda user_id, **kwargs: {
            "success": True,
            "deposit_address": "MNaddrAlice",
            "user_id": user_id,
            "created": True,
            "generated": True,
        },
    )
    monkeypatch.setattr(
        "backend.services.mn2_onchain_wallet.chain_balance_for_user",
        lambda user_id: {
            "available": True,
            "confirmed_mn2": 12.5,
            "unconfirmed_mn2": 0.0,
            "addresses": ["MNaddrAlice"],
        },
    )
    # Ledger must not be consulted for chrome paint.
    monkeypatch.setattr(
        "backend.routes.mn2_routes.get_balance",
        lambda user_id: (_ for _ in ()).throw(AssertionError("ledger get_balance")),
    )

    app = _app_with_lifecycle()
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = "alice"
        r = client.get("/api/mn2/balance/onchain")
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert data["mn2_balance"] == 12.5
    assert data["signed_in"] is True
    assert data["balance_source"] == "onchain"
    assert data["deposit_address"] == "MNaddrAlice"
    assert data["onchain"]["confirmed_mn2"] == 12.5
    assert "mn2_usd_price" not in data
    assert "private" in (r.headers.get("Cache-Control") or "")


def test_fast_alias_uses_onchain(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_onchain_wallet.ensure_user_address",
        lambda user_id, **kwargs: {"success": True, "deposit_address": "MNq", "user_id": user_id, "created": False},
    )
    monkeypatch.setattr(
        "backend.services.mn2_onchain_wallet.chain_balance_for_user",
        lambda user_id: {"available": True, "confirmed_mn2": 3.0, "unconfirmed_mn2": 0, "addresses": ["MNq"]},
    )
    app = _app_with_lifecycle()
    with app.test_client() as client:
        r = client.get("/api/mn2/balance/fast?user_id=bob")
    data = r.get_json()
    assert data["mn2_balance"] == 3.0
    assert data["signed_in"] is False
    assert data["balance_source"] == "onchain"


def test_onchain_chrome_anonymous_omits_balance(monkeypatch):
    called = {"n": 0}

    def no_ensure(_user_id, **kwargs):
        called["n"] += 1
        return {"success": True, "deposit_address": "x"}

    monkeypatch.setattr("backend.services.mn2_onchain_wallet.ensure_user_address", no_ensure)
    app = _app_with_lifecycle()
    with app.test_client() as client:
        r = client.get("/api/mn2/balance/onchain")
    data = r.get_json()
    assert data["signed_in"] is False
    assert "mn2_balance" not in data
    assert called["n"] == 0


def test_onchain_chrome_address_failure_surfaces_error(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_onchain_wallet.ensure_user_address",
        lambda user_id, **kwargs: {
            "success": False,
            "error": "Wallet is locked. Set MN2_WALLET_PASSPHRASE so a new address can be created.",
            "code": "wallet_unlock_needed",
        },
    )
    app = _app_with_lifecycle()
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = "alice"
        r = client.get("/api/mn2/balance/onchain")
    data = r.get_json()
    assert data["success"] is False
    assert data["code"] == "wallet_unlock_needed"
    assert "passphrase" in data["error"].lower() or "locked" in data["error"].lower()


def test_onchain_chrome_rpc_scan_failure_no_ledger_fallback(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_onchain_wallet.ensure_user_address",
        lambda user_id, **kwargs: {"success": True, "deposit_address": "MNaddr", "user_id": user_id, "created": False},
    )
    monkeypatch.setattr(
        "backend.services.mn2_onchain_wallet.chain_balance_for_user",
        lambda user_id: {
            "available": False,
            "confirmed_mn2": None,
            "unconfirmed_mn2": None,
            "addresses": ["MNaddr"],
            "error": "connection refused",
        },
    )
    monkeypatch.setattr(
        "backend.routes.mn2_routes.get_balance",
        lambda user_id: {"success": True, "mn2_balance": 99.0},
    )
    app = _app_with_lifecycle()
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = "alice"
        r = client.get("/api/mn2/balance/onchain")
    data = r.get_json()
    assert data["success"] is False
    assert data["deposit_address"] == "MNaddr"
    assert "mn2_balance" not in data or data.get("mn2_balance") != 99.0


def test_detail_balance_still_includes_onchain(monkeypatch):
    monkeypatch.setattr(
        "backend.routes.mn2_routes.get_balance",
        lambda user_id: {"success": True, "user_id": user_id, "mn2_balance": 3.0},
    )
    monkeypatch.setattr(
        "backend.services.mn2_onchain_wallet.chain_balance_for_user",
        lambda user_id: {"available": True, "confirmed": 1.0, "confirmed_mn2": 1.0},
    )
    monkeypatch.setattr(
        "backend.services.mn2_onchain_wallet.reconcile_user",
        lambda user_id, ledger: {"ok": True, "delta": 0},
    )
    monkeypatch.setattr(
        "backend.services.mn2_chainz.chainz_ticker_usd_with_updated",
        lambda: {"price": 0.01, "last_updated_iso": "2026-01-01T00:00:00Z"},
    )
    app = _app_with_lifecycle()
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = "alice"
        r = client.get("/api/mn2/balance")
    data = r.get_json()
    assert data["onchain"]["confirmed_mn2"] == 1.0
    assert data["reconcile"]["ok"] is True


def test_onchain_path_skips_lifecycle_identify(monkeypatch):
    ensure_calls = {"n": 0}

    def fake_identify(request):
        ensure_calls["n"] += 1
        return {"success": True, "user_id": "auto-created"}

    monkeypatch.setattr(
        "backend.services.user_identification.user_identification.identify_or_create_user",
        fake_identify,
    )
    app = _app_with_lifecycle()
    with app.test_client() as client:
        r = client.get("/api/mn2/balance/onchain")
    assert r.status_code == 200
    assert ensure_calls["n"] == 0
    assert r.get_json()["signed_in"] is False
