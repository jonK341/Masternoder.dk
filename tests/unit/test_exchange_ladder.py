from backend.services.exchange_ladder_service import (
    _default_config,
    entry_price,
    load_state,
    lowest_own_sell,
    run_ladder,
)

MK = {"price_decimals": 6, "qty_decimals": 2, "min_qty": 0.0, "min_quote": 1.0}


def _cfg(**over):
    cfg = {**_default_config(), "execute": True, "symbols": ["ALGO"], "levels": 3,
           "fill_model_enabled": False, "inventory_skew_bps": 0.0}
    cfg.update(over)
    return cfg


class FakeVenue:
    """Lists orders under a different id than create returns; closed orders are looked up by tag."""

    def __init__(self):
        self.open = {}
        self.closed_rows = {}
        self.placed = []
        self.cancelled = []
        self.next_id = 0
        self.reject = []

    def open_ids(self, _symbol):
        return dict(self.open)

    def closed(self, _symbol, coids):
        return {c: r for c, r in self.closed_rows.items() if c in coids}

    def place(self, symbol, side, qty, price, coid):
        if self.reject:
            return {"success": False, "error": self.reject.pop(0)}
        if any(p["coid"] == coid for p in self.placed):
            return {"success": False, "error": "Bad userProvidedId. This value should be either unique or null"}
        self.next_id += 1
        self.open[coid] = f"o{self.next_id}"
        self.placed.append({"symbol": symbol, "side": side, "qty": qty, "price": price, "coid": coid})
        return {"success": True, "mode": "live"}

    def cancel(self, _symbol, oid):
        coid = next(k for k, v in self.open.items() if v == oid)
        del self.open[coid]
        self.closed_rows[coid] = {"id": oid, "executedQuantity": 0, "status": "Cancelled"}
        self.cancelled.append(coid)
        return {"success": True}

    def fill(self, coid, qty=None):
        oid = self.open.pop(coid)
        order = next(p for p in self.placed if p["coid"] == coid)
        self.closed_rows[coid] = {"id": oid, "executedQuantity": order["qty"] if qty is None else qty, "status": "Filled"}


def _run(venue, tmp_path, *, mid=0.093, now=1000.0, bal=None, cfg=None, maker_sell=None, sleeps=None, **kw):
    return run_ladder(
        **kw,
        cfg=cfg or _cfg(),
        top=lambda _s: {"bid": mid, "ask": mid},
        # Default quote is above the ~3-rung operating target so exit-first stays off.
        balances=bal if bal is not None else {"ALGO": 300.0, "USDT": 20.0},
        open_ids=venue.open_ids, closed=venue.closed, market=lambda _s: MK,
        place=venue.place, cancel=venue.cancel,
        maker_sell=lambda _s: maker_sell,
        clock=lambda: now, path=str(tmp_path / "ladder.json"),
        sleep=(sleeps.append if sleeps is not None else (lambda _s: None)),
    )


def _by(venue, side):
    return [p for p in venue.placed if p["side"] == side]


def test_first_tick_places_small_rungs_both_sides_within_budget(tmp_path):
    venue = FakeVenue()
    rep = _run(venue, tmp_path)
    sells, buys = _by(venue, "sell"), _by(venue, "buy")
    assert [p["price"] for p in sells] == [entry_price(0.093, "sell", k, _cfg(), 6) for k in range(3)]
    assert all(3.0 <= p["qty"] * p["price"] <= 3.5 for p in venue.placed)
    assert len(buys) == 3  # $20 USDT funds three $3.50 buys
    assert buys[0]["price"] < 0.093 < sells[0]["price"]
    assert all(p["coid"].startswith("ld-ALGO-") for p in venue.placed)
    assert rep["open_orders"] == 6
    assert lowest_own_sell("ALGO", str(tmp_path / "ladder.json")) == sells[0]["price"]


