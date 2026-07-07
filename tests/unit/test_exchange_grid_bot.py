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


def _seed_live_state(grid, order_ids):
    """Put resting orders into state as if placed live."""
    all_state = {}
    key = grid._key("binance", "DOGE")
    st = grid._new_asset_state()
    st["inventory_base"] = 10.0  # small, stays under the 15 USD inventory cap at these prices
    st["avg_cost_usd"] = 0.10
    st["open_orders"] = [{"order_id": oid, "side": "sell", "price": 0.11,
                          "size_base": 10.0, "ts": grid._iso()} for oid in order_ids]
    all_state[key] = st
    grid._write_state(all_state)
    return key


def test_live_reconcile_skips_when_book_read_fails(grid, monkeypatch):
    import backend.services.exchange_venue_api_service as vapi
    key = _seed_live_state(grid, ["A", "B", "C"])
    monkeypatch.setattr(grid, "grid_live_enabled", lambda: True)
    # Order-book read fails -> must NOT infer any fills, must keep tracked orders.
    monkeypatch.setattr(vapi, "get_open_orders", lambda *a, **k: {"success": False, "error": "timeout"})
    monkeypatch.setattr(vapi, "place_limit_order", lambda *a, **k: {"success": True, "order_id": "new"})
    monkeypatch.setattr(vapi, "parse_spot_balances", lambda *a, **k: {})
    r = grid.run_grid_tick("binance", "DOGE", mid=0.10)
    assert r["reconcile_note"] == "open_orders_read_failed"
    assert r["fills_this_tick"] == 0  # no phantom fills
    assert r["realized_pnl_usd"] == 0.0
    assert len(grid._read_state()[key]["open_orders"]) == 3  # tracked orders preserved


def test_live_reconcile_drops_rejected_without_phantom_fill(grid, monkeypatch):
    import backend.services.exchange_venue_api_service as vapi
    key = _seed_live_state(grid, ["A", "B", "C"])
    monkeypatch.setattr(grid, "grid_live_enabled", lambda: True)
    # Venue lists only order A as open; B & C disappeared.
    monkeypatch.setattr(vapi, "get_open_orders",
                        lambda *a, **k: {"success": True, "orders": [{"orderId": "A"}]})
    # B was actually FILLED; C was REJECTED/never rested.
    def _status(venue, asset, oid, **k):
        if str(oid) == "B":
            return {"success": True, "filled": True, "resting": False}
        return {"success": True, "filled": False, "resting": False}  # C: gone, not filled
    monkeypatch.setattr(vapi, "get_order_status", _status)
    monkeypatch.setattr(vapi, "place_limit_order", lambda *a, **k: {"success": True, "order_id": "new"})
    monkeypatch.setattr(vapi, "parse_spot_balances", lambda *a, **k: {})
    r = grid.run_grid_tick("binance", "DOGE", mid=0.10)
    # Only B books a fill; C is dropped silently (no phantom fill).
    assert r["fills_this_tick"] == 1
    # A stays resting; C dropped; B replaced by a paired buy -> A + paired buy tracked.
    oids = [o["order_id"] for o in grid._read_state()[key]["open_orders"]]
    assert "A" in oids and "C" not in oids


def test_grid_targets_merges_multi_venue(grid, tmp_path, monkeypatch):
    import json
    p = tmp_path / "multi.json"
    p.write_text(json.dumps({
        "enabled": True, "venue": "binance", "assets": ["BTC", "DOGE"],
        "venues": {"nonkyc": ["BTC", "XRP"], "xeggex": ["ETH"]},
    }), encoding="utf-8")
    monkeypatch.setattr(grid, "_CFG_PATH", str(p))
    cfg = grid.load_config()
    targets = grid.grid_targets(cfg)
    # binance BTC/DOGE + nonkyc BTC/XRP + xeggex ETH; binance BTC != nonkyc BTC (venue-scoped)
    assert ("binance", "BTC") in targets
    assert ("nonkyc", "BTC") in targets
    assert ("nonkyc", "XRP") in targets
    assert ("xeggex", "ETH") in targets
    assert len(targets) == 5
    assert len(targets) == len(set(targets))  # de-duplicated


