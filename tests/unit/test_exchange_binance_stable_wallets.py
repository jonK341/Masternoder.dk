"""Binance USDT/USDC exchange wallets + MN2 quote trading."""
import pytest
from flask import Flask


@pytest.fixture
def payout_client(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_secrets_vault_service as vault
    from backend.services import exchange_payout_service as pay
    from backend.routes import crypto_exchange_routes as routes

    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)
    (data / "wallets").mkdir(parents=True)

    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_WALLETS_DIR", str(data / "wallets"))
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(vault, "_DATA_DIR", str(data))
    monkeypatch.setattr(vault, "_VAULT_PATH", str(data / "secrets_vault.enc"))
    monkeypatch.setattr(vault, "_REGISTRY_PATH", str(data / "wallet_registry.json"))
    monkeypatch.setattr(pay, "_PAYOUT_PATH", str(data / "payout_config.json"))
    monkeypatch.setattr(pay, "_SWEEPS_PATH", str(data / "payout_sweeps.jsonl"))
    monkeypatch.delenv("EXCHANGE_ADMIN_KEY", raising=False)
    monkeypatch.delenv("COGS_ADMIN_REPORT_KEY", raising=False)
    monkeypatch.delenv("BINANCE_API_KEY", raising=False)
    monkeypatch.delenv("BINANCE_API_SECRET", raising=False)
    monkeypatch.delenv("EXCHANGE_VAULT_KEY", raising=False)

    app = Flask(__name__)
    app.register_blueprint(routes.crypto_exchange_bp)
    return app.test_client()


def test_stable_wallets_status_route(payout_client):
    res = payout_client.get("/api/exchange/binance/stable-wallets")
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assets = {w["asset"] for w in body["wallets"]}
    assert assets == {"USDT", "USDC"}
    assert body["tradeable"] is True
    assert "USDT" in body["quote_currencies"]
    assert "USDC" in body["quote_currencies"]


def test_sync_stable_wallets_route_requires_admin(payout_client):
    res = payout_client.post("/api/exchange/payout/sync-binance-wallets")
    assert res.status_code == 401


def test_full_app_registers_crypto_exchange_blueprint():
    import inspect
    from backend.register_blueprints import _register_all_blueprints_impl, register_lite_blueprints

    marker = "from backend.routes.crypto_exchange_routes import crypto_exchange_bp"
    assert marker in inspect.getsource(_register_all_blueprints_impl)
    assert marker in inspect.getsource(register_lite_blueprints)


def test_sync_stable_wallets_route_admin(payout_client, monkeypatch):
    monkeypatch.setenv("EXCHANGE_ADMIN_KEY", "test-admin")
    res = payout_client.post(
        "/api/exchange/payout/sync-binance-wallets",
        headers={"X-Exchange-Admin-Key": "test-admin"},
        json={},
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assets = {w["asset"] for w in body["wallets"]}
    assert assets == {"USDT", "USDC"}
