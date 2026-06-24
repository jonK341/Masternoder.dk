"""Casino v12 earnings — shop, hunt, features."""
from __future__ import annotations

import os
import tempfile

import pytest


@pytest.fixture
def earnings_state(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, "users.json")
        import backend.services.casino_earnings_service as svc

        monkeypatch.setattr(svc, "_STATE_PATH", state_path)
        yield svc


def test_shop_purchase(earnings_state, monkeypatch):
    svc = earnings_state
    monkeypatch.setattr(svc, "_casino_level", lambda uid: 5)
    monkeypatch.setattr(
        "backend.services.casino_service.get_balance",
        lambda uid: {"success": True, "coins": 500},
    )
    monkeypatch.setattr(
        "backend.services.casino_service._apply_balance_delta",
        lambda *a, **k: None,
    )
    out = svc.purchase_shop_item("shop_u", "casino-daily-chest-plus")
    assert out["success"] is True
    cat = svc.get_shop_catalog("shop_u")
    owned = cat.get("owned_items") or []
    assert "casino-daily-chest-plus" in owned


def test_hunt_claim(earnings_state, monkeypatch):
    svc = earnings_state
    monkeypatch.setattr(svc, "_casino_level", lambda uid: 10)
    monkeypatch.setattr(svc, "_progression_metrics", lambda uid: {"bets": 5, "casino_level": 10})
    st = svc.get_hunt_status("hunt_u")
    quest = next(q for q in st["quests"] if q["id"] == "hunt_floor_chip")
    assert quest["claimable"] is True
    out = svc.claim_hunt_quest("hunt_u", "hunt_floor_chip")
    assert out["success"] is True


def test_features_unlocked_by_level(earnings_state, monkeypatch):
    svc = earnings_state
    monkeypatch.setattr(svc, "_casino_level", lambda uid: 1)
    low = svc.get_features_public("u1")
    locked = [f for f in low["features"] if f["id"] == "earn_leaderboard_mn2"][0]
    assert locked["unlocked"] is False
    monkeypatch.setattr(svc, "_casino_level", lambda uid: 10)
    high = svc.get_features_public("u1")
    same = [f for f in high["features"] if f["id"] == "earn_leaderboard_mn2"][0]
    assert same["unlocked"] is True