def test_grid_targets_dedups_overlap(grid, tmp_path, monkeypatch):
    import json
    p = tmp_path / "dup.json"
    p.write_text(json.dumps({
        "enabled": True, "venue": "binance", "assets": ["DOGE"],
        "venues": {"binance": ["DOGE", "BTC"]},  # DOGE overlaps legacy assets
    }), encoding="utf-8")
    monkeypatch.setattr(grid, "_CFG_PATH", str(p))
    targets = grid.grid_targets(grid.load_config())
    assert targets.count(("binance", "DOGE")) == 1
    assert ("binance", "BTC") in targets


@pytest.fixture
def profit_data(grid, tmp_path, monkeypatch):
    """Seed a ledger profit index + pair catalog for ranking tests."""
    import json
    idx = tmp_path / "idx.json"
    idx.write_text(json.dumps({"hits": [
        {"symbol": "BTC", "buy_venue": "binance", "sell_venue": "nonkyc",
         "avg_net_bps": 56.0, "hit_rate_pct": 100.0, "fill_count": 26},
        {"symbol": "DOGE", "buy_venue": "binance", "sell_venue": "nonkyc",
         "avg_net_bps": 34.0, "hit_rate_pct": 100.0, "fill_count": 1},
        {"symbol": "LINK", "buy_venue": "nonkyc", "sell_venue": "binance",
         "avg_net_bps": 11.8, "hit_rate_pct": 50.0, "fill_count": 0},  # net < fees -> filtered
    ]}), encoding="utf-8")
    cat = tmp_path / "cat.json"
    cat.write_text(json.dumps({
        "binance_usdc_bases": ["BTC", "DOGE", "LINK", "ETH"],
        "nonkyc_usdt_bases": ["BTC", "DOGE", "LINK"],
    }), encoding="utf-8")
    monkeypatch.setattr(grid, "_PROFIT_INDEX_PATH", str(idx))
    monkeypatch.setattr(grid, "_PAIR_CATALOG_PATH", str(cat))
    return grid


def test_rank_profit_pairs_ranks_by_measured_edge(profit_data):
    ranked = profit_data.rank_profit_pairs(include_live=False, min_score=3.0)
    syms = [r["symbol"] for r in ranked]
    assert syms[0] == "BTC"           # highest measured edge + confidence
    assert "LINK" not in syms          # net edge below fees -> dropped
    btc = ranked[0]
    assert btc["net_edge_bps"] == pytest.approx(56.0 - 20.0)  # minus round-trip maker fees
    assert set(btc["venues"]) == {"binance", "nonkyc", "xeggex"}


def test_autoselect_applies_to_multi_venue_config(profit_data, tmp_path, monkeypatch):
    import json
    # cfg with an existing venues map; autoselect should merge winners in (de-duped).
    p = tmp_path / "cfg2.json"
    p.write_text(json.dumps({"enabled": True, "venue": "binance", "assets": ["SOL"],
                             "venues": {"nonkyc": ["XRP"]},
                             "maker_fee_bps": 10.0}), encoding="utf-8")
    monkeypatch.setattr(profit_data, "_CFG_PATH", str(p))
    res = profit_data.autoselect_profit_pairs(min_score=3.0, include_live=False, apply=True)
    assert res["applied"] is True
    v = res["config_venues"]
    assert "BTC" in v["binance"] and "SOL" in v["binance"]   # winners + legacy assets merged
    assert "BTC" in v["nonkyc"] and "XRP" in v["nonkyc"]     # winners + existing merged
    # persisted
    cfg2 = profit_data.load_config()
    assert "BTC" in (cfg2.get("venues") or {}).get("binance", [])


