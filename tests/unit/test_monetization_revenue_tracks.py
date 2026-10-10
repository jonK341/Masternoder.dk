"""Monetization machine — revenue tracks registry and metrics."""
from __future__ import annotations

import os

import pytest

from backend.services.monetization_revenue_tracks_service import (
    get_machine_status,
    get_north_star,
    get_track_metrics,
    list_track_definitions,
    list_tracks,
    reload_revenue_tracks,
)


@pytest.fixture(autouse=True)
def _reload_tracks():
    reload_revenue_tracks()
    yield
    reload_revenue_tracks()


def test_track_definitions_loaded():
    tracks = list_track_definitions()
    assert len(tracks) >= 34
    ids = {t["id"] for t in tracks}
    assert "A1" in ids
    assert "A3" in ids
    assert "A9" in ids
    assert "B3" in ids
    assert "B6" in ids
    assert "D3" in ids
    assert "E1" in ids
    assert "E6" in ids


def test_north_star_phase():
    ns = get_north_star()
    assert ns.get("phase") in ("A", "B", "C")
    assert ns.get("headline_metric")


def test_list_tracks_public_catalog():
    out = list_tracks(include_metrics=False)
    assert out["success"] is True
    assert out["count"] == len(out["tracks"])
    assert out["tracks"][0]["id"]
    assert "metrics" not in out["tracks"][0]


def test_list_tracks_with_metrics_empty_ledger():
    out = list_tracks(include_metrics=True, since_days=7)
    assert out["success"] is True
    for row in out["tracks"]:
        assert "metrics" in row


def test_track_not_found():
    out = get_track_metrics("ZZ99")
    assert out["success"] is False
    assert out["error"] == "track_not_found"


def test_track_metrics_known_id():
    out = get_track_metrics("A1", since_days=30)
    assert out["success"] is True
    assert out["track"]["id"] == "A1"
    assert out["track"]["name"]
    assert "metrics" in out


def test_machine_status_summary():
    out = get_machine_status(since_days=7)
    assert out["success"] is True
    summary = out["summary"]
    assert summary["track_count"] >= 33
    assert "A" in summary["by_tier"]
    assert "by_status" in summary


def test_a7_config_track_metrics():
    out = get_track_metrics("A7")
    assert out["success"] is True
    metrics = out["metrics"]
    assert "feature_enabled" in metrics
    assert metrics["config_flag"] == "MONETIZATION_TIER_ENFORCEMENT"


def test_b5_auction_fee_track():
    out = get_track_metrics("B5")
    assert out["success"] is True
    assert out["metrics"].get("fee_percent") == 5


def test_a9_casino_track_metrics():
    out = get_track_metrics("A9")
    assert out["success"] is True
    assert out["track"]["name"] == "Casino monetization"
    assert "bet_count" in out["metrics"]


def test_a3_hosting_track_live():
    tracks = list_track_definitions()
    a3 = next(t for t in tracks if t["id"] == "A3")
    assert a3["status"] == "live"
    assert a3["metric_source"] == "hosting"
