"""Tests for casino global hub controller and revenue reports."""
import json
import os
import sqlite3
from datetime import datetime, timezone

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _tmp_logs(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(log_dir))
    return log_dir


def _seed_bet(log_dir, user_id="u1", net=100, currency="coins", day=None):
    day = day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    db = log_dir / "casino_ledger.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS casino_bets (
            bet_id TEXT PRIMARY KEY, user_id TEXT, game TEXT, currency TEXT,
            bet REAL, payout REAL, net REAL, outcome TEXT, created_at TEXT,
            exclude_leaderboard INTEGER DEFAULT 0, details TEXT
        )
        """
    )
    conn.execute(
        "INSERT OR REPLACE INTO casino_bets VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (f"bet-{user_id}-{net}", user_id, "coin_flip", currency, 50, 50 + net, net, "win",
         f"{day}T12:00:00Z", 0, "{}"),
    )
    conn.commit()
    conn.close()


def test_global_leaderboard_top25(tmp_path, monkeypatch):
    log_dir = _tmp_logs(tmp_path, monkeypatch)
    _seed_bet(log_dir, "alice", 200)
    _seed_bet(log_dir, "bob", 50)

    from backend.services import casino_global_controller

    out = casino_global_controller.get_global_leaderboard(period="today", limit=25, currency="coins")
    assert out["success"] is True
    assert out["scope"] == "global"
    assert out["hub_id"] == "masternoder-main"
    assert len(out["leaderboard"]) >= 2
    assert out["leaderboard"][0]["user_id"] == "alice"


def test_global_stats(tmp_path, monkeypatch):
    log_dir = _tmp_logs(tmp_path, monkeypatch)
    _seed_bet(log_dir)

    from backend.services import casino_global_controller

    stats = casino_global_controller.get_global_stats()
    assert stats["success"] is True
    assert "coins" in stats["by_currency"]
    assert stats["totals"]["bets"] >= 1


def test_revenue_daily_report(tmp_path, monkeypatch):
    log_dir = _tmp_logs(tmp_path, monkeypatch)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    _seed_bet(log_dir, net=1500, day=day)

    from backend.services import casino_revenue_report

    report = casino_revenue_report.daily_report(day)
    assert report["success"] is True
    assert report["day"] == day
    assert report["by_currency"]["coins"]["bets"] >= 1
    assert report["house_edge_profit_total"] <= 0  # player won in seed

    multi = casino_revenue_report.daily_reports(days=3)
    assert multi["success"] is True
    assert len(multi["reports"]) == 3

    today = casino_revenue_report.today_summary()
    assert today["success"] is True
    assert "summary" in today


def test_global_and_revenue_routes(tmp_path, monkeypatch):
    from flask import Flask
    from backend.routes.casino_routes import casino_bp

    _tmp_logs(tmp_path, monkeypatch)
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(casino_bp)

    with app.test_client() as client:
        glb = client.get("/api/casino/global/leaderboard?limit=5")
        assert glb.status_code == 200
        assert glb.get_json()["success"] is True

        gst = client.get("/api/casino/global/stats")
        assert gst.status_code == 200
        assert gst.get_json()["hub_id"]

        rev = client.get("/api/casino/revenue/daily?days=2")
        assert rev.status_code == 200
        assert len(rev.get_json()["reports"]) == 2

        today = client.get("/api/casino/revenue/report/today")
        assert today.status_code == 200
        assert today.get_json()["day"]


def test_slots_api_count(tmp_path, monkeypatch):
    from flask import Flask
    import backend.services.casino_service as casino
    from backend.routes.casino_routes import casino_bp

    cfg_path = tmp_path / "casino_config.json"
    real_cfg = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "casino_config.json",
    )
    cfg_path.write_text(open(real_cfg, encoding="utf-8").read(), encoding="utf-8")
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg_path))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(casino_bp)
    with app.test_client() as client:
        resp = client.get("/api/casino/slots")
    body = resp.get_json()
    assert resp.status_code == 200
    assert body["success"] is True
    assert body["count"] >= 35
