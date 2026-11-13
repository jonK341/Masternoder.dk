"""Unit tests for generator MN2 pricing and tier resolution."""
import pytest

from backend.services.generator_mn2_service import (
    _tier_from_config,
    quote_generation,
    get_public_pricing,
    normalize_addon_chain,
)


def test_tier_standard_by_default():
    assert _tier_from_config({"quality_mode": "medium"}) == "standard"


def test_tier_express_when_pay_with_mn2():
    assert _tier_from_config({}, {"pay_with_mn2": True}) == "express"


def test_tier_ultra_from_quality_mode():
    assert _tier_from_config({"quality_mode": "ultra"}) == "ultra"


def test_quote_express_has_price():
    q = quote_generation(tier="express", duration=120)
    assert q["success"] is True
    assert q["price_mn2"] > 0
    assert q["earn_on_finish_mn2"] > 0


def test_public_pricing_includes_tiers():
    p = get_public_pricing()
    assert p["success"] is True
    assert "express" in p["tiers"]
    assert p["tiers"]["standard"]["price_mn2"] == 0
    assert p["addon_chain"][0]["id"] == "vision_monitor"


def test_addon_chain_stops_at_first_gap():
    assert normalize_addon_chain(["vision_monitor", "multi_ai"]) == ["vision_monitor"]
    assert normalize_addon_chain("vision_monitor,narration,multi_ai") == [
        "vision_monitor",
        "narration",
        "multi_ai",
    ]


def test_addon_chain_adds_fee_and_reward():
    plain = quote_generation(tier="express", duration=120)
    chained = quote_generation(
        tier="express",
        duration=120,
        addons=["vision_monitor", "narration"],
    )
    assert chained["addon_fee_mn2"] == 0.035
    assert chained["addon_reward_mn2"] == 0.007
    assert chained["price_mn2"] == round(plain["price_mn2"] + 0.035, 8)
    assert chained["earn_on_finish_mn2"] == round(plain["earn_on_finish_mn2"] + 0.007, 8)
    assert [link["id"] for link in chained["addon_chain"]] == ["vision_monitor", "narration"]


def test_standard_without_addons_stays_free():
    q = quote_generation(tier="standard", addons=[])
    assert q["price_mn2"] == 0
    assert q["addon_fee_mn2"] == 0
