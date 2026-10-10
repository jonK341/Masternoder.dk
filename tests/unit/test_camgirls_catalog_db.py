"""Camgirls DB catalog read path."""
import json
import os
import sqlite3

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_load_performers_from_db_roundtrip(tmp_path, monkeypatch):
    from backend.services import camgirls_catalog_db_service as cdb
    from backend.services import camgirls_service as cg

    db = tmp_path / "cam.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        """CREATE TABLE camgirls_performers (
           performer_id TEXT UNIQUE, stage_name TEXT, bio TEXT, status TEXT,
           payload_json TEXT, payout_address TEXT)"""
    )
    payload = {
        "id": "performer_db_1",
        "display_name": "DB Star",
        "unlock_price_mn2": 9,
        "tip_min_mn2": 5,
        "active": True,
        "ai_enabled": True,
    }
    conn.execute(
        "INSERT INTO camgirls_performers VALUES (?,?,?,?,?,?)",
        ("performer_db_1", "DB Star", "From DB", "active", json.dumps(payload), None),
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setenv("CAMGIRLS_CATALOG_SOURCE", "auto")
    monkeypatch.setattr(cg, "_PERFORMERS_FILE", str(tmp_path / "missing.json"))

    rows = cdb.load_performers_from_db()
    assert rows and rows[0]["id"] == "performer_db_1"
    loaded = cg._load_performers_raw()
    assert any(p.get("id") == "performer_db_1" for p in loaded)

    monkeypatch.setenv("CAMGIRLS_CATALOG_SOURCE", "json")
    assert not any(p.get("id") == "performer_db_1" for p in cg._load_performers_raw())


def test_provision_payout_addresses_cached(tmp_path, monkeypatch):
    from backend.services import camgirls_payout_service as pay

    monkeypatch.setattr(pay, "_PAYOUT_FILE", str(tmp_path / "payout.json"))
    pay._write({"performers": {"p1": {"address": "JCachedAddr", "created_at": "t"}}})
    out = pay.provision_payout_addresses(performer_ids=["p1"])
    assert out.get("success") is True
    assert out["results"][0].get("created") is False


def test_livekit_stub_without_env(monkeypatch):
    from backend.services.camgirls_livekit_service import issue_voice_token

    monkeypatch.delenv("LIVEKIT_URL", raising=False)
    monkeypatch.delenv("LIVEKIT_API_KEY", raising=False)
    monkeypatch.delenv("LIVEKIT_API_SECRET", raising=False)
    out = issue_voice_token("user_a", "performer_nova", require_unlock=False)
    assert out.get("success") is True
    assert out.get("mode") == "stub"
