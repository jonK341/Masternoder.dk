"""Profit pipeline service tests."""
from __future__ import annotations


def test_pipeline_status_minimal(monkeypatch):
    import backend.services.exchange_profit_pair_search_service as pps
    import backend.services.exchange_profit_orchestrator_service as orch

    monkeypatch.setattr(pps, "read_index", lambda: {"hot_symbols": ["BTC"], "hits": [], "updated_at": "t"})
    monkeypatch.setattr(pps, "enabled", lambda: True)
    monkeypatch.setattr(
        "backend.services.exchange_extended_profit_service.read_arb_threshold_state",
        lambda: {"best_net_bps": 10, "threshold_bps": 14, "ready": False},
    )
    monkeypatch.setattr(
        "backend.services.exchange_grid_bot_service.grid_status",
        lambda: {"live": False, "targets_total": 5, "realized_pnl_usd": 0},
    )
    monkeypatch.setattr(
        "backend.services.exchange_stuck_inventory_service.ops_state",
        lambda: {"last_stuck_count": 0},
    )
    monkeypatch.setattr(
        "backend.services.business_control_preflight_service.run_preflight",
        lambda **kw: {"success": True, "failed": []},
    )

    out = orch.pipeline_status(light=True)
    assert out["success"] is True
    assert out["pair_search"]["hot_symbols"] == ["BTC"]
