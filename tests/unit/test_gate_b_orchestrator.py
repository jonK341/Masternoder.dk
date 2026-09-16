"""Gate B orchestrator tests — economy core services."""
import os

import pytest


def test_game_mn2_rewards_rejects_anon():
    from backend.services.game_mn2_rewards import credit_mn2
    r = credit_mn2("default_user", 0.01, source="test", reference="t1")
    assert r.get("success") is False


def test_game_mn2_rewards_credits_authenticated(tmp_path, monkeypatch):
    from backend.services import game_mn2_rewards as gm
    from backend.services import unified_points_database as upd
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    base = tmp_path / "app"
    db = upd.UnifiedPointsDatabase(base_dir=str(base))
    monkeypatch.setattr(upd, "unified_points_db", db)
    r = gm.credit_mn2("user_gate_b", 0.01, source="test_reward", reference="gateb-ref-1")
    assert r.get("success") is True
    bal = db.get_all_points("user_gate_b")
    assert float(bal["points"]["mn2_balance"]) >= 0.01


def test_generator_pricing_importable():
    from backend.services.generator_mn2_service import quote_generation
    from backend.services.generator_pricing_service import pricing_suggestion

    q = quote_generation(tier="express", duration=120)
    assert q.get("success") is True
    assert float(q.get("price_mn2") or 0) >= 0
    ps = pricing_suggestion()
    assert "success" in ps


def test_p2p_market_list_orders():
    from backend.services.p2p_market_service import list_orders
    r = list_orders()
    assert r.get("success") is True
    assert isinstance(r.get("orders"), list)


def test_activity_events_emit(tmp_path, monkeypatch):
    from backend.services import activity_events_service as aes

    log = tmp_path / "activity_events.jsonl"
    monkeypatch.setattr(aes, "_LOG_PATH", str(log))
    aes.emit("test_event", channel="ops", user_id="u1", payload={"x": 1})
    assert log.is_file()
    assert "test_event" in log.read_text(encoding="utf-8")


def test_backup_service(tmp_path, monkeypatch):
    from backend.services import backup_service as bs

    base = tmp_path / "app"
    (base / "data").mkdir(parents=True)
    (base / "logs" / "unified_points").mkdir(parents=True)
    (base / "data" / "mn2_ledger.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(bs, "_BASE", str(base))
    monkeypatch.setattr(bs, "_BACKUP_ROOT", str(base / "backups" / "mn2"))
    r = bs.run_backup()
    assert r.get("success") is True
    assert os.path.isdir(r["backup_dir"])
