"""PayPal-focused profit daemon profile (low CPU)."""
from __future__ import annotations


def test_paypal_profile_intervals_disable_fast_and_grid():
    from scripts.all_profit_daemons import PROFILE_INTERVALS, _loop_interval, _resolve_intervals

    iv = _resolve_intervals("paypal", PROFILE_INTERVALS["paypal"])
    assert iv["fast"] == 0
    assert iv["grid"] == 0
    assert _loop_interval("EXCHANGE_GRID_INTERVAL", iv, "grid", 30) == 0


def test_pair_search_throttle_uses_index(monkeypatch):
    from backend.services import exchange_profit_pair_search_service as pps

    monkeypatch.setenv("EXCHANGE_PAIR_SEARCH_MIN_INTERVAL_SEC", "300")
    monkeypatch.setattr(pps, "enabled", lambda: True)
    monkeypatch.setattr(
        pps,
        "read_index",
        lambda: {"updated_at": pps._iso(), "hot_symbols": ["BTC/USDT"], "hits": []},
    )
    out = pps.run_profit_pair_search()
    assert out.get("success") is True
    assert out.get("throttled") is True
    assert out.get("hot_symbols") == ["BTC/USDT"]