@pytest.fixture
def cross_scan(profit_data, monkeypatch):
    """Stub the arbitrage scanner with known cross-venue opportunities."""
    import backend.services.exchange_arbitrage_service as arb

    def fake_scan(symbols=None, venues=None, **k):
        return {"opportunities": [
            {"symbol": "DOGE", "buy_venue": "binance", "buy_ask": 0.10, "sell_venue": "nonkyc",
             "sell_bid": 0.102, "gross_bps": 200.0, "fee_bps": 30.0, "net_bps": 170.0, "est_profit_usd": 1.70},
            {"symbol": "BTC", "buy_venue": "nonkyc", "sell_venue": "binance",
             "gross_bps": 7.8, "fee_bps": 30.0, "net_bps": -22.2, "est_profit_usd": -0.22},
            {"symbol": "ETH", "buy_venue": "internal", "sell_venue": "binance", "net_bps": 99.0},
        ]}
    monkeypatch.setattr(arb, "scan_opportunities", fake_scan)
    return profit_data


def test_scan_cross_venue_differences_filters(cross_scan):
    res = cross_scan.scan_cross_venue_differences(min_net_bps=5.0)
    assert res["success"] is True
    syms = [d["symbol"] for d in res["differences"]]
    assert syms == ["DOGE"]                 # only DOGE clears net>=5 and is a real cross-venue route
    d = res["differences"][0]
    assert d["route"] == "binance\u2192nonkyc"
    assert d["net_bps"] == 170.0


def test_scan_cross_excludes_internal_leg(cross_scan):
    res = cross_scan.scan_cross_venue_differences(min_net_bps=-100.0)  # include even negatives
    syms = [d["symbol"] for d in res["differences"]]
    assert "ETH" not in syms                # internal leg is not a venue-to-venue cross-trade
    assert "BTC" in syms                    # negative net still a real route, included at low threshold


def test_autoselect_cross_venue_applies(cross_scan, tmp_path, monkeypatch):
    import json
    p = tmp_path / "cxcfg.json"
    p.write_text(json.dumps({"enabled": True, "venue": "binance", "assets": [],
                             "venues": {}, "maker_fee_bps": 10.0}), encoding="utf-8")
    monkeypatch.setattr(cross_scan, "_CFG_PATH", str(p))
    res = cross_scan.autoselect_cross_venue_pairs(min_net_bps=5.0, apply=True)
    assert res["applied"] is True
    v = res["config_venues"]
    # DOGE is listed on all three (per profit_data catalog) -> added everywhere it lists
    assert "DOGE" in v["binance"] and "DOGE" in v["nonkyc"]


def test_effective_config_applies_venue_override(grid, tmp_path, monkeypatch):
    import json
    p = tmp_path / "ov.json"
    p.write_text(json.dumps({
        "enabled": True, "venue": "binance", "assets": ["DOGE"],
        "grid_step_pct": 0.004, "order_size_usd": 6.0, "maker_fee_bps": 10.0,
        "enforce_fee_positive_step": True, "min_edge_over_fee_bps": 2.0,
        "venue_overrides": {"nonkyc": {"grid_step_pct": 0.008, "maker_fee_bps": 20.0}},
    }), encoding="utf-8")
    monkeypatch.setattr(grid, "_CFG_PATH", str(p))
    base = grid.load_config()
    eb = grid.effective_config("binance", base)
    en = grid.effective_config("nonkyc", base)
    assert eb["grid_step_pct"] == pytest.approx(0.004)   # base
    assert en["grid_step_pct"] == pytest.approx(0.008)   # override
    assert en["maker_fee_bps"] == 20.0


