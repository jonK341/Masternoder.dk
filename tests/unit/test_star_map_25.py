"""
Unit tests for Star Map 25 (Top 25 hardening).
Run: .venv/bin/python -m pytest tests/unit/test_star_map_25.py -q
"""
import json
from pathlib import Path
from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()

ROOT = Path(__file__).resolve().parents[2]


def _app():
    from flask import Flask
    from backend.routes.star_map_routes import star_map_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(star_map_bp)
    return app


def test_star_map_25_data_has_25_unique_points():
    data = json.loads((ROOT / "data" / "star_map_25.json").read_text(encoding="utf-8"))
    points = data.get("points") or []
    assert len(points) == 25
    ids = [p.get("id") for p in points]
    assert all(ids)
    assert len(set(ids)) == 25


def test_starmap25_events_have_active_window():
    from backend.routes import star_map_routes as sm

    payload = sm._active_star_map_events()
    assert isinstance(payload.get("active"), list)
    assert len(payload["active"]) >= 1, "expected at least one live Star Map event"
    assert any(e.get("id") == "hydraphur_revolt" for e in payload["active"])


def test_log_event_participation_writes_without_active_event(tmp_path, monkeypatch):
    from backend.routes import star_map_routes as sm

    log_path = tmp_path / "starmap25_events.jsonl"
    monkeypatch.setattr(sm, "STAR_MAP_25_EVENT_LOG_PATH", str(log_path))
    sm._log_event_participation("u_test", "investigate", "terra_sol", [], {"points_awarded": 12})
    assert log_path.is_file()
    rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["action"] == "investigate"
    assert rows[0]["event_active"] is False
    assert rows[0]["event_ids"] == []


def test_get_star_map_25_and_health_endpoints():
    client = _app().test_client()
    r = client.get("/api/star-map/25")
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("success") is True
    points = (body.get("star_map_25") or {}).get("points") or []
    assert len(points) == 25

    h = client.get("/api/star-map/25/health")
    assert h.status_code in (200, 500)
    health = h.get_json()
    assert "checks" in health
    assert "success" in health


def test_events_endpoint_lists_active():
    client = _app().test_client()
    r = client.get("/api/star-map/25/events")
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("success") is True
    assert len(body.get("active_events") or []) >= 1


def test_build_allows_different_building_types_on_same_planet(tmp_path, monkeypatch):
    from backend.routes import star_map_routes as sm

    buildup_path = tmp_path / "starmap25_buildup.json"
    buildup_path.write_text(json.dumps({"users": {}}), encoding="utf-8")
    monkeypatch.setattr(sm, "STAR_MAP_25_BUILDUP_PATH", str(buildup_path))

    inv_path = tmp_path / "investigations.json"
    inv_path.write_text(json.dumps({"u_build": ["terra_sol"]}), encoding="utf-8")
    monkeypatch.setattr(sm, "STAR_MAP_25_INVESTIGATIONS_PATH", str(inv_path))

    class _FakePts:
        def get_all_points(self, user_id):
            return {"points": {"game_points": 10000}}

        def add_points(self, *args, **kwargs):
            return True

    app = _app()
    with patch("backend.services.unified_points_database.unified_points_db", _FakePts()):
        client = app.test_client()
        first = client.post(
            "/api/star-map/25/build",
            json={
                "user_id": "u_build",
                "point_id": "terra_sol",
                "planet": "Terra",
                "building_id": "outpost",
            },
        )
        assert first.status_code == 200, first.get_json()
        assert first.get_json().get("success") is True

        second = client.post(
            "/api/star-map/25/build",
            json={
                "user_id": "u_build",
                "point_id": "terra_sol",
                "planet": "Terra",
                "building_id": "listening_post",
            },
        )
        assert second.status_code == 200, second.get_json()
        assert second.get_json().get("success") is True

        third = client.post(
            "/api/star-map/25/build",
            json={
                "user_id": "u_build",
                "point_id": "terra_sol",
                "planet": "Terra",
                "building_id": "outpost",
            },
        )
        assert third.status_code == 400
        err = third.get_json()
        assert err.get("success") is False
        assert "maximum" in (err.get("error") or "").lower()


def test_deploy_manifest_includes_gameplay_json():
    from scripts import deploy as deploy_mod

    files = deploy_mod.MANIFESTS["starmap25"]
    required = [
        "data/starmap25_buildings.json",
        "data/starmap25_units.json",
        "data/starmap25_events.json",
        "data/starmap25_buildup.json",
        "data/starmap25_invasions.json",
        "docs/STARMAP25_TODO_25.md",
        "starmap25/index.html",
    ]
    for path in required:
        assert path in files, f"missing from starmap25 deploy manifest: {path}"


def test_monitor_ui_keeps_cards_on_monitor_tab():
    html = (ROOT / "starmap25" / "index.html").read_text(encoding="utf-8")
    assert "TABS_WITH_CARDS" in html
    assert "monitor: true" in html