def test_sell_fill_places_profitable_buyback_and_rung_reopens_after_it_fills(tmp_path):
    venue = FakeVenue()
    cfg = _cfg(sides=["sell"], levels=1)
    _run(venue, tmp_path, cfg=cfg)
    entry = venue.placed[0]
    venue.fill(entry["coid"])
    rep = _run(venue, tmp_path, cfg=cfg, now=1060.0, bal={"ALGO": 300.0 - entry["qty"], "USDT": 3.5})
    exit_order = venue.placed[-1]
    assert rep["fills"][0]["kind"] == "entry"
    assert exit_order["side"] == "buy"
    assert exit_order["price"] <= entry["price"] * (1 - 0.008)
    assert exit_order["qty"] > entry["qty"]
    assert len(venue.placed) == 2  # the sell rung stays closed while its exit rests

    venue.fill(exit_order["coid"])
    rep = _run(venue, tmp_path, cfg=cfg, now=1120.0)
    assert rep["fills"][0]["kind"] == "exit"
    assert rep["fills"][0]["pnl_usd"] > 0
    assert rep["realized_usd"] == rep["fills"][0]["pnl_usd"]
    assert venue.placed[-1]["side"] == "sell" and len(venue.placed) == 3


def test_buy_fill_places_take_profit_sell(tmp_path):
    venue = FakeVenue()
    cfg = _cfg(sides=["buy"], levels=1)
    _run(venue, tmp_path, cfg=cfg)
    entry = venue.placed[0]
    venue.fill(entry["coid"])
    _run(venue, tmp_path, cfg=cfg, now=1060.0, bal={"ALGO": entry["qty"], "USDT": 0.0})
    exit_order = venue.placed[-1]
    assert exit_order["side"] == "sell"
    assert exit_order["price"] >= entry["price"] * 1.008
    assert exit_order["qty"] <= entry["qty"]


def test_recentre_moves_entries_but_keeps_exits(tmp_path):
    venue = FakeVenue()
    cfg = _cfg(sides=["sell"], levels=2)
    _run(venue, tmp_path, cfg=cfg)
    venue.fill(venue.placed[0]["coid"])
    _run(venue, tmp_path, cfg=cfg, now=1060.0, bal={"ALGO": 260.0, "USDT": 3.5})
    exit_coid = venue.placed[-1]["coid"]
    _run(venue, tmp_path, cfg=cfg, mid=0.0960, now=1120.0, bal={"ALGO": 260.0, "USDT": 0.0})
    assert exit_coid in venue.open
    assert venue.cancelled == [venue.placed[1]["coid"]]
    newest = venue.placed[-1]
    assert newest["side"] == "sell" and newest["price"] == entry_price(0.0960, "sell", 1, cfg, 6)
    state = load_state(str(tmp_path / "ladder.json"))
    assert state["anchors"]["ALGO"]["ref"] == 0.0960
    assert sum(1 for o in state["orders"].values() if not o.get("cancelled")) == 2


def test_open_order_cap_and_inventory_limit(tmp_path):
    venue = FakeVenue()
    rep = _run(venue, tmp_path, cfg=_cfg(max_open_orders=2))
    assert len(venue.placed) == 2
    venue2 = FakeVenue()
    _run(venue2, tmp_path / "b", bal={"ALGO": 40.0, "USDT": 0.0}, cfg=_cfg(sides=["sell"]))
    assert len(venue2.placed) == 1  # 40 ALGO covers one $3.50 rung, the rest is under $3
    assert rep["skipped"][-1]["reason"] == "max_open_orders"


def test_insufficient_funds_is_retried(tmp_path):
    venue = FakeVenue()
    venue.reject = ["Insufficient funds for order creation"]
    sleeps = []
    _run(venue, tmp_path, cfg=_cfg(sides=["sell"], levels=1), sleeps=sleeps)
    assert len(venue.placed) == 1
    assert sleeps == [1.5]


def test_buy_never_crosses_our_maker_sell(tmp_path):
    venue = FakeVenue()
    _run(venue, tmp_path, cfg=_cfg(sides=["buy"], levels=3), maker_sell=0.0927)
    assert [p["price"] for p in venue.placed] == [entry_price(0.093, "buy", k, _cfg(), 6) for k in (1, 2)]
    assert all(p["price"] < 0.0927 for p in venue.placed)


