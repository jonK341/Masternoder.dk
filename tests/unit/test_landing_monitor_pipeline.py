"""12-minute interactive AI pipeline — sats recount, no history."""
from __future__ import annotations

from flask import Flask


def test_sats_and_unique_cuts(tmp_path, monkeypatch):
    from backend.services import landing_monitor_pipeline_service as pipe

    monkeypatch.setattr(pipe, "_PIPELINE_PATH", str(tmp_path / "pipeline.json"))
    pipe._CURRENT = {}

    monkeypatch.setattr(
        pipe,
        "collect_sats_snapshot",
        lambda: {
            "success": True,
            "totals": {"network_sats": 1000, "trade_sats": 250, "combined_sats": 1250},
            "network": {"mn2": {"sats": 1000, "coins": 0.00001}, "venue_btc": {"venues": {}}},
            "daemon_trades": {"detail": {"recent_fills": [], "fill_count": 0, "realized_pnl_usd": 0}},
        },
    )

    a = pipe.build_pipeline(force=True, use_llm=False, reason="test_a")
    b = pipe.build_pipeline(force=True, use_llm=False, reason="test_b")
    assert a["success"] is True
    assert a["duration_ms"] == pipe.PIPELINE_MS
    assert a["scene_count"] >= 8
    assert a["persist"] is False
    assert a["interactive"] is True
    # Every forced cut is a different movie.
    assert a["cut_id"] != b["cut_id"]
    assert a["scenes"][0]["id"] != b["scenes"][0]["id"]

    # Same fingerprint within window reuses the current cut (not a new archive).
    c = pipe.build_pipeline(force=False, use_llm=False, reason="get")
    assert c["cut_id"] == b["cut_id"]

    # New stats fingerprint forces a new movie.
    monkeypatch.setattr(
        pipe,
        "collect_sats_snapshot",
        lambda: {
            "success": True,
            "totals": {"network_sats": 9999, "trade_sats": 250, "combined_sats": 10249},
            "network": {"mn2": {"sats": 9999, "coins": 0.0001}, "venue_btc": {"venues": {}}},
            "daemon_trades": {"detail": {"recent_fills": [], "fill_count": 2, "realized_pnl_usd": 1.5}},
        },
    )
    d = pipe.build_pipeline(force=False, use_llm=False, reason="get")
    assert d["regen_reason"] == "stats_changed"
    assert d["cut_id"] != b["cut_id"]

    # Scratch file has metadata only — not a library of scenes.
    scratch = pipe._read_json(str(tmp_path / "pipeline.json"), {})
    assert "scenes" not in scratch
    assert scratch.get("fingerprint")


def test_pipeline_routes(tmp_path, monkeypatch):
    from backend.routes.landing_monitor_routes import landing_monitor_bp
    from backend.services import landing_monitor_pipeline_service as pipe

    monkeypatch.setattr(pipe, "_PIPELINE_PATH", str(tmp_path / "pipeline.json"))
    pipe._CURRENT = {}
    monkeypatch.setattr(
        pipe,
        "collect_sats_snapshot",
        lambda: {
            "success": True,
            "totals": {"network_sats": 10, "trade_sats": 5, "combined_sats": 15},
            "network": {"mn2": {"sats": 10, "coins": 0}, "venue_btc": {"venues": {}}},
            "daemon_trades": {"detail": {"recent_fills": [], "fill_count": 0, "realized_pnl_usd": 0}},
        },
    )

    app = Flask(__name__)
    app.register_blueprint(landing_monitor_bp)
    c = app.test_client()

    sats = c.get("/api/landing/monitor/sats")
    assert sats.status_code == 200
    assert sats.get_json()["totals"]["network_sats"] == 10

    post = c.post("/api/landing/monitor/pipeline", json={"use_llm": False})
    assert post.status_code == 200
    body = post.get_json()
    assert body["duration_ms"] == pipe.PIPELINE_MS
    assert body["persist"] is False
    assert len(body["scenes"]) >= 8

    get = c.get("/api/landing/monitor/pipeline")
    assert get.status_code == 200
    assert get.get_json()["cut_id"] == body["cut_id"]
