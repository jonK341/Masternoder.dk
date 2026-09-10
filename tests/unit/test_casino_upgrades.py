"""Casino level-up upgrades — catalog count, unlock logic, API endpoints."""
from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _app(tmp_path, monkeypatch):
    from flask import Flask
    import backend.services.casino_service as casino
    from backend.routes.casino_routes import casino_bp

    log_dir = tmp_path / "logs"
    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(log_dir))

    cfg = tmp_path / "casino_config.json"
    cfg.write_text(
        '{"currency":"coins","min_bet":5,"max_bet":500,"max_bets_per_day":50,'
        '"progression":{"levels":[{"level":1,"title":"Rookie","xp_required":0,"reward_coins":0},'
        '{"level":2,"title":"Regular","xp_required":500,"reward_coins":50}],'
        '"xp_per_coin_wagered":1.0}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg))

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    catalog_src = os.path.join(root, "data", "casino_upgrades.json")
    catalog_dst = tmp_path / "casino_upgrades.json"
    catalog_dst.write_text(open(catalog_src, encoding="utf-8").read(), encoding="utf-8")

    import backend.services.casino_upgrades_service as up_svc
    monkeypatch.setattr(up_svc, "_CATALOG_PATH", str(catalog_dst))
    monkeypatch.setattr(up_svc, "_owned_path", lambda: str(log_dir / "casino_upgrades_owned.json"))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    app.register_blueprint(casino_bp)
    return app


def test_catalog_has_250_upgrades(tmp_path, monkeypatch):
    import backend.services.casino_upgrades_service as up_svc

    _app(tmp_path, monkeypatch)
    data = up_svc.get_catalog()
    assert data["success"] is True
    assert data["total"] == 250
    assert len(data["upgrades"]) == 250
    assert len(data["categories"]) == 10
    cats = {c["id"]: c["count"] for c in data["categories"]}
    assert all(v == 25 for v in cats.values())


def test_rtp_audit_compliant(tmp_path, monkeypatch):
    import backend.services.casino_upgrades_service as up_svc

    _app(tmp_path, monkeypatch)
    audit = up_svc.audit_rtp_compliance()
    assert audit["success"] is True
    assert audit["total"] == 250
    assert audit["compliant"] is True
    assert audit["violations"] == []


def test_unlock_first_upgrade_with_coins(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 5000}}

    with app.test_client() as client:
        with patch("backend.services.casino_service.unified_points_db", mock_points, create=True):
            with patch("backend.services.unified_points_database.unified_points_db", mock_points):
                cat = client.get("/api/casino/upgrades/catalog?user_id=up-user")
                assert cat.status_code == 200
                first = cat.get_json()["upgrades"][0]
                assert first["status"] == "available"

                buy = client.post(
                    "/api/casino/upgrades/purchase",
                    json={"user_id": "up-user", "upgrade_id": first["id"], "currency": "coins"},
                )
                assert buy.status_code == 200
                body = buy.get_json()
                assert body["success"] is True
                assert body["progress"]["unlocked"] == 1

                prog = client.get("/api/casino/upgrades/progress?user_id=up-user")
                assert prog.status_code == 200
                assert first["id"] in prog.get_json()["owned_ids"]


def test_prerequisite_blocks_skip(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 999999}}

    with app.test_client() as client:
        with patch("backend.services.casino_service.unified_points_db", mock_points, create=True):
            with patch("backend.services.unified_points_database.unified_points_db", mock_points):
                cat = client.get("/api/casino/upgrades/catalog?user_id=skip-user")
                rows = cat.get_json()["upgrades"]
                with_prereq = next(r for r in rows if r.get("prerequisite"))
                buy = client.post(
                    "/api/casino/upgrades/purchase",
                    json={"user_id": "skip-user", "upgrade_id": with_prereq["id"], "currency": "coins"},
                )
                assert buy.status_code == 400
                assert buy.get_json()["code"] == "PREREQUISITE"


def test_level_gate_blocks_low_level(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 999999}}

    with app.test_client() as client:
        with patch("backend.services.casino_service.unified_points_db", mock_points, create=True):
            with patch("backend.services.unified_points_database.unified_points_db", mock_points):
                cat = client.get("/api/casino/upgrades/catalog?user_id=low-user")
                high = next(r for r in cat.get_json()["upgrades"] if int(r.get("level_required") or 1) >= 10)
                buy = client.post(
                    "/api/casino/upgrades/purchase",
                    json={"user_id": "low-user", "upgrade_id": high["id"], "currency": "coins"},
                )
                assert buy.status_code == 400
                assert buy.get_json()["code"] == "LEVEL_TOO_LOW"


def test_category_filter_api(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    with app.test_client() as client:
        resp = client.get("/api/casino/upgrades/catalog?user_id=cat-user&category=slots")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["count"] == 25
        assert all(u["category"] == "slots" for u in body["upgrades"])
