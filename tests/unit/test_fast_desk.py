"""Plain-language lines for the fast USDT desk."""
from backend.services.fast_desk_service import describe_coin, summarize_tick


def test_thin_book_says_how_much_is_there():
    text = describe_coin({
        "symbol": "XLM",
        "decision": "book_too_thin",
        "net_bps": 71.8,
        "executable_usd": 0.29,
    })
    assert "XLM" in text
    assert "71.8 bps" in text
    assert "$0.29" in text
    assert "Waiting" in text


def test_inside_fees_waits():
    text = describe_coin({"symbol": "XRP", "decision": "below_fees", "net_bps": -56.0, "executable_usd": 0})
    assert text.startswith("XRP:")
    assert "inside the fees" in text


def test_summary_names_a_ready_coin():
    text = summarize_tick([
        {"symbol": "XRP", "decision": "below_fees", "net_bps": -10, "executable_usd": 0},
        {"symbol": "SOL", "decision": "paper_candidate", "net_bps": 40, "executable_usd": 30},
    ])
    assert text.startswith("Paper fill ready for SOL.")
    assert "XRP:" in text
