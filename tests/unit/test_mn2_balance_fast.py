"""Fast MN2 ledger read for wallet chrome (no chain scan / Chainz)."""
from __future__ import annotations

from flask import Flask, session


def _app_with_lifecycle():
    from backend.middleware.ai_user_lifecycle_middleware import register_ai_user_lifecycle_middleware
    from backend.routes.mn2_routes import mn2_bp

    app = Flask(__name__)
    app.secret_key = "test-mn2-balance-fast"
    app.register_blueprint(mn2_bp)
    register_ai_user_lifecycle_middleware(app)
    return app


def test_fast_balance_session_user_no_unspent(monkeypatch):
    calls = {"chain": 0, "reconcile": 0, "chainz": 0}

    monkeypatch.setattr(
        "backend.services.mn2_wallet_service.get_balance",
        lambda user_id: {"success": True, "user_id": user_id, "mn2_balance": 12.5},
    )

    def boom_chain(*_a, **_k):
        calls["chain"] += 1
        raise AssertionError("chain_balance_for_user must not run on fast path")

    def boom_reconcile(*_a, **_k):
        calls["reconcile"] += 1
        raise AssertionError("reconcile_user must not run on fast path")

    def boom_chainz(*_a, **_k):
        calls["chainz"] += 1
        raise AssertionError("chainz must not run on fast path")

    monkeypatch.setattr(
        "backend.services.mn2_onchain_wallet.chain_balance_for_user",
        boom_chain,
    )
    monkeypatch.setattr(
        "backend.services.mn2_onchain_wallet.reconcile_user",
        boom_reconcile,
    )
    monkeypatch.setattr(
        "backend.services.mn2_chainz.chainz_ticker_usd_with_updated",
        boom_chainz,
    )

    app = _app_with_lifecycle()
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = "alice"
        r = client.get("/api/mn2/balance/fast")
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert data["mn2_balance"] == 12.5
    assert data["signed_in"] is True
    assert "wallet_mode" in data
    assert "mn2_usd_price" not in data
    assert "price_usd" not in data
    assert "onchain" not in data
    assert calls["chain"] == 0
    assert calls["reconcile"] == 0
    assert calls["chainz"] == 0
    assert "private" in (r.headers.get("Cache-Control") or "")
    assert "no-store" in (r.headers.get("Cache-Control") or "")


def test_fast_balance_query_user_signed_in_false(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_wallet_service.get_balance",
        lambda user_id: {"success": True, "user_id": user_id, "mn2_balance": 12.5},
    )
    app = _app_with_lifecycle()
    with app.test_client() as client:
        r = client.get("/api/mn2/balance/fast?user_id=alice")
    data = r.get_json()
    assert data["mn2_balance"] == 12.5
    assert data["signed_in"] is False


def test_fast_balance_anonymous_omits_balance(monkeypatch):
    called = {"bal": 0}

    def no_balance(_user_id):
        called["bal"] += 1
        return {"success": True, "mn2_balance": 99}

    monkeypatch.setattr("backend.services.mn2_wallet_service.get_balance", no_balance)
    app = _app_with_lifecycle()
    with app.test_client() as client:
        r = client.get("/api/mn2/balance/fast")
    data = r.get_json()
    assert data["signed_in"] is False
    assert "mn2_balance" not in data
    assert called["bal"] == 0


def test_fast_balance_survives_rpc_failure(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_wallet_service.get_balance",
        lambda user_id: {"success": True, "user_id": user_id, "mn2_balance": 12.5},
    )
    monkeypatch.setattr(
        "backend.services.mn2_rpc_client._call",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("daemon down")),
    )
    app = _app_with_lifecycle()
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = "alice"
        r = client.get("/api/mn2/balance/fast")
    assert r.get_json()["mn2_balance"] == 12.5


def test_detail_balance_still_includes_onchain(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_wallet_service.get_balance",
        lambda user_id: {"success": True, "user_id": user_id, "mn2_balance": 3.0},
    )
    monkeypatch.setattr(
        "backend.services.mn2_onchain_wallet.chain_balance_for_user",
        lambda user_id: {"available": True, "confirmed": 1.0},
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
    assert data["onchain"]["confirmed"] == 1.0
    assert data["reconcile"]["ok"] is True


def test_fast_path_skips_ensure_user_address(monkeypatch):
    ensure_calls = {"n": 0}

    def fake_identify(request):
        ensure_calls["n"] += 1
        return {"success": True, "user_id": "auto-created"}

    monkeypatch.setattr(
        "backend.services.user_identification.user_identification.identify_or_create_user",
        fake_identify,
    )
    # Also guard deposit address creation if anything still calls it
    monkeypatch.setattr(
        "backend.services.mn2_wallet_service.ensure_user_address",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("ensure_user_address")),
        raising=False,
    )
    monkeypatch.setattr(
        "backend.services.mn2_wallet_service.get_or_create_deposit_address",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("deposit")),
        raising=False,
    )

    app = _app_with_lifecycle()
    with app.test_client() as client:
        r = client.get("/api/mn2/balance/fast")
    assert r.status_code == 200
    assert ensure_calls["n"] == 0
    assert r.get_json()["signed_in"] is False
