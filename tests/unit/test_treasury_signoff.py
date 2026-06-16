"""Treasury cold-wallet sign-off gate tests."""
import json
import pytest


@pytest.fixture
def signoff_paths(tmp_path, monkeypatch):
    from backend.services import treasury_signoff_service as tss

    signoff_file = tmp_path / "treasury_signoff.json"
    monkeypatch.setattr(tss, "_SIGNOFF_FILE", str(signoff_file))
    return tss


def test_not_signed_off_blocks_large_batch(signoff_paths):
    tss = signoff_paths
    err = tss.assert_distribution_allowed(estimated_total_mn2=600_000)
    assert err is not None
    assert "signoff" in err.lower()


def test_small_batch_allowed_without_signoff(signoff_paths):
    tss = signoff_paths
    assert tss.assert_distribution_allowed(estimated_total_mn2=50_000) is None


def test_record_and_get_signoff(signoff_paths, monkeypatch):
    tss = signoff_paths
    monkeypatch.setattr(tss, "reconcile_snapshot", lambda: {"ok": True, "checks": []})
    monkeypatch.setattr(
        "backend.services.agent_wallet_service.get_treasury",
        lambda: {"address": "hot_addr", "per_agent_mn2": 100000, "trader_agent_count": 6},
    )
    monkeypatch.setattr("backend.services.agent_wallet_service.get_treasury_pool_balance", lambda: 50000)

    r = tss.record_signoff(
        approver="Jon",
        cold_wallet_address="MColdWalletAddr123456789",
        max_batch_mn2=600000,
        notes="MN2_OPS §8.6",
    )
    assert r["success"] is True
    assert tss.is_signed_off() is True
    status = tss.get_signoff()
    assert status["signed"] is True
    assert status["signoff"]["approver"] == "Jon"


def test_distribute_blocked_without_signoff(tmp_path, monkeypatch):
    from backend.services import agent_wallet_service as aw
    from backend.services import unified_points_database as upd
    from backend.services import treasury_signoff_service as tss
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
    monkeypatch.setattr(tss, "_SIGNOFF_FILE", str(tmp_path / "signoff.json"))
    monkeypatch.setattr("backend.services.mn2_ledger.append_entry", lambda *a, **k: {"success": True})
    monkeypatch.setattr("backend.services.activity_events_service.emit", lambda *a, **k: {"success": True})

    aw.set_treasury_address("treasury_addr_test", per_agent_mn2=100_000, trader_count=6)
    db.add_points(aw.TREASURY_POOL_USER, "mn2_balance", 700_000, source="seed", metadata={"reference": "pool-seed-block-test"})

    blocked = aw.distribute_agent_funding()
    assert blocked.get("success") is False
    assert "signoff" in (blocked.get("error") or "").lower()

    monkeypatch.setattr(tss, "reconcile_snapshot", lambda: {"ok": True, "checks": []})
    tss.record_signoff(
        approver="Jon",
        cold_wallet_address="MColdWalletAddr123456789",
        max_batch_mn2=600000,
    )
    ok = aw.distribute_agent_funding()
    assert ok.get("success") is True
    assert ok.get("distributed_total") == pytest.approx(600_000, rel=1e-6)
