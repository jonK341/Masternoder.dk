"""Operator cashflow — income aggregator + fail-closed ops auth."""
import json
from datetime import datetime, timezone
from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_summarize_includes_cashflow_blocks(tmp_path, monkeypatch):
    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path / "logs"))
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    (log_dir / "casino_paypal_deposits.json").write_text(
        json.dumps({
            "pending": {},
            "captured": {
                "ord1": {
                    "user_id": "u1",
                    "pack_id": "casino_usd_5",
                    "amount_usd": 5.0,
                    "bonus_usd": 0,
                    "captured_at": now,
                }
            },
        }),
        encoding="utf-8",
    )
    with (log_dir / "casino_cashflow.jsonl").open("w", encoding="utf-8") as f:
        f.write(json.dumps({
            "type": "mn2_buyin",
            "user_id": "u1",
            "pack_id": "casino_mn2_starter",
            "price_mn2": 25,
            "casino_usd_credit": 8,
            "at": now,
        }) + "\n")

    bets = log_dir / "casino_bets.jsonl"
    with bets.open("w", encoding="utf-8") as f:
        f.write(json.dumps({
            "bet_id": "b1",
            "user_id": "u1",
            "game": "dice",
            "currency": "usd",
            "bet": 10,
            "payout": 0,
            "net": -10,
            "created_at": now,
            "details": {"rake": 0.5},
        }) + "\n")

    from backend.services.house_income_aggregator import summarize

    with patch(
        "backend.services.house_income_aggregator._exchange_to_casino",
        return_value={"count": 1, "amount_usd": 12.5, "casino_coins": 1250},
    ):
        data = summarize(since_hours=24, venue="casino")

    assert data["success"] is True
    assert data["cashflow"]["paypal_deposits"]["amount_usd"] == 5.0
    assert data["cashflow"]["mn2_buyins"]["casino_usd_credit"] == 8.0
    assert data["cashflow"]["exchange_to_casino"]["amount_usd"] == 12.5
    assert "usd" in data["casino"]
    assert data["casino"]["usd"]["house_edge"] == 10.0
    assert data["casino"]["usd"]["rake"] == 0.5
    assert data["by_game"]["dice"]["usd"]["house_edge"] == 10.0
    assert data["financial_usd"]["paypal_deposits_usd"] == 5.0
    assert "net_ops_usd" in data["financial_usd"]


def test_income_summary_requires_ops_secret(tmp_path, monkeypatch):
    from flask import Flask
    from backend.routes.casino_routes import casino_bp

    monkeypatch.delenv("MN2_OPS_SECRET", raising=False)
    monkeypatch.delenv("MN2_SCAN_SECRET", raising=False)
    monkeypatch.delenv("DISCORD_OPS_SECRET", raising=False)

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(casino_bp)
    with app.test_client() as client:
        resp = client.get("/api/casino/ops/income-summary")
    assert resp.status_code == 403
    assert resp.get_json().get("code") == "OPS_AUTH_REQUIRED"


def test_income_summary_accepts_ops_token(tmp_path, monkeypatch):
    from flask import Flask
    from backend.routes.casino_routes import casino_bp

    monkeypatch.setenv("MN2_OPS_SECRET", "test-ops-secret")
    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path / "logs"))
    (tmp_path / "logs").mkdir(parents=True)

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(casino_bp)
    with app.test_client() as client:
        denied = client.get("/api/casino/ops/income-summary")
        assert denied.status_code == 403
        ok = client.get(
            "/api/casino/ops/income-summary?since_hours=24&venue=casino",
            headers={"X-Ops-Token": "test-ops-secret"},
        )
    data = ok.get_json()
    assert ok.status_code == 200
    assert data["success"] is True
    assert "cashflow" in data
    assert "financial_usd" in data
