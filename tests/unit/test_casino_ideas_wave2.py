"""Tests for casino ideas Wave 2 — seasonal, referral quests, crew LB, VIP, fairness export, SSE."""
import json
import os
import sqlite3

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _tmp_logs(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(log_dir))
    return log_dir


def _seed_fairness_bet(log_dir, user_id="u1", bet_id="bet-f1"):
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
    details = json.dumps({
        "fairness": {
            "server_seed_hash": "abc123hash",
            "client_seed": "client-seed-1",
            "nonce": 42,
        }
    })
    conn.execute(
        "INSERT OR REPLACE INTO casino_bets VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (bet_id, user_id, "crash", "coins", 10, 20, 10, "win",
         "2026-06-28T12:00:00Z", 0, details),
    )
    conn.commit()
    conn.close()


def test_seasonal_slots_active_window():
    import backend.services.casino_service as casino

    out = casino.get_seasonal_slots()
    assert out["success"] is True
    assert out.get("enabled") is True
    assert isinstance(out.get("active_windows"), list)
    assert out.get("count", 0) >= 1


def test_referral_quest_tracking(tmp_path, monkeypatch):
    from backend.services import casino_social_service

    ref_path = tmp_path / "casino_referrals.json"
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    ref_path.write_text(json.dumps({
        "codes": {"MN-ABC": "referrer1"},
        "signups": [{
            "referrer_user_id": "referrer1",
            "referred_user_id": "referee1",
            "referral_code": "MN-ABC",
            "bet_count": 0,
            "tiers_claimed": [],
        }],
    }), encoding="utf-8")
    monkeypatch.setattr(casino_social_service, "_CASINO_REFERRALS_PATH", str(ref_path))

    casino_social_service.track_referral_bet("referee1")
    store = json.loads(ref_path.read_text(encoding="utf-8"))
    row = store["signups"][0]
    assert row["bet_count"] == 1
    assert "bets_1" in row.get("tiers_claimed", [])

    quests = casino_social_service.get_referral_quests("referrer1")
    assert quests["success"] is True
    assert quests["referral_count"] == 1
    assert quests["referrals"][0]["bet_count"] == 1


def test_vip_lounge_locked_by_default():
    import backend.services.casino_service as casino

    out = casino.get_vip_lounge("wave2_new_user")
    assert out["success"] is True
    assert out.get("enabled") is True
    assert out.get("unlocked") is False
    assert out.get("min_xp") == 5000


def test_fairness_export_csv(tmp_path, monkeypatch):
    log_dir = _tmp_logs(tmp_path, monkeypatch)
    _seed_fairness_bet(log_dir, user_id="export_user")

    import backend.services.casino_service as casino

    audit = casino.export_fairness_audit("export_user", limit=10)
    assert audit["success"] is True
    assert audit["count"] >= 1
    assert audit["rows"][0]["server_seed_hash"] == "abc123hash"
    assert audit["rows"][0]["nonce"] == 42

    csv_body = casino.fairness_audit_csv("export_user", limit=10)
    assert "server_seed_hash" in csv_body
    assert "abc123hash" in csv_body


def test_crew_leaderboard_enhanced_fields():
    import backend.services.casino_service as casino

    out = casino.get_crew_casino_leaderboard("u1", currency="coins")
    assert out["success"] is True
    assert out.get("period") == "week"
    assert "week_key" in out
    assert "since" in out


def test_wave2_routes(tmp_path, monkeypatch):
    from flask import Flask
    from backend.routes.casino_routes import casino_bp

    log_dir = _tmp_logs(tmp_path, monkeypatch)
    _seed_fairness_bet(log_dir, user_id="export_user", bet_id="bet-export-route")

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(casino_bp)

    with app.test_client() as client:
        seasonal = client.get("/api/casino/seasonal/slots")
        assert seasonal.status_code == 200
        assert seasonal.get_json()["success"] is True

        quests = client.get("/api/casino/social/referral/quests?user_id=referrer1")
        assert quests.status_code == 200
        assert quests.get_json()["success"] is True

        crew = client.get("/api/casino/crew/leaderboard?user_id=u1")
        assert crew.status_code == 200
        assert crew.get_json()["success"] is True
        assert crew.get_json().get("week_key")

        vip = client.get("/api/casino/vip/lounge?user_id=u1")
        assert vip.status_code == 200
        assert vip.get_json()["success"] is True

        export_json = client.get("/api/casino/fairness/export?user_id=export_user&format=json")
        assert export_json.status_code == 200
        assert export_json.get_json()["count"] >= 1

        export_csv = client.get("/api/casino/fairness/export?user_id=export_user&limit=5")
        assert export_csv.status_code == 200
        assert b"server_seed_hash" in export_csv.data

        stream = client.get("/api/casino/activity-feed/stream?limit=3&interval=1&max_ticks=1")
        assert stream.status_code == 200
        assert b"text/event-stream" in (stream.content_type or "").encode() or stream.mimetype == "text/event-stream"
        assert b"connected" in stream.data or b"wins" in stream.data


def test_agent_wave2_parity():
    from flask import Flask
    from backend.routes.agent_casino_routes import agent_casino_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(agent_casino_bp)

    with app.test_client() as client:
        seasonal = client.get("/api/agent/casino/seasonal/slots")
        assert seasonal.status_code == 200

        quests = client.get("/api/agent/casino/social/referral/quests?user_id=u1")
        assert quests.status_code == 200

        vip = client.get("/api/agent/casino/vip/lounge?user_id=u1")
        assert vip.status_code == 200

        crew = client.get("/api/agent/casino/crew/leaderboard?user_id=u1")
        assert crew.status_code == 200

        export = client.get("/api/agent/casino/fairness/export?user_id=u1&format=json")
        assert export.status_code == 200

        feed = client.get("/api/agent/casino/activity-feed/stream?limit=5")
        assert feed.status_code == 200
