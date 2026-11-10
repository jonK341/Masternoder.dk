import time

from backend.services import exchange_fill_model_service as fill
from backend.services import exchange_inventory_skew as skew
from backend.services import exchange_market_feed_service as feed
from backend.services import exchange_redis_bus as bus
from backend.services.exchange_ladder_service import entry_price, _default_config


def test_redis_bus_roundtrip_and_file_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(bus, "_FALLBACK_DIR", str(tmp_path / "bus"))
    bus.reset_client()
    assert bus.bus_set("test:key", {"a": 1}) in ("redis", "file")
    assert bus.bus_get("test:key") == {"a": 1}
    assert bus.bus_get("test:key", max_age_sec=0.0) is None or bus.bus_get("test:key", max_age_sec=60) == {"a": 1}

    # Force file path
    bus.reset_client()
    monkeypatch.setattr(bus, "get_client", lambda: None)
    assert bus.bus_set("file:only", {"b": 2}) == "file"
    assert bus.bus_get("file:only") == {"b": 2}
    assert (tmp_path / "bus" / "file__only.json").exists()


def test_market_feed_cache_preferred_over_rest(tmp_path, monkeypatch):
    monkeypatch.setattr(bus, "_FALLBACK_DIR", str(tmp_path / "bus"))
    bus.reset_client()
    monkeypatch.setattr(bus, "get_client", lambda: None)
    feed.publish_top("XRP", 1.10, 1.11, source="test")
    calls = []

    def rest(_s):
        calls.append(1)
        return {"bid": 9.0, "ask": 9.1}

    hit = feed.prefer_cached_binance_top("XRP", rest, max_age_sec=5)
    assert hit["bid"] == 1.10 and calls == []
    time.sleep(0.02)
    miss = feed.prefer_cached_binance_top("XRP", rest, max_age_sec=0.01)
    assert miss["bid"] == 9.0 and calls == [1]


def test_inventory_skew_pulls_sells_in_when_long_base():
    cfg = {**_default_config(), "inventory_skew_bps": 40.0}
    long_base = skew.skew_factor({"ALGO": 1000.0, "USDT": 1.0}, "ALGO", 0.1, "USDT")
    assert long_base > 0.9
    sell = skew.skewed_entry_offset_bps("sell", 0, cfg, skew=long_base)
    buy = skew.skewed_entry_offset_bps("buy", 0, cfg, skew=long_base)
    assert sell < cfg["first_bps"] < buy

    cfg["_inventory_skew"] = long_base
    px_sell = entry_price(0.1, "sell", 0, cfg, 6)
    cfg["_inventory_skew"] = 0.0
    px_flat = entry_price(0.1, "sell", 0, cfg, 6)
    assert px_sell < px_flat


def test_fill_model_trains_and_tunes(tmp_path, monkeypatch):
    fills = []
    for level in range(6):
        fills.append({"kind": "entry", "level": level, "side": "sell", "venue": "nonkyc"})
        fills.append({"kind": "entry", "level": level, "side": "buy", "venue": "binance"})
    monkeypatch.setattr(fill, "_MODEL_PATH", str(tmp_path / "model.joblib"))
    monkeypatch.setattr(fill, "_META_PATH", str(tmp_path / "meta.json"))
    meta = fill.train_and_save(fills)
    assert meta["status"] == "trained" and meta["n"] >= fill.MIN_SAMPLES
    p0 = fill.predict_fill_prob(level=0, side="sell", distance_bps=30, fee_bps=20, venue="nonkyc",
                                model_path=str(tmp_path / "model.joblib"))
    p5 = fill.predict_fill_prob(level=5, side="sell", distance_bps=230, fee_bps=20, venue="nonkyc",
                                model_path=str(tmp_path / "model.joblib"))
    assert 0 < p5 <= p0 <= 1
    tuned = fill.tune_ladder_cfg({**_default_config(), "fill_model_enabled": True, "first_bps": 30, "step_bps": 40},
                                 venue="nonkyc")
    assert "_fill_prob_l0" in tuned


def test_metrics_observe_does_not_crash():
    from backend.services.exchange_metrics_service import observe_feed, observe_ladder

    observe_ladder({"venue": "nonkyc", "realized_usd": 0.1, "open_orders": 2, "pending_exits": 1,
                    "fills": [{"kind": "exit", "side": "buy"}], "cancelled": ["a"], "repriced": [],
                    "fill_counts": {"entry": 3, "exit": 1}, "_fill_prob_l0": 0.42},
                   balances={"USDT": 1.5}, quote="USDT", skews={"XRP": 0.2})
    observe_feed({"backend": "file", "symbols": {"XRP": {"ok": True, "age_sec": 0.5}}})
