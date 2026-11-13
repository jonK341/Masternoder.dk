"""Unit tests for datamaxi playbook, funding basis, and precision swing."""
from __future__ import annotations


def test_precision_swing_floor_pivots():
    from backend.services.exchange_precision_swing_service import floor_pivot_levels, classify_trend

    lv = floor_pivot_levels(high=110.0, low=100.0, close=105.0)
    assert lv["pivot"] == 105.0
    assert lv["r1"] == 110.0
    assert lv["s1"] == 100.0
    bars = [{"close": x, "high": x + 1, "low": x - 1, "open": x} for x in range(10, 20)]
    assert classify_trend(bars) == "up"


def test_precision_swing_tick_mocked(monkeypatch, tmp_path):
    from backend.services import exchange_precision_swing_service as swing

    monkeypatch.setenv("PRECISION_SWING_ENABLED", "1")
    monkeypatch.setenv("PRECISION_SWING_SYMBOLS", "BTCUSDT")
    monkeypatch.setattr(swing, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(swing, "_LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(swing, "_LEVELS_PATH", str(tmp_path / "levels.json"))
    monkeypatch.setattr(
        swing,
        "fetch_daily_ohlc",
        lambda symbol, limit=30: [
            {"open": 90 + i, "high": 95 + i, "low": 88 + i, "close": 92 + i} for i in range(12)
        ],
    )
    out = swing.run_precision_swing_tick(force=True)
    assert out["success"] is True
    assert out["count"] == 1
    assert out["top"]["ok"] is True
    assert "pivot" in (out["top"].get("levels") or {})


def test_funding_basis_score_actionable():
    from backend.services.exchange_funding_basis_arm_service import score_basis_row

    row = score_basis_row(
        {
            "symbol": "BTCUSDT",
            "markPrice": "101000",
            "indexPrice": "100000",
            "lastFundingRate": "0.001",  # 0.1% / 8h → high APR
        }
    )
    assert row["symbol"] == "BTCUSDT"
    assert row["basis_bps"] == 100.0
    assert row["funding_apr_pct"] > 50
    assert row["actionable"] is True
    assert row["side"] == "long_spot_short_perp"


def test_funding_basis_tick_handles_api_error(monkeypatch, tmp_path):
    from backend.services import exchange_funding_basis_arm_service as basis

    monkeypatch.setenv("FUNDING_BASIS_ENABLED", "1")
    monkeypatch.setattr(basis, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(basis, "_LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(basis, "_BOOK_PATH", str(tmp_path / "book.json"))
    monkeypatch.setattr(basis, "fetch_premium_index", lambda symbol=None: (_ for _ in ()).throw(RuntimeError("geo_block")))
    out = basis.run_funding_basis_tick(force=True)
    assert out["success"] is False
    assert "geo_block" in str(out.get("skip_reason") or out.get("error") or "")


def test_datamaxi_playbook_gate_uses_cutting_edge():
    from backend.services.exchange_datamaxi_cex_spread_service import _playbook_gate

    bad = _playbook_gate(
        {"net_bps": 10, "est_profit_usd": 0.01, "mid_skew_bps": 0},
        min_net_bps=25.0,
        min_profit=0.02,
    )
    assert bad["ok"] is False
    assert bad["reason"] == "below_playbook_min_net"

    good = _playbook_gate(
        {
            "net_bps": 40,
            "est_profit_usd": 0.06,
            "mid_skew_bps": 8,
            "buy_ask": 1.001,
            "buy_bid": 1.0,
            "sell_ask": 1.006,
            "sell_bid": 1.005,
        },
        min_net_bps=25.0,
        min_profit=0.02,
    )
    assert good["ok"] is True


def test_datamaxi_tick_local_fallback(monkeypatch, tmp_path):
    from backend.services import exchange_datamaxi_cex_spread_service as dm

    monkeypatch.setenv("DATAMAXI_CEX_SPREAD_ENABLED", "1")
    monkeypatch.setenv("DATAMAXI_MIN_NET_BPS", "20")
    monkeypatch.setattr(dm, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(dm, "_LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(dm, "_BOOK_PATH", str(tmp_path / "book.json"))
    monkeypatch.setattr(dm, "fetch_datamaxi_premium", lambda **kw: {"ok": False, "reason": "no_key", "rows": []})
    monkeypatch.setattr(
        dm,
        "_local_premium_scan",
        lambda **kw: {
            "ok": True,
            "source": "local_bn_nk",
            "rows": [{
                "symbol": "ADA",
                "buy_venue": "binance",
                "sell_venue": "nonkyc",
                "buy_ask": 0.5,
                "buy_bid": 0.499,
                "sell_ask": 0.505,
                "sell_bid": 0.504,
                "net_bps": 45.0,
                "est_profit_usd": 0.07,
                "mid_skew_bps": 10.0,
                "notional_usd": 15.0,
                "profitable": True,
            }],
        },
    )
    monkeypatch.setattr("backend.services.exchange_profit_head_service.set_kill_shot", lambda s: None)
    monkeypatch.setattr("backend.services.exchange_profit_head_service.set_prefund_hint", lambda h: None)
    out = dm.run_datamaxi_cex_spread_tick(force=True)
    assert out["success"] is True
    assert out["qualifying_count"] >= 1
    assert out["handed_to_hunter"] is True


def test_profiles_mark_installed():
    from backend.config.profit_trading_profiles import PROFIT_TRADING_PROFILES

    assert PROFIT_TRADING_PROFILES["precision_level_swing"]["fit"] == "installed"
    assert PROFIT_TRADING_PROFILES["hummingbot_spot_perp_basis"]["fit"] == "installed"
    assert PROFIT_TRADING_PROFILES["datamaxi_cex_spread"]["fit"] == "installed"
