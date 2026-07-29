"""Unified trading ops — stuck inventory + portal micro-chain (offline)."""
from __future__ import annotations


def test_recalculate_options_empty(monkeypatch):
    import backend.services.exchange_grid_bot_service as grid
    import backend.services.exchange_swap_rotation_service as rot
    from backend.services import exchange_stuck_inventory_service as stuck

    monkeypatch.setattr(grid, "rank_profit_pairs", lambda **kw: [])
    monkeypatch.setattr(grid, "scan_cross_venue_differences", lambda **kw: {"differences": []})
    monkeypatch.setattr(rot, "suggest_swap_actions", lambda **kw: {"actions": []})

    out = stuck.recalculate_options([])
    assert out["success"] is True
    assert out["plan_count"] == 0


def test_monitor_5d_pulse_emit():
    from backend.services.monitor_5d_pulse_service import emit_pulse, recent

    r = emit_pulse("Test unified pulse", summary="unit test", source="test")
    assert r.get("success") is True
    items = recent(limit=5).get("items") or []
    assert any("Test unified pulse" in (i.get("title") or "") for i in items)