def test_unfunded_exit_waits_for_the_next_tick(tmp_path):
    venue = FakeVenue()
    cfg = _cfg(sides=["sell"], levels=1)
    _run(venue, tmp_path, cfg=cfg)
    venue.fill(venue.placed[0]["coid"])
    rep = _run(venue, tmp_path, cfg=cfg, now=1060.0, bal={"ALGO": 260.0, "USDT": 0.0})
    assert rep["pending_exits"] == 1 and len(venue.placed) == 1
    rep = _run(venue, tmp_path, cfg=cfg, now=1120.0, bal={"ALGO": 260.0, "USDT": 3.5})
    assert rep["pending_exits"] == 0 and venue.placed[-1]["side"] == "buy"


def test_execute_off_places_nothing(tmp_path):
    venue = FakeVenue()
    assert _run(venue, tmp_path, cfg=_cfg(execute=False))["placed"] == []
    assert venue.placed == []


def test_binance_block_overlays_nonkyc_config(tmp_path, monkeypatch):
    import json

    from backend.services import exchange_ladder_service as lad

    cfg_path = tmp_path / "ladder.json"
    cfg_path.write_text(json.dumps({"execute": True, "order_usd": 3.5, "levels": 12,
                                    "binance": {"execute": True, "order_usd": 5.5, "quote_reserve": 5.0}}))
    monkeypatch.setattr(lad, "_CFG_PATH", str(cfg_path))
    nk, bn = lad.load_config("nonkyc"), lad.load_config("binance")
    assert (nk["quote"], nk["order_usd"], nk["quote_reserve"]) == ("USDT", 3.5, 0.0)
    assert (bn["quote"], bn["order_usd"], bn["quote_reserve"], bn["levels"]) == ("USDC", 5.5, 5.0, 12)
    cfg_path.write_text(json.dumps({"execute": True}))
    assert lad.load_config("binance")["execute"] is False
    assert lad.state_path(None, "binance").endswith("ladder_state_binance.json")


def test_binance_ladder_spends_usdc_above_the_reserve(tmp_path):
    venue = FakeVenue()
    mk = {"price_decimals": 4, "qty_decimals": 1, "min_qty": 0.1, "min_quote": 5.0}
    cfg = _cfg(venue="binance", quote="USDC", symbols=["XRP"], order_usd=5.5, min_order_usd=5.1,
               quote_reserve=5.0, levels=10, fee_bps=10.0, exit_bps=50.0,
               max_entry_bps=500.0, first_bps=20.0, step_bps=30.0)
    rep = run_ladder(
        cfg=cfg, top=lambda _s: {"bid": 1.09, "ask": 1.0902},
        balances={"XRP": 20.0, "USDC": 17.0},
        open_ids=venue.open_ids, closed=venue.closed, market=lambda _s: mk,
        place=venue.place, cancel=venue.cancel, clock=lambda: 1000.0,
        path=str(tmp_path / "bn.json"), sleep=lambda _s: None,
    )
    buys, sells = _by(venue, "buy"), _by(venue, "sell")
    assert len(buys) == 2  # $12 above the $5 reserve funds two $5.50 rungs
    assert len(sells) == 4  # 20 XRP covers four ~5 XRP rungs
    assert all(p["qty"] * p["price"] >= 5.0 for p in venue.placed)
    assert rep["venue"] == "binance"

    venue.fill(buys[0]["coid"])
    run_ladder(
        cfg=cfg, top=lambda _s: {"bid": 1.09, "ask": 1.0902},
        balances={"XRP": 20.0 + buys[0]["qty"], "USDC": 0.0},
        open_ids=venue.open_ids, closed=venue.closed, market=lambda _s: mk,
        place=venue.place, cancel=venue.cancel, clock=lambda: 1060.0,
        path=str(tmp_path / "bn.json"), sleep=lambda _s: None,
    )
    exit_order = venue.placed[-1]
    assert exit_order["side"] == "sell" and exit_order["price"] >= buys[0]["price"] * 1.005


