"""Phase 11 game earn + quest alias tests."""
import pytest
from flask import Flask


@pytest.fixture
def points_db(tmp_path, monkeypatch):
    from backend.services import unified_points_database as upd
    from backend.services import game_mn2_rewards as gmr
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path / "points"))
    monkeypatch.setattr(upd, "unified_points_db", db)
    monkeypatch.setattr("backend.services.mn2_ledger.append_entry", lambda *a, **k: {"success": True})
    monkeypatch.setattr("backend.services.activity_events_service.emit", lambda *a, **k: {"success": True})
    monkeypatch.setattr(gmr, "_STATE", str(tmp_path / "game_earn_state.json"))
    return db


def test_top10_list():
    from backend.services.game_mn2_rewards import list_top10_earn, TOP10_EARN
    data = list_top10_earn()
    assert data["success"] is True
    assert len(data["earn_functions"]) == len(TOP10_EARN) == 10


def test_monitor_check_in_idempotent(points_db):
    from backend.services.game_mn2_rewards import monitor_check_in
    r1 = monitor_check_in("player_mon")
    r2 = monitor_check_in("player_mon")
    assert r1.get("success") is True
    assert r2.get("duplicate") is True


def test_cross_game_combo(points_db):
    from backend.services.game_mn2_rewards import record_game_activity
    out = record_game_activity("player_combo", "battle")
    assert out.get("success") is True
    out2 = record_game_activity("player_combo", "starmap")
    assert any(b.get("earn_id") == "cross_game_combo" for b in (out2.get("bonuses") or []) if b.get("success"))


def test_quest_user_alias():
    from backend.routes.quest_routes import quest_bp
    app = Flask(__name__)
    app.register_blueprint(quest_bp)
    c = app.test_client()
    r = c.get("/api/quests/user/player_x")
    assert r.status_code == 200
    assert r.get_json().get("success") is True
    assert r.get_json().get("user_id") == "player_x"


def test_game_hub_earn_routes(points_db, monkeypatch):
    from backend.routes.game_hub_routes import game_hub_bp
    app = Flask(__name__)
    app.register_blueprint(game_hub_bp)
    c = app.test_client()
    r = c.get("/api/game-hub/earn/top10")
    assert r.status_code == 200
    assert len(r.get_json().get("earn_functions") or []) == 10
    r2 = c.post("/api/game-hub/earn/check-in", json={"user_id": "hub_user"})
    assert r2.status_code == 200
    assert r2.get_json().get("success") is True
