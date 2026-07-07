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


def test_allow_sell_existing_default_true(grid, tmp_path, monkeypatch):
    # A config that omits the flag should default it to True (opt-out switch).
    import json
    p = tmp_path / "noflag.json"
    p.write_text(json.dumps({"enabled": True, "venue": "binance", "assets": ["DOGE"]}),
                 encoding="utf-8")
    monkeypatch.setattr(grid, "_CFG_PATH", str(p))
    assert grid.load_config()["allow_sell_existing_inventory"] is True


def test_sell_from_existing_seeds_sell_orders(grid, tmp_path, monkeypatch):
    import json
    p = tmp_path / "sellexist.json"
    p.write_text(json.dumps({
        "enabled": True, "venue": "binance", "assets": ["DOGE"],
        "grid_levels": 2, "grid_step_pct": 0.01, "order_size_usd": 6.0,
        "max_inventory_usd": 15.0, "hard_loss_cap_usd": 5.0, "min_notional_usd": 5.0,
        "taker_fee_bps": 0.0, "maker_fee_bps": 0.0,
        "allow_sell_existing_inventory": True,
    }), encoding="utf-8")
    monkeypatch.setattr(grid, "_CFG_PATH", str(p))

    # Bot has NO accumulated inventory but holds plenty of DOGE on the venue -> sells are seeded.
    r = grid.run_grid_tick("binance", "DOGE", mid=0.10, dry_run=True, spot_free_base=1000.0)
    assert r["success"]
    st = grid._read_state()[grid._key("binance", "DOGE")]
    sells = [o for o in st["open_orders"] if o["side"] == "sell"]
    assert len(sells) == 2  # both sell levels seeded from existing coin
    assert all(o.get("is_existing_inv_sell") for o in sells)


def test_sell_from_existing_disabled_skips_sells(grid, tmp_path, monkeypatch):
    import json
    p = tmp_path / "nosell.json"
    p.write_text(json.dumps({
        "enabled": True, "venue": "binance", "assets": ["DOGE"],
        "grid_levels": 2, "grid_step_pct": 0.01, "order_size_usd": 6.0,
        "max_inventory_usd": 15.0, "hard_loss_cap_usd": 5.0, "min_notional_usd": 5.0,
        "taker_fee_bps": 0.0, "maker_fee_bps": 0.0,
        "allow_sell_existing_inventory": False,
    }), encoding="utf-8")
    monkeypatch.setattr(grid, "_CFG_PATH", str(p))
    r = grid.run_grid_tick("binance", "DOGE", mid=0.10, dry_run=True, spot_free_base=1000.0)
    st = grid._read_state()[grid._key("binance", "DOGE")]
    sells = [o for o in st["open_orders"] if o["side"] == "sell"]
    assert sells == []  # no bot inventory + flag off -> no sells


def test_sell_from_existing_budget_limits_orders(grid, tmp_path, monkeypatch):
    import json
    p = tmp_path / "budget.json"
    p.write_text(json.dumps({
        "enabled": True, "venue": "binance", "assets": ["DOGE"],
        "grid_levels": 3, "grid_step_pct": 0.01, "order_size_usd": 6.0,
        "max_inventory_usd": 15.0, "hard_loss_cap_usd": 5.0, "min_notional_usd": 5.0,
        "taker_fee_bps": 0.0, "maker_fee_bps": 0.0,
        "allow_sell_existing_inventory": True,
    }), encoding="utf-8")
    monkeypatch.setattr(grid, "_CFG_PATH", str(p))
    # mid 0.10, order_size $6 -> 60 DOGE per sell. Only 90 DOGE free -> at most 1 full sell level.
    r = grid.run_grid_tick("binance", "DOGE", mid=0.10, dry_run=True, spot_free_base=90.0)
    st = grid._read_state()[grid._key("binance", "DOGE")]
    sells = [o for o in st["open_orders"] if o["side"] == "sell"]
    assert len(sells) == 1


def test_existing_inv_sell_books_only_grid_edge(grid):
    # Selling existing coin books only (fill - reference), not the coin's principal value.
    st = grid._new_asset_state()
    realized = grid.apply_fill(
        st, {"side": "sell", "price": 0.11, "size_base": 100.0,
             "is_existing_inv_sell": True, "existing_ref_px": 0.10},
        fee_bps=0.0)
    assert realized == pytest.approx(100.0 * (0.11 - 0.10))  # $1 edge, not $11 principal
    assert st["inventory_base"] == pytest.approx(0.0)  # does not touch avg-cost book
    assert st["realized_pnl_usd"] == pytest.approx(1.0)


def test_sell_from_existing_full_cycle_profit(grid, tmp_path, monkeypatch):
    import json
    p = tmp_path / "cycle.json"
    p.write_text(json.dumps({
        "enabled": True, "venue": "binance", "assets": ["DOGE"],
        "grid_levels": 1, "grid_step_pct": 0.02, "order_size_usd": 6.0,
        "max_inventory_usd": 100.0, "hard_loss_cap_usd": 50.0, "min_notional_usd": 5.0,
        "taker_fee_bps": 0.0, "maker_fee_bps": 0.0,
        "allow_sell_existing_inventory": True,
    }), encoding="utf-8")
    monkeypatch.setattr(grid, "_CFG_PATH", str(p))
    # Tick 1: seed sell against existing coin at mid 0.10 -> sell resting at 0.102
    grid.run_grid_tick("binance", "DOGE", mid=0.10, dry_run=True, spot_free_base=1000.0)
    # Tick 2: price rises to 0.103 -> existing sell fills, booking the 2% edge
    r2 = grid.run_grid_tick("binance", "DOGE", mid=0.103, dry_run=True,
                            simulate_fill_mid=0.103, spot_free_base=1000.0)
    assert r2["fills_this_tick"] >= 1
    assert r2["realized_pnl_usd"] > 0  # grid edge booked
    key = grid._key("binance", "DOGE")
    # A paired buy was placed one step below the sell fill.
    buys = [o for o in grid._read_state()[key]["open_orders"] if o["side"] == "buy"]
    assert len(buys) >= 1


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