def test_refresh_every_ten_minutes_only_replaces_rungs_whose_price_moved(tmp_path):
    venue = FakeVenue()
    cfg = _cfg(sides=["sell"], levels=3)
    _run(venue, tmp_path, cfg=cfg)
    rep = _run(venue, tmp_path, cfg=cfg, mid=0.093001, now=1000.0 + 10 * 60)
    assert venue.cancelled == [] and rep["kept"] == 3
    rep = _run(venue, tmp_path, cfg=cfg, mid=0.0934, now=1000.0 + 11 * 60)
    assert len(venue.cancelled) == 3 and len(venue.open) == 3
    assert sorted(p["price"] for p in venue.placed[-3:]) == [entry_price(0.0934, "sell", k, cfg, 6) for k in range(3)]


def test_unfilled_exit_steps_toward_market_but_keeps_its_profit(tmp_path):
    venue = FakeVenue()
    cfg = _cfg(sides=["sell"], levels=1)
    _run(venue, tmp_path, cfg=cfg)
    entry = venue.placed[0]
    venue.fill(entry["coid"])
    _run(venue, tmp_path, cfg=cfg, now=1060.0, bal={"ALGO": 260.0, "USDT": 3.5})
    first_exit = venue.placed[-1]
    assert first_exit["price"] <= entry["price"] * (1 - 0.008)

    rep = _run(venue, tmp_path, cfg=cfg, now=1060.0 + 61 * 60, bal={"ALGO": 260.0, "USDT": 0.0})
    mid_exit = venue.placed[-1]
    assert rep["repriced"] == [first_exit["coid"]]
    assert first_exit["price"] < mid_exit["price"] < entry["price"] * (1 - 0.0055)

    _run(venue, tmp_path, cfg=cfg, now=1060.0 + 200 * 60, bal={"ALGO": 260.0, "USDT": 0.0})
    last_exit = venue.placed[-1]
    assert last_exit["price"] <= entry["price"] * (1 - 0.0055)
    assert last_exit["price"] > mid_exit["price"]
    _run(venue, tmp_path, cfg=cfg, now=1060.0 + 300 * 60, bal={"ALGO": 260.0, "USDT": 0.0})
    assert venue.placed[-1] == last_exit  # floor reached, no further moves

    venue.fill(last_exit["coid"])
    rep = _run(venue, tmp_path, cfg=cfg, now=1060.0 + 301 * 60)
    assert rep["fills"][0]["kind"] == "exit" and rep["fills"][0]["pnl_usd"] > 0


def test_entry_and_exit_on_the_same_rung_get_distinct_tags(tmp_path):
    venue = FakeVenue()
    cfg = _cfg(levels=1)
    _run(venue, tmp_path, cfg=cfg)
    venue.fill(_by(venue, "sell")[0]["coid"])
    rep = _run(venue, tmp_path, cfg=cfg, mid=0.0925, now=1000.0 + 11 * 60, bal={"ALGO": 300.0, "USDT": 20.0})
    assert rep["errors"] == []
    kinds = sorted((p["kind"], p["side"]) for p in rep["placed"])
    assert kinds == [("entry", "buy"), ("exit", "buy")]
    assert len({p["coid"] for p in venue.placed}) == len(venue.placed)


def test_quote_reserve_does_not_starve_buy_exits(tmp_path):
    """Reserved quote is for new entries; pending buy-backs may spend it."""
    venue = FakeVenue()
    cfg = _cfg(sides=["sell"], levels=1, quote_reserve=3.0)
    _run(venue, tmp_path, cfg=cfg, bal={"ALGO": 300.0, "USDT": 3.5})
    entry = venue.placed[0]
    venue.fill(entry["coid"])
    # Free USDT equals the reserve only — previously this stayed exit_unfunded.
    rep = _run(venue, tmp_path, cfg=cfg, now=1060.0, bal={"ALGO": 260.0, "USDT": 3.5})
    assert rep["pending_exits"] == 0
    assert venue.placed[-1]["side"] == "buy"
    assert not any(s.get("reason") == "exit_unfunded" for s in rep["skipped"])


