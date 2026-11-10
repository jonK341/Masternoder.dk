from backend.services.exchange_maker_quote_service import (
    _default_config,
    own_sell_price,
    quote_price,
    run_maker_quotes,
)


def _cfg(**over):
    # Unit fixtures use thin USDT by default; disable yield so sell-quote paths stay testable.
    cfg = {
        **_default_config(),
        "execute": True,
        "symbols": ["ALGO"],
        "sides": ["sell"],
        "yield_to_ladder": False,
    }
    cfg.update(over)
    return cfg


class FakeVenue:
    """NonKYC lists a different id than the create call returns; orders are matched by our tag."""

    def __init__(self):
        self.open = {}
        self.placed = []
        self.cancelled = []
        self.filled = {}
        self.next_id = 0

    def open_ids(self, _symbol):
        return dict(self.open)

    def place(self, symbol, side, qty, price, coid):
        self.next_id += 1
        self.open[coid] = f"o{self.next_id}"
        self.placed.append((symbol, side, qty, price, coid))
        return {"success": True, "mode": "live", "order_id": f"create-{self.next_id}"}

    def cancel(self, _symbol, oid):
        coid = next(k for k, v in self.open.items() if v == oid)
        del self.open[coid]
        self.cancelled.append(oid)
        return {"success": True}

    def fill(self, coid, qty):
        oid = self.open.pop(coid)
        self.filled[coid] = (oid, qty)

    def status(self, _symbol, coid):
        oid, qty = self.filled.get(coid, ("", 0))
        return {"id": oid, "executedQuantity": qty, "status": "Filled" if qty else "Cancelled"}


def _run(venue, tmp_path, *, ask=0.0931, now=1000.0, bal=None, cfg=None):
    return run_maker_quotes(
        cfg=cfg or _cfg(),
        top=lambda _s: {"bid": ask - 0.0001, "ask": ask},
        balances=bal if bal is not None else {"ALGO": 586.5, "USDT": 0.04},
        open_ids=venue.open_ids, status=venue.status, place=venue.place, cancel=venue.cancel,
        clock=lambda: now, path=str(tmp_path / "maker.json"),
    )


def test_quote_price_carries_fees_and_edge_and_rounds_away():
    cfg = _cfg()
    sell = quote_price(0.0931, "sell", cfg)
    buy = quote_price(0.0930, "buy", cfg)
    assert sell == 0.093547
    assert buy == 0.092553
    assert (sell / 0.0931 - 1) * 1e4 >= 48
    assert (1 - buy / 0.0930) * 1e4 >= 48
    assert quote_price(1.0906, "sell", cfg) == 1.0959


def test_places_one_resting_sell_and_keeps_it_while_price_holds(tmp_path):
    venue = FakeVenue()
    rep = _run(venue, tmp_path)
    assert venue.placed == [("ALGO", "sell", 267.24, 0.093547, venue.placed[0][4])]
    assert venue.placed[0][4].startswith("mk-ALGO-s-")
    assert own_sell_price("ALGO", str(tmp_path / "maker.json")) == 0.093547
    rep = _run(venue, tmp_path, now=1060.0)
    assert rep["quotes"][0]["resting"] == venue.placed[0][4]
    assert len(venue.placed) == 1 and venue.cancelled == []


def test_reprices_when_binance_moves_or_order_ages(tmp_path):
    venue = FakeVenue()
    _run(venue, tmp_path)
    _run(venue, tmp_path, ask=0.0935, now=1060.0)
    assert venue.cancelled == ["o1"]
    assert venue.placed[-1][3] == quote_price(0.0935, "sell", _cfg())
    _run(venue, tmp_path, ask=0.0935, now=1060.0 + 31 * 60)
    assert venue.cancelled == ["o1", "o2"]
    assert list(venue.open.values()) == ["o3"]


