from backend.services.exchange_ladder_service import (
    _default_config,
    entry_price,
    load_state,
    lowest_own_sell,
    run_ladder,
)

MK = {"price_decimals": 6, "qty_decimals": 2, "min_qty": 0.0, "min_quote": 1.0}


def _cfg(**over):
    cfg = {**_default_config(), "execute": True, "symbols": ["ALGO"], "levels": 3}
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
        balances=bal if bal is not None else {"ALGO": 300.0, "USDT": 8.0},
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
    assert len(buys) == 2  # $8 USDT funds two $3.50 buys
    assert buys[0]["price"] < 0.093 < sells[0]["price"]
    assert all(p["coid"].startswith("ld-ALGO-") for p in venue.placed)
    assert rep["open_orders"] == 5
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
               quote_reserve=5.0, levels=10, fee_bps=10.0, exit_bps=50.0)
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
