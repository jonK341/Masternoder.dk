"""Gate S hardening tests."""
import threading

import pytest


def test_earn_auth_blocks_anonymous():
    from backend.services.mn2_earn_auth import require_earn_user
    ok, err = require_earn_user("default_user")
    assert ok is False
    assert err == "authenticated_user_required"


def test_generator_finish_bonus_blocks_anon():
    from backend.services.generator_mn2_service import award_finish_bonus
    r = award_finish_bonus("anon", "doc123")
    assert r.get("success") is False


def test_admin_audit_log(tmp_path, monkeypatch):
    from backend.services import admin_audit_service as aas

    log = tmp_path / "admin_audit.jsonl"
    monkeypatch.setattr(aas, "_LOG", str(log))
    aas.log_action("test_action", actor="ops", payload={"k": "v"})
    assert "test_action" in log.read_text(encoding="utf-8")


def test_idempotency_duplicate_reference(tmp_path, monkeypatch):
    from backend.services import unified_points_database as upd
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path))
    meta = {"reference": "idem-test-001"}
    r1 = db.add_points("user_s", "mn2_balance", 1.0, source="test", metadata=meta)
    r2 = db.add_points("user_s", "mn2_balance", 1.0, source="test", metadata=meta)
    assert r1.get("success") is True
    assert r2.get("duplicate") is True
    bal = db.get_all_points("user_s")
    assert float(bal["points"]["mn2_balance"]) == 1.0


def test_concurrent_idempotency(tmp_path, monkeypatch):
    from backend.services import unified_points_database as upd
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path))
    errors = []

    def worker(i):
        try:
            db.add_points("user_c", "mn2_balance", 0.1, source="test", metadata={"reference": f"ref-{i}"})
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not errors
    bal = db.get_all_points("user_c")
    mn2 = float(bal["points"].get("mn2_balance") or bal["points"].get("systems", {}).get("mn2_balance") or 0)
    assert mn2 == pytest.approx(0.8, rel=1e-6)
