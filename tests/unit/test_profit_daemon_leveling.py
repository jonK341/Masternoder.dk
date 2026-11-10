"""Daemon levels: 20 assignments define a level's vision and next profit move."""
from __future__ import annotations

import json

import pytest


@pytest.fixture
def level_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import profit_daemon_leveling_service as lvl

    data = tmp_path / "crypto_exchange"
    data.mkdir()
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_BASE", str(tmp_path))
    monkeypatch.delenv("PROFIT_DAEMON_ADMIN_KEY", raising=False)
    monkeypatch.delenv("YOUTUBE_VIDEO_ID", raising=False)
    monkeypatch.delenv("YOUTUBE_CHANNEL_URL", raising=False)
    return lvl


def _board(text="set"):
    from backend.services.profit_daemon_leveling_service import blank_assignments

    rows = blank_assignments()
    for row in rows:
        row["text"] = f"{text}-{row['slot']}"
    return rows


def test_twenty_assignments_earn_level_one(level_env):
    lvl = level_env
    saved = lvl.assign_level("See the book", "Buy DOGE on Binance under the fee floor", _board())
    assert saved["earned"] is True
    assert saved["saved_level"] == 1
    assert saved["level"] == 1
    assert saved["defined"] is True
    assert saved["vision"] == "See the book"
    assert saved["next_profit_move"] == "Buy DOGE on Binance under the fee floor"
    assert saved["progress"]["filled"] == 0
    assert saved["editing_level"] == 2
    directive = lvl.active_directive()
    assert directive["level"] == 1
    assert directive["vision"] == "See the book"
    assert len(directive["assignments"]) == 20


def test_partial_board_does_not_earn_a_level(level_env):
    lvl = level_env
    rows = _board()
    rows[4]["text"] = ""
    saved = lvl.assign_level("Vision", "Move", rows)
    assert saved["earned"] is False
    assert saved["level"] == 0
    assert saved["saved_level"] == 1
    assert "venue" in saved["missing"]
    assert lvl.active_directive()["defined"] is False


def test_missing_headline_blocks_the_level(level_env):
    lvl = level_env
    saved = lvl.assign_level("", "Move", _board())
    assert saved["earned"] is False
    assert "vision" in saved["missing"]
    saved = lvl.assign_level("Vision", "  ", _board())
    assert saved["earned"] is False
    assert "next_profit_move" in saved["missing"]


def test_assignment_count_must_be_twenty(level_env):
    lvl = level_env
    rows = _board()
    with pytest.raises(lvl.LevelInputError) as caught:
        lvl.assign_level("Vision", "Move", rows[:-1])
    assert caught.value.code == "assignments_must_be_20"
    with pytest.raises(lvl.LevelInputError):
        lvl.assign_level("Vision", "Move", rows + [{"slot": 21, "text": "extra"}])


def test_second_complete_board_earns_level_two(level_env):
    lvl = level_env
    first = lvl.assign_level("First vision", "First move", _board("a"))
    assert first["level"] == 1
    second = lvl.assign_level("Second vision", "Second move", _board("b"))
    assert second["earned"] is True
    assert second["saved_level"] == 2
    assert second["level"] == 2
    assert second["vision"] == "Second vision"
    assert second["next_profit_move"] == "Second move"
    assert [row["level"] for row in second["levels"]] == [1, 2]


def test_editing_earned_level_keeps_the_number(level_env):
    lvl = level_env
    lvl.assign_level("First vision", "First move", _board("a"))
    lvl.assign_level("Second vision", "Second move", _board("b"))
    edited = lvl.assign_level("Sharper vision", "Sell the bounce", _board("c"), level=1)
    assert edited["saved_level"] == 1
    assert edited["level"] == 2
    assert edited["levels"][0]["vision"] == "Sharper vision"
    assert edited["levels"][1]["vision"] == "Second vision"
    assert lvl.active_directive()["vision"] == "Second vision"


def test_uneaning_a_level_drops_later_levels(level_env):
    lvl = level_env
    lvl.assign_level("First vision", "First move", _board("a"))
    lvl.assign_level("Second vision", "Second move", _board("b"))
    edited = lvl.assign_level("First vision", "", _board("a"), level=1)
    assert edited["earned"] is False
    assert edited["level"] == 0
    assert [row["level"] for row in edited["levels"]] == [1]


def test_parse_youtube_live_html():
    from backend.services.profit_daemon_leveling_service import parse_youtube_live_html

    live = parse_youtube_live_html(
        '<html><title>Show - YouTube</title>'
        '"title":{"content":"Masternoder2 live"}'
        'BADGE_STYLE_TYPE_LIVE_NOW'
    )
    assert live["live"] is True
    assert live["title"] == "Masternoder2 live"
    assert live["note"] == "Live now."

    offline = parse_youtube_live_html(
        '"title":{"content":"Masternoder2 Livestreaming and crypto channel 5D monitor view"}'
        'Streamed 3 months ago'
    )
    assert offline["live"] is False
    assert "3 months ago" in offline["note"]
    assert "Masternoder2" in offline["title"]


def test_parse_youtube_oembed():
    from backend.services.profit_daemon_leveling_service import parse_youtube_oembed

    meta = parse_youtube_oembed({
        "title": "Masternoder2 Livestreaming and crypto channel 5D monitor view",
        "author_name": "__Jon Ulrik__",
        "author_url": "https://www.youtube.com/@Jon_Ulrik",
    })
    assert meta["author"] == "__Jon Ulrik__"
    assert "Jon_Ulrik" in meta["author_url"]


def test_check_youtube_live_uses_injected_fetch(level_env):
    lvl = level_env
    pages = {
        "oembed": json.dumps({
            "title": "Masternoder2 Livestreaming and crypto channel 5D monitor view",
            "author_name": "__Jon Ulrik__",
            "author_url": "https://www.youtube.com/@Jon_Ulrik",
        }),
        "live": '"title":{"content":"Masternoder2 Livestreaming and crypto channel 5D monitor view"} Streamed 3 months ago',
    }

    def fetch(url):
        if "oembed" in url:
            return pages["oembed"]
        return pages["live"]

    result = lvl.check_youtube_live(fetch=fetch)
    assert result["live"] is False
    assert result["video_id"] == "-iSYSBSn_8E"
    assert result["author"] == "__Jon Ulrik__"
    assert "3 months ago" in result["note"]
    again = lvl.snapshot()
    assert again["youtube"]["live"] is False


def test_level_route_round_trip(level_env):
    from flask import Flask

    from backend.routes.profit_daemon_routes import profit_daemon_bp

    app = Flask(__name__)
    app.register_blueprint(profit_daemon_bp)
    client = app.test_client()
    empty = client.get("/api/profit-daemon/level")
    assert empty.status_code == 200
    assert empty.get_json()["level"] == 0
    assert len(empty.get_json()["slots"]) == 20

    saved = client.post(
        "/api/profit-daemon/level",
        json={
            "vision": "Show the book",
            "next_profit_move": "Quote DOGE tighter",
            "assignments": _board(),
        },
    )
    assert saved.status_code == 200
    body = saved.get_json()
    assert body["earned"] is True
    assert body["level"] == 1

    short = client.post(
        "/api/profit-daemon/level",
        json={"vision": "x", "next_profit_move": "y", "assignments": _board()[:3]},
    )
    assert short.status_code == 400
    assert short.get_json()["error"] == "assignments_must_be_20"
