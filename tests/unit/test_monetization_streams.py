"""Monetization distribution streams + activity queue for paid masternode renters."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from backend.services.monetization_activity_queue_service import (
    enqueue_renter,
    list_paid_renters,
    list_queue,
    sync_rented_masternodes_to_queue,
)
from backend.services.monetization_streams_service import (
    build_recap,
    build_top_25_streams,
    list_distribution_streams,
    reload_streams,
    stream_hub,
)


@pytest.fixture(autouse=True)
def _reload():
    reload_streams()
    yield
    reload_streams()


def test_distribution_streams_loaded():
    streams = list_distribution_streams()
    assert len(streams) >= 7
    ids = {s["id"] for s in streams}
    assert "google-play-casino" in ids
    assert "discord-casino-full" in ids
    assert "facebook-casino" in ids
    assert "youtube-monetization" in ids
    assert "ipodcast-premium" in ids
    assert "masternode-hosting" in ids


def test_stream_hub_success():
    out = stream_hub(include_metrics=False)
    assert out["success"] is True
    assert out["stream_count"] >= 7
    assert out["streams"][0].get("readiness")


def test_top_25_streams():
    rows = build_top_25_streams()
    assert len(rows) >= 7
    assert rows[0].get("priority") <= rows[1].get("priority", 99)


def test_recap_shape():
    out = build_recap()
    assert out["success"] is True
    assert "revenue_stats" in out
    assert "activity_queue" in out


def test_activity_queue_enqueue_idempotent(tmp_path, monkeypatch):
    queue_file = tmp_path / "queue.jsonl"
    seen_file = tmp_path / "seen.json"
    monkeypatch.setattr(
        "backend.services.monetization_activity_queue_service._QUEUE_PATH",
        str(queue_file),
    )
    monkeypatch.setattr(
        "backend.services.monetization_activity_queue_service._SEEN_PATH",
        str(seen_file),
    )
    row = {
        "source": "hosting_order",
        "order_id": "mnq_test123",
        "user_id": "user_test_queue",
        "host_ids": ["host-abc"],
        "slots": 1,
        "usd_total": 4.99,
        "payment_method": "paypal",
    }
    first = enqueue_renter(row)
    second = enqueue_renter(row)
    assert first.get("enqueued") is True
    assert second.get("enqueued") is False
    items = list_queue(limit=10)
    assert len(items) == 1
    assert items[0].get("type") == "masternode_rental"


def test_sync_rented_masternodes():
    out = sync_rented_masternodes_to_queue()
    assert out["success"] is True
    assert "scanned" in out
    assert "enqueued" in out


def test_list_paid_renters_returns_list():
    rows = list_paid_renters()
    assert isinstance(rows, list)
