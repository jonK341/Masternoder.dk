"""Dedicated tests for game_mn2_rewards service."""
import pytest


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
    monkeypatch.setattr("backend.services.activity_events_service.emit", lambda *a, **k: {"success": True})
    return db


def test_credit_rejects_anonymous():
    from backend.services.game_mn2_rewards import credit_mn2
    r = credit_mn2("guest", 0.01, source="battle", reference="r1")
    assert r.get("success") is False


def test_credit_idempotent(points_db):
    from backend.services.game_mn2_rewards import credit_mn2
    r1 = credit_mn2("player_a", 0.05, source="battle", reference="battle-win-1")
    r2 = credit_mn2("player_a", 0.05, source="battle", reference="battle-win-1")
    assert r1.get("success") is True
    assert r2.get("duplicate") is True
    bal = points_db.get_all_points("player_a")
    assert float(bal["points"]["mn2_balance"]) == pytest.approx(0.05, rel=1e-6)
