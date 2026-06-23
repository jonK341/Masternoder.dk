"""Tier C8 — weekly Phase C margin report."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture
def margin_paths(monkeypatch):
    tmp_path = tempfile.mkdtemp(prefix="margin_report_")
    ledger = os.path.join(tmp_path, "payment_ledger.jsonl")
    metering = os.path.join(tmp_path, "metering.jsonl")
    mn2_ledger = os.path.join(tmp_path, "mn2_ledger.json")
    now = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")

    with open(ledger, "w", encoding="utf-8") as f:
        f.write(
            "\n".join([
                json.dumps({
                    "ts": week_ago,
                    "amount_usd": 20.0,
                    "provider": "paypal",
                    "user_id": "u1",
                    "item_id": "coin-pack-100",
                }),
                json.dumps({
                    "ts": week_ago,
                    "amount_usd": 50.0,
                    "provider": "b2b_scr",
                    "user_id": "studio_a",
                    "item_id": "scr-studio-90d-500",
                    "studio_sku_id": "scr-studio-90d-500",
                }),
            ]) + "\n"
        )
    with open(metering, "w", encoding="utf-8") as f:
        f.write(
            json.dumps({
                "ts": week_ago,
                "user_id": "u1",
                "job_id": "j1",
                "cogs_usd": {"total_usd": 5.0},
            }) + "\n"
        )
    with open(mn2_ledger, "w", encoding="utf-8") as f:
        json.dump({"entries": []}, f)

    monkeypatch.setattr(
        "backend.services.monetization_ledger_service.payment_ledger_file_path",
        lambda: ledger,
    )
    monkeypatch.setattr(
        "backend.services.cogs_metering_service.metering_jsonl_path",
        lambda: metering,
    )
    monkeypatch.setattr(
        "backend.services.monetization_scr_blend_service._mn2_ledger_path_default",
        lambda: mn2_ledger,
    )
    try:
        yield tmp_path
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_build_margin_report_aggregates(margin_paths):
    from backend.services.monetization_margin_report_service import build_margin_report

    report = build_margin_report(since_days=7)

    assert report["success"] is True
    assert report["revenue_usd_total"] == pytest.approx(70.0, abs=0.01)
    assert report["cogs_usd_total"] == pytest.approx(5.0, abs=0.01)
    assert report["gross_profit_usd"] == pytest.approx(65.0, abs=0.01)
    assert report["blended_gross_margin"] == pytest.approx(0.928571, abs=0.001)
    assert report["scr_studio"]["revenue_usd_total"] == pytest.approx(50.0, abs=0.01)


def test_run_weekly_margin_report_dry_run(margin_paths):
    from backend.services.monetization_margin_report_service import run_weekly_margin_report

    out = run_weekly_margin_report(dry_run=True)
    assert out["success"] is True
    assert out["dry_run"] is True
    assert "report" in out


def test_format_email_contains_margin_sections(margin_paths):
    from backend.services.monetization_margin_report_service import (
        build_margin_report,
        format_margin_report_email,
    )

    body = format_margin_report_email(build_margin_report(since_days=7))
    assert "Blended margin" in body
    assert "Revenue by product line" in body
    assert "B2B studio" in body
