"""Unit tests for generator MN2 pricing and tier resolution."""
import pytest

from backend.services.generator_mn2_service import (
    _tier_from_config,
    quote_generation,
    get_public_pricing,
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
