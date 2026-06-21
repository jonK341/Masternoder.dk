"""Security cron endpoint tests."""
import os
import sys
from types import ModuleType

from flask import Flask


def _app():
    from backend.routes.security_cron_routes import security_cron_bp
    app = Flask(__name__)
    app.register_blueprint(security_cron_bp)
    return app


def test_security_sweep_localhost(monkeypatch):
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)
    monkeypatch.delenv("DISCORD_OPS_SECRET", raising=False)
    monkeypatch.setattr(
        "backend.services.mn2_conservation_gate.conservation_gate",
        lambda: {"success": True, "ok": True},
    )
    monkeypatch.setattr(
        "backend.services.mn2_deposit_scanner.run_scanner",
        lambda: {"success": True, "scanned": 0},
    )
    monkeypatch.setattr(
        "backend.services.mn2_balance_commit.recover_stale",
        lambda max_age_minutes=30: {"success": True, "recovered": 0},
    )
    monkeypatch.setattr(
        "backend.services.webhook_outbox.process_pending",
        lambda limit=50: {"success": True, "processed": 0},
    )
    fake_casino = ModuleType("backend.services.casino_discord_fanout")
    fake_casino.run_fanout = lambda: {"success": True, "sent": 0}
    monkeypatch.setitem(sys.modules, "backend.services.casino_discord_fanout", fake_casino)
    monkeypatch.setattr(
        "backend.services.backup_service.run_backup",
        lambda: {"success": True, "backup_dir": "mock"},
    )
    app = _app()
    client = app.test_client()
    r = client.post("/api/security/cron/sweep", environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert "results" in data


def test_security_backup_localhost(monkeypatch, tmp_path):
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)
    monkeypatch.delenv("DISCORD_OPS_SECRET", raising=False)
    from backend.services import backup_service as bs
    base = tmp_path / "app"
    (base / "data").mkdir(parents=True)
    (base / "data" / "mn2_ledger.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(bs, "_BASE", str(base))
    monkeypatch.setattr(bs, "_BACKUP_ROOT", str(base / "backups" / "mn2"))

    app = _app()
    client = app.test_client()
    r = client.post("/api/security/cron/backup", environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200
    assert r.get_json().get("success") is True
