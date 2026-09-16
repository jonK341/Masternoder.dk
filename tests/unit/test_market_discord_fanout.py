"""Market Discord fan-out tests."""
from unittest.mock import patch


def test_market_fanout_skips_small_fill():
    from backend.services import market_discord_fanout as mdf

    rows = [{
        "type": "p2p_market_fill",
        "channel": "market",
        "ts": "2026-06-17T12:00:00Z",
        "payload": {"mn2": 1.0, "coins": 100, "buyer": "a", "seller": "b"},
    }]
    with patch.object(mdf, "_read_new_events", return_value=(rows, 1)):
        with patch("backend.services.discord_service.post_message") as post:
            result = mdf.run_fanout()
    assert result["success"] is True
    post.assert_not_called()
    assert result["skipped"] >= 1


def test_market_fanout_posts_large_fill():
    from backend.services import market_discord_fanout as mdf

    rows = [{
        "type": "p2p_market_fill",
        "channel": "market",
        "ts": "2026-06-17T12:00:00Z",
        "payload": {"mn2": 10.5, "coins": 500, "buyer": "user1", "seller": "user2", "order_id": "o1"},
    }]
    with patch.object(mdf, "_read_new_events", return_value=(rows, 1)):
        with patch.object(mdf, "_save_cursor"):
            with patch("backend.services.discord_service.post_message", return_value={"success": True}) as post:
                result = mdf.run_fanout()
    assert result["success"] is True
    assert result["posted"] == 1
    post.assert_called_once()
