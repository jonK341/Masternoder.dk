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


def test_shop_catalog_has_stable_starmap25_consumables():
    from backend.services.shop_catalog_seed import build_seed_shop_items

    items = build_seed_shop_items(include_dynamic_offers=False)
    by_id = {i["id"]: i for i in items}
    for item_id in (
        "starmap25-booster-1h",
        "starmap25-level-skip",
        "starmap25-daily-reset-bonus",
        "starmap25-structure-unlock",
        "starmap25-level-pack",
        "starmap25-unit-marines",
        "starmap25-unit-mechanicus",
        "starmap25-unit-inquisition",
    ):
        assert item_id in by_id, item_id
        assert by_id[item_id]["category"] == "starmap25"


def test_trophy_semantics_terra_first_and_segmentum_full(tmp_path, monkeypatch):
    from backend.routes import star_map_routes as sm

    solar_ids = [
        p["id"] for p in sm._load_star_map_25()["points"]
        if p.get("segmentum") == "Solar"
    ]
    # Put a non-Terra system first so Segmentum Clear ≠ Terra trophy
    if "mars_sol" in solar_ids:
        solar_ids = ["mars_sol"] + [pid for pid in solar_ids if pid != "mars_sol"]

    inv_path = tmp_path / "investigations.json"
    inv_path.write_text(json.dumps({
        "u_terra": ["terra_sol", "mars_sol"],
        "u_seg": solar_ids,
    }), encoding="utf-8")
    monkeypatch.setattr(sm, "STAR_MAP_25_INVESTIGATIONS_PATH", str(inv_path))
    buildup_path = tmp_path / "buildup.json"
    buildup_path.write_text(json.dumps({"users": {}}), encoding="utf-8")
    monkeypatch.setattr(sm, "STAR_MAP_25_BUILDUP_PATH", str(buildup_path))

    terra = sm._compute_starmap25_trophies("u_terra")
    assert terra["terra"] is True
    assert terra["full_clear"] is False
    assert terra["lore_master"] is False

    seg = sm._compute_starmap25_trophies("u_seg")
    assert seg["segmentum_clear"] is True
    assert seg["terra"] is False  # first investigation is not terra_sol


def test_consume_level_skip_and_daily_reset(tmp_path, monkeypatch):
    from backend.routes import star_map_routes as sm

    buildup_path = tmp_path / "buildup.json"
    buildup_path.write_text(json.dumps({"users": {}}), encoding="utf-8")
    monkeypatch.setattr(sm, "STAR_MAP_25_BUILDUP_PATH", str(buildup_path))
    inv_path = tmp_path / "investigations.json"
    inv_path.write_text(json.dumps({"u_consume": ["terra_sol"]}), encoding="utf-8")
    monkeypatch.setattr(sm, "STAR_MAP_25_INVESTIGATIONS_PATH", str(inv_path))

    client = _app().test_client()
    reserved = {"item_name": "System Level Skip Token", "item_id": "starmap25-level-skip"}
    with patch.object(sm, "_consume_inventory_item", return_value=("starmap25-level-skip", reserved)):
        r = client.post(
            "/api/star-map/25/consume-shop-item",
            json={"user_id": "u_consume", "item_id": "starmap25-level-skip", "point_id": "terra_sol"},
        )
        assert r.status_code == 200, r.get_json()
        body = r.get_json()
        assert body["success"] is True
        assert body["effect"] == "starmap25_level_skip"
        assert body["result"]["new_level"] >= 2

    with patch.object(sm, "_consume_inventory_item", return_value=("starmap25-daily-reset-bonus", {"item_name": "Daily Reset Bonus 24h"})):
        r2 = client.post(
            "/api/star-map/25/consume-shop-item",
            json={"user_id": "u_consume", "item_id": "starmap25-daily-reset-bonus"},
        )
        assert r2.status_code == 200, r2.get_json()
        assert r2.get_json()["effect"] == "starmap25_daily_reset_bonus"
        assert sm._personal_daily_reset_bonus_active("u_consume") is True


def test_special_unit_unlock_and_deploy_gate(tmp_path, monkeypatch):
    from backend.routes import star_map_routes as sm

    buildup_path = tmp_path / "buildup.json"
    buildup_path.write_text(json.dumps({"users": {}}), encoding="utf-8")
    monkeypatch.setattr(sm, "STAR_MAP_25_BUILDUP_PATH", str(buildup_path))
    inv_path = tmp_path / "investigations.json"
    inv_path.write_text(json.dumps({"u_special": ["terra_sol"]}), encoding="utf-8")
    monkeypatch.setattr(sm, "STAR_MAP_25_INVESTIGATIONS_PATH", str(inv_path))

    # Baseline roster excludes specials until unlocked
    unlocked = set(sm._user_unlocked_specials("u_special"))
    assert "guard" in unlocked
    assert "marines" not in unlocked

    sm.unlock_starmap25_special_unit("u_special", "marines")
    assert "marines" in sm._user_unlocked_specials("u_special")

    class _FakePts:
        def get_all_points(self, user_id):
            return {"points": {"game_points": 10000}}

        def add_points(self, *args, **kwargs):
            return True

    with patch("backend.services.unified_points_database.unified_points_db", _FakePts()):
        client = _app().test_client()
        # Without unlock, mechanicus blocked
        blocked = client.post(
            "/api/star-map/25/deploy",
            json={
                "user_id": "u_special",
                "point_id": "terra_sol",
                "planet": "Terra",
                "unit_id": "mechanicus",
            },
        )
        assert blocked.status_code == 400
        assert "not unlocked" in (blocked.get_json().get("error") or "").lower()

        ok = client.post(
            "/api/star-map/25/deploy",
            json={
                "user_id": "u_special",
                "point_id": "terra_sol",
                "planet": "Terra",
                "unit_id": "marines",
            },
        )
        assert ok.status_code == 200, ok.get_json()


def test_booster_matcher_accepts_stable_ids():
    from backend.routes import star_map_routes as sm

    with patch.object(sm, "_get_points_snapshot", return_value={
        "active_boosters": [
            {"id": "starmap25-booster-6h", "name": "Star Map 25 Booster 6h", "expires_at": "2099-01-01T00:00:00"},
            {"id": "xp-booster", "name": "XP Booster 1h", "expires_at": "2099-01-01T00:00:00"},
        ]
    }):
        active = sm._active_starmap25_boosters("u")
        assert len(active) == 1
        assert sm._starmap25_booster_multiplier("u") == 2.0


def test_game_tab_has_deploy_invade_actions():
    html = (ROOT / "game" / "index.html").read_text(encoding="utf-8")
    assert "starmap25-deploy-btn" in html
    assert "starmap25-invade-btn" in html
    assert "starmap25_booster_multiplier" in html


def test_trophies_page_loads_starmap25_progress():
    html = (ROOT / "trophies" / "index.html").read_text(encoding="utf-8")
    assert "loadStarMap25TrophyProgress" in html
    assert "starmap25-trophy-list" in html
