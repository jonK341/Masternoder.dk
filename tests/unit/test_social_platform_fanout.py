"""Social platform fan-out — Facebook, YouTube, unified hub."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _fanout_tmp(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="spf-test-", dir=os.path.join(os.getcwd(), ".pytest-tmp"))
    events = os.path.join(tmp, "activity_events.jsonl")
    fb_cursor = os.path.join(tmp, "fb_cursor.json")
    yt_cursor = os.path.join(tmp, "yt_cursor.json")
    fb_outbox = os.path.join(tmp, "fb_outbox.jsonl")
    yt_queue = os.path.join(tmp, "yt_queue.jsonl")
    import backend.services.social_platform_fanout_service as svc

    monkeypatch.setattr(svc, "_EVENTS", events)
    monkeypatch.setattr(svc, "_FB_CURSOR", fb_cursor)
    monkeypatch.setattr(svc, "_YT_CURSOR", yt_cursor)
    monkeypatch.setattr(svc, "_FB_OUTBOX", fb_outbox)
    monkeypatch.setattr(svc, "_YT_QUEUE", yt_queue)
    return {"events": events, "fb_outbox": fb_outbox, "yt_queue": yt_queue, "svc": svc, "tmp": tmp}


def test_platform_hub_matrix():
    from backend.services.social_platform_fanout_service import get_platform_hub

    hub = get_platform_hub()
    assert hub["success"] is True
    ids = {p["id"] for p in hub["platforms"]}
    assert ids == {"discord", "facebook", "youtube"}


def test_facebook_fanout_outbox_without_token(monkeypatch):
    paths = _fanout_tmp(monkeypatch)
    svc = paths["svc"]
    with open(paths["events"], "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": "2026-06-24T12:00:00Z",
            "type": "casino_tournament_end",
            "channel": "casino",
            "payload": {"title": "Daily", "pool": 50, "currency": "mn2"},
        }) + "\n")
    result = svc.run_facebook_fanout()
    assert result["posted"] == 1
    with open(paths["fb_outbox"], encoding="utf-8") as f:
        lines = f.read().strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row.get("posted") is False


def test_youtube_fanout_queues(monkeypatch):
    paths = _fanout_tmp(monkeypatch)
    svc = paths["svc"]
    with open(paths["events"], "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": "2026-06-24T12:00:00Z",
            "type": "platform_news",
            "channel": "site",
            "payload": {"title": "Casino v14"},
        }) + "\n")
    result = svc.run_youtube_fanout()
    assert result["queued"] == 1
    with open(paths["yt_queue"], encoding="utf-8") as f:
        assert f.read().strip()


def test_discovery_rotator_dry_run(monkeypatch):
    paths = _fanout_tmp(monkeypatch)
    result = paths["svc"].run_discovery_rotator(platform="facebook", dry_run=True)
    assert result["success"] is True
    assert "message" in result


def test_youtube_subscribe_claim_idempotent(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="yt-test-", dir=os.path.join(os.getcwd(), ".pytest-tmp"))
    claims = os.path.join(tmp, "claims.json")
    import backend.services.youtube_fanout_service as yt

    monkeypatch.setattr(yt, "_CLAIMS_PATH", claims)
    monkeypatch.setattr(
        "backend.services.unified_points_database.unified_points_db.add_points",
        lambda *a, **k: {"success": True},
    )
    first = yt.claim_subscribe_reward("user_yt_1")
    assert first["success"] is True
    second = yt.claim_subscribe_reward("user_yt_1")
    assert second["success"] is False


def test_social_platform_hub_route():
    from flask import Flask
    from backend.routes.social_platform_routes import social_platform_bp

    app = Flask(__name__)
    app.register_blueprint(social_platform_bp)
    with app.test_client() as client:
        resp = client.get("/api/social/platforms/hub")
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert len(data["platforms"]) == 3


def test_discord_fanout_run_route(monkeypatch):
    from flask import Flask
    from backend.routes.discord_routes import discord_bp
    import backend.services.casino_discord_fanout as cdf

    monkeypatch.setattr(cdf, "run_fanout", lambda **kw: {"success": True, "posted": 0})
    app = Flask(__name__)
    app.register_blueprint(discord_bp)
    with app.test_client() as client:
        resp = client.post("/api/discord/fanout/run")
    assert resp.status_code == 403
    with patch.dict("os.environ", {"DISCORD_OPS_SECRET": "test-secret"}):
        with app.test_client() as client:
            resp = client.post(
                "/api/discord/fanout/run",
                json={"channel": "casino", "dry_run": True},
                headers={"X-Ops-Secret": "test-secret"},
            )
    data = resp.get_json()
    assert resp.status_code == 200
    assert data.get("success") is True
