"""Wave 5 casino ideas — video poker ladder and PayPal deposit bundles."""
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _wave5_app(tmp_path, monkeypatch):
    from flask import Flask
    import backend.services.casino_service as casino
    from backend.routes.casino_routes import casino_bp

    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path / "logs"))
    cfg = tmp_path / "casino_config.json"
    cfg.write_text(
        '{"currency":"coins","min_bet":5,"max_bet":500,"max_bets_per_day":50,'
        '"real_money":{"enabled":true,"rails":["paypal"],'
        '"paypal_deposit_packs":[{"id":"casino_usd_5","label":"$5","amount_usd":5.0}],'
        '"paypal_min_bet":0.5,"paypal_max_bet":25.0},'
        '"games":{"video_poker":{"rtp_estimate":99.5,'
        '"paytable":{"royal_flush":250,"straight_flush":50,"four_kind":25,'
        '"full_house":9,"flush":6,"straight":4,"three_kind":3,"two_pair":2,"jacks_or_better":1}}},'
        '"video_poker_ladder":{"enabled":true,"rank_by":"daily_rank","rtp_published":99.5,'
        '"tiers":[{"tier_id":"champion","label":"Champion","min_rank":1,"max_rank":1,"paytable_boost":1.2},'
        '{"tier_id":"base","label":"Base","default":true,"min_rank":51,"max_rank":9999,"paytable_boost":1.0}]},'
        '"deposit_packs":{"enabled":true,"packs":[{"id":"starter_welcome_10","label":"Starter",'
        '"amount_usd":10.0,"bonus_usd":2.0,"bonus_coins":100,"starter_only":true,"max_per_user":1}]},'
        '"tournaments":{"enabled":false,"templates":[]},"jackpot":{"enabled":false}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    app.register_blueprint(casino_bp)
    return app


def test_video_poker_ladder_status(tmp_path, monkeypatch):
    app = _wave5_app(tmp_path, monkeypatch)
    with app.test_client() as client:
        with patch(
            "backend.services.casino_video_poker_ladder_service._user_daily_rank",
            return_value=1,
        ):
            resp = client.get("/api/casino/video-poker/ladder?user_id=vp-ladder-u")
    data = resp.get_json()
    assert data["success"] is True
    assert data["enabled"] is True
    assert data["daily_rank"] == 1
    assert data["current_tier"]["tier_id"] == "champion"


def test_video_poker_draw_uses_base_payout(tmp_path, monkeypatch):
    app = _wave5_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    mock_points.add_points.return_value = {"success": True}
    fake_draw = {"float": 0.42, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value=fake_draw):
                with patch(
                    "backend.services.casino_video_poker_ladder_service._user_daily_rank",
                    return_value=1,
                ):
                    start = client.post(
                        "/api/casino/play/video-poker",
                        json={"user_id": "vp-u", "bet": 10},
                    )
                    rid = start.get_json()["round_id"]
                    drawn = client.post(
                        "/api/casino/play/video-poker/draw",
                        json={"user_id": "vp-u", "round_id": rid, "hold": []},
                    )
    data = drawn.get_json()
    assert data["success"] is True
    assert data.get("display_multiplier") is not None
    assert data.get("ladder_tier")
    assert data["multiplier"] == data["details"]["multiplier"]


def test_deposit_packs_route(tmp_path, monkeypatch):
    app = _wave5_app(tmp_path, monkeypatch)
    with app.test_client() as client:
        resp = client.get("/api/casino/deposit/packs?user_id=new-u")
    data = resp.get_json()
    assert data["success"] is True
    assert len(data.get("packs") or []) >= 2
    starter = next(p for p in data["packs"] if p["id"] == "starter_welcome_10")
    assert starter["bonus_usd"] == 2.0
    assert starter["available"] is True


def test_deposit_paypal_create_alias(tmp_path, monkeypatch):
    app = _wave5_app(tmp_path, monkeypatch)
    with app.test_client() as client:
        with patch(
            "backend.services.casino_service.create_paypal_deposit_order",
            return_value={"success": True, "order_id": "ord-w5", "approve_url": "https://paypal.test/approve"},
        ):
            resp = client.post(
                "/api/casino/deposit/paypal/create",
                json={"user_id": "dep-u", "pack_id": "casino_usd_5"},
            )
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["order_id"] == "ord-w5"


def test_starter_pack_unavailable_after_purchase(tmp_path, monkeypatch):
    app = _wave5_app(tmp_path, monkeypatch)
    import backend.services.casino_service as casino

    casino._save_paypal_deposits({
        "pending": {},
        "captured": {"ord1": {"user_id": "repeat-u", "pack_id": "starter_welcome_10", "amount_usd": 10.0}},
        "pack_purchases": {"repeat-u": ["starter_welcome_10"]},
    })
    with app.test_client() as client:
        resp = client.get("/api/casino/deposit/packs?user_id=repeat-u")
    starter = next(p for p in resp.get_json()["packs"] if p["id"] == "starter_welcome_10")
    assert starter["available"] is False


def test_capture_applies_pack_bonuses(tmp_path, monkeypatch):
    app = _wave5_app(tmp_path, monkeypatch)
    import backend.services.casino_service as casino

    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 50, "casino_fiat_balance": 0.0}}
    mock_points.add_points.return_value = {"success": True}

    casino._save_paypal_deposits({
        "pending": {"ord-bonus": {"user_id": "bonus-u", "pack_id": "starter_welcome_10", "amount_usd": 10.0}},
        "captured": {},
    })

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch(
                "backend.services.paypal_service.capture_order",
                return_value={"success": True, "amount": 10.0, "capture_id": "cap-bonus", "currency": "USD"},
            ):
                resp = client.post(
                    "/api/casino/paypal/capture",
                    json={"user_id": "bonus-u", "order_id": "ord-bonus", "pack_id": "starter_welcome_10"},
                )
    data = resp.get_json()
    assert data["success"] is True
    assert data.get("bonus_usd") == 2.0
    assert data.get("bonus_coins") == 100
