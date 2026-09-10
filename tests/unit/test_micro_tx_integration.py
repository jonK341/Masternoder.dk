"""Integration tests — micro-tx wired through reward pipelines."""
import pytest


@pytest.fixture
def micro_tx_env(tmp_path, monkeypatch):
    import backend.services.mn2_micro_tx_service as svc

    log_dir = tmp_path / "logs" / "mn2_micro_tx"
    log_dir.mkdir(parents=True)
    cfg_path = tmp_path / "data" / "mn2_micro_tx_config.json"
    cfg_path.parent.mkdir(parents=True)
    cfg_path.write_text(
        '{"enabled":true,"min_amount_mn2":1e-8,"max_amount_mn2":1.0,'
        '"daily_cap_per_user_mn2":10.0,"rate_limit_per_minute":1000,'
        '"allowed_sources":["quest_complete","casino_spin","game_win","shop_purchase",'
        '"referral","daily_login","creator_rating","staking_accrual","aggregator_action"],'
        '"source_default_amounts_mn2":{"quest_complete":0.005,"casino_spin":0.0001,'
        '"game_win":0.002,"shop_purchase":0.01,"referral":0.05,"daily_login":0.001,'
        '"creator_rating":0.002,"staking_accrual":0.00001,"aggregator_action":0.00005}}',
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


@pytest.fixture
def points_db(tmp_path, monkeypatch):
    from backend.services import unified_points_database as upd
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path))
    monkeypatch.setattr(upd, "unified_points_db", db)
    monkeypatch.setattr("backend.services.mn2_ledger.append_entry", lambda *a, **k: {"success": True})
    monkeypatch.setattr("backend.services.activity_events_service.emit", lambda *a, **k: None)
    return db


def test_credit_mn2_reward_routes_quest_via_micro_tx(micro_tx_env, points_db):
    from backend.services.micro_tx_hooks import credit_mn2_reward

    r = credit_mn2_reward(
        "quest_user_1",
        0.005,
        source="trophy_quest",
        reference="tq-daily-1",
        idempotency_key="tq-daily-1",
        metadata={"quest_id": "tq-daily-1"},
    )
    assert r.get("success") is True
    assert r.get("micro_tx") is True
    assert r.get("amount") == pytest.approx(0.005, rel=1e-6)
    bal = points_db.get_all_points("quest_user_1")
    assert float(bal["points"]["mn2_balance"]) == pytest.approx(0.005, rel=1e-6)


def test_game_mn2_rewards_uses_micro_tx(micro_tx_env, points_db):
    from backend.services.game_mn2_rewards import credit_mn2

    r = credit_mn2("battle_user_1", 0.002, source="battle_crypto_claim", reference="battle-ref-1")
    assert r.get("success") is True
    assert r.get("micro_tx") is True


def test_trophy_credit_mn2_helper(micro_tx_env, points_db):
    from backend.services.trophy_level_service import _credit_mn2

    ok = _credit_mn2("trophy_user_1", 0.001, "trophy_income", metadata={"quest_id": "inc-1"})
    assert ok is True
    bal = points_db.get_all_points("trophy_user_1")
    assert float(bal["points"]["mn2_balance"]) >= 0.00001


def test_large_reward_falls_back_to_direct(micro_tx_env, points_db):
    from backend.services.micro_tx_hooks import credit_mn2_reward

    r = credit_mn2_reward(
        "whale_user",
        5.0,
        source="battle_crypto_claim",
        reference="whale-win-1",
    )
    assert r.get("success") is True
    assert r.get("micro_tx") is False
    assert r.get("amount") == pytest.approx(5.0, rel=1e-6)
