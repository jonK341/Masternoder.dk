"""HTTP coverage for owner Business Control board APIs."""
import pytest


@pytest.fixture
def board_client(ctl_env, monkeypatch):
    from flask import Flask
    from backend.routes import crypto_exchange_routes as routes

    monkeypatch.setenv("EXCHANGE_ADMIN_KEY", "board-test-key")
    app = Flask(__name__)
    app.register_blueprint(routes.crypto_exchange_bp)
    client = app.test_client()
    headers = {"X-Exchange-Admin-Key": "board-test-key"}
    return client, headers, ctl_env["ctl"]


@pytest.fixture
def ctl_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_arbitrage_service as arb
    from backend.services import trading_bots_control_service as ctl

    data = tmp_path / "crypto_exchange"
    (data / "agent_accounts").mkdir(parents=True)
    (data / "wallets").mkdir(parents=True)

    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(ex, "_TRADES_PATH", str(data / "trades.jsonl"))
    monkeypatch.setattr(ex, "_WALLETS_DIR", str(data / "wallets"))
    monkeypatch.setattr(arb, "_ACCOUNTS_DIR", str(data / "agent_accounts"))
    monkeypatch.setattr(ctl, "_CONTROL_PATH", str(data / "trading_bots_control.json"))
    return {"ex": ex, "arb": arb, "ctl": ctl}


def test_control_board_requires_admin_key(board_client, monkeypatch):
    client, headers, _ctl = board_client
    monkeypatch.delenv("EXCHANGE_ADMIN_KEY", raising=False)
    assert client.get("/api/exchange/control-board/overview").status_code == 401
    monkeypatch.setenv("EXCHANGE_ADMIN_KEY", "board-test-key")
    bad = client.get("/api/exchange/control-board/overview", headers={"X-Exchange-Admin-Key": "wrong"})
    assert bad.status_code == 401


def test_control_board_overview(board_client):
    client, headers, _ctl = board_client
    res = client.get("/api/exchange/control-board/overview", headers=headers)
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert "supervisors" in body
    assert "live_pack" in body


def test_control_board_bot_supervisor_kill_run(board_client):
    client, headers, ctl = board_client
    ov = client.get("/api/exchange/control-board/overview", headers=headers).get_json()
    bot_id = (ov.get("bots") or [{}])[0].get("id") or "arb_agent_btc_eth"

    off = client.post(
        "/api/exchange/control-board/bot",
        headers=headers,
        json={"bot_id": bot_id, "enabled": False},
    )
    assert off.status_code == 200
    assert off.get_json()["success"] is True

    sup = client.post(
        "/api/exchange/control-board/supervisor",
        headers=headers,
        json={"supervisor_id": "sup_arbitrage", "enabled": False},
    )
    assert sup.status_code == 200

    ks = client.post("/api/exchange/control-board/kill-switch", headers=headers, json={"on": True})
    assert ks.status_code == 200
    assert ks.get_json()["kill_switch"] is True

    run = client.post("/api/exchange/control-board/run", headers=headers, json={})
    assert run.status_code == 200
    assert run.get_json()["success"] is False

    client.post("/api/exchange/control-board/kill-switch", headers=headers, json={"on": False})
    client.post(
        "/api/exchange/control-board/supervisor",
        headers=headers,
        json={"supervisor_id": "sup_arbitrage", "enabled": True},
    )
    client.post(
        "/api/exchange/control-board/bot",
        headers=headers,
        json={"bot_id": bot_id, "enabled": True},
    )

    run2 = client.post("/api/exchange/control-board/run", headers=headers, json={"force": True})
    assert run2.status_code == 200
    assert run2.get_json()["success"] is True
    assert "results" in run2.get_json()


def test_control_board_bot_missing_id(board_client):
    client, headers, _ctl = board_client
    res = client.post("/api/exchange/control-board/bot", headers=headers, json={"enabled": True})
    assert res.status_code == 200
    assert res.get_json()["success"] is False


def test_control_board_supervisor_not_found(board_client):
    client, headers, _ctl = board_client
    res = client.post(
        "/api/exchange/control-board/supervisor",
        headers=headers,
        json={"supervisor_id": "sup_missing", "enabled": True},
    )
    assert res.get_json()["success"] is False