def test_effective_config_bumps_step_to_be_fee_positive(grid, tmp_path, monkeypatch):
    import json
    p = tmp_path / "bump.json"
    # step 10 bps but maker 20 bps -> round trip fee 40 bps; step must bump to >= 42 bps (0.0042)
    p.write_text(json.dumps({
        "enabled": True, "venue": "nonkyc", "assets": ["DOGE"],
        "grid_step_pct": 0.001, "maker_fee_bps": 20.0,
        "enforce_fee_positive_step": True, "min_edge_over_fee_bps": 2.0,
    }), encoding="utf-8")
    monkeypatch.setattr(grid, "_CFG_PATH", str(p))
    e = grid.effective_config("nonkyc", grid.load_config())
    assert e["grid_step_pct"] == pytest.approx((2 * 20.0 + 2.0) / 10000.0)  # 0.0042
    assert e.get("step_bumped_for_fees") is True
    step_bps = e["grid_step_pct"] * 1e4
    assert step_bps - 2 * e["maker_fee_bps"] >= 2.0  # net-positive per pair


def test_spread_gate_blocks_thin_spread(grid, tmp_path, monkeypatch):
    import json
    p = tmp_path / "gate.json"
    p.write_text(json.dumps({
        "enabled": True, "venue": "nonkyc", "assets": ["DOGE"],
        "grid_step_pct": 0.008, "order_size_usd": 6.0, "max_inventory_usd": 40.0,
        "hard_loss_cap_usd": 5.0, "min_notional_usd": 5.0, "maker_fee_bps": 20.0,
        "allow_sell_existing_inventory": True, "require_spread_over_fee": True,
    }), encoding="utf-8")
    monkeypatch.setattr(grid, "_CFG_PATH", str(p))
    # spread 30 bps < 2*maker(40) -> no seeding; 60 bps >= 40 -> seeds.
    thin = grid.run_grid_tick("nonkyc", "DOGE", mid=0.10, dry_run=True, spot_free_base=1000.0, spread_bps=30.0)
    assert thin["open_orders"] == 0 and thin["spread_gate_ok"] is False
    assert thin["reconcile_note"] == "spread_below_fee"
    wide = grid.run_grid_tick("nonkyc", "DOGE", mid=0.10, dry_run=True, spot_free_base=1000.0, spread_bps=60.0)
    assert wide["open_orders"] > 0 and wide["spread_gate_ok"] is True


def test_spread_gate_disabled_allows_any_spread(grid, tmp_path, monkeypatch):
    import json
    p = tmp_path / "nogate.json"
    p.write_text(json.dumps({
        "enabled": True, "venue": "nonkyc", "assets": ["DOGE"],
        "grid_step_pct": 0.008, "order_size_usd": 6.0, "max_inventory_usd": 40.0,
        "hard_loss_cap_usd": 5.0, "min_notional_usd": 5.0, "maker_fee_bps": 20.0,
        "allow_sell_existing_inventory": True, "require_spread_over_fee": False,
    }), encoding="utf-8")
    monkeypatch.setattr(grid, "_CFG_PATH", str(p))
    r = grid.run_grid_tick("nonkyc", "DOGE", mid=0.10, dry_run=True, spot_free_base=1000.0, spread_bps=1.0)
    assert r["open_orders"] > 0  # gate off -> seeds regardless of thin spread


def test_apply_venue_profile_specializes_exchange(grid, tmp_path, monkeypatch):
    import json
    p = tmp_path / "spec.json"
    p.write_text(json.dumps({"enabled": True, "venue": "binance", "assets": ["DOGE"],
                             "venue_overrides": {}}), encoding="utf-8")
    monkeypatch.setattr(grid, "_CFG_PATH", str(p))
    r = grid.apply_venue_profile("nonkyc", "illiquid_wide")
    assert r["success"] and r["profile"] == "illiquid_wide"
    e = grid.effective_config("nonkyc", grid.load_config())
    assert e["_profile"] == "illiquid_wide"
    assert e["require_spread_over_fee"] is True
    assert e["min_spread_bps"] == 40.0
    assert grid.apply_venue_profile("nonkyc", "bogus")["success"] is False