def test_unfunded_exit_cancels_far_buy_entry_to_free_quote(tmp_path):
    venue = FakeVenue()
    cfg = _cfg(levels=2)
    _run(venue, tmp_path, cfg=cfg, bal={"ALGO": 300.0, "USDT": 20.0})
    sell = _by(venue, "sell")[0]
    buys = _by(venue, "buy")
    assert len(buys) >= 1
    venue.fill(sell["coid"])
    # After the sell fill, free USDT is zero but resting buy entries still lock quote.
    free_usdt = 0.0
    rep = _run(venue, tmp_path, cfg=cfg, now=1060.0, bal={"ALGO": 300.0 - sell["qty"], "USDT": free_usdt})
    assert any(p.get("kind") == "exit" and p.get("side") == "buy" for p in rep["placed"]) or rep["pending_exits"] == 0
    assert rep.get("freed_for_exit") or rep.get("released_buys") or not any(
        s.get("reason") == "exit_unfunded" for s in rep["skipped"]
    )


def test_sell_entries_fill_before_buys_under_open_cap(tmp_path):
    venue = FakeVenue()
    _run(venue, tmp_path, cfg=_cfg(max_open_orders=2, levels=3))
    assert [p["side"] for p in venue.placed] == ["sell", "sell"]


def test_skew_guard_skips_buys_when_long_base(tmp_path):
    venue = FakeVenue()
    rep = _run(
        venue,
        tmp_path,
        cfg=_cfg(sides=["buy", "sell"], levels=1, inventory_skew_bps=25.0),
        # Quote above exit-first target so the skip is from skew, not thin-quote.
        bal={"ALGO": 1000.0, "USDT": 20.0},
    )
    assert _by(venue, "buy") == []
    assert len(_by(venue, "sell")) == 1
    assert any(s.get("reason") == "skew_long_base" for s in rep["skipped"])


def test_client_order_ids_stay_unique_across_ticks(tmp_path):
    venue = FakeVenue()
    cfg = _cfg(sides=["sell"], levels=2)
    _run(venue, tmp_path, cfg=cfg)
    _run(venue, tmp_path, cfg=cfg, mid=0.094, now=1000.0 + 11 * 60)
    assert len({p["coid"] for p in venue.placed}) == len(venue.placed)
    assert all("-" in p["coid"] and p["coid"].startswith("ld-ALGO-") for p in venue.placed)


def test_thin_quote_cancels_far_buy_entries_to_free_capital(tmp_path):
    venue = FakeVenue()
    cfg = _cfg(levels=3, inventory_skew_bps=0.0)
    # Fund several buy rungs while quote looks healthy.
    _run(venue, tmp_path, cfg=cfg, bal={"ALGO": 300.0, "USDT": 20.0})
    buys = _by(venue, "buy")
    assert len(buys) >= 2
    # Next tick: free USDT is starved but resting buys still lock quote.
    rep = _run(venue, tmp_path, cfg=cfg, now=1060.0, bal={"ALGO": 300.0, "USDT": 2.0})
    assert rep.get("released_buys")
    assert any(c in venue.cancelled for c in rep["released_buys"])
    # Cancelled buy notional should push free USDT toward the operating target.
    assert float(rep.get("released_quote_target") or 0) >= 12.0


