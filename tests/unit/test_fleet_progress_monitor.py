"""Public 5D fleet progress monitor API."""
import pytest


@pytest.fixture
def monitor_client(ctl_env, monkeypatch):
    from flask import Flask
    from backend.routes import crypto_exchange_routes as routes

    app = Flask(__name__)
    app.register_blueprint(routes.crypto_exchange_bp)
    return app.test_client()


@pytest.fixture
def ctl_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_arbitrage_service as arb
    from backend.services import trading_bots_control_service as ctl

    data = tmp_path / "crypto_exchange"
    (data / "agent_accounts").mkdir(parents=True)
    data.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(arb, "_ACCOUNTS_DIR", str(data / "agent_accounts"))
    monkeypatch.setattr(ctl, "_CONTROL_PATH", str(data / "trading_bots_control.json"))
    return {"ex": ex, "arb": arb, "ctl": ctl}


def test_public_monitor_shape(ctl_env, monkeypatch):
    from backend.services.exchange_fleet_progress_monitor_service import public_fleet_progress_monitor

    monkeypatch.setenv("FLEET_PROGRESS_MONITOR_PUBLIC", "1")

    out = public_fleet_progress_monitor(light=True)
    assert out["success"] is True
    assert out["privacy"]["pii"] is False
    assert "narration" in out
    assert "fleet" in out and "bots" in out["fleet"]
    assert "progression" in out
    assert "@" not in out["narration"]


def test_public_monitor_route(monitor_client, monkeypatch):
    monkeypatch.setenv("FLEET_PROGRESS_MONITOR_PUBLIC", "1")
    res = monitor_client.get("/api/exchange/fleet-progress-monitor/public")
    assert res.status_code == 200
    data = res.get_json()
    assert data.get("success") is True
    assert data.get("privacy", {}).get("users_redacted") is True


def test_public_monitor_disabled(monitor_client, monkeypatch):
    monkeypatch.setenv("FLEET_PROGRESS_MONITOR_PUBLIC", "0")
    res = monitor_client.get("/api/exchange/fleet-progress-monitor/public")
    assert res.status_code == 404


def test_embed_token_gate(monitor_client, monkeypatch):
    monkeypatch.setenv("FLEET_PROGRESS_MONITOR_PUBLIC", "1")
    monkeypatch.setenv("FLEET_MONITOR_EMBED_TOKEN", "embed-secret")
    bad = monitor_client.get("/api/exchange/fleet-progress-monitor/public?embed=1")
    assert bad.status_code == 403
    ok = monitor_client.get("/api/exchange/fleet-progress-monitor/public?embed=1&embed_token=embed-secret")
    assert ok.status_code == 200
