from backend.services.exchange_microstructure_service import (
    blend_skew,
    depth_imbalance,
    maker_edge_bps,
    publish_depth,
    push_mid,
    regime_distance_mult,
    regime_for,
    realized_vol_bps,
)


def test_depth_imbalance_bid_heavy():
    bids = [["1.0", "100"], ["0.99", "50"]]
    asks = [["1.01", "10"], ["1.02", "10"]]
    imb = depth_imbalance(bids, asks)
    assert imb > 0.5


def test_maker_edge_reacts_to_imbalance():
    buy_tight = maker_edge_bps(20.0, "buy", 0.8)
    sell_wide = maker_edge_bps(20.0, "sell", 0.8)
    assert buy_tight < 20.0 < sell_wide


def test_blend_skew_and_regime_mult():
    assert abs(blend_skew(1.0, -1.0, weight=0.5)) < 1e-9
    assert regime_distance_mult("calm") < 1.0 < regime_distance_mult("volatile")


def test_push_mid_and_regime_file_fallback(tmp_path, monkeypatch):
    import backend.services.exchange_microstructure_service as micro
    from backend.services import exchange_redis_bus as bus

    monkeypatch.setattr(bus, "get_client", lambda: None)
    monkeypatch.setattr(micro, "_mid_file", lambda symbol: str(tmp_path / f"{symbol}.json"))
    for i in range(25):
        # Gentle walk so vol stays finite.
        push_mid("XRP", 1.0 + i * 0.0001)
    mids = micro._load_mids("XRP")
    assert len(mids) >= 20
    vol = realized_vol_bps(mids)
    assert vol >= 0.0
    regime = regime_for("XRP")
    assert regime["n"] >= 20
    assert regime["state"] in ("calm", "normal", "volatile")


def test_publish_depth_file_bus(tmp_path, monkeypatch):
    from backend.services import exchange_redis_bus as bus
    import backend.services.exchange_microstructure_service as micro

    monkeypatch.setattr(bus, "_FALLBACK_DIR", str(tmp_path / "bus"))
    bus.reset_client()
    monkeypatch.setattr(bus, "get_client", lambda: None)
    backend = publish_depth("SOL", [["80", "2"], ["79.9", "1"]], [["80.1", "0.5"], ["80.2", "0.5"]])
    assert backend == "file"
    row = micro.cached_depth("SOL", max_age_sec=5)
    assert row and row["imbalance"] > 0
