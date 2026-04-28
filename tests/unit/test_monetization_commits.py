"""P0–P2 monetization commits: config JSON, tier evaluation, ledger path."""
from __future__ import annotations

import os

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


def test_monetization_json_loads_coin_packs():
    reload_monetization_config()
    m = get_coin_pack_map()
    assert "coin-pack-s" in m
    assert m["coin-pack-s"]["coins_granted"] == 100
    assert get_credit_reference_fraction() > 0
    pub = get_public_config()
    assert "coin_packs" in pub
    assert len(pub["coin_packs"]) >= 1
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
