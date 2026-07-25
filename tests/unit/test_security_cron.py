"""Security cron endpoint tests (Phase 9)."""
from flask import Flask


def _app(monkeypatch):
    monkeypatch.delenv("MN2_OPS_SECRET", raising=False)
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)
    monkeypatch.delenv("DISCORD_OPS_SECRET", raising=False)
    from backend.routes.security_cron_routes import security_cron_bp
    app = Flask(__name__)
    app.register_blueprint(security_cron_bp)
    return app


def test_security_presets():
    from backend.services.security_cron_service import list_presets, PRESETS
    data = list_presets()
    assert data["success"] is True
    assert "sweep" in data["presets"]
    assert "full" in PRESETS


def test_security_sweep_localhost(monkeypatch):
    monkeypatch.setattr(
        "backend.services.security_cron_service.run_security_sweep",
        lambda **kwargs: {"success": True, "ok": True, "jobs": ["conservation"], "results": {"conservation": {"ok": True}}},
    )
    c = _app(monkeypatch).test_client()
    r = c.post("/api/security/cron/sweep", json={"preset": "sweep"}, environ_base={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("ok") is True


def test_security_sweep_runs_jobs(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "backend.services.mn2_conservation_gate.conservation_gate",
        lambda: {"success": True, "ok": True},
    )
    monkeypatch.setattr(
        "backend.services.points_drift_service.scan_all",
        lambda limit=100: {"success": True, "scanned": 0},
    )
    monkeypatch.setattr(
        "backend.services.mn2_deposit_scanner.run_scanner",
        lambda: {"success": True, "scanned": 0},
    )
    monkeypatch.setattr(
        "backend.services.agent_admin_service.reconcile_treasury_pool",
        lambda: {"ok": True, "pool_balance_mn2": 0},
    )
    monkeypatch.setattr(
        "backend.services.agent_kill_switch.get_status",
        lambda: {"success": True, "global_halt": False},
    )
    from backend.services import security_cron_service as scs
    monkeypatch.setattr(scs, "_RISK_LOG", str(tmp_path / "risk.jsonl"))
    monkeypatch.setattr(scs, "_ACTIVITY", str(tmp_path / "act.jsonl"))
    out = scs.run_security_sweep(preset="sweep")
    assert out["success"] is True
    assert "conservation" in out["results"]
    assert "withdrawal_risk" in out["results"]
    assert "anomaly" in out["results"]


def test_security_backup_localhost(monkeypatch, tmp_path):
    from backend.services import backup_service as bs
    base = tmp_path / "app"
    (base / "data").mkdir(parents=True)
    (base / "data" / "mn2_ledger.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(bs, "_BASE", str(base))
    monkeypatch.setattr(bs, "_BACKUP_ROOT", str(base / "backups" / "mn2"))
    c = _app(monkeypatch).test_client()
    r = c.post("/api/security/cron/backup", environ_base={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200
    assert r.get_json().get("success") is True


def test_security_presets_route(monkeypatch):
    c = _app(monkeypatch).test_client()
    r = c.get("/api/security/cron/presets")
    assert r.status_code == 200
    assert "sweep" in (r.get_json().get("presets") or {})
