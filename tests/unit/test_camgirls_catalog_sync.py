"""Phase 4 — JSON → SQLite catalog sync."""
import json

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_sync_json_catalog_to_db(tmp_path, monkeypatch):
    from backend.services import camgirls_catalog_db_service as cdb
    from backend.services import camgirls_catalog_sync_service as sync
    from backend.services import camgirls_service as cg

    db = tmp_path / "cam.db"
    json_file = tmp_path / "performers.json"
    performers = {
        "performers": [
            {"id": "performer_sync_a", "display_name": "Sync A", "active": True, "bio": "hi"},
            {"id": "performer_sync_b", "display_name": "Sync B", "active": False},
        ]
    }
    json_file.write_text(json.dumps(performers), encoding="utf-8")

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setenv("CAMGIRLS_CATALOG_SOURCE", "db")
    monkeypatch.setattr(cg, "_PERFORMERS_FILE", str(json_file))

    out = sync.sync_json_catalog_to_db(json_path=str(json_file))
    assert out.get("success") is True
    assert out.get("synced") == 2

    rows = cdb.load_performers_from_db()
    assert rows
    active = [r for r in rows if r.get("active")]
    assert len(active) == 1
    assert active[0]["id"] == "performer_sync_a"

    monkeypatch.setattr(cg, "_PERFORMERS_FILE", str(json_file))
    loaded = cg._load_performers_raw()
    assert any(p.get("id") == "performer_sync_a" for p in loaded)


def test_upsert_performer_writes_db(tmp_path, monkeypatch):
    from backend.services import camgirls_service as cg

    db = tmp_path / "cam.db"
    perf_file = tmp_path / "camgirls_performers.json"
    perf_file.write_text(json.dumps({"performers": []}), encoding="utf-8")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setattr(cg, "_PERFORMERS_FILE", str(perf_file))

    result = cg.upsert_performer(
        {"id": "performer_ops_1", "display_name": "Ops One", "unlock_price_mn2": 12}
    )
    assert result.get("success") is True
    assert result.get("catalog_db_synced") is True
