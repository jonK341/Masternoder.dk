"""Fleet activation tests."""
from __future__ import annotations


def test_activate_fleet_assigns_analytics_symbols():
    from backend.services.trading_bots_control_service import _default_controls
    from backend.services.exchange_fleet_activation_service import activate_fleet_for_profit
    from backend.services.exchange_supervisor_fleet_service import merge_fleet_into_controls

    controls = _default_controls()
    merge_fleet_into_controls(controls)
    res = activate_fleet_for_profit(
        controls,
        hot_symbols=["BTC", "ETH", "DOGE"],
        pair_search={"hits": [{"symbol": "XRP"}], "hit_count": 5},
        enable_dormant=False,
    )
    assert res["success"]
    analytics = [b for b in controls["fleet_bots"] if b.get("kind") == "analytics"]
    assert analytics
    assert analytics[0].get("config", {}).get("symbols")
