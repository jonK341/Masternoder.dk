"""YouTube / OBS trade stream helpers."""
import json

from backend.services import profit_trade_stream_service as pts


def test_append_and_interest(tmp_path, monkeypatch):
    events = tmp_path / "trades.jsonl"
    interest = tmp_path / "interest.json"
    yt = tmp_path / "yt.jsonl"
    monkeypatch.setattr(pts, "_EVENTS_PATH", str(events))
    monkeypatch.setattr(pts, "_INTEREST_PATH", str(interest))
    monkeypatch.setattr(pts, "_YT_BROADCAST", str(yt))

    def write_json(path, data):
        open(path, "w", encoding="utf-8").write(json.dumps(data))

    def read_json(path, default=None):
        import os

        if not os.path.isfile(path):
            return default if default is not None else {}
        return json.loads(open(path, encoding="utf-8").read())

    monkeypatch.setattr(pts.ex, "_write_json", write_json)
    monkeypatch.setattr(pts.ex, "_read_json", read_json)

    pts.append_trade(strategy="ladder", message="Ladder nonkyc open=3", mode="live", delta_usd=0.4)
    rows = pts.recent_trades(limit=5)
    assert len(rows) == 1
    assert rows[0]["strategy"] == "ladder"
    assert yt.is_file()

    st = pts.register_interest(voter="alice")
    assert st["votes"] == 1
    assert st["interested_enough"] is False
    for i in range(4):
        pts.register_interest(voter=f"u{i}")
    st2 = pts.interest_status()
    assert st2["votes"] == 5
    assert st2["interested_enough"] is True
