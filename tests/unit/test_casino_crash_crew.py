"""Wave 3 — Crash crew, streak shield, coupons, big-win SVG."""
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _wave3_app(tmp_path, monkeypatch):
    from flask import Flask
    import backend.services.casino_service as casino
    from backend.routes.casino_routes import casino_bp

    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path / "logs"))
    cfg = tmp_path / "casino_config.json"
    cfg.write_text(
        '{"currency":"coins","min_bet":5,"max_bet":500,"max_bets_per_day":50,'
        '"games":{"crash":{"label":"Crash","house_edge":0.03,'
        '"growth_per_second":0.13863,"max_round_seconds":60,"max_auto_cashout":100,'
        '"rtp_estimate":97.0}},'
        '"crash_crew":{"enabled":true,"lobby_seconds":30,"min_players":2,"max_players":6},'
        '"streak_shield":{"enabled":true,"shields_per_week":1,"refund_pct":50,"currency":"coins"},'
        '"lab_coupons":{"enabled":true,"codes":{"LAB-FREEBET":{"type":"free_daily_bet","uses":1}}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    app.register_blueprint(casino_bp)
    return app


def test_crash_crew_create_join_launch_cashout(tmp_path, monkeypatch):
    app = _wave3_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000, "mn2_balance": 0}}
    mock_points.add_points.return_value = {"success": True}
    fake_draw = {"float": 0.99, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value=fake_draw):
                created = client.post(
                    "/api/casino/crash-crew/create",
                    json={"user_id": "host1", "bet": 10},
                )
                assert created.status_code == 200
                room_id = created.get_json()["room"]["room_id"]

                joined = client.post(
                    "/api/casino/crash-crew/join",
                    json={"user_id": "guest1", "room_id": room_id},
                )
                assert joined.status_code == 200

                launched = client.post(
                    "/api/casino/crash-crew/launch",
                    json={"user_id": "host1", "room_id": room_id},
                )
                assert launched.status_code == 200
                assert launched.get_json()["room"]["status"] == "live"

                cashout = client.post(
                    "/api/casino/crash-crew/cashout",
                    json={"user_id": "host1", "room_id": room_id, "multiplier": 1.0},
                )
    data = cashout.get_json()
    assert data["success"] is True
    assert data["game"] == "crash_crew"
    assert data["outcome"] in ("win", "loss")


def test_streak_shield_refunds_once(tmp_path, monkeypatch):
    app = _wave3_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 500}}
    mock_points.add_points.return_value = {"success": True}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            st = client.get("/api/casino/streak-shield?user_id=shield-u")
            assert st.get_json()["shields_remaining"] == 1

            first = client.post(
                "/api/casino/streak-shield/apply",
                json={"user_id": "shield-u", "bet": 20, "currency": "coins"},
            )
            assert first.status_code == 200
            assert first.get_json()["refund"] == 10

            second = client.post(
                "/api/casino/streak-shield/apply",
                json={"user_id": "shield-u", "bet": 20, "currency": "coins"},
            )
    assert second.status_code == 400
    assert second.get_json()["error"] == "no_shields_left"


def test_big_win_svg_route(tmp_path, monkeypatch):
    app = _wave3_app(tmp_path, monkeypatch)
    with app.test_client() as client:
        resp = client.get(
            "/api/casino/share/big-win/card.svg?game=crash&net=250&currency=coins&mult=4.5&user_id=u-svg"
        )
    assert resp.status_code == 200
    assert resp.mimetype == "image/svg+xml"
    body = resp.get_data(as_text=True)
    assert "BIG WIN CLIP" in body
    assert "Crash" in body


def test_lab_coupon_redeem_free_bet(tmp_path, monkeypatch):
    app = _wave3_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 500}}
    mock_points.add_points.return_value = {"success": True}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            resp = client.post(
                "/api/casino/coupons/redeem",
                json={"user_id": "coupon-u", "code": "LAB-FREEBET"},
            )
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["type"] == "free_daily_bet"

    with app.test_client() as client:
        dup = client.post(
            "/api/casino/coupons/redeem",
            json={"user_id": "coupon-u", "code": "LAB-FREEBET"},
        )
    assert dup.status_code == 400
    assert dup.get_json()["error"] == "already_redeemed"
