"""Agent treasury distribution tests."""
import pytest


def test_distribute_idempotent_top_up(tmp_path, monkeypatch):
    from backend.services import agent_wallet_service as aw
    from backend.services import unified_points_database as upd
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    monkeypatch.setattr(upd, "_IDEMPOTENCY_CACHE", {})
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path / "points"))
    monkeypatch.setattr(upd, "unified_points_db", db)
    monkeypatch.setattr(aw, "_WALLETS_FILE", str(tmp_path / "wallets.json"))
    monkeypatch.setattr(aw, "_TREASURY_FILE", str(tmp_path / "treasury.json"))
    monkeypatch.setattr("backend.services.treasury_signoff_service._SIGNOFF_FILE", str(tmp_path / "signoff.json"))
    monkeypatch.setattr("backend.services.mn2_ledger.append_entry", lambda *a, **k: {"success": True})
    monkeypatch.setattr("backend.services.activity_events_service.emit", lambda *a, **k: {"success": True})

    aw.set_treasury_address("treasury_addr_test", per_agent_mn2=100, trader_count=1)
    db.add_points(aw.TREASURY_POOL_USER, "mn2_balance", 200, source="seed", metadata={"reference": "pool-seed-topup-test"})

    r1 = aw.distribute_agent_funding()
    assert r1.get("success") is True
    assert aw.get_balance("trader_agent_1") == pytest.approx(100, rel=1e-6)

    r2 = aw.distribute_agent_funding()
    assert r2["results"][0].get("skipped") is True
    assert aw.get_treasury_pool_balance() == pytest.approx(100, rel=1e-6)
