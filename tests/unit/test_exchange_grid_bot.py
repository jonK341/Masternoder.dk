"""Grid/market-maker bot: grid math, fill reconciliation, risk caps, and paper end-to-end."""
import json
import pytest


@pytest.fixture
def grid(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_grid_bot_service as g

    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(g, "_STATE_PATH", str(data / "grid_bot_state.json"))
    monkeypatch.setattr(g, "_LEDGER_PATH", str(data / "grid_bot_ledger.jsonl"))

    cfg_path = tmp_path / "grid_cfg.json"
    cfg_path.write_text(json.dumps({
        "enabled": True, "venue": "binance", "assets": ["DOGE"],
        "grid_levels": 2, "grid_step_pct": 0.01, "order_size_usd": 6.0,
        "max_inventory_usd": 15.0, "hard_loss_cap_usd": 5.0,
        "min_spread_bps": 8.0, "min_vol_pct": 0.5,
        "taker_fee_bps": 0.0, "maker_fee_bps": 0.0,
    }), encoding="utf-8")
    monkeypatch.setattr(g, "_CFG_PATH", str(cfg_path))
    return g


def test_load_config_clamps_bad_values(grid, tmp_path, monkeypatch):
    import json
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"grid_levels": 0, "grid_step_pct": 0, "order_size_usd": -3,
                             "hard_loss_cap_usd": -1, "min_notional_usd": -2}), encoding="utf-8")
    monkeypatch.setattr(grid, "_CFG_PATH", str(p))
    cfg = grid.load_config()
    assert cfg["grid_levels"] >= 1
    assert cfg["grid_step_pct"] > 0
    assert cfg["order_size_usd"] >= 1.0
    assert cfg["hard_loss_cap_usd"] >= 0.0
    assert cfg["min_notional_usd"] >= 0.0


def test_min_notional_skips_dust_orders(grid, tmp_path, monkeypatch):
    import json
    p = tmp_path / "mn.json"
    # order size $6 but min notional $50 -> every grid order is below min -> none placed
    p.write_text(json.dumps({"enabled": True, "venue": "binance", "assets": ["DOGE"],
                             "grid_levels": 2, "grid_step_pct": 0.01, "order_size_usd": 6.0,
                             "max_inventory_usd": 100.0, "hard_loss_cap_usd": 50.0,
                             "min_notional_usd": 50.0}), encoding="utf-8")
    monkeypatch.setattr(grid, "_CFG_PATH", str(p))
    r = grid.run_grid_tick("binance", "DOGE", mid=100.0, dry_run=True)
    assert r["open_orders"] == 0  # all below the $50 min notional


def test_compute_grid_orders(grid):
    cfg = grid.load_config()
    orders = grid.compute_grid_orders(100.0, cfg)
    buys = sorted([o["price"] for o in orders if o["side"] == "buy"])
    sells = sorted([o["price"] for o in orders if o["side"] == "sell"])
    assert buys == [98.0, 99.0]
    assert sells == [101.0, 102.0]
    buy99 = next(o for o in orders if o["side"] == "buy" and o["price"] == 99.0)
    assert buy99["size_base"] == pytest.approx(6.0 / 99.0)


def test_apply_fill_buy_then_sell_profit(grid):
    st = grid._new_asset_state()
    grid.apply_fill(st, {"side": "buy", "price": 100.0, "size_base": 1.0}, fee_bps=0.0)
    assert st["inventory_base"] == 1.0
    assert st["avg_cost_usd"] == pytest.approx(100.0)
    realized = grid.apply_fill(st, {"side": "sell", "price": 103.0, "size_base": 1.0}, fee_bps=0.0)
    assert realized == pytest.approx(3.0)
    assert st["inventory_base"] == pytest.approx(0.0)
    assert st["realized_pnl_usd"] == pytest.approx(3.0)


def test_apply_fill_partial_sell(grid):
    st = grid._new_asset_state()
    grid.apply_fill(st, {"side": "buy", "price": 100.0, "size_base": 2.0}, fee_bps=0.0)
    realized = grid.apply_fill(st, {"side": "sell", "price": 110.0, "size_base": 1.0}, fee_bps=0.0)
    assert realized == pytest.approx(10.0)
    assert st["inventory_base"] == pytest.approx(1.0)


def test_risk_check_loss_cap(grid):
    cfg = grid.load_config()
    st = grid._new_asset_state()
    st["inventory_base"] = 1.0
    st["avg_cost_usd"] = 100.0
    rc = grid.risk_check(st, cfg, 90.0)  # unrealized -10 <= -5 cap
    assert rc["halt"] is True
    assert rc["reason"] == "hard_loss_cap"


def test_risk_check_inventory_cap(grid):
    cfg = grid.load_config()
    st = grid._new_asset_state()
    st["inventory_base"] = 1.0
    st["avg_cost_usd"] = 20.0  # so no loss at mid 20
    rc = grid.risk_check(st, cfg, 20.0)  # inventory_usd 20 > max 15
    assert rc["halt"] is True
    assert rc["reason"] == "inventory_cap"


def test_select_assets(grid):
    cfg = grid.load_config()
    cands = [
        {"symbol": "AAA", "bid": 100.0, "ask": 100.2, "vol_pct": 2.0},   # 20 bps, vol ok -> keep
        {"symbol": "BBB", "bid": 100.0, "ask": 100.01, "vol_pct": 2.0},  # 1 bps -> drop
        {"symbol": "CCC", "bid": 100.0, "ask": 100.5, "vol_pct": 0.1},   # vol too low -> drop
    ]
    out = grid.select_assets(cands, cfg)
    assert [c["symbol"] for c in out] == ["AAA"]


def test_run_grid_tick_paper_places_and_fills(grid):
    # Tick 1: place grid at mid 100 (buys only; no inventory yet)
    r1 = grid.run_grid_tick("binance", "DOGE", mid=100.0, dry_run=True)
    assert r1["success"] and r1["mode"] == "paper"
    assert r1["open_orders"] >= 1  # buys placed within inventory cap

    # Tick 2: price drops to 98 -> buy orders fill, inventory accrues
    r2 = grid.run_grid_tick("binance", "DOGE", mid=98.0, dry_run=True, simulate_fill_mid=98.0)
    assert r2["fills_this_tick"] >= 1
    assert r2["inventory_base"] > 0

    # Tick 3: price rises to 103 -> sell orders (placed in tick2) fill, realizing PnL
    r3 = grid.run_grid_tick("binance", "DOGE", mid=103.0, dry_run=True, simulate_fill_mid=103.0)
    assert r3["fills_this_tick"] >= 1
    prof = grid.grid_profit()
    assert prof["total_fills"] >= 2
    # ledger recorded fills
    import os
    assert os.path.isfile(grid._LEDGER_PATH)


def test_run_grid_tick_halts_on_loss_cap(grid):
    # Seed inventory bought high, then price craters below the loss cap
    all_state = {}
    key = grid._key("binance", "DOGE")
    st = grid._new_asset_state()
    st["inventory_base"] = 1.0
    st["avg_cost_usd"] = 100.0
    all_state[key] = st
    grid._write_state(all_state)

    r = grid.run_grid_tick("binance", "DOGE", mid=90.0, dry_run=True)
    assert r["halted"] is True
    assert r["reason"] == "hard_loss_cap"
    assert grid._read_state()[key]["open_orders"] == []