def test_liquid_dense_profile_ignores_spread_gate(grid, tmp_path, monkeypatch):
    import json
    p = tmp_path / "dense.json"
    p.write_text(json.dumps({
        "enabled": True, "venue": "binance", "assets": ["DOGE"], "maker_fee_bps": 10.0,
        "venue_overrides": {"binance": {"_profile": "liquid_dense", "grid_step_pct": 0.003,
                            "grid_levels": 4, "require_spread_over_fee": False,
                            "min_spread_bps": 1.0, "maker_fee_bps": 10.0}},
        "require_spread_over_fee": True,  # base on, but venue overrides OFF
    }), encoding="utf-8")
    monkeypatch.setattr(grid, "_CFG_PATH", str(p))
    # Tiny 2 bps spread would fail a gate, but liquid_dense has the gate OFF -> still seeds.
    r = grid.run_grid_tick("binance", "DOGE", mid=100.0, dry_run=True, spot_free_base=100.0, spread_bps=2.0)
    assert r["spread_gate_ok"] is True and r["open_orders"] > 0
    assert r["profile"] == "liquid_dense"


def test_illiquid_profile_gates_on_min_spread(grid, tmp_path, monkeypatch):
    import json
    p = tmp_path / "illiq.json"
    p.write_text(json.dumps({
        "enabled": True, "venue": "nonkyc", "assets": ["DOGE"], "maker_fee_bps": 10.0,
        "venue_overrides": {"nonkyc": {"_profile": "illiquid_wide", "grid_step_pct": 0.010,
                            "grid_levels": 3, "require_spread_over_fee": True,
                            "min_spread_bps": 40.0, "maker_fee_bps": 20.0}},
        "allow_sell_existing_inventory": True, "min_notional_usd": 5.0,
        "order_size_usd": 6.0, "max_inventory_usd": 40.0,
    }), encoding="utf-8")
    monkeypatch.setattr(grid, "_CFG_PATH", str(p))
    # min_spread 40 (> 2*maker=40 tie) -> 30 bps blocked, 50 bps seeds.
    blocked = grid.run_grid_tick("nonkyc", "DOGE", mid=0.10, dry_run=True, spot_free_base=1000.0, spread_bps=30.0)
    seeds = grid.run_grid_tick("nonkyc", "DOGE", mid=0.10, dry_run=True, spot_free_base=1000.0, spread_bps=50.0)
    assert blocked["open_orders"] == 0 and blocked["spread_gate_ok"] is False
    assert seeds["open_orders"] > 0 and seeds["spread_gate_ok"] is True


