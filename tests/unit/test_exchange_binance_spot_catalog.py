"""Binance spot catalog service tests."""
from __future__ import annotations


def test_catalog_batch_rotates(monkeypatch, tmp_path):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_binance_spot_catalog_service as cat

    cache = tmp_path / "binance_spot_catalog.json"
    monkeypatch.setattr(ex, "_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(cat, "_CACHE_PATH", str(cache))
    monkeypatch.setattr(
        cat,
        "refresh_binance_spot_catalog",
        lambda **kw: {
            "success": True,
            "bases_by_quote": {"USDC": ["AAA", "BBB", "CCC", "DDD"]},
            "all_bases": ["AAA", "BBB", "CCC", "DDD"],
            "count": 4,
        },
    )
    batch, nxt, total = cat.catalog_batch(batch_size=2, offset=0, quote="USDC")
    assert batch == ["AAA", "BBB"]
    assert nxt == 2
    assert total == 4
    batch2, nxt2, _ = cat.catalog_batch(batch_size=2, offset=nxt, quote="USDC")
    assert batch2 == ["CCC", "DDD"]
    assert nxt2 == 0
