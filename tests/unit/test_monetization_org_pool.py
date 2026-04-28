"""SCR org pool + export helpers (§4)."""
from __future__ import annotations

import json
import os
import subprocess
import sys

from backend.services.monetization_org_pool_service import (
    evaluate_org_pool_for_generation,
    get_org_pool_balance,
    resolve_scr_org_label,
)


def test_resolve_scr_org_label_from_config():
    assert resolve_scr_org_label("u1", {"scr_org_label": " Acme Studio "}) == "Acme Studio"


def test_org_pool_balance_ledger_minus_metering(tmp_path):
    ledger = tmp_path / "payment_ledger.jsonl"
    metering = tmp_path / "metering.jsonl"
    ledger.write_text(
        json.dumps({
            "provider": "b2b_scr",
            "org_label": "Acme",
            "generation_credits_granted": 100.0,
            "amount_usd": 2500.0,
        })
        + "\n",
        encoding="utf-8",
    )
    metering.write_text(
        json.dumps({
            "org_label": "Acme",
            "ratio_vs_reference_job": 1.0,
            "user_id": "u1",
            "job_id": "j1",
        })
        + "\n",
        encoding="utf-8",
    )
    bal = get_org_pool_balance("Acme", ledger_path=str(ledger), metering_path=str(metering))
    # ref_fraction 0.25 → 1.0 ratio = 4 generation credits burned
    assert bal["generation_credits_in"] == 100.0
    assert bal["generation_credits_out"] == 4.0
    assert bal["generation_credits_balance"] == 96.0
    assert bal["amount_usd_b2b_in"] == 2500.0


def test_org_pool_enforcement_blocks_when_depleted(tmp_path, monkeypatch):
    monkeypatch.setenv("MONETIZATION_ORG_POOL_ENFORCEMENT", "1")
    monkeypatch.delenv("MONETIZATION_ORG_POOL_MIN_CREDITS_PER_JOB", raising=False)
    ledger = tmp_path / "ledger.jsonl"
    metering = tmp_path / "metering.jsonl"
    ledger.write_text("", encoding="utf-8")
    metering.write_text(
        json.dumps({
            "org_label": "Dry",
            "ratio_vs_reference_job": 10.0,
        })
        + "\n",
        encoding="utf-8",
    )

    from backend.services import monetization_org_pool_service as m

    def fake_balance(org, *, ledger_path=None, metering_path=None):
        return get_org_pool_balance(org, ledger_path=str(ledger), metering_path=str(metering))

    monkeypatch.setattr(m, "get_org_pool_balance", fake_balance)
    ok, err = evaluate_org_pool_for_generation("u1", {"scr_org_label": "Dry"})
    assert ok is False
    assert err and err.get("code") == "ORG_POOL_EXHAUSTED"


def test_scr_usage_export_script_runs(tmp_path):
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ledger = tmp_path / "l.jsonl"
    metering = tmp_path / "m.jsonl"
    ledger.write_text("", encoding="utf-8")
    metering.write_text("", encoding="utf-8")
    out = tmp_path / "out"
    cmd = [
        sys.executable,
        os.path.join(root, "scripts", "scr_usage_export.py"),
        "--ledger",
        str(ledger),
        "--metering",
        str(metering),
        "--out-dir",
        str(out),
    ]
    r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert (out / "metering_jobs.csv").is_file()
    assert (out / "ledger_scr.csv").is_file()
    assert (out / "org_pool_summary.csv").is_file()
