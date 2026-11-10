"""YouTube / OBS trade stream helpers."""
import json

from backend.services import profit_trade_stream_service as pts


def test_append_and_dual_audience_interest(tmp_path, monkeypatch):
    events = tmp_path / "trades.jsonl"
    interest = tmp_path / "interest.json"
    yt = tmp_path / "yt.jsonl"
    monkeypatch.setattr(pts, "_EVENTS_PATH", str(events))
    monkeypatch.setattr(pts, "_INTEREST_PATH", str(interest))
    monkeypatch.setattr(pts, "_YT_BROADCAST", str(yt))
    monkeypatch.setenv("PROFIT_YT_STREAM_INTEREST_MIN", "3")
    monkeypatch.setenv("PROFIT_YT_STREAM_SUB_INTEREST_MIN", "2")

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
    rows = pts.recent_trades(limit=5)
    assert len(rows) == 1
    assert rows[0]["strategy"] == "ladder"
    assert yt.is_file()

    st = pts.register_interest(voter="alice", audience="local")
    assert st["local_votes"] == 1
    assert st["subscriber_votes"] == 0
    assert st["interested_enough"] is False

    pts.register_interest(voter="bob", audience="youtube_subscriber", user_id="sub1")
    st2 = pts.interest_status()
    assert st2["subscriber_votes"] == 1
    assert st2["interested_enough"] is False

    pts.register_interest(
        voter="cara",
        audience="youtube_subscriber",
        self_attest_subscriber=True,
    )
    st3 = pts.interest_status()
    assert st3["subscriber_votes"] == 2
    assert st3["audiences"]["youtube_subscriber"]["interested_enough"] is True
    assert st3["interested_enough"] is True


def test_legacy_voters_migrate_to_local(tmp_path, monkeypatch):
    interest = tmp_path / "interest.json"
    interest.write_text(json.dumps({"voters": ["old1", "old2"], "votes": 2}), encoding="utf-8")
    monkeypatch.setattr(pts, "_INTEREST_PATH", str(interest))
    monkeypatch.setattr(pts.ex, "_write_json", lambda path, data: open(path, "w", encoding="utf-8").write(json.dumps(data)))
    monkeypatch.setattr(
        pts.ex,
        "_read_json",
        lambda path, default=None: json.loads(open(path, encoding="utf-8").read()) if __import__("os").path.isfile(path) else (default or {}),
    )
    st = pts.interest_status()
    assert st["local_votes"] == 2
