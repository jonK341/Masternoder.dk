"""YouTube / Discord / OBS trade stream helpers."""
import json

from backend.services import profit_trade_stream_service as pts


def test_append_and_triple_audience_interest(tmp_path, monkeypatch):
    events = tmp_path / "trades.jsonl"
    interest = tmp_path / "interest.json"
    yt = tmp_path / "yt.jsonl"
    monkeypatch.setattr(pts, "_EVENTS_PATH", str(events))
    monkeypatch.setattr(pts, "_INTEREST_PATH", str(interest))
    monkeypatch.setattr(pts, "_YT_BROADCAST", str(yt))
    monkeypatch.setenv("PROFIT_YT_STREAM_INTEREST_MIN", "3")
    monkeypatch.setenv("PROFIT_YT_STREAM_SUB_INTEREST_MIN", "2")
    monkeypatch.setenv("PROFIT_YT_STREAM_DISCORD_INTEREST_MIN", "2")

    def write_json(path, data):
        open(path, "w", encoding="utf-8").write(json.dumps(data))

    def read_json(path, default=None):
        import os

        if not os.path.isfile(path):
            return default if default is not None else {}
        return json.loads(open(path, encoding="utf-8").read())

    monkeypatch.setattr(pts.ex, "_write_json", write_json)
    monkeypatch.setattr(pts.ex, "_read_json", read_json)
    monkeypatch.setattr(pts, "_is_known_subscriber", lambda uid: uid == "sub1")

    pts.append_trade(strategy="ladder", message="Ladder nonkyc open=3", mode="live", delta_usd=0.4)
    assert pts.recent_trades(limit=5)[0]["strategy"] == "ladder"

    pts.register_interest(voter="alice", audience="local")
    pts.register_interest(voter="bob", audience="youtube_subscriber", user_id="sub1")
    st = pts.interest_status()
    assert st["discord_votes"] == 0
    assert st["interested_enough"] is False

    pts.register_interest(voter="d1", audience="discord", discord_id="111")
    pts.register_interest(voter="d2", audience="discord", discord_id="222")
    st2 = pts.interest_status()
    assert st2["discord_votes"] == 2
    assert st2["audiences"]["discord"]["interested_enough"] is True
    assert st2["interested_enough"] is True


def test_discord_slash_streamvote(monkeypatch):
    from backend.services import discord_controller_service as dc

    monkeypatch.setattr(
        "backend.services.profit_trade_stream_service.register_interest",
        lambda **k: {"registered": True, "audience": "discord"},
    )
    monkeypatch.setattr(
        "backend.services.profit_trade_stream_service.interest_status",
        lambda: {
            "interested_enough": False,
            "local_votes": 0,
            "subscriber_votes": 0,
            "local_threshold": 5,
            "subscriber_threshold": 5,
            "audiences": {"discord": {"votes": 1, "threshold": 5}},
        },
    )
    out = dc.handle_slash_command("streamvote", "999888777")
    assert out["type"] == 4
    assert "Trade stream vote counted" in out["data"]["content"]
