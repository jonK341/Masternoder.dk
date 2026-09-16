"""Tests for Binance clock sync helper."""
from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_binance_timestamp_uses_offset(monkeypatch):
    from backend.services import exchange_binance_time_service as bts

    monkeypatch.setattr(bts, "_offset_ms", 5000.0)
    monkeypatch.setattr(bts, "_last_sync_mono", __import__("time").monotonic())
    ts = bts.binance_timestamp_ms()
    local = int(__import__("time").time() * 1000)
    assert ts >= local + 4000


def test_sync_binance_time_parses_response(monkeypatch):
    from backend.services import exchange_binance_time_service as bts

    class FakeResp:
        status_code = 200

        def json(self):
            return {"serverTime": 1_700_000_000_000}

    monkeypatch.setattr(
        "requests.get",
        lambda *a, **k: FakeResp(),
    )
    out = bts.sync_binance_time()
    assert out["success"] is True
    assert "offset_ms" in out