def test_fill_is_logged_and_next_sell_uses_remaining_inventory(tmp_path):
    venue = FakeVenue()
    _run(venue, tmp_path, bal={"ALGO": 300.0})
    venue.fill(venue.placed[0][4], 267.24)
    rep = _run(venue, tmp_path, now=1060.0, bal={"ALGO": 32.76})
    assert rep["fills"][0]["qty"] == 267.24
    assert rep["fills"][0]["order_id"] == "o1"
    assert rep["fills"][0]["usd"] == round(267.24 * 0.093547, 4)
    assert rep["quotes"][0]["skipped"] == "inventory"
    assert own_sell_price("ALGO", str(tmp_path / "maker.json")) is None


def test_execute_off_and_missing_book_place_nothing(tmp_path):
    venue = FakeVenue()
    assert _run(venue, tmp_path, cfg=_cfg(execute=False))["quotes"] == []
    rep = run_maker_quotes(
        cfg=_cfg(), top=lambda _s: None, balances={"ALGO": 500},
        open_ids=venue.open_ids, status=venue.status, place=venue.place, cancel=venue.cancel,
        path=str(tmp_path / "maker.json"),
    )
    assert rep["quotes"][0]["skipped"] == "no_book"
    assert venue.placed == []


def test_reprice_retries_while_cancelled_funds_are_freed(tmp_path):
    venue = FakeVenue()
    _run(venue, tmp_path)
    real_place, answers, sleeps = venue.place, [{"success": False, "error": "Insufficient funds for order creation"}], []

    def flaky(*args):
        return answers.pop(0) if answers else real_place(*args)

    run_maker_quotes(
        cfg=_cfg(), top=lambda _s: {"bid": 0.0934, "ask": 0.0935}, balances={"ALGO": 586.5},
        open_ids=venue.open_ids, status=venue.status, place=flaky, cancel=venue.cancel,
        clock=lambda: 1060.0, path=str(tmp_path / "maker.json"), sleep=sleeps.append,
    )
    assert sleeps == [1.5]
    assert venue.cancelled == ["o1"] and list(venue.open.values()) == ["o2"]


def test_symbol_removed_from_config_is_cancelled(tmp_path):
    venue = FakeVenue()
    _run(venue, tmp_path)
    rep = _run(venue, tmp_path, now=1060.0, cfg=_cfg(symbols=[]))
    assert venue.cancelled == ["o1"] and venue.open == {}
    assert rep["quotes"][0]["retired"] == venue.placed[0][4]
    assert own_sell_price("ALGO", str(tmp_path / "maker.json")) is None


def test_strategy_buy_never_crosses_our_resting_sell(tmp_path):
    from backend.services.exchange_strategy_service import dispatch_strategy_orders

    venue = FakeVenue()
    maker_path = str(tmp_path / "maker.json")
    _run(venue, tmp_path)
    calls = []
    sent = dispatch_strategy_orders(
        {"execute": True, "rows": [{"strategy": "momentum", "symbol": "ALGO", "signal": "long", "ready": True, "notional_usd": 25}]},
        place=lambda *args: calls.append(args) or {"success": True, "mode": "live"},
        balances={"binance": {"USDC": 0}, "nonkyc": {"USDT": 30.0}},
        quotes={"ALGO": {"bid": 0.093, "ask": 0.0931}},
        walk_book=lambda _s, _usd: 0.0936,
        state_path=str(tmp_path / "strategy.json"),
        maker_state_path=maker_path,
    )
    assert calls == []
    assert sent[0]["skipped"] == "own_maker_sell"


def test_yields_resting_quotes_when_quote_is_thin(tmp_path):
    venue = FakeVenue()
    _run(venue, tmp_path, bal={"ALGO": 586.5, "USDT": 40.0})
    assert len(venue.placed) == 1
    rep = run_maker_quotes(
        cfg=_cfg(yield_to_ladder=True),
        top=lambda _s: {"bid": 0.0930, "ask": 0.0931},
        balances={"ALGO": 586.5, "USDT": 0.04},
        open_ids=venue.open_ids,
        status=venue.status,
        place=venue.place,
        cancel=venue.cancel,
        clock=lambda: 1060.0,
        path=str(tmp_path / "maker.json"),
    )
    assert rep["yielded_to_ladder"] is True
    assert venue.cancelled == ["o1"]
    assert venue.open == {}
    assert own_sell_price("ALGO", str(tmp_path / "maker.json")) is None
