"""Usage vs allowance (§8.2 habit loops) and ref-eq pack enrichment."""
from __future__ import annotations

import json
import os
import tempfile

from backend.services.monetization_config_service import (
    credits_to_ref_eq_generations,
    enrich_coin_pack,
    get_public_config,
    ratio_to_credits_used,
    ref_eq_label,
    reload_monetization_config,
)
from backend.services.monetization_allowance_service import (
    get_user_usage_allowance,
    run_allowance_nudge_scan,
)
from backend.services.monetization_subscription_service import (
    list_bindings_for_user,
    save_subscription_binding,
)


def test_ref_eq_helpers():
    reload_monetization_config()
    assert credits_to_ref_eq_generations(4.0) == 1.0
    assert ref_eq_label(4.0) == "≈ 1 ref-eq generation"
    assert ratio_to_credits_used(0.25) == 1.0
    pack = enrich_coin_pack({"id": "x", "generation_credits_granted": 1.5})
    assert pack["reference_equivalent_generations"] == 0.38
    assert "ref-eq" in pack["reference_eq_label"]


def test_public_config_includes_ref_eq_on_packs_and_plans():
    reload_monetization_config()
    pub = get_public_config()
    pack_m = next(p for p in pub["coin_packs"] if p["id"] == "coin-pack-m")
    assert pack_m.get("reference_eq_label")
    plans = pub["subscriptions"]["plans"]
    assert plans["P-PLACEHOLDER-PRO"].get("reference_eq_label_monthly")


def test_usage_allowance_with_metering_and_subscription(monkeypatch):
    reload_monetization_config()
    with tempfile.TemporaryDirectory() as tmp:
        log_dir = os.path.join(tmp, "logs", "monetization")
        os.makedirs(log_dir, exist_ok=True)
        cogs_dir = os.path.join(tmp, "logs", "cogs")
        os.makedirs(cogs_dir, exist_ok=True)

        bindings = {
            "I-TEST-SUB": {
                "user_id": "u_allow",
                "plan_id": "P-PLACEHOLDER-PRO",
                "updated_at": "2026-06-01T00:00:00+00:00",
            }
        }
        with open(os.path.join(log_dir, "subscription_bindings.json"), "w", encoding="utf-8") as f:
            json.dump(bindings, f)

        metering = os.path.join(cogs_dir, "metering.jsonl")
        with open(metering, "w", encoding="utf-8") as f:
            f.write(
                json.dumps({
                    "ts": "2026-06-15T12:00:00+00:00",
                    "user_id": "u_allow",
                    "ratio_vs_reference_job": 1.0,
                    "cogs_usd": {"total_usd": 0.5},
                }) + "\n"
            )

        monkeypatch.setenv("MASTERNODER_LOG_DIR", os.path.join(tmp, "logs"))
        monkeypatch.setattr(
            "backend.services.cogs_metering_service._cogs_log_path",
            lambda: metering,
        )

        out = get_user_usage_allowance("u_allow", period_days=30)
        assert out["success"] is True
        assert out["subscription"]["has_subscription"] is True
        assert out["metering"]["jobs_in_period"] == 1
        assert out["metering"]["generation_credits_used"] == 4.0
        assert out["nudge"]["percent_of_monthly_allowance"] == 50.0
        assert out["nudge"]["nudge_level"] == "info"


def test_list_bindings_for_user(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        log_dir = os.path.join(tmp, "logs", "monetization")
        os.makedirs(log_dir, exist_ok=True)
        monkeypatch.setenv("MASTERNODER_LOG_DIR", os.path.join(tmp, "logs"))
        save_subscription_binding("I-A", "user_x", "P-PLACEHOLDER-PRO")
        rows = list_bindings_for_user("user_x")
        assert len(rows) == 1
        assert rows[0]["subscription_id"] == "I-A"


def test_nudge_scan_writes_log(monkeypatch):
    reload_monetization_config()
    with tempfile.TemporaryDirectory() as tmp:
        log_dir = os.path.join(tmp, "logs", "monetization")
        os.makedirs(log_dir, exist_ok=True)
        cogs_dir = os.path.join(tmp, "logs", "cogs")
        os.makedirs(cogs_dir, exist_ok=True)

        bindings = {
            "I-HIGH": {
                "user_id": "u_high",
                "plan_id": "P-PLACEHOLDER-PRO",
                "updated_at": "2026-06-01T00:00:00+00:00",
            }
        }
        with open(os.path.join(log_dir, "subscription_bindings.json"), "w", encoding="utf-8") as f:
            json.dump(bindings, f)

        metering = os.path.join(cogs_dir, "metering.jsonl")
        with open(metering, "w", encoding="utf-8") as f:
            for _ in range(3):
                f.write(
                    json.dumps({
                        "ts": "2026-06-16T12:00:00+00:00",
                        "user_id": "u_high",
                        "ratio_vs_reference_job": 1.0,
                        "cogs_usd": {"total_usd": 0.5},
                    }) + "\n"
                )

        monkeypatch.setenv("MASTERNODER_LOG_DIR", os.path.join(tmp, "logs"))
        monkeypatch.setattr(
            "backend.services.cogs_metering_service._cogs_log_path",
            lambda: metering,
        )

        result = run_allowance_nudge_scan(min_percent=75.0)
        assert result["scanned"] == 1
        assert result["nudged"] == 1
        assert os.path.isfile(os.path.join(log_dir, "allowance_nudges.jsonl"))
