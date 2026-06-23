"""Unit tests for aggregator MN2 generation service."""
import pytest

from backend.services.aggregator_mn2_service import (
    award_for_action,
    get_config,
    get_public_stats,
    get_user_stats,
    _normalize_action,
)


def test_normalize_action():
    assert _normalize_action("Monitor Move") == "monitor_move"


def test_config_has_rewards():
    cfg = get_config()
    assert cfg.get("enabled") is True
    assert float(cfg.get("daily_cap_mn2") or 0) > 0
    rewards = cfg.get("action_rewards_mn2") or {}
    assert "monitor_battle_complete" in rewards


def test_award_respects_cap(monkeypatch):
    import backend.services.aggregator_mn2_service as svc

    store = {"users": {}, "platform_total_mn2": 0.0, "platform_events": 0}

    monkeypatch.setattr(svc, "get_config", lambda: {
        "enabled": True,
        "daily_cap_mn2": 0.001,
        "action_rewards_mn2": {"interaction": 0.0005},
        "default_reward_mn2": 0.0005,
    })
    monkeypatch.setattr(svc, "_load_awards", lambda: dict(store))
    monkeypatch.setattr(svc, "_save_awards", lambda data: store.update(data))

    credited = []

    def fake_credit(user_id, amount, meta):
        credited.append(amount)
        return True

    monkeypatch.setattr(svc, "_credit", fake_credit)

    r1 = award_for_action("test_user_agg", "interaction")
    r2 = award_for_action("test_user_agg", "interaction")
    r3 = award_for_action("test_user_agg", "interaction")

    assert r1.get("success") is True
    assert r1.get("mn2_awarded", 0) > 0
    assert r2.get("success") is True
    total = sum(credited)
    assert total <= 0.001 + 1e-9
    if r3.get("skipped") == "daily_cap":
        assert r3.get("mn2_awarded") == 0.0


def test_public_stats():
    stats = get_public_stats()
    assert stats.get("success") is True
    assert "platform_total_mn2" in stats


def test_user_stats_empty_user():
    stats = get_user_stats("nonexistent_test_user_xyz")
    assert stats.get("success") is True
    assert stats.get("earned_today_mn2") == 0.0