def test_venue_performance_aggregates_from_ledger(grid):
    import json as _json
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    recent = now.isoformat().replace("+00:00", "Z")
    old = (now - timedelta(hours=48)).isoformat().replace("+00:00", "Z")
    rows = [
        {"ts": recent, "venue": "nonkyc", "asset": "DOGE", "side": "sell", "realized_delta_usd": 0.40},
        {"ts": recent, "venue": "nonkyc", "asset": "LINK", "side": "sell", "realized_delta_usd": 0.20},
        {"ts": recent, "venue": "binance", "asset": "DOGE", "side": "sell", "realized_delta_usd": 0.05},
        {"ts": old,    "venue": "binance", "asset": "DOGE", "side": "sell", "realized_delta_usd": 9.99},  # outside window
    ]
    with open(grid._LEDGER_PATH, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(_json.dumps(r) + "\n")
    perf = grid.venue_performance(window_hours=24.0)
    assert perf["success"]
    by = {v["venue"]: v for v in perf["venues"]}
    assert "binance" in by and "nonkyc" in by
    assert by["nonkyc"]["fills"] == 2                       # old binance row excluded
    assert by["nonkyc"]["realized_usd"] == pytest.approx(0.60)
    assert by["binance"]["fills"] == 1                      # 48h-old row filtered out
    # nonkyc pays more/day -> it's the focus suggestion and sorts first
    assert perf["focus_suggestion"] == "nonkyc"
    assert perf["venues"][0]["venue"] == "nonkyc"


def test_venue_performance_empty(grid):
    perf = grid.venue_performance()
    assert perf["success"] and perf["venues"] == [] and perf["focus_suggestion"] is None


def test_circuit_breaker_pauses_losing_venue(grid, tmp_path, monkeypatch):
    import json as _json
    from datetime import datetime, timezone
    p = tmp_path / "cb.json"
    p.write_text(_json.dumps({
        "enabled": True, "venue": "binance", "assets": ["DOGE"],
        "venues": {"nonkyc": ["DOGE"]},
        "circuit_breaker": {"enabled": True, "window_hours": 6.0,
                            "loss_threshold_usd": 3.0, "cooldown_hours": 12.0},
    }), encoding="utf-8")
    monkeypatch.setattr(grid, "_CFG_PATH", str(p))
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    # nonkyc bleeding (-5 realized), binance fine (+1) in the window.
    with open(grid._LEDGER_PATH, "w", encoding="utf-8") as fh:
        fh.write(_json.dumps({"ts": now, "venue": "nonkyc", "asset": "DOGE", "side": "sell",
                              "realized_delta_usd": -5.0}) + "\n")
        fh.write(_json.dumps({"ts": now, "venue": "binance", "asset": "DOGE", "side": "sell",
                              "realized_delta_usd": 1.0}) + "\n")
    r = grid.check_circuit_breakers()
    assert "nonkyc" in r["paused"] and "binance" not in r["paused"]
    assert any(e["action"] == "pause" and e["venue"] == "nonkyc" for e in r["events"])
    # run_all now skips the paused venue.
    res = grid.run_all(dry_run=True)
    skipped = [t for t in res["ticks"] if t.get("reason") == "venue_paused"]
    assert any(t["venue"] == "nonkyc" for t in skipped)
    assert "nonkyc" in res["paused_venues"]


def test_circuit_breaker_auto_resume_after_cooldown(grid, tmp_path, monkeypatch):
    import json as _json
    from datetime import datetime, timezone, timedelta
    p = tmp_path / "cb2.json"
    p.write_text(_json.dumps({
        "enabled": True, "venue": "nonkyc", "assets": ["DOGE"],
        "circuit_breaker": {"enabled": True, "window_hours": 6.0,
                            "loss_threshold_usd": 3.0, "cooldown_hours": 12.0},
    }), encoding="utf-8")
    monkeypatch.setattr(grid, "_CFG_PATH", str(p))
    # Paused 13h ago (past the 12h cooldown), non-manual -> should auto-resume.
    old = (datetime.now(timezone.utc) - timedelta(hours=13)).isoformat().replace("+00:00", "Z")
    grid._write_state({"paused_venues": {"nonkyc": {"reason": "realized_loss", "manual": False,
                                                    "paused_at": old, "realized_usd": -5.0}}})
    # no recent losing fills -> nothing re-pauses
    r = grid.check_circuit_breakers()
    assert "nonkyc" not in r["paused"]
    assert any(e["action"] == "auto_resume" and e["venue"] == "nonkyc" for e in r["events"])


def test_manual_pause_persists_through_cooldown(grid, tmp_path, monkeypatch):
    import json as _json
    from datetime import datetime, timezone, timedelta
    p = tmp_path / "cb3.json"
    p.write_text(_json.dumps({"enabled": True, "venue": "nonkyc", "assets": ["DOGE"],
                              "circuit_breaker": {"enabled": True, "cooldown_hours": 1.0,
                                                  "window_hours": 1.0, "loss_threshold_usd": 3.0}}),
                 encoding="utf-8")
    monkeypatch.setattr(grid, "_CFG_PATH", str(p))
    old = (datetime.now(timezone.utc) - timedelta(hours=99)).isoformat().replace("+00:00", "Z")
    grid._write_state({"paused_venues": {"nonkyc": {"reason": "manual", "manual": True,
                                                    "paused_at": old}}})
    r = grid.check_circuit_breakers()
    assert "nonkyc" in r["paused"]  # manual pause is NOT auto-resumed
    assert grid.resume_venue("nonkyc")["resumed"] is True
    assert "nonkyc" not in grid.paused_venues()


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
