"""Tests for casino ideas slice — big-win HOF, slot of day, RG, shop audit, reconcile."""
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


def _seed_multiplier_bet(log_dir, user_id="u1", bet=10, payout=100, game="slot_magic"):
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
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn.execute(
        "INSERT OR REPLACE INTO casino_bets VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (f"bet-{user_id}", user_id, game, "coins", bet, payout, payout - bet, "win",
         f"{day}T12:00:00Z", 0, "{}"),
    )
    conn.commit()
    conn.close()


def test_top_big_wins_from_ledger(tmp_path, monkeypatch):
    log_dir = _tmp_logs(tmp_path, monkeypatch)
    _seed_multiplier_bet(log_dir, bet=10, payout=100)

    from backend.services import casino_ledger

    rows = casino_ledger.top_big_wins(days=7, limit=5)
    assert len(rows) >= 1
    assert rows[0]["multiplier"] == 10.0


def test_big_win_hall_of_fame_service(tmp_path, monkeypatch):
    log_dir = _tmp_logs(tmp_path, monkeypatch)
    _seed_multiplier_bet(log_dir)

    import backend.services.casino_service as casino

    out = casino.get_big_win_hall_of_fame(days=7, limit=5)
    assert out["success"] is True
    assert out["count"] >= 1
    assert out["wins"][0]["multiplier"] == 10.0


def test_slot_of_the_day(tmp_path, monkeypatch):
    import backend.services.casino_service as casino

    cfg_path = tmp_path / "casino_config.json"
    real_cfg = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "casino_config.json",
    )
    cfg_path.write_text(open(real_cfg, encoding="utf-8").read(), encoding="utf-8")
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg_path))

    out = casino.get_slot_of_the_day()
    assert out["success"] is True
    assert out.get("slot") is not None
    assert out["slot"].get("id", "").startswith("slot_")


def test_referral_leaderboard(tmp_path, monkeypatch):
    from backend.services import casino_social_service

    ref_path = tmp_path / "casino_referrals.json"
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    ref_path.write_text(json.dumps({
        "codes": {"MN-ABC": "referrer1"},
        "signups": [
            {"referrer_user_id": "referrer1", "referred_user_id": "a"},
            {"referrer_user_id": "referrer1", "referred_user_id": "b"},
            {"referrer_user_id": "referrer2", "referred_user_id": "c"},
        ],
    }), encoding="utf-8")
    monkeypatch.setattr(casino_social_service, "_CASINO_REFERRALS_PATH", str(ref_path))

    board = casino_social_service.get_referral_leaderboard(limit=5)
    assert board["success"] is True
    assert board["leaderboard"][0]["user_id"] == "referrer1"
    assert board["leaderboard"][0]["referrals"] == 2


def test_shop_rtp_audit_passes():
    from backend.services import casino_shop_service

    audit = casino_shop_service.audit_rtp_compliance()
    assert audit["success"] is True
    assert audit["ok"] is True
    assert audit["item_count"] >= 20


def test_revenue_reconcile_empty(tmp_path, monkeypatch):
    _tmp_logs(tmp_path, monkeypatch)
    from backend.services import casino_revenue_report

    out = casino_revenue_report.reconcile_check()
    assert out["success"] is True
    assert out["ok"] is True


def test_rg_status_for_user():
    from backend.services.casino_responsible_gaming import status_for_user

    r = status_for_user("test_rg_user", "coins")
    assert r.get("success") is True
    assert "session_loss" in r
    assert r.get("currency") == "coins"


def test_ideas_slice_routes(tmp_path, monkeypatch):
    from flask import Flask
    from backend.routes.casino_routes import casino_bp

    log_dir = _tmp_logs(tmp_path, monkeypatch)
    _seed_multiplier_bet(log_dir)

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(casino_bp)

    with app.test_client() as client:
        hof = client.get("/api/casino/big-wins/hall-of-fame?limit=3")
        assert hof.status_code == 200
        assert hof.get_json()["success"] is True

        sod = client.get("/api/casino/slot-of-the-day")
        assert sod.status_code == 200
        assert sod.get_json().get("slot")

        rg = client.get("/api/casino/responsible-gaming/status?user_id=u1")
        assert rg.status_code == 200
        assert rg.get_json()["success"] is True

        recon = client.get("/api/casino/revenue/reconcile")
        assert recon.status_code == 200
        assert recon.get_json()["success"] is True

        audit = client.get("/api/casino/shop/rtp-audit")
        assert audit.status_code == 200
        assert audit.get_json()["ok"] is True

        ref_lb = client.get("/api/casino/social/referral/leaderboard")
        assert ref_lb.status_code == 200
        assert ref_lb.get_json()["success"] is True

        news = client.get("/api/casino/news/platform?limit=3")
        assert news.status_code == 200
        assert news.get_json()["success"] is True
