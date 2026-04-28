"""monetization_scr_export helpers (temp ledger + metering files)."""
from __future__ import annotations

import json
import os
import tempfile

from tests.unit.test_utils import ensure_project_root

ensure_project_root()

from backend.services.monetization_scr_blend_service import run_ledger_metering_blend  # noqa: E402


def test_run_export_empty_files():
    with tempfile.TemporaryDirectory() as tmp:
        lp = os.path.join(tmp, "ledger.jsonl")
        mp = os.path.join(tmp, "metering.jsonl")
        open(lp, "w", encoding="utf-8").close()
        open(mp, "w", encoding="utf-8").close()
        out = run_ledger_metering_blend(ledger_path=lp, metering_path=mp, since_days=None, scr_only=False)
        assert out["success"] is True
        assert out["revenue_usd_total"] == 0.0
        assert out["cogs_usd_total"] == 0.0


def test_run_export_sums_and_margin():
    with tempfile.TemporaryDirectory() as tmp:
        lp = os.path.join(tmp, "ledger.jsonl")
        mp = os.path.join(tmp, "metering.jsonl")
        ts = "2026-04-01T12:00:00+00:00"
        with open(lp, "w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "ts": ts,
                        "provider": "paypal",
                        "user_id": "u1",
                        "amount_usd": 10.0,
                        "item_id": "pack",
                    }
                )
                + "\n"
            )
        with open(mp, "w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "ts": ts,
                        "user_id": "u1",
                        "job_id": "j1",
                        "cogs_usd": {"total_usd": 3.0},
                    }
                )
                + "\n"
            )
        out = run_ledger_metering_blend(ledger_path=lp, metering_path=mp, since_days=None, scr_only=False)
        assert out["revenue_usd_total"] == 10.0
        assert out["cogs_usd_total"] == 3.0
        assert out["blended_gross_margin_vs_metering"] == 0.7
        assert "u1" in out["user_ids_with_both_ledger_and_metering"]
