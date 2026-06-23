"""C7 — metered generator API tiers."""
from __future__ import annotations

import os
import shutil
import tempfile

import pytest

from backend.services.monetization_config_service import reload_monetization_config
from backend.services.generator_api_key_service import (
    check_api_quota,
    create_api_key,
    get_user_api_status,
    grant_tier_subscription,
    list_public_tiers,
    purchase_tier_coins,
    record_api_usage,
    resolve_api_key,
    tier_for_sku,
)


@pytest.fixture
def api_keys_store(monkeypatch):
    tmp_dir = tempfile.mkdtemp(prefix="gen_api_")
    path = os.path.join(tmp_dir, "generator_api_keys.json")
    monkeypatch.setattr("backend.services.generator_api_key_service._KEYS_PATH", path)
    monkeypatch.setenv("GENERATOR_API_KEY_SECRET", "test-secret")
    try:
        yield path
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


class FakePointsDB:
    def __init__(self):
        self.coins = {}

    def get_all_points(self, user_id="default_user"):
        return {
            "success": True,
            "user_id": user_id,
            "points": {"coins": int(self.coins.get(user_id, 0)), "mn2_balance": 0.0},
        }

    def add_points(self, user_id, point_type, amount, source="system", metadata=None):
        if point_type == "coins":
            self.coins[user_id] = int(self.coins.get(user_id, 0)) + int(amount)
        return {"success": True}


def test_public_tiers_catalog():
    reload_monetization_config()
    out = list_public_tiers()
    assert out["success"] is True
    ids = {t["id"] for t in out["tiers"]}
    assert "gen-api-starter" in ids
    assert "gen-api-enterprise" in ids


def test_tier_for_sku():
    reload_monetization_config()
    assert tier_for_sku("gen-api-pro-monthly") == "gen-api-pro"


def test_subscription_key_quota_flow(api_keys_store):
    reload_monetization_config()
    uid = "api_user_1"
    grant = grant_tier_subscription(uid, "gen-api-starter", source="test")
    assert grant["success"] is True

    created = create_api_key(org_label="acme", user_id=uid, tier_id="gen-api-starter", label="prod")
    assert created["success"] is True
    row = resolve_api_key(created["api_key"])
    assert row is not None

    ok = check_api_quota(row, duration_sec=60)
    assert ok["success"] is True
    assert ok["jobs_remaining"] == 50

    record_api_usage(row, job_id="job-1", duration_sec=60)
    status = get_user_api_status(uid)
    assert status["subscriptions"][0]["jobs_used"] == 1
    assert status["subscriptions"][0]["jobs_remaining"] == 49


def test_duration_exceeds_tier(api_keys_store):
    reload_monetization_config()
    uid = "api_user_2"
    grant_tier_subscription(uid, "gen-api-starter")
    created = create_api_key(org_label="acme", user_id=uid, tier_id="gen-api-starter")
    row = resolve_api_key(created["api_key"])
    bad = check_api_quota(row, duration_sec=999)
    assert bad["success"] is False
    assert bad["error"] == "duration_exceeds_tier"


def test_coin_purchase(api_keys_store, monkeypatch):
    reload_monetization_config()
    db = FakePointsDB()
    monkeypatch.setattr(
        "backend.services.unified_points_database.unified_points_db",
        db,
    )
    uid = "api_buyer"
    db.coins[uid] = 5000
    out = purchase_tier_coins(uid, "gen-api-starter")
    assert out["success"] is True
    assert out["price_paid_coins"] == 999
    status = get_user_api_status(uid)
    assert len(status["subscriptions"]) == 1
