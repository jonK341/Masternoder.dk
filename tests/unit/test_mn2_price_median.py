"""Tests for multi-source MN2 USD price median."""
from unittest.mock import patch

import pytest

import backend.services.mn2_chainz as chainz


def test_mn2_usd_price_median_single_chainz():
    with patch.object(chainz, "chainz_ticker_usd_with_updated", return_value={"price": 0.42, "last_updated_iso": "2026-01-01T00:00:00Z"}):
        with patch.dict("os.environ", {}, clear=False):
            out = chainz.mn2_usd_price_median()
    assert out is not None
    assert out["price"] == 0.42
    assert out["sources"]["chainz"] == 0.42


def test_mn2_usd_price_median_median_of_two():
    with patch.object(chainz, "chainz_ticker_usd_with_updated", return_value={"price": 0.40}):
        with patch("backend.routes.mn2_routes._load_mn2_config", return_value={"mn2_usd_price": 0.50}):
            out = chainz.mn2_usd_price_median()
    assert out is not None
    assert out["price"] == pytest.approx(0.45)
    assert out["source_label"] == "median"
