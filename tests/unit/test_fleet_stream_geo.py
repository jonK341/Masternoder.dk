"""Fleet stream GPS/GPRS telemetry."""
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


@pytest.fixture
def geo_env(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs" / "fleet_stream_geo"
    log_dir.mkdir(parents=True)
    monkeypatch.setattr(
        "backend.services.fleet_stream_geo_service._GEO_LOG_DIR",
        str(log_dir),
    )
    monkeypatch.setattr(
        "backend.services.fleet_stream_geo_service._GEO_LOG_FILE",
        str(log_dir / "pings.jsonl"),
    )
    return log_dir


def test_public_geo_has_gprs_nodes(geo_env):
    from backend.services.fleet_stream_geo_service import public_geo_snapshot

    snap = public_geo_snapshot()
    assert snap["success"] is True
    assert snap["enabled"] is True
    assert snap["counts"]["gprs"] >= 1
    assert snap["maps"]["google_embed"]
    assert snap["maps"]["osm_embed"]


def test_record_ping_coarse(geo_env):
    from backend.services.fleet_stream_geo_service import public_geo_snapshot, record_geo_ping

    r = record_geo_ping(latitude=55.6761987, longitude=12.5683123, accuracy_m=12.0, source="browser_gps")
    assert r["success"] is True
    assert r["ping"]["latitude"] == 55.68
    snap = public_geo_snapshot()
    kinds = {m["kind"] for m in snap["markers"]}
    assert "gps" in kinds


def test_go_live_assign(monkeypatch, geo_env):
    import backend.services.youtube_stream_agent_service as yta

    monkeypatch.setattr(
        yta,
        "assign_youtube_stream_agents",
        lambda uid, aid="youtube_stream_agent": {"success": True, "user_id": uid},
    )
    from backend.services.fleet_stream_geo_service import start_livestream_session

    out = start_livestream_session("stream_op")
    assert out["success"] is True
    assert out["assign"]["success"] is True
    assert out["geo"]["success"] is True


def test_geo_routes(monitor_client, geo_env, monkeypatch):
    from backend.routes import crypto_exchange_routes as routes

    monkeypatch.setattr(
        "backend.services.exchange_fleet_progress_monitor_service.monitor_public_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        routes,
        "_fleet_chat_uid",
        lambda: "geo_user",
    )
    r = monitor_client.get("/api/exchange/fleet-stream/geo/public")
    assert r.status_code == 200
    assert r.get_json().get("markers")
    r2 = monitor_client.post(
        "/api/exchange/fleet-stream/geo/ping",
        json={"latitude": 55.5, "longitude": 12.5, "guest_id": "g1"},
    )
    assert r2.status_code == 200
