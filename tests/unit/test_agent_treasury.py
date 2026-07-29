"""Agent treasury distribution + Option C dry-run / live gate tests."""
from contextlib import contextmanager

import pytest


@contextmanager
def _noop_ctx():
    yield


def _setup(tmp_path, monkeypatch, *, live_distribute=True, per_agent=100, count=1):
    from backend.services import agent_wallet_service as aw
    from backend.services import unified_points_database as upd

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    monkeypatch.setattr(upd, "_IDEMPOTENCY_CACHE", {})
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path / "points"))
    monkeypatch.setattr(upd, "unified_points_db", db)
    monkeypatch.setattr(aw, "_WALLETS_FILE", str(tmp_path / "wallets.json"))
    monkeypatch.setattr(aw, "_TREASURY_FILE", str(tmp_path / "treasury.json"))
    monkeypatch.setattr(aw, "_MN2_CONFIG", str(tmp_path / "mn2_config.json"))
    (tmp_path / "mn2_config.json").write_text(
        '{"agent_funding": {"per_agent_mn2": %s, "trader_agent_count": %s, "top_up": true, "live_distribute": %s}}'
        % (per_agent, count, "true" if live_distribute else "false"),
        encoding="utf-8",
    )
    monkeypatch.setattr("backend.services.treasury_signoff_service._SIGNOFF_FILE", str(tmp_path / "signoff.json"))
    monkeypatch.setattr("backend.services.mn2_ledger.append_entry", lambda *a, **k: {"success": True})
    monkeypatch.setattr("backend.services.activity_events_service.emit", lambda *a, **k: {"success": True})
    return aw, db


def test_distribute_idempotent_top_up(tmp_path, monkeypatch):
    aw, db = _setup(tmp_path, monkeypatch, live_distribute=True, per_agent=100, count=1)
    aw.set_treasury_address("treasury_addr_test", per_agent_mn2=100, trader_count=1, live_distribute=True)
    db.add_points(aw.TREASURY_POOL_USER, "mn2_balance", 200, source="seed", metadata={"reference": "pool-seed-topup-test"})

    r1 = aw.distribute_agent_funding(allow_live=True)
    assert r1.get("success") is True
    assert r1.get("dry_run") is False
    assert aw.get_balance("trader_agent_1") == pytest.approx(100, rel=1e-6)

    r2 = aw.distribute_agent_funding(allow_live=True)
    assert r2["results"][0].get("skipped") is True
    assert aw.get_treasury_pool_balance() == pytest.approx(100, rel=1e-6)


def test_default_is_dry_run_when_live_distribute_false(tmp_path, monkeypatch):
    aw, db = _setup(tmp_path, monkeypatch, live_distribute=False, per_agent=100, count=2)
    aw.set_treasury_address("addr", per_agent_mn2=100, trader_count=2, live_distribute=False)
    db.add_points(aw.TREASURY_POOL_USER, "mn2_balance", 500, source="seed", metadata={"reference": "pool-seed-dry"})

    r = aw.distribute_agent_funding()
    assert r.get("success") is True
    assert r.get("dry_run") is True
    assert aw.get_balance("trader_agent_1") == 0
    assert aw.get_treasury_pool_balance() == pytest.approx(500)


def test_treasury_status_reports_gaps(tmp_path, monkeypatch):
    aw, db = _setup(tmp_path, monkeypatch, live_distribute=False, per_agent=1000, count=2)
    aw.set_treasury_address("addr2", per_agent_mn2=1000, trader_count=2, live_distribute=False)
    db.add_points(aw.TREASURY_POOL_USER, "mn2_balance", 50, source="seed", metadata={"reference": "pool-seed-status"})
    st = aw.treasury_status()
    assert st["live_distribute"] is False
    assert st["required_total_mn2"] == pytest.approx(2000)
    assert st["need_total_mn2"] == pytest.approx(2000)
    assert st["pool_covers_need"] is False
    assert st["blocked_reason"] == "live_distribute_false"
    assert len(st["agents"]) == 2


def test_large_batch_requires_signoff(tmp_path, monkeypatch):
    aw, db = _setup(tmp_path, monkeypatch, live_distribute=True, per_agent=100000, count=2)
    aw.set_treasury_address("addr3", per_agent_mn2=100000, trader_count=2, live_distribute=True)
    db.add_points(
        aw.TREASURY_POOL_USER, "mn2_balance", 300000,
        source="seed", metadata={"reference": "pool-seed-big"},
    )
    r = aw.distribute_agent_funding(allow_live=True)
    assert r.get("success") is False
    assert "signoff" in str(r.get("error") or "").lower()


def test_no_over_distribution_beyond_pool(tmp_path, monkeypatch):
    aw, db = _setup(tmp_path, monkeypatch, live_distribute=True, per_agent=100, count=3)
    aw.set_treasury_address("addr4", per_agent_mn2=100, trader_count=3, live_distribute=True)
    db.add_points(aw.TREASURY_POOL_USER, "mn2_balance", 50, source="seed", metadata={"reference": "pool-seed-short"})
    r = aw.distribute_agent_funding(allow_live=True)
    assert r.get("success") is False
    assert r.get("error") == "insufficient_treasury_pool"
    assert aw.get_balance("trader_agent_1") == 0


def test_funding_config_from_mn2_config(tmp_path, monkeypatch):
    aw, _db = _setup(tmp_path, monkeypatch, live_distribute=False, per_agent=123, count=4)
    cfg = aw.load_agent_funding_config()
    assert cfg["per_agent_mn2"] == pytest.approx(123)
    assert cfg["trader_agent_count"] == 4
    assert cfg["required_total_mn2"] == pytest.approx(492)
    assert cfg["live_distribute"] is False


def test_routes_ops_gated_and_dry_run(tmp_path, monkeypatch):
    from flask import Flask
    from backend.routes.agent_treasury_routes import agent_treasury_bp
    from backend.services import agent_wallet_service as aw

    aw_mod, db = _setup(tmp_path, monkeypatch, live_distribute=False, per_agent=100, count=1)
    aw_mod.set_treasury_address("route-addr", per_agent_mn2=100, trader_count=1, live_distribute=False)
    db.add_points(aw.TREASURY_POOL_USER, "mn2_balance", 100, source="seed", metadata={"reference": "pool-route"})

    monkeypatch.setenv("MN2_OPS_SECRET", "test-ops-secret")
    app = Flask(__name__)
    app.register_blueprint(agent_treasury_bp)
    c = app.test_client()

    assert c.get("/api/agents/treasury/status").status_code == 403
    r = c.get("/api/agents/treasury/status", headers={"X-Ops-Secret": "test-ops-secret"})
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("dry_run") is True
    assert body.get("live_distribute") is False

    d = c.post(
        "/api/agents/treasury/distribute",
        headers={"X-Ops-Secret": "test-ops-secret"},
        json={},
    )
    assert d.status_code == 200
    assert d.get_json().get("dry_run") is True
    assert aw_mod.get_balance("trader_agent_1") == 0