def test_live_balance_path_runs_venue_quote_topup(tmp_path, monkeypatch):
    from backend.services import exchange_ladder_service as lad

    calls = []

    def fake_topup(venue, **kwargs):
        calls.append((venue, kwargs))
        return {"success": True, "skipped": True, "venue": venue}

    monkeypatch.setattr(lad, "parse_spot_balances", lambda *_a, **_k: {"ALGO": 50.0, "USDT": 20.0})
    monkeypatch.setattr(lad, "top_up_venue_quote", fake_topup)
    monkeypatch.setattr(lad, "refresh_venue_fees", lambda: None)
    monkeypatch.setattr(lad, "enhance_ladder_cfg", lambda cfg, **_k: cfg)
    monkeypatch.setattr(lad, "tune_ladder_cfg", lambda cfg, **_k: cfg)
    venue = FakeVenue()
    run_ladder(
        cfg=_cfg(sides=["sell"], levels=1),
        balances=None,
        top=lambda _s: {"bid": 0.093, "ask": 0.093},
        open_ids=venue.open_ids,
        closed=venue.closed,
        market=lambda _s: MK,
        place=venue.place,
        cancel=venue.cancel,
        clock=lambda: 1000.0,
        path=str(tmp_path / "ladder.json"),
        sleep=lambda _s: None,
    )
    assert calls and calls[0][0] == "nonkyc"
    assert calls[0][1]["quote"] == "USDT"


def test_nonkyc_venue_defaults_do_not_follow_maker_venue(monkeypatch):
    """Ladder NonKYC adapters must call NonKYC even when maker is on Binance."""
    from backend.services import exchange_ladder_service as lad

    calls = []

    def fake_place(venue_id, symbol, side, qty, price, **kwargs):
        calls.append(("place", venue_id, kwargs.get("quote"), symbol, side))
        return {"success": True, "mode": "live", "body": {"id": "x1"}}

    def fake_cancel(venue_id, symbol, order_id, **kwargs):
        calls.append(("cancel", venue_id, kwargs.get("quote"), symbol, order_id))
        return {"success": True}

    def fake_open(venue_id, symbol, **kwargs):
        calls.append(("open", venue_id, kwargs.get("quote"), symbol))
        return {
            "success": True,
            "body": [{"userProvidedId": "ld-a", "id": "oid-1"}],
        }

    monkeypatch.setattr(lad, "place_limit_order", fake_place)
    monkeypatch.setattr(lad, "cancel_order", fake_cancel)
    monkeypatch.setattr(lad, "get_open_orders", fake_open)
    monkeypatch.setattr(lad, "_venue_quote", lambda _v: "USDT")

    adapters = lad._venue_defaults("nonkyc")
    assert adapters["place"]("DOGE", "sell", 10.0, 0.067572, "ld-test")["success"]
    assert adapters["cancel"]("DOGE", "oid-1")["success"]
    assert adapters["open_ids"]("DOGE") == {"ld-a": "oid-1"}
    assert calls[0] == ("place", "nonkyc", "USDT", "DOGE", "sell")
    assert calls[1] == ("cancel", "nonkyc", "USDT", "DOGE", "oid-1")
    assert calls[2] == ("open", "nonkyc", "USDT", "DOGE")

    monkeypatch.setattr(
        lad,
        "get_open_orders",
        lambda *_a, **_k: {"success": True, "body": []},
    )
    assert adapters["open_ids"]("DOGE") == {}


def test_max_entry_bps_skips_far_rungs_and_pulls_dead(tmp_path):
    import json

    venue = FakeVenue()
    cfg = _cfg(levels=6, first_bps=20.0, step_bps=30.0, max_entry_bps=55.0, sides=["sell", "buy"])
    # Offsets: 20, 50, 80, 110… — only levels 0–1 should place under the 55 bps cap.
    rep = _run(venue, tmp_path, cfg=cfg)
    levels_placed = sorted({int(row["level"]) for row in rep["placed"]})
    assert levels_placed == [0, 1]
    assert any(s.get("reason") == "max_entry_bps" for s in rep["skipped"])

    far = next(row for row in rep["placed"] if row["side"] == "sell" and int(row["level"]) == 0)
    far_px = 0.093 * 1.02  # ~200 bps above mid
    path = tmp_path / "ladder.json"
    state = json.loads(path.read_text())
    state["orders"][far["coid"]]["price"] = far_px
    path.write_text(json.dumps(state))
    rep2 = _run(venue, tmp_path, cfg=cfg, now=1060.0)
    assert far["coid"] in rep2["cancelled"]
    assert any(d.get("coid") == far["coid"] for d in (rep2.get("dead_pulled") or []))
