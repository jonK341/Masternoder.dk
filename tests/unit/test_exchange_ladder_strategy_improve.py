from backend.services.exchange_ladder_strategy_improve import (
    apply_dynamic_level_cap,
    apply_exit_first_sides,
    apply_fee_table_to_cfg,
    filter_symbols_by_ppp_edge,
    refresh_venue_fees,
    top_up_nonkyc_quote,
    top_up_venue_quote,
)


def test_dynamic_level_cap_shrinks_when_quote_thin():
    cfg = {"levels": 10, "order_usd": 5.0, "quote_reserve": 5.0, "sides": ["buy", "sell"], "max_open_orders": 40}
    out = apply_dynamic_level_cap(cfg, free_quote=6.0)  # usable=1 < 2*order
    assert out["_dynamic_cap"]["thin"] is True
    assert out["levels"] < 10
    assert out["max_open_orders"] <= 40
    assert out["_dynamic_cap"]["buy_slots"] == 0
    fat = apply_dynamic_level_cap(cfg, free_quote=50.0)
    assert fat["_dynamic_cap"]["thin"] is False
    assert fat["levels"] == 10


def test_fee_table_raises_exit_bps_when_too_tight(tmp_path, monkeypatch):
    from backend.services import exchange_ladder_strategy_improve as imp

    monkeypatch.setattr(imp, "_FEE_PATH", str(tmp_path / "fees.json"))
    refresh_venue_fees(force=True)
    cfg = {"fee_bps": 1.0, "exit_bps": 5.0, "min_exit_bps": 1.0}
    out = apply_fee_table_to_cfg(cfg, "binance")
    assert out["exit_bps"] >= 2 * out["fee_bps"]


def test_ppp_filter_fallback_keeps_symbols(monkeypatch):
    import backend.services.exchange_ladder_strategy_improve as m

    def boom(*_a, **_k):
        raise RuntimeError("no ppp")

    monkeypatch.setattr(
        "backend.services.exchange_profit_path_service.profit_path_summary",
        boom,
        raising=False,
    )
    out = m.filter_symbols_by_ppp_edge({"symbols": ["XRP", "ALGO"]})
    assert out["symbols"] == ["XRP", "ALGO"]
    assert out.get("_ppp_filter", {}).get("fallback") or out["symbols"]


def test_topup_dry_run_without_creds(monkeypatch):
    from backend.services import exchange_ladder_strategy_improve as imp

    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.venue_has_credentials",
        lambda _v: False,
    )
    out = top_up_nonkyc_quote(dry_run=True)
    assert out["success"] is False
    out_bn = top_up_venue_quote("binance", quote="USDC", dry_run=True)
    assert out_bn["success"] is False
    assert out_bn["venue"] == "binance"


def test_topup_venue_quote_skips_when_funded(monkeypatch):
    from backend.services import exchange_ladder_strategy_improve as imp

    monkeypatch.setattr(imp, "venue_has_credentials", lambda _v: True)
    monkeypatch.setattr(imp, "parse_spot_balances", lambda *_a, **_k: {"USDC": 40.0, "XRP": 10.0})
    out = top_up_venue_quote("binance", quote="USDC", min_quote_usd=12.0, dry_run=True)
    assert out["skipped"] is True
    assert out["quote"] == "USDC"
    assert out["free"] == 40.0


def test_exit_first_strips_buys_when_quote_thin():
    cfg = {"sides": ["buy", "sell"], "order_usd": 3.5}
    thin = apply_exit_first_sides(cfg, free_quote=2.0)
    assert thin["_exit_first"]["active"] is True
    assert "buy" not in thin["sides"]
    assert "sell" in thin["sides"]
    fat = apply_exit_first_sides(cfg, free_quote=20.0)
    assert fat["_exit_first"]["active"] is False
    assert "buy" in fat["sides"]


def test_reduce_notional_cap_fits_free_quote():
    from backend.services.exchange_swap_rotation_service import _reduce_notional_action

    act = _reduce_notional_action("binance", "USDC", 6.0, 25.0, score=1.0)
    assert act["suggested_notional_usd"] <= 6.0
    assert act["suggested_notional_usd"] >= 5.0
