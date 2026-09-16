"""Tier C3 — weekly revenue pulse."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


@pytest.fixture
def pulse_paths(tmp_path, monkeypatch):
    ledger = tmp_path / "payment_ledger.jsonl"
    orders = tmp_path / "orders.json"
    tips = tmp_path / "tips.jsonl"
    now = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=3)).isoformat().replace("+00:00", "Z")

    ledger.write_text(
        "\n".join([
            json.dumps({
                "ts": week_ago,
                "amount_usd": 9.99,
                "provider": "paypal",
                "user_id": "u1",
                "item_id": "coin-pack-100",
                "item_name": "100 Coins",
            }),
            json.dumps({
                "ts": week_ago,
                "amount_usd": 4.99,
                "provider": "paypal",
                "user_id": "u2",
                "item_name": "camgirls_tip",
                "extra": {"product": "camgirls"},
            }),
        ]) + "\n",
        encoding="utf-8",
    )
    orders.write_text(
        json.dumps({
            "mnq_test1": {
                "order_id": "mnq_test1",
                "status": "paid",
                "slots": 2,
                "usd_total": 9.98,
                "usd_per_slot": 4.99,
                "payment_method": "paypal",
                "paid_at": week_ago,
            }
        }),
        encoding="utf-8",
    )
    tips.write_text(
        json.dumps({
            "ts": week_ago,
            "performer_id": "nova",
            "amount_mn2": 5.0,
            "user_id": "u3",
        }) + "\n",
        encoding="utf-8",
    )

    import backend.services.monetization_revenue_pulse_service as pulse

    monkeypatch.setattr(
        "backend.services.monetization_ledger_service.payment_ledger_file_path",
        lambda: str(ledger),
    )
    monkeypatch.setattr(pulse, "_ORDERS_PATH", str(orders))
    monkeypatch.setattr(pulse, "_TIPS_PATH", str(tips))
    monkeypatch.setattr(
        "backend.services.cogs_metering_service.metering_jsonl_path",
        lambda: str(tmp_path / "missing_meter.jsonl"),
    )
    return tmp_path


def test_build_revenue_pulse_aggregates(pulse_paths, monkeypatch):
    from backend.services.monetization_revenue_pulse_service import build_revenue_pulse

    monkeypatch.setenv("MN2_USD_PRICE", "0.01")
    report = build_revenue_pulse(since_days=7)

    assert report["ledger"]["revenue_usd_total"] == pytest.approx(14.98, abs=0.01)
    assert report["ledger"]["payment_count"] == 2
    assert report["hosting"]["paid_orders"] == 1
    assert report["hosting"]["slots_sold"] == 2
    assert report["camgirls_tips"]["tip_count"] == 1
    assert report["camgirls_tips"]["mn2_total"] == pytest.approx(5.0)


def test_run_weekly_revenue_pulse_dry_run(pulse_paths):
    from backend.services.monetization_revenue_pulse_service import run_weekly_revenue_pulse

    out = run_weekly_revenue_pulse(dry_run=True)
    assert out["success"] is True
    assert out["dry_run"] is True
    assert "report" in out


def test_format_email_contains_sections(pulse_paths, monkeypatch):
    from backend.services.monetization_revenue_pulse_service import (
        build_revenue_pulse,
        format_revenue_pulse_email,
    )

    monkeypatch.setenv("MN2_USD_PRICE", "0.01")
    body = format_revenue_pulse_email(build_revenue_pulse(since_days=7))
    assert "Payment ledger" in body
    assert "Masternode hosting" in body
    assert "Camgirls tips" in body
