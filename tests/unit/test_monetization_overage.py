"""Subscription overage PayPal top-ups."""
from __future__ import annotations

import json
import os
import tempfile

from backend.services.monetization_config_service import (
    get_overage_packs,
    get_retail_coin_packs,
    is_overage_pack,
    reload_monetization_config,
)
from backend.services.monetization_overage_service import (
    build_entitlement_upsell,
    get_overage_offers,
)


def test_overage_packs_in_config():
    reload_monetization_config()
    packs = get_overage_packs()
    assert len(packs) >= 2
    assert all(is_overage_pack(p) for p in packs)
    retail = get_retail_coin_packs()
    assert not any(is_overage_pack(p) for p in retail)


def test_overage_offers_when_over_allowance(monkeypatch):
    reload_monetization_config()
    with tempfile.TemporaryDirectory() as tmp:
        log_dir = os.path.join(tmp, "logs", "monetization")
        os.makedirs(log_dir, exist_ok=True)
        cogs_dir = os.path.join(tmp, "logs", "cogs")
        os.makedirs(cogs_dir, exist_ok=True)

        bindings = {
            "I-OVR": {
                "user_id": "u_over",
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
                        "user_id": "u_over",
                        "ratio_vs_reference_job": 1.0,
                        "cogs_usd": {"total_usd": 0.5},
                    }) + "\n"
                )

        monkeypatch.setenv("MASTERNODER_LOG_DIR", os.path.join(tmp, "logs"))
        monkeypatch.setattr(
            "backend.services.cogs_metering_service._cogs_log_path",
            lambda: metering,
        )

        out = get_overage_offers("u_over")
        assert out["success"] is True
        assert out["overage_eligible"] is True
        assert len(out["packs"]) >= 2
        assert out["recommended_pack_id"] in {p["id"] for p in out["packs"]}
        assert out["shortfall_generation_credits"] > 0


def test_entitlement_upsell_includes_overage_packs(monkeypatch):
    reload_monetization_config()
    with tempfile.TemporaryDirectory() as tmp:
        log_dir = os.path.join(tmp, "logs", "monetization")
        os.makedirs(log_dir, exist_ok=True)
        bindings = {
            "I-OVR2": {
                "user_id": "u_ent",
                "plan_id": "P-PLACEHOLDER-PRO",
                "updated_at": "2026-06-01T00:00:00+00:00",
            }
        }
        with open(os.path.join(log_dir, "subscription_bindings.json"), "w", encoding="utf-8") as f:
            json.dump(bindings, f)
        monkeypatch.setenv("MASTERNODER_LOG_DIR", os.path.join(tmp, "logs"))
        monkeypatch.setattr(
            "backend.services.cogs_metering_service._cogs_log_path",
            lambda: os.path.join(tmp, "nope.jsonl"),
        )

        upsell = build_entitlement_upsell("u_ent", required_credits=5.0, available_credits=0.5)
        assert upsell["reason"] == "subscription_overage"
        assert upsell.get("overage_packs")
        assert upsell.get("recommended_pack_id")
