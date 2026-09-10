"""Unit tests for MN2 micro-transaction instant payout service."""
import pytest

from backend.services.mn2_micro_tx_service import (
    get_config,
    get_platform_stats,
    get_public_config,
    get_user_stats,
    instant_payout,
)


@pytest.fixture
def micro_tx_env(tmp_path, monkeypatch):
    import backend.services.mn2_micro_tx_service as svc

    log_dir = tmp_path / "logs" / "mn2_micro_tx"
    log_dir.mkdir(parents=True)
    cfg_path = tmp_path / "data" / "mn2_micro_tx_config.json"
    cfg_path.parent.mkdir(parents=True)
    cfg_path.write_text(
        '{"enabled":true,"min_amount_mn2":1e-8,"max_amount_mn2":1.0,'
        '"daily_cap_per_user_mn2":0.01,"rate_limit_per_minute":1000,'
        '"allowed_sources":["quest_complete","casino_spin","manual_ops"],'
        '"source_default_amounts_mn2":{"quest_complete":0.005}}',
        encoding="utf-8",
    )

    monkeypatch.setattr(svc, "_BASE", str(tmp_path))
    monkeypatch.setattr(svc, "_CONFIG_PATH", str(cfg_path))
    monkeypatch.setattr(svc, "_LOG_DIR", str(log_dir))
    monkeypatch.setattr(svc, "_LEDGER_PATH", str(log_dir / "ledger.jsonl"))
    monkeypatch.setattr(svc, "_IDEM_PATH", str(log_dir / "idempotency.json"))
    monkeypatch.setattr(svc, "_DAILY_PATH", str(log_dir / "daily_totals.json"))
    monkeypatch.setattr(svc, "_STATS_PATH", str(log_dir / "platform_stats.json"))
    monkeypatch.setattr(svc, "_SWEEP_PATH", str(log_dir / "batch_sweep_queue.json"))
    return svc


def test_config_loads(micro_tx_env):
    cfg = get_config()
    assert cfg.get("enabled") is True
    assert float(cfg.get("max_amount_mn2") or 0) == 1.0


def test_public_config(micro_tx_env):
    pub = get_public_config()
    assert pub.get("success") is True
    assert "quest_complete" in pub.get("allowed_sources", [])


def test_payout_success(micro_tx_env, tmp_path, monkeypatch):
    from backend.services import unified_points_database as upd
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path))

    import backend.services.mn2_micro_tx_service as svc
    monkeypatch.setattr(svc, "_current_balance", lambda uid: 0.005)

    with monkeypatch.context() as m:
        m.setattr(
            "backend.services.mn2_micro_tx_service.unified_points_db",
            db,
            raising=False,
        )
        m.setattr(
            "backend.services.unified_points_database.unified_points_db",
            db,
        )

        r = instant_payout(
            "micro_tx_user_1",
            amount_mn2=0.005,
            reason="test quest",
            source="quest_complete",
            idempotency_key="test-payout-001",
        )
        assert r.get("success") is True
        assert r.get("amount_mn2") == 0.005
        assert r.get("instant") is True


def test_idempotency_duplicate(micro_tx_env, tmp_path, monkeypatch):
    from backend.services import unified_points_database as upd
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path))

    import backend.services.mn2_micro_tx_service as svc
    monkeypatch.setattr(svc, "_current_balance", lambda uid: 0.002)

    with monkeypatch.context() as m:
        m.setattr("backend.services.unified_points_database.unified_points_db", db)

        key = "idem-micro-tx-002"
        r1 = instant_payout("micro_tx_user_2", amount_mn2=0.002, source="manual_ops", idempotency_key=key)
        r2 = instant_payout("micro_tx_user_2", amount_mn2=0.002, source="manual_ops", idempotency_key=key)
        assert r1.get("success") is True
        assert r2.get("duplicate") is True

        bal = db.get_all_points("micro_tx_user_2")
        mn2 = float(bal["points"].get("mn2_balance") or 0)
        assert mn2 == pytest.approx(0.002, rel=1e-6)


def test_daily_cap_blocks(micro_tx_env, tmp_path, monkeypatch):
    from backend.services import unified_points_database as upd
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path))

    import backend.services.mn2_micro_tx_service as svc
    monkeypatch.setattr(svc, "_current_balance", lambda uid: 0.0)

    with monkeypatch.context() as m:
        m.setattr("backend.services.unified_points_database.unified_points_db", db)

        r1 = instant_payout("cap_user", amount_mn2=0.008, source="manual_ops", idempotency_key="cap-1")
        r2 = instant_payout("cap_user", amount_mn2=0.008, source="manual_ops", idempotency_key="cap-2")
        assert r1.get("success") is True
        assert r2.get("success") is False
        assert r2.get("code") == "daily_cap"


def test_max_amount_rejected(micro_tx_env):
    r = instant_payout("micro_tx_user_3", amount_mn2=5.0, source="manual_ops")
    assert r.get("success") is False
    assert r.get("code") == "above_max"


def test_source_denied(micro_tx_env):
    r = instant_payout("micro_tx_user_4", amount_mn2=0.001, source="unknown_source")
    assert r.get("success") is False
    assert r.get("code") == "source_denied"


def test_anon_user_rejected(micro_tx_env):
    r = instant_payout("default_user", amount_mn2=0.001, source="manual_ops")
    assert r.get("success") is False
    assert r.get("code") == "auth_required"


def test_platform_stats(micro_tx_env):
    stats = get_platform_stats()
    assert stats.get("success") is True
    assert "total_volume_mn2" in stats


def test_user_stats_empty(micro_tx_env):
    stats = get_user_stats("nonexistent_micro_user")
    assert stats.get("success") is True
    assert stats.get("earned_today_mn2") == 0.0
