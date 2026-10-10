"""Tests for casino competition expansion — shop, trophies, rivals, achievements."""
from __future__ import annotations

import os
import shutil
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()

_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
_DATA = os.path.join(_ROOT, "data")


def _setup_data(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(log_dir))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for name in ("casino_config.json", "casino_shop_catalog.json", "casino_trophies.json", "casino_achievements.json"):
        src = os.path.join(_DATA, name)
        if os.path.isfile(src):
            shutil.copy(src, data_dir / name)
    return data_dir, log_dir


def _casino_app(tmp_path, monkeypatch):
    from flask import Flask
    import backend.services.casino_service as casino
    from backend.routes.casino_routes import casino_bp

    data_dir, _ = _setup_data(tmp_path, monkeypatch)
    cfg_path = data_dir / "casino_config.json"
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg_path))

    import backend.services.casino_shop_service as shop_svc
    import backend.services.casino_trophies_service as trophy_svc
    import backend.services.casino_progression as prog_svc
    monkeypatch.setattr(shop_svc, "_CATALOG_PATH", str(data_dir / "casino_shop_catalog.json"))
    monkeypatch.setattr(trophy_svc, "_TROPHIES_PATH", str(data_dir / "casino_trophies.json"))
    monkeypatch.setattr(prog_svc, "_ACHIEVEMENT_CATALOG_PATH", str(data_dir / "casino_achievements.json"))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    app.register_blueprint(casino_bp)
    return app


def test_shop_catalog_and_purchase(tmp_path, monkeypatch):
    app = _casino_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 50000, "mn2_balance": 10}}
    mock_points.add_points.return_value = {"success": True}
    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            catalog = client.get("/api/casino/shop/catalog?user_id=shop-u")
            assert catalog.status_code == 200
            body = catalog.get_json()
            assert body["success"] is True
            assert body["count"] >= 20
            item_id = body["items"][0]["id"]
            buy = client.post(
                "/api/casino/shop/purchase",
                json={"user_id": "shop-u", "item_id": item_id, "currency": "coins"},
            )
            assert buy.status_code == 200
            assert buy.get_json()["success"] is True
            owned = client.get("/api/casino/shop/owned?user_id=shop-u")
            assert owned.get_json()["count"] >= 1


def test_trophies_list(tmp_path, monkeypatch):
    app = _casino_app(tmp_path, monkeypatch)
    with app.test_client() as client:
        resp = client.get("/api/casino/trophies?user_id=trophy-u")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert len(body["trophies"]) >= 20


def test_achievements_with_progress(tmp_path, monkeypatch):
    app = _casino_app(tmp_path, monkeypatch)
    with app.test_client() as client:
        resp = client.get("/api/casino/achievements?user_id=ach-u")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert len(body["achievements"]) >= 30
        assert "progress_pct" in body["achievements"][0]


def test_rival_board_and_races(tmp_path, monkeypatch):
    app = _casino_app(tmp_path, monkeypatch)
    with app.test_client() as client:
        rivals = client.get("/api/casino/rivals?user_id=rival-u&period=week")
        assert rivals.status_code == 200
        assert rivals.get_json()["success"] is True
        races = client.get("/api/casino/achievement-races?user_id=rival-u")
        assert races.status_code == 200
        assert len(races.get_json()["races"]) >= 3
        crew = client.get("/api/casino/crew-leaderboard?user_id=rival-u")
        assert crew.status_code == 200


def test_dice_duel_create(tmp_path, monkeypatch):
    app = _casino_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    mock_points.add_points.return_value = {"success": True}
    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value={"float": 0.8, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}):
                created = client.post(
                    "/api/casino/duels/create",
                    json={"user_id": "d1", "bet": 10, "game": "dice", "choice": "high"},
                )
                assert created.status_code == 200
                duel_id = created.get_json()["duel"]["duel_id"]
                accepted = client.post(
                    "/api/casino/duels/accept",
                    json={"user_id": "d2", "duel_id": duel_id, "choice": "low"},
                )
                assert accepted.status_code == 200
                assert accepted.get_json()["success"] is True


def test_progression_unlocks_first_bet_achievement(tmp_path, monkeypatch):
    _setup_data(tmp_path, monkeypatch)
    from backend.services import casino_progression
    import backend.services.casino_progression as prog_svc
    data_dir = tmp_path / "data"
    monkeypatch.setattr(prog_svc, "_ACHIEVEMENT_CATALOG_PATH", str(data_dir / "casino_achievements.json"))
    casino_progression._save_state({})
    casino_progression._save_achievements({})
    result = casino_progression.on_bet({
        "user_id": "prog-u",
        "bet": 10,
        "currency": "coins",
        "game": "coin_flip",
        "outcome": "loss",
        "net": -10,
        "created_at": "2026-06-25T12:00:00Z",
    })
    assert result is not None
    ach = casino_progression._load_achievements().get("prog-u") or []
    assert "ach-first-bet" in ach
