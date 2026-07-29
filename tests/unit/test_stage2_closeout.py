"""Stage 2 close-out: casino buy-in emit, wallet refresh, generator MN2 charge."""
import json
import os

import pytest
from flask import Flask


@pytest.fixture
def points_db(tmp_path, monkeypatch):
    from backend.services import unified_points_database as upd
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    monkeypatch.setattr(upd, "_IDEMPOTENCY_CACHE", {})
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path))
    monkeypatch.setattr(upd, "unified_points_db", db)
    return db


@pytest.fixture
def activity_log(tmp_path, monkeypatch):
    import backend.services.activity_events_service as aes

    path = tmp_path / "activity_events.jsonl"
    monkeypatch.setattr(aes, "_LOG_PATH", str(path))
    return path


def test_casino_mn2_buyin_emits_activity(points_db, activity_log, monkeypatch):
    import backend.services.casino_service as casino

    points_db.add_points("casino_user", "mn2_balance", 5.0, source="seed", metadata={"reference": "seed1"})
    monkeypatch.setattr(
        casino,
        "get_mn2_buyin_packs",
        lambda: {
            "success": True,
            "packs": [{"id": "starter", "price_mn2": 1.0, "casino_usd_credit": 10.0}],
        },
    )

    result = casino.purchase_mn2_buyin_pack("casino_user", "starter")
    assert result.get("success") is True

    rows = activity_log.read_text(encoding="utf-8").strip().splitlines()
    assert rows
    event = json.loads(rows[-1])
    assert event.get("type") == "casino_mn2_buyin"
    assert event.get("user_id") == "casino_user"


def test_wallet_refresh_rotates_address(tmp_path, monkeypatch, activity_log):
    import backend.services.mn2_wallet_service as mws

    addr_file = tmp_path / "mn2_user_addresses.json"
    monkeypatch.setattr(mws, "_addresses_path", lambda: str(addr_file))
    seq = iter(["MN2AddrFirst111", "MN2AddrSecond222"])
    monkeypatch.setattr(mws, "_generate_valid_address", lambda **_: {
        "success": True,
        "deposit_address": next(seq),
    })

    created = mws.get_or_create_deposit_address("wallet_user_a")
    assert created.get("success") is True
    assert created.get("deposit_address") == "MN2AddrFirst111"

    refreshed = mws.refresh_deposit_address("wallet_user_a")
    assert refreshed.get("success") is True
    assert refreshed.get("deposit_address") == "MN2AddrSecond222"

    listing = mws.list_user_addresses("wallet_user_a")
    addresses = [r.get("address") for r in listing.get("addresses") or []]
    assert "MN2AddrFirst111" in addresses
    assert "MN2AddrSecond222" in addresses

    rows = activity_log.read_text(encoding="utf-8").strip().splitlines()
    assert any("wallet_deposit_address_rotated" in line for line in rows)


def test_wallet_refresh_route(tmp_path, monkeypatch):
    from backend.routes.mn2_routes import mn2_bp
    import backend.services.mn2_wallet_service as mws

    addr_file = tmp_path / "mn2_user_addresses.json"
    monkeypatch.setattr(mws, "_addresses_path", lambda: str(addr_file))
    monkeypatch.setattr(mws, "_generate_valid_address", lambda **_: {
        "success": True,
        "deposit_address": "MN2RouteRefreshAddr",
    })

    app = Flask(__name__)
    app.register_blueprint(mn2_bp)
    client = app.test_client()
    r = client.post("/api/mn2/wallet/refresh", json={"user_id": "route_wallet_user"})
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("deposit_address") == "MN2RouteRefreshAddr"


def test_unified_generate_video_charges_mn2(monkeypatch):
    import backend.routes.missing_endpoints_routes as mer

    charged = {}

    def fake_charge(user_id, doc_id, config, body=None):
        charged["user_id"] = user_id
        charged["doc_id"] = doc_id
        charged["config"] = config
        return {"success": True, "charged": True, "price_mn2": 0.5}

    monkeypatch.setattr(mer, "_start_documentary_encoding", lambda *a, **k: None)
    monkeypatch.setattr(mer, "_ensure_video_job", lambda *a, **k: None)
    monkeypatch.setattr(mer, "_get_video_job", lambda doc_id: {})
    monkeypatch.setattr(mer, "_set_video_job", lambda *a, **k: None)
    monkeypatch.setattr("backend.services.generator_mn2_service.charge_if_requested", fake_charge)

    app = Flask(__name__)

    @app.route("/api/unified/generate-video", methods=["POST"])
    def _route():
        return mer.unified_generate_video()

    client = app.test_client()
    r = client.post(
        "/api/unified/generate-video",
        json={
            "user_id": "gen_user",
            "prompt": "test video",
            "pay_with_mn2": True,
            "quality_mode": "premium",
        },
    )
    assert r.status_code == 202
    body = r.get_json()
    assert body.get("success") is True
    assert charged.get("user_id") == "gen_user"
    assert charged.get("config", {}).get("pay_with_mn2") is True
