"""Unit tests for strategy categories, momentum, VWAP, and enrichment."""
from __future__ import annotations


def test_four_strategy_categories():
    from backend.config.profit_strategy_categories import STRATEGY_CATEGORIES, list_categories

    cats = list_categories()
    ids = {c["id"] for c in cats}
    assert ids == {"arbitrage", "momentum", "vwap", "grid"}
    assert "hunter" in STRATEGY_CATEGORIES["arbitrage"]["limbs"]
    assert "momentum" in STRATEGY_CATEGORIES["momentum"]["limbs"]
    assert "vwap" in STRATEGY_CATEGORIES["vwap"]["limbs"]
    assert "grid" in STRATEGY_CATEGORIES["grid"]["limbs"]


def test_profiles_tagged_with_categories():
    from backend.config.profit_trading_profiles import PROFIT_TRADING_PROFILES, strategy_catalog

    assert PROFIT_TRADING_PROFILES["momentum_volume_burst"]["fit"] == "installed"
    assert PROFIT_TRADING_PROFILES["vwap_intraday_levels"]["fit"] == "installed"
    assert PROFIT_TRADING_PROFILES["grid_range_harvest"]["category"] == "grid"
    assert PROFIT_TRADING_PROFILES["spatial_taker_cut"]["category"] == "arbitrage"
    catalog = strategy_catalog()
    assert set(catalog["category_ids"]) == {"arbitrage", "momentum", "vwap", "grid"}


def test_momentum_score_actionable_burst():
    from backend.services.exchange_momentum_arm_service import score_momentum_bars

    # Rising closes + volume spike on last bar
    bars = []
    for i in range(20):
        bars.append({
            "open": 100 + i * 0.1,
            "high": 100.5 + i * 0.1,
            "low": 99.5 + i * 0.1,
            "close": 100 + i * 0.4,
            "volume": 100.0,
        })
    bars[-1]["volume"] = 400.0
    bars[-1]["close"] = bars[-2]["close"] * 1.01
    out = score_momentum_bars(bars, lookback=6, min_return_bps=20.0, min_volume_ratio=1.3, stop_pct=1.5)
    assert out["ok"] is True
    assert out["actionable"] is True
    assert out["bias"] == "long_burst"
    assert out["stop_pct"] == 1.5
    assert out["stop_price"] < out["last_close"]


def test_momentum_tick_mocked(monkeypatch, tmp_path):
    from backend.services import exchange_momentum_arm_service as mom

    monkeypatch.setenv("MOMENTUM_ARM_ENABLED", "1")
    monkeypatch.setenv("MOMENTUM_SYMBOLS", "BTCUSDT")
    monkeypatch.setenv("MOMENTUM_LIVE", "0")
    monkeypatch.setattr(mom, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(mom, "_LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(mom, "_BOARD_PATH", str(tmp_path / "board.json"))

    def _fake_klines(symbol, interval="5m", limit=36):
        rows = []
        for i in range(30):
            rows.append({
                "open": 20000 + i,
                "high": 20100 + i,
                "low": 19900 + i,
                "close": 20050 + i * 2,
                "volume": 10.0 if i < 29 else 40.0,
            })
        return rows

    monkeypatch.setattr(mom, "fetch_klines", _fake_klines)
    out = mom.run_momentum_tick(force=True)
    assert out["success"] is True
    assert out["category"] == "momentum"
    assert out["count"] == 1


def test_vwap_compute_buy_below():
    from backend.services.exchange_vwap_arm_service import compute_vwap

    bars = []
    for i in range(60):
        # Price drifts down under a higher-volume early session → last below VWAP
        px = 100.0 - i * 0.05
        bars.append({
            "open": px,
            "high": px + 0.2,
            "low": px - 0.2,
            "close": px,
            "volume": 50.0 if i < 20 else 5.0,
        })
    out = compute_vwap(bars)
    assert out["ok"] is True
    assert out["distance_bps"] < 0
    assert out["session_bias"] == "buy_below_vwap"
    assert "bands" in out


def test_vwap_tick_mocked(monkeypatch, tmp_path):
    from backend.services import exchange_vwap_arm_service as vwap

    monkeypatch.setenv("VWAP_ARM_ENABLED", "1")
    monkeypatch.setenv("VWAP_SYMBOLS", "ETHUSDT")
    monkeypatch.setattr(vwap, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(vwap, "_LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(vwap, "_LEVELS_PATH", str(tmp_path / "levels.json"))

    def _fake_bars(symbol, limit=240):
        rows = []
        for i in range(80):
            px = 3000.0 + (i % 5) * 0.5
            rows.append({"open": px, "high": px + 1, "low": px - 1, "close": px, "volume": 12.0})
        return rows

    monkeypatch.setattr(vwap, "fetch_minute_bars", _fake_bars)
    out = vwap.run_vwap_tick(force=True)
    assert out["success"] is True
    assert out["category"] == "vwap"
    assert out["count"] == 1
    assert out["top"]["ok"] is True


def test_enrich_deal_attaches_strategy_block(monkeypatch, tmp_path):
    from backend.services import exchange_strategy_enrichment_service as enrich
    from backend.services import exchange_momentum_arm_service as mom
    from backend.services import exchange_vwap_arm_service as vwap

    monkeypatch.setattr(mom, "_BOARD_PATH", str(tmp_path / "mom_board.json"))
    monkeypatch.setattr(vwap, "_LEVELS_PATH", str(tmp_path / "vwap_levels.json"))
    from backend.services import crypto_exchange_service as ex

    ex._write_json(
        mom._BOARD_PATH,
        {
            "rows": [{
                "symbol": "ADAUSDT",
                "ok": True,
                "momentum_score": 80.0,
                "return_bps": 40.0,
                "volume_ratio": 2.0,
                "stop_pct": 1.5,
                "stop_price": 0.5,
                "bias": "long_burst",
                "actionable": True,
            }],
            "top": {
                "symbol": "ADAUSDT",
                "ok": True,
                "momentum_score": 80.0,
                "return_bps": 40.0,
                "volume_ratio": 2.0,
                "stop_pct": 1.5,
                "stop_price": 0.5,
                "bias": "long_burst",
                "actionable": True,
            },
        },
    )
    ex._write_json(
        vwap._LEVELS_PATH,
        {
            "levels": [{
                "symbol": "ADAUSDT",
                "ok": True,
                "vwap": 0.55,
                "distance_bps": -12.0,
                "session_bias": "buy_below_vwap",
                "bands": {"upper_1": 0.56, "lower_1": 0.54},
                "support": 0.54,
                "resistance": 0.56,
            }],
            "top": {
                "symbol": "ADAUSDT",
                "ok": True,
                "vwap": 0.55,
                "distance_bps": -12.0,
                "session_bias": "buy_below_vwap",
                "bands": {"upper_1": 0.56, "lower_1": 0.54},
                "support": 0.54,
                "resistance": 0.56,
            },
        },
    )
    row = enrich.enrich_deal({"symbol": "ADA", "net_bps": 55.0, "buy_venue": "binance", "sell_venue": "nonkyc"})
    assert row["strategy"]["primary"] == "arbitrage"
    assert "momentum" in row["strategy"]["categories"]
    assert "vwap" in row["strategy"]["categories"]
    assert row["momentum_score"] == 80.0
    assert row["vwap_bias"] == "buy_below_vwap"
