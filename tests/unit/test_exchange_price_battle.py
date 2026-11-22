"""Hold-to-profit price battle: $5 lots, small TP, 2h time-stop, dip buys."""
from __future__ import annotations

import json
import time
from pathlib import Path


def _cfg(**extra):
    base = {
        "enabled": True,
        "venue_id": "binance",
        "quote": "USDC",
        "position_usd": 5.0,
        "max_open_positions": 2,
        "min_venue_quote_reserve_usd": 10.0,
        "min_profit_bps": 50,
        "fee_buffer_bps": 20,
        "min_hold_sec": 0,
        "max_hold_sec": 7200,
        "buy_dip_only": False,
        "dip_bps": 25,
        "symbols": ["XRP", "ADA"],
    }
    base.update(extra)
    return base


def _patch_paths(tmp_path, monkeypatch, pb, ex):
    data = tmp_path / "crypto_exchange"
    data.mkdir()
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_BASE", str(tmp_path))
    monkeypatch.setattr(pb, "_CFG_PATH", str(tmp_path / "cfg.json"))
    monkeypatch.setattr(pb, "_POSITIONS_PATH", str(data / "positions.json"))
    monkeypatch.setattr(pb, "_BUYS_PATH", str(data / "buys.jsonl"))
    monkeypatch.setattr(pb, "_SELLS_PATH", str(data / "sells.jsonl"))
    monkeypatch.setattr(pb, "_STATE_PATH", str(data / "state.json"))
    return data


def test_profit_ready_uses_net_plus_fee_buffer(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_price_battle_service as pb

    _patch_paths(tmp_path, monkeypatch, pb, ex)
    (tmp_path / "cfg.json").write_text(json.dumps(_cfg()), encoding="utf-8")

    pos = {"qty": 10.0, "entry_price": 1.0, "bought_at_unix": 0}
    # 50 + 20 = 70 bps → need 1.007
    waiting = pb._profit_ready(pos, 1.005, pb.load_config())
    assert waiting["ready"] is False
    assert waiting["reason"] == "waiting_profit"
    ready = pb._profit_ready(pos, 1.008, pb.load_config())
    assert ready["ready"] is True
    assert ready["pnl_usd"] > 0


def test_time_stop_ready_after_max_hold(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_price_battle_service as pb

    _patch_paths(tmp_path, monkeypatch, pb, ex)
    (tmp_path / "cfg.json").write_text(json.dumps(_cfg(max_hold_sec=7200)), encoding="utf-8")

    pos = {"qty": 10.0, "entry_price": 1.0, "bought_at_unix": time.time() - 7300}
    timed = pb._time_stop_ready(pos, 0.99, pb.load_config())
    assert timed["ready"] is True
    assert timed["reason"] == "time_stop"


def test_dip_filter_requires_ask_below_high(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_price_battle_service as pb

    _patch_paths(tmp_path, monkeypatch, pb, ex)
    (tmp_path / "cfg.json").write_text(json.dumps(_cfg(buy_dip_only=True, dip_bps=25)), encoding="utf-8")
    cfg = pb.load_config()
    highs = {"XRP": 1.0}
    assert pb._is_dip("XRP", 0.998, highs, cfg)["ok"] is False
    assert pb._is_dip("XRP", 0.997, highs, cfg)["ok"] is True


def test_tick_buys_holds_sells_on_profit(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_price_battle_service as pb

    _patch_paths(tmp_path, monkeypatch, pb, ex)
    (tmp_path / "cfg.json").write_text(json.dumps(_cfg(symbols=["XRP"])), encoding="utf-8")
    monkeypatch.setattr(pb, "live_enabled", lambda: False)

    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.refresh_venue_balances",
        lambda *a, **k: {"success": True},
    )
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.parse_spot_balances",
        lambda *a, **k: {"USDC": 40.0, "XRP": 100.0},
    )
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.market_order_for_leg",
        lambda *a, **k: {
            "ok": True,
            "quantity": 5.0,
            "notional_usd": 5.0,
            "price_usd": 1.0,
            "base": "XRP",
            "quote": "USDC",
        },
    )
    prices = {"bid": 1.0, "ask": 1.0, "last": 1.0}
    monkeypatch.setattr(pb, "_ticker_prices", lambda *a, **k: dict(prices))

    res1 = pb.run_tick(force=True, dry_run=True)
    assert res1["success"] is True
    assert res1["open_positions"] == 1
    assert any(a.get("action") == "bought" for a in res1["actions"])
    buys = Path(pb._BUYS_PATH).read_text(encoding="utf-8").strip().splitlines()
    assert len(buys) == 1

    res2 = pb.run_tick(force=True, dry_run=True)
    assert res2["open_positions"] == 1
    assert any(a.get("action") == "hold" for a in res2["actions"])

    prices["bid"] = 1.008
    prices["ask"] = 1.009
    prices["last"] = 1.008
    res3 = pb.run_tick(force=True, dry_run=True)
    assert any(a.get("action") == "sold" and a.get("exit_reason") == "profit" for a in res3["actions"])
    sell = json.loads(Path(pb._SELLS_PATH).read_text(encoding="utf-8").strip().splitlines()[0])
    assert sell["exit_reason"] == "profit"
    assert sell["pnl_usd"] > 0


def test_tick_time_stops_stale_position(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_price_battle_service as pb

    _patch_paths(tmp_path, monkeypatch, pb, ex)
    (tmp_path / "cfg.json").write_text(
        json.dumps(_cfg(symbols=["XRP"], max_hold_sec=100, buy_dip_only=False)),
        encoding="utf-8",
    )
    monkeypatch.setattr(pb, "live_enabled", lambda: False)
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.refresh_venue_balances",
        lambda *a, **k: {"success": True},
    )
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.parse_spot_balances",
        lambda *a, **k: {"USDC": 40.0, "XRP": 100.0},
    )
    monkeypatch.setattr(pb, "_ticker_prices", lambda *a, **k: {"bid": 0.99, "ask": 1.0, "last": 0.995})
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.market_order_for_leg",
        lambda *a, **k: {"ok": True, "quantity": 5.0, "notional_usd": 5.0, "price_usd": 1.0},
    )

    # Seed a stale open position.
    Path(pb._POSITIONS_PATH).write_text(
        json.dumps({
            "open": [{
                "id": "pb_old",
                "symbol": "XRP",
                "qty": 5.0,
                "entry_price": 1.0,
                "cost_usd": 5.0,
                "bought_at_unix": time.time() - 500,
                "bought_at": "old",
            }]
        }),
        encoding="utf-8",
    )
    res = pb.run_tick(force=True, dry_run=True)
    sold = [a for a in res["actions"] if a.get("action") == "sold"]
    assert sold and sold[0].get("exit_reason") == "time_stop"
    sell = json.loads(Path(pb._SELLS_PATH).read_text(encoding="utf-8").strip().splitlines()[0])
    assert sell["exit_reason"] == "time_stop"
