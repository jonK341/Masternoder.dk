"""Landing monitor action learn/store/reel + category FX sounds."""
from __future__ import annotations

from flask import Flask


def test_categorize_and_record(tmp_path, monkeypatch):
    from backend.services import landing_monitor_actions_service as acts

    monkeypatch.setattr(acts, "_ACTIONS_PATH", str(tmp_path / "actions.json"))
    monkeypatch.setattr(acts, "_LEARN_PATH", str(tmp_path / "learn.json"))

    assert acts.categorize("mn2_deposit") == "wallet"
    assert acts.categorize("battle_win") == "battle"
    assert acts.categorize("video_generator_done") == "generator"

    r1 = acts.record_action("mn2_deposit", title="Deposit MN2", text="user deposited")
    assert r1["success"] is True
    assert r1["action"]["category"] == "wallet"
    assert r1["action"]["fx"]["sound"] == "coin_sparkle"
    assert r1["action"]["played"] is False

    r2 = acts.record_action("battle_win", title="Battle win")
    assert r2["action"]["fx"]["sound"] == "impact_blast"

    listed = acts.list_actions(limit=10)
    assert listed["count"] >= 2

    learn = acts.learning_snapshot()["learning"]
    assert learn["total_actions"] >= 2
    assert "wallet" in learn["categories"]
    assert learn["categories"]["wallet"]["count"] >= 1

    reel = acts.build_reel(limit=10)
    assert reel["count"] >= 2
    assert reel["reel"][0]["fx"]["sound"]
    assert reel["reel"][0]["scene_ms"] > 0

    marked = acts.mark_played([r1["action"]["id"]])
    assert marked["marked"] == 1
    again = acts.list_actions(unplayed_only=True)
    ids = {a["id"] for a in again["actions"]}
    assert r1["action"]["id"] not in ids


def test_record_dedupes_same_ts(tmp_path, monkeypatch):
    from backend.services import landing_monitor_actions_service as acts

    monkeypatch.setattr(acts, "_ACTIONS_PATH", str(tmp_path / "actions.json"))
    monkeypatch.setattr(acts, "_LEARN_PATH", str(tmp_path / "learn.json"))

    a = acts.record_action("discord_post", ts="2026-01-01T00:00:00Z", text="hi")
    b = acts.record_action("discord_post", ts="2026-01-01T00:00:00Z", text="hi")
    assert a["action"]["id"] == b["action"]["id"]
    assert b.get("deduped") is True
    assert acts.list_actions()["count"] == 1


def test_actions_routes(tmp_path, monkeypatch):
    from backend.routes.landing_monitor_routes import landing_monitor_bp
    from backend.services import landing_monitor_actions_service as acts

    monkeypatch.setattr(acts, "_ACTIONS_PATH", str(tmp_path / "actions.json"))
    monkeypatch.setattr(acts, "_LEARN_PATH", str(tmp_path / "learn.json"))

    app = Flask(__name__)
    app.register_blueprint(landing_monitor_bp)
    c = app.test_client()

    post = c.post(
        "/api/landing/monitor/actions",
        json={"type": "shop_purchase", "title": "Bought item", "text": "wallet shop"},
    )
    assert post.status_code == 201
    body = post.get_json()
    assert body["action"]["category"] == "wallet"
    assert body["action"]["fx"]["sound"] == "coin_sparkle"

    get = c.get("/api/landing/monitor/actions")
    assert get.status_code == 200
    assert get.get_json()["count"] >= 1

    reel = c.get("/api/landing/monitor/reel")
    assert reel.status_code == 200
    assert reel.get_json()["count"] >= 1

    learn = c.get("/api/landing/monitor/learning")
    assert learn.status_code == 200
    assert learn.get_json()["learning"]["total_actions"] >= 1

    played = c.post("/api/landing/monitor/played", json={"ids": [body["action"]["id"]]})
    assert played.status_code == 200
    assert played.get_json()["marked"] == 1


def test_snapshot_includes_reel(tmp_path, monkeypatch):
    from backend.services import landing_monitor_actions_service as acts
    from backend.services import landing_monitor_service as svc

    monkeypatch.setattr(acts, "_ACTIONS_PATH", str(tmp_path / "actions.json"))
    monkeypatch.setattr(acts, "_LEARN_PATH", str(tmp_path / "learn.json"))
    monkeypatch.setattr(svc, "_CACHE_PATH", str(tmp_path / "cache.json"))
    monkeypatch.setattr(
        svc,
        "_collect_stats",
        lambda: {
            "total_videos": 1,
            "total_users": 1,
            "total_achievements": 0,
            "total_battles": 0,
            "mn2_usd_price": 0.02,
            "daemon_ok": None,
            "block_height": None,
        },
    )
    monkeypatch.setattr(acts, "sync_from_activity", lambda limit=30: {"imported": 0})

    acts.record_action("video_clip_ready", title="Clip ready")
    payload = svc.refresh_snapshot(force=True)
    assert payload["success"] is True
    assert "reel" in payload
    assert "learning" in payload
    assert payload["reel_count"] >= 1
    assert payload["reel"][0]["fx"]["sound"] == "whoosh_rise"
