"""Casino fund path — MN2 buy-in packs + PayPal capture binding."""
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _fund_app(tmp_path, monkeypatch):
    from flask import Flask
    import backend.services.casino_service as casino
    from backend.routes.casino_routes import casino_bp

    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path / "logs"))
    cfg = tmp_path / "casino_config.json"
    cfg.write_text(
        '{"currency":"coins","min_bet":5,"max_bet":500,"max_bets_per_day":50,'
        '"real_money":{"enabled":true,"rails":["mn2","paypal"],'
        '"paypal_deposit_packs":[{"id":"casino_usd_5","label":"$5","amount_usd":5.0}],'
        '"mn2_buyin_packs":['
        '{"id":"casino_mn2_starter","label":"Starter","price_mn2":25,"casino_usd_credit":8},'
        '{"id":"casino_mn2_grinder","label":"Grinder","price_mn2":75,"casino_usd_credit":25}'
        '],'
        '"paypal_min_bet":0.5,"paypal_max_bet":25.0,"paypal_currency":"USD"},'
        '"deposit_packs":{"enabled":true,"packs":[]},'
        '"tournaments":{"enabled":false,"templates":[]},"jackpot":{"enabled":false},"games":{}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    app.register_blueprint(casino_bp)
    return app


def test_mn2_buyin_packs_include_affordability(tmp_path, monkeypatch):
    app = _fund_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {
        "points": {"mn2_balance": 30, "casino_fiat_balance": 1.5}
    }
    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            resp = client.get("/api/casino/mn2/buyin-packs?user_id=fund-u")
    data = resp.get_json()
    assert data["success"] is True
    assert data["enabled"] is True
    assert data["mn2_balance"] == 30
    starter = next(p for p in data["packs"] if p["id"] == "casino_mn2_starter")
    grinder = next(p for p in data["packs"] if p["id"] == "casino_mn2_grinder")
    assert starter["can_afford"] is True
    assert grinder["can_afford"] is False


def test_mn2_buyin_purchase_returns_balances(tmp_path, monkeypatch):
    app = _fund_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.side_effect = [
        {"points": {"mn2_balance": 40, "casino_fiat_balance": 0}},
        {"points": {"mn2_balance": 15, "casino_fiat_balance": 8}},
        {"points": {"mn2_balance": 15, "casino_fiat_balance": 8}},
    ]
    mock_points.add_points.return_value = {"success": True}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch(
                "backend.services.account_security_service.check_real_money_action",
                return_value=None,
            ):
                resp = client.post(
                    "/api/casino/mn2/buyin",
                    json={"user_id": "fund-buy", "pack_id": "casino_mn2_starter"},
                )
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["casino_usd_credited"] == 8
    assert data["price_mn2"] == 25
    assert "mn2_balance" in data
    assert "fiat_balance" in data
    assert mock_points.add_points.call_count == 2


def test_paypal_capture_rejects_pack_mismatch(tmp_path, monkeypatch):
    app = _fund_app(tmp_path, monkeypatch)
    import backend.services.casino_service as casino

    casino._save_paypal_deposits({
        "pending": {
            "ord-fund-1": {
                "user_id": "fund-pp",
                "pack_id": "casino_usd_5",
                "amount_usd": 5.0,
                "created_at": "2026-11-22T00:00:00+00:00",
            }
        },
        "captured": {},
        "pack_purchases": {},
    })

    with app.test_client() as client:
        resp = client.post(
            "/api/casino/paypal/capture",
            json={
                "user_id": "fund-pp",
                "order_id": "ord-fund-1",
                "pack_id": "weekend_boost_25",
            },
        )
    data = resp.get_json()
    assert resp.status_code == 400
    assert data["success"] is False
    assert "match" in (data.get("error") or "").lower()


def test_paypal_capture_rejects_amount_mismatch(tmp_path, monkeypatch):
    app = _fund_app(tmp_path, monkeypatch)
    import backend.services.casino_service as casino

    casino._save_paypal_deposits({
        "pending": {
            "ord-fund-2": {
                "user_id": "fund-pp2",
                "pack_id": "casino_usd_5",
                "amount_usd": 5.0,
                "created_at": "2026-11-22T00:00:00+00:00",
            }
        },
        "captured": {},
        "pack_purchases": {},
    })

    with app.test_client() as client:
        with patch(
            "backend.services.paypal_service.capture_order",
            return_value={
                "success": True,
                "amount": 25.0,
                "currency": "USD",
                "capture_id": "cap-x",
            },
        ):
            resp = client.post(
                "/api/casino/paypal/capture",
                json={
                    "user_id": "fund-pp2",
                    "order_id": "ord-fund-2",
                    "pack_id": "casino_usd_5",
                },
            )
    data = resp.get_json()
    assert resp.status_code == 400
    assert data.get("code") == "AMOUNT_MISMATCH"
