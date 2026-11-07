"""Tests for hosting treasury → preferred wallet transfer."""
from __future__ import annotations

import json
from contextlib import contextmanager


def test_transfer_agent_treasury_to_preferred_dry_run(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir(parents=True)

    cfg = {
        "enabled": True,
        "collateral_mn2": 5000,
        "ops": {"preferred_wallet_user_id": "user_test_preferred"},
    }
    (data / "mn2_masternode_config.json").write_text(json.dumps(cfg), encoding="utf-8")
    (data / "mn2_masternode_hosts.json").write_text(json.dumps({"hosts": []}), encoding="utf-8")

    import backend.services.mn2_masternode_service as mn_svc
    import backend.services.mn2_hosting_treasury_ops as ht
    import backend.services.unified_points_database as upd

    monkeypatch.setattr(mn_svc, "_base", lambda: str(tmp_path))

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    monkeypatch.setattr(upd, "_IDEMPOTENCY_CACHE", {})
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path / "logs" / "unified_points"))
    monkeypatch.setattr(upd, "unified_points_db", db)
    monkeypatch.setattr("backend.services.mn2_ledger.append_entry", lambda *a, **k: None)

    db.add_points("agent_treasury", "mn2_balance", 100_000, source="seed", metadata={"reference": "seed-treasury"})
    db.add_points("user_test_preferred", "mn2_balance", 10, source="seed", metadata={"reference": "seed-pref"})

    out = ht.transfer_agent_treasury_to_preferred(20_000, dry_run=True)
    assert out["success"] is True
    assert out["to_user"] == "user_test_preferred"
    assert out["treasury_after_mn2"] == 80_000
    assert out["preferred_after_mn2"] == 20_010
