"""Casino MN2 cashback accrual + claim (Phase 7)."""
from contextlib import contextmanager

from flask import Flask


def test_cashback_accrue_and_claim(tmp_path, monkeypatch):
    from backend.services import casino_mn2_cashback_service as cb
    from backend.services import unified_points_database as upd

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path / "points"))
    monkeypatch.setattr(upd, "unified_points_db", db)
    monkeypatch.setattr(cb, "_STATE", str(tmp_path / "cashback.json"))
    monkeypatch.setattr(cb, "_config", lambda: {"enabled": True, "rate": 0.01, "max_daily_claim_mn2": 1.0, "min_claim_mn2": 0.0001})
    monkeypatch.setattr("backend.services.mn2_ledger.append_entry", lambda *a, **k: {"success": True})
    monkeypatch.setattr("backend.services.activity_events_service.emit", lambda *a, **k: {"success": True})

    accrued = cb.accrue("cash_user", 2.0, game="crash", bet_id="b1")
    assert accrued and accrued["accrued"] == 0.02
    st = cb.status("cash_user")
    assert st["pending_mn2"] == 0.02

    claimed = cb.claim("cash_user", day="2026-07-25")
    assert claimed.get("success") is True
    assert float(claimed.get("mn2_awarded") or 0) == 0.02

    again = cb.claim("cash_user", day="2026-07-25")
    assert again.get("success") is False
    assert again.get("error") == "already_claimed_today"


def test_cashback_routes_reject_anon(tmp_path, monkeypatch):
    from backend.routes.casino_routes import casino_bp
    from backend.services import casino_mn2_cashback_service as cb

    monkeypatch.setattr(cb, "_STATE", str(tmp_path / "cashback.json"))
    app = Flask(__name__)
    app.register_blueprint(casino_bp)
    c = app.test_client()
    r = c.post("/api/casino/mn2/cashback/claim", json={"user_id": "default_user"})
    assert r.status_code in (400, 403)
