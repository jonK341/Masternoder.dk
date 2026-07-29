"""Gate S hardening tests — concurrency, idempotency, ledger conservation."""
import threading
from contextlib import contextmanager

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


@contextmanager
def _noop_ctx():
    yield


def _points_db(tmp_path, monkeypatch):
    from backend.services import unified_points_database as upd

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    monkeypatch.setattr(upd, "_IDEMPOTENCY_CACHE", {})
    return upd.UnifiedPointsDatabase(base_dir=str(tmp_path))


def test_idempotency_duplicate_reference(tmp_path, monkeypatch):
    db = _points_db(tmp_path, monkeypatch)
    meta = {"reference": "idem-test-001"}
    r1 = db.add_points("user_s", "mn2_balance", 1.0, source="test", metadata=meta)
    r2 = db.add_points("user_s", "mn2_balance", 1.0, source="test", metadata=meta)
    assert r1.get("success") is True
    assert r2.get("duplicate") is True
    bal = db.get_all_points("user_s")
    assert float(bal["points"]["mn2_balance"]) == 1.0


def test_concurrent_idempotency(tmp_path, monkeypatch):
    """Distinct refs under concurrency must all credit (no lost updates)."""
    db = _points_db(tmp_path, monkeypatch)
    errors = []

    def worker(i):
        try:
            db.add_points(
                "user_c", "mn2_balance", 0.1, source="test",
                metadata={"reference": f"ref-{i}"},
            )
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


def test_same_reference_storm_credits_once(tmp_path, monkeypatch):
    """Gate S load: many threads, one deposit reference → single credit."""
    db = _points_db(tmp_path, monkeypatch)
    results = []

    def worker():
        results.append(
            db.add_points(
                "user_storm", "mn2_balance", 5.0, source="deposit",
                metadata={"reference": "deposit:txid-same"},
            )
        )

    threads = [threading.Thread(target=worker) for _ in range(32)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    applied = [r for r in results if r.get("success") and not r.get("duplicate")]
    dupes = [r for r in results if r.get("duplicate")]
    assert len(applied) == 1
    assert len(dupes) == 31
    bal = db.get_all_points("user_storm")
    assert float(bal["points"]["mn2_balance"]) == pytest.approx(5.0)


def test_credit_debit_conservation_under_load(tmp_path, monkeypatch):
    """Signed credits/debits under concurrency conserve to expected net."""
    db = _points_db(tmp_path, monkeypatch)
    errors = []

    def credit(i):
        try:
            db.add_points(
                "user_cd", "mn2_balance", 1.0, source="test",
                metadata={"reference": f"credit-{i}"},
            )
        except Exception as exc:
            errors.append(exc)

    def debit(i):
        try:
            db.add_points(
                "user_cd", "mn2_balance", -1.0, source="test",
                metadata={"reference": f"debit-{i}"},
            )
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=credit, args=(i,)) for i in range(20)]
    threads += [threading.Thread(target=debit, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not errors
    bal = db.get_all_points("user_cd")
    assert float(bal["points"]["mn2_balance"]) == pytest.approx(12.0)


def test_escrow_roundtrip_conserves(tmp_path, monkeypatch):
    """Escrow debit + release credit leaves balance unchanged (market-shaped)."""
    db = _points_db(tmp_path, monkeypatch)
    db.add_points(
        "seller", "mn2_balance", 50.0, source="seed",
        metadata={"reference": "seed-seller"},
    )
    db.add_points(
        "seller", "mn2_balance", -20.0, source="p2p_escrow",
        metadata={"reference": "escrow:order-1"},
    )
    db.add_points(
        "seller", "mn2_balance", 20.0, source="p2p_escrow_return",
        metadata={"reference": "escrow-return:order-1"},
    )
    bal = db.get_all_points("seller")
    assert float(bal["points"]["mn2_balance"]) == pytest.approx(50.0)


def test_ledger_concurrent_appends_no_lost_entries(tmp_path, monkeypatch):
    """Gate S: concurrent unique ledger appends must not lose rows."""
    from backend.services import mn2_ledger as ledger

    path = tmp_path / "mn2_ledger.json"
    path.write_text('{"entries": []}', encoding="utf-8")
    monkeypatch.setattr(ledger, "_ledger_path", lambda: str(path))
    monkeypatch.setattr(ledger, "_data_dir", lambda: str(tmp_path))

    n = 40
    errors = []

    def worker(i):
        try:
            ledger.append_entry(
                user_id=f"u{i}",
                entry_type="shop_payment",
                amount=float(i),
                txid=f"shop-{i}",
            )
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not errors
    assert ledger.ledger_entry_count() == n


def test_ledger_deposit_txid_idempotent_under_concurrency(tmp_path, monkeypatch):
    """Same deposit txid under load → one ledger credit row."""
    from backend.services import mn2_ledger as ledger

    path = tmp_path / "mn2_ledger.json"
    path.write_text('{"entries": []}', encoding="utf-8")
    monkeypatch.setattr(ledger, "_ledger_path", lambda: str(path))
    monkeypatch.setattr(ledger, "_data_dir", lambda: str(tmp_path))

    results = []

    def worker():
        results.append(
            ledger.append_entry(
                user_id="depositor",
                entry_type="deposit",
                amount=10.0,
                txid="txid-dup-load",
                address="addr1",
            )
        )

    threads = [threading.Thread(target=worker) for _ in range(24)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert sum(1 for r in results if not r.get("duplicate")) == 1
    assert sum(1 for r in results if r.get("duplicate")) == 23
    assert ledger.is_txid_processed("txid-dup-load") is True
    entries = [e for e in ledger._load_entries() if e.get("txid") == "txid-dup-load"]
    assert len(entries) == 1


def test_deposit_credit_and_ledger_conserve(tmp_path, monkeypatch):
    """Simulated deposit: points + ledger stay aligned under duplicate retries."""
    from backend.services import mn2_ledger as ledger

    db = _points_db(tmp_path, monkeypatch)
    path = tmp_path / "data" / "mn2_ledger.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"entries": []}', encoding="utf-8")
    monkeypatch.setattr(ledger, "_ledger_path", lambda: str(path))
    monkeypatch.setattr(ledger, "_data_dir", lambda: str(path.parent))

    txid = "onchain-abc"
    amount = 3.25

    def attempt():
        db.add_points(
            "user_dep", "mn2_balance", amount, source="mn2_deposit",
            metadata={"reference": f"deposit:{txid}", "txid": txid},
        )
        ledger.append_entry(
            user_id="user_dep", entry_type="deposit", amount=amount, txid=txid,
        )

    threads = [threading.Thread(target=attempt) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    bal = db.get_all_points("user_dep")
    assert float(bal["points"]["mn2_balance"]) == pytest.approx(amount)
    deps = [e for e in ledger._load_entries() if e.get("type") == "deposit"]
    assert len(deps) == 1
    assert float(deps[0]["amount"]) == pytest.approx(amount)
