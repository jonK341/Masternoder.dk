"""Unit tests for wallet micro-earn click-to-earn service and routes."""
import json
import os
from unittest.mock import patch

import pytest
from flask import Flask


@pytest.fixture
def earn_paths(tmp_path, monkeypatch):
    cfg_path = tmp_path / "wallet_micro_earn_config.json"
    state_path = tmp_path / "wallet_micro_earn_state.json"
    cfg_path.write_text(
        json.dumps(
            {
                "enabled": True,
                "global_daily_cap_mn2": 0.05,
                "diminishing_factor": 0.85,
                "min_amount_mn2": 0.0001,
                "captcha_hook_enabled": False,
                "events": {
                    "network_pulse_click": {
                        "unit_id": "WR-EARN-1",
                        "name": "Network Pulse",
                        "description": "Test pulse",
                        "base_amount": 0.002,
                        "daily_cap_mn2": 0.01,
                        "max_clicks_per_day": 5,
                        "cooldown_seconds": 0,
                    },
                    "wallet_daily_open": {
                        "unit_id": "WR-EARN-2",
                        "name": "Daily Open",
                        "description": "Once per day",
                        "base_amount": 0.005,
                        "daily_cap_mn2": 0.005,
                        "max_clicks_per_day": 1,
                        "cooldown_seconds": 0,
                    },
                },
                "game_links": [{"id": "battle", "name": "Battle", "path": "/battle", "icon": "⚔️"}],
            }
        ),
        encoding="utf-8",
    )
    import backend.services.wallet_micro_earn_service as svc

    monkeypatch.setattr(svc, "_CONFIG_PATH", str(cfg_path))
    monkeypatch.setattr(svc, "_STATE_PATH", str(state_path))
    return cfg_path, state_path


@pytest.fixture
def points_db(tmp_path, monkeypatch):
    from backend.services import unified_points_database as upd
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path))
    monkeypatch.setattr(upd, "unified_points_db", db)
    monkeypatch.setattr("backend.services.mn2_ledger.append_entry", lambda *a, **k: None)
    monkeypatch.setattr("backend.services.activity_events_service.emit", lambda *a, **k: None)
    return db


def _app():
    from backend.routes.wallet_v2_routes import wallet_v2_bp

    app = Flask(__name__)
    app.register_blueprint(wallet_v2_bp)
    return app


def test_status_lists_events_for_guest(earn_paths):
    from backend.services.wallet_micro_earn_service import get_status

    status = get_status("default_user")
    assert status["success"] is True
    assert status["guest"] is True
    assert len(status["events"]) == 2
    assert status["events"][0]["event_id"] == "network_pulse_click"
    assert status["game_links"][0]["id"] == "battle"


def test_record_click_credits_mn2(earn_paths, points_db):
    from backend.services.wallet_micro_earn_service import get_status, record_click

    r = record_click("player_earn", "network_pulse_click")
    assert r["success"] is True
    assert r["mn2_awarded"] == pytest.approx(0.002, rel=1e-6)

    status = get_status("player_earn")
    assert status["earned_today_mn2"] == pytest.approx(0.002, rel=1e-6)
    assert status["events"][0]["clicks_today"] == 1

    bal = points_db.get_all_points("player_earn")
    assert float(bal["points"]["mn2_balance"]) == pytest.approx(0.002, rel=1e-6)


def test_diminishing_returns_on_repeat_clicks(earn_paths, points_db):
    from backend.services.wallet_micro_earn_service import record_click

    r1 = record_click("player_dim", "network_pulse_click")
    r2 = record_click("player_dim", "network_pulse_click")
    assert r1["mn2_awarded"] == pytest.approx(0.002, rel=1e-6)
    assert r2["mn2_awarded"] == pytest.approx(0.0017, rel=1e-3)


def test_rejects_guest_user(earn_paths):
    from backend.services.wallet_micro_earn_service import record_click

    r = record_click("guest", "network_pulse_click")
    assert r["success"] is False
    assert r["error"] == "authenticated_user_required"


def test_daily_open_single_click(earn_paths, points_db):
    from backend.services.wallet_micro_earn_service import record_click

    r1 = record_click("player_daily", "wallet_daily_open")
    r2 = record_click("player_daily", "wallet_daily_open")
    assert r1["success"] is True
    assert r2["success"] is False
    assert r2["error"] == "max_clicks"


@patch("backend.routes.wallet_v2_routes.resolve_user_id")
@patch("backend.routes.wallet_v2_routes.micro_earn_click")
def test_earn_click_route(mock_click, mock_resolve):
    mock_resolve.return_value = "route_user"
    mock_click.return_value = {"success": True, "mn2_awarded": 0.002, "event_id": "network_pulse_click"}
    client = _app().test_client()
    r = client.post(
        "/api/wallet/v2/earn/click",
        json={"event_id": "network_pulse_click"},
    )
    assert r.status_code == 200
    mock_click.assert_called_once_with("route_user", "network_pulse_click", captcha_token=None)


@patch("backend.routes.wallet_v2_routes.resolve_user_id")
@patch("backend.routes.wallet_v2_routes.micro_earn_status")
def test_earn_status_route(mock_status, mock_resolve):
    mock_resolve.return_value = "route_user"
    mock_status.return_value = {"success": True, "earned_today_mn2": 0.01, "events": []}
    client = _app().test_client()
    r = client.get("/api/wallet/v2/earn/status")
    assert r.status_code == 200
    data = r.get_json()
    assert data["earned_today_mn2"] == 0.01
