"""Encoder attachable micro rewards tests."""
import pytest


def test_list_attachable_micro_rewards():
    from backend.services.encoder_micro_rewards_service import list_attachable_micro_rewards

    catalog = list_attachable_micro_rewards()
    assert catalog.get("success") is True
    actions = {r["action"] for r in catalog.get("rewards") or []}
    assert "discord_welcome" in actions
    assert "encoder_fulfillment" in actions
    assert "discord_welcome" in (catalog.get("default_actions") or [])


def test_attach_micro_rewards_bundle(monkeypatch):
    import backend.services.encoder_micro_rewards_service as ems
    import backend.services.aggregator_mn2_service as agg

    monkeypatch.setattr(agg, "get_config", lambda: {
        "enabled": True,
        "daily_cap_mn2": 0.25,
        "action_rewards_mn2": {
            "discord_welcome": 0.001,
            "interaction": 0.00005,
        },
        "default_reward_mn2": 0.00005,
    })

    calls = []

    def fake_award(uid, action, meta=None):
        calls.append(action)
        return {"success": True, "mn2_awarded": 0.001, "action": action}

    monkeypatch.setattr(agg, "award_for_action", fake_award)
    monkeypatch.setattr(ems, "_fulfillment_cfg", lambda: {"attach_bonus_mn2": False})

    res = ems.attach_micro_rewards("discord_test", actions=["discord_welcome", "interaction"])
    assert res.get("success") is True
    assert res.get("awarded_count", 0) >= 2
    assert res.get("total_mn2_awarded", 0) > 0
    assert calls == ["discord_welcome", "interaction"]
