"""Treasury pool sync from ledger + scanner credit tests."""
import pytest


def test_sync_treasury_pool_from_ledger(tmp_path, monkeypatch):
    from backend.services import agent_wallet_service as aw
    from backend.services import unified_points_database as upd
    from backend.services import mn2_ledger as ledger
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    ledger_path = tmp_path / "mn2_ledger.json"
    monkeypatch.setattr(ledger, "_LEDGER_FILENAME", "mn2_ledger.json")
    monkeypatch.setattr(ledger, "_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    monkeypatch.setattr(upd, "_IDEMPOTENCY_CACHE", {})
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path / "points"))
    monkeypatch.setattr(upd, "unified_points_db", db)

    ledger.append_entry(
        user_id="agent_treasury",
        entry_type="treasury_deposit",
        amount=200.0,
        txid="abc123",
        address="JJi8g5CYTXL6NVW1za4tJtzC1X61M7WRZi",
    )
    r1 = aw.sync_treasury_pool_from_ledger()
    assert r1["synced_count"] == 1
    assert aw.get_treasury_pool_balance() == pytest.approx(200.0, rel=1e-6)
    r2 = aw.sync_treasury_pool_from_ledger()
    assert r2["synced_count"] == 0


def test_is_txid_processed_includes_treasury_deposit(tmp_path, monkeypatch):
    from backend.services import mn2_ledger as ledger

    monkeypatch.setattr(ledger, "_data_dir", lambda: str(tmp_path))
    ledger.append_entry(
        user_id="agent_treasury",
        entry_type="treasury_deposit",
        amount=1.0,
        txid="tx-treasury-1",
    )
    assert ledger.is_txid_processed("tx-treasury-1") is True
    assert ledger.is_txid_processed("tx-other") is False
