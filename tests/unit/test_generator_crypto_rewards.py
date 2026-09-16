"""Unit tests for generator MN2 crypto reward breakdown."""
import pytest

from backend.services.generator_crypto_rewards_service import (
    _compute_breakdown,
    public_crypto_rewards_info,
)


def test_multi_ai_breakdown():
    b = _compute_breakdown("user1", "doc-a", {"_providers_used": ["groq", "gemini", "openrouter", "cohere"]})
    assert b.get("multi_ai") == pytest.approx(0.003, abs=1e-6)


def test_public_crypto_info():
    info = public_crypto_rewards_info()
    assert info["success"] is True
    assert info["currency"] == "MN2"
    assert float(info["base_finish_mn2"]) > 0
