from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _app(tmp_path, monkeypatch):
    from flask import Flask
    import backend.services.casino_service as casino
    from backend.routes.casino_routes import casino_bp

    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path / "logs"))
    cfg = tmp_path / "casino_config.json"
    cfg.write_text(
        '{"currency":"coins","min_bet":5,"max_bet":500,"max_bets_per_day":50,'
        '"games":{"coin_flip":{"label":"Coin flip","payout_multiplier":1.9,"choices":["heads","tails"]},'
        '"dice":{"label":"Dice","payout_multiplier":4,"sides":6},'
        '"rps_bet":{"label":"RPS","payout_multiplier":2,"choices":["rock","paper","scissors"]}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    app.register_blueprint(casino_bp)
    return app


def test_casino_config_and_balance(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 100}}

    with app.test_client() as client:
        with patch("backend.services.casino_service.unified_points_db", mock_points, create=True):
            with patch("backend.services.unified_points_database.unified_points_db", mock_points):
                cfg = client.get("/api/casino/settings")
                bal = client.get("/api/casino/balance?user_id=user-a")

    assert cfg.status_code == 200
    assert cfg.get_json()["success"] is True
    assert "coin_flip" in cfg.get_json()["games"]
    assert bal.status_code == 200
    bal_json = bal.get_json()
    assert bal_json["balance"] == 100
    assert "disclaimer" in bal_json
    assert "coin_flip" in bal_json["games"]


def test_coin_flip_deducts_and_pays(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.side_effect = [
        {"points": {"coins": 100}},
        {"points": {"coins": 90}},
        {"points": {"coins": 137}},
    ]
    mock_points.add_points.return_value = {"success": True}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_service.random.choice", return_value="heads"):
                response = client.post("/api/casino/play/coin-flip", json={
                    "user_id": "user-a",
                    "bet": 10,
                    "choice": "heads",
                })

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["outcome"] == "win"
    assert data["payout"] == 19
    assert mock_points.add_points.call_count == 2


def test_insufficient_coins_rejected(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1}}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            response = client.post("/api/casino/play/dice", json={
                "user_id": "user-a",
                "bet": 10,
                "guess": 3,
            })

    assert response.status_code == 400
    assert response.get_json()["error"] == "Insufficient coins"
