"""P0–P2 monetization commits: config JSON, tier evaluation, ledger path."""
from __future__ import annotations

import os
import json

import pytest

from backend.services.monetization_config_service import (
    get_b2b_studio_sku,
    get_coin_pack_map,
    get_credit_reference_fraction,
    get_public_config,
    list_subscription_plan_ids,
    reload_monetization_config,
)
from backend.services.monetization_tier_service import evaluate_generation_against_tier
from backend.services.monetization_scr_blend_service import run_ledger_metering_blend


def test_monetization_json_loads_coin_packs():
    reload_monetization_config()
    m = get_coin_pack_map()
    assert "coin-pack-s" in m
    assert m["coin-pack-s"]["coins_granted"] == 100
    assert get_credit_reference_fraction() > 0
    pub = get_public_config()
    assert "coin_packs" in pub
    assert len(pub["coin_packs"]) >= 1
    assert pub["coin_packs"][0].get("payment_rails")
    assert pub.get("payment_rails_catalog")
    assert isinstance(pub.get("digital_goods"), list)
    assert len(pub["digital_goods"]) >= 1
    assert "artifact_path" not in pub["digital_goods"][0]
    assert isinstance(pub.get("content_bundles"), list)
    assert any(x.get("id") == "bundle-creator-starter" for x in pub["content_bundles"])
    assert "subscriptions" in pub
    assert isinstance(pub["subscriptions"].get("plans"), dict)
    subs = list_subscription_plan_ids()
    assert isinstance(subs, list)
    assert "P-PLACEHOLDER-PRO" in subs
    assert any(x.get("id") == "scr-studio-90d-500" for x in (pub.get("b2b_studio_skus") or []))
    assert get_b2b_studio_sku("scr-studio-90d-500").get("list_price_usd") == 2499.0


def test_tier_enforcement_off_by_default():
    os.environ.pop("MONETIZATION_TIER_ENFORCEMENT", None)
    ok, err = evaluate_generation_against_tier(
        "u1",
        {"duration": 9999, "short_clip": False},
    )
    assert ok is True and err is None


def test_tier_enforcement_blocks_extreme_duration_when_on():
    os.environ["MONETIZATION_TIER_ENFORCEMENT"] = "1"
    os.environ["MONETIZATION_FORCE_TIER"] = "creator"
    try:
        ok, err = evaluate_generation_against_tier(
            "u1",
            {"duration": 9999, "short_clip": False},
        )
        assert ok is False
        assert err and err.get("code")
    finally:
        os.environ.pop("MONETIZATION_TIER_ENFORCEMENT", None)
        os.environ.pop("MONETIZATION_FORCE_TIER", None)


def test_phase4_revenue_report_breaks_down_rails_and_lines(tmp_path):
    ledger = tmp_path / "payment_ledger.jsonl"
    metering = tmp_path / "metering.jsonl"
    mn2 = tmp_path / "mn2_ledger.json"

    ledger.write_text(
        "\n".join([
            json.dumps({
                "ts": "2026-04-29T00:00:00+00:00",
                "provider": "paypal",
                "user_id": "u1",
                "amount_usd": 12.99,
                "item_id": "bundle-creator-starter",
            }),
            json.dumps({
                "ts": "2026-04-29T00:00:00+00:00",
                "provider": "b2b_scr",
                "user_id": "studio",
                "amount_usd": 100.0,
                "item_id": "scr-studio-90d-500",
                "deal_kind": "b2b_block",
            }),
        ]) + "\n",
        encoding="utf-8",
    )
    metering.write_text(
        json.dumps({
            "ts": "2026-04-29T00:00:00+00:00",
            "user_id": "u1",
            "cogs_usd": {"total_usd": 2.5},
        }) + "\n",
        encoding="utf-8",
    )
    mn2.write_text(
        json.dumps({
            "entries": [
                {
                    "created_at": "2026-04-29T00:00:00Z",
                    "user_id": "u1",
                    "type": "shop_payment",
                    "amount": 1.25,
                    "metadata": {"item_id": "bundle-theme-growth"},
                }
            ]
        }),
        encoding="utf-8",
    )

    out = run_ledger_metering_blend(
        ledger_path=str(ledger),
        metering_path=str(metering),
        mn2_ledger_path=str(mn2),
        mn2_usd_price=2.0,
        since_days=None,
        scr_only=False,
    )
    assert out["revenue_by_provider"]["paypal"] == pytest.approx(12.99)
    assert out["revenue_by_provider"]["b2b_scr"] == pytest.approx(100.0)
    assert out["revenue_by_line"]["bundle"] == pytest.approx(12.99)
    assert out["revenue_by_line"]["b2b_studio"] == pytest.approx(100.0)
    assert out["mn2_shop_payments"]["mn2_total"] == pytest.approx(1.25)
    assert out["mn2_shop_payments"]["usd_estimated"] == pytest.approx(2.5)
