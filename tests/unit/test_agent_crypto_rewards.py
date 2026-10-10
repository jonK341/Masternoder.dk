"""Agent / AI-assisted MN2 + coins reward tests."""
import os
import pytest


def test_public_rewards_info():
    from backend.services.agent_crypto_rewards_service import public_rewards_info

    info = public_rewards_info()
    assert info.get("success") is True
    assert "routed_chat" in (info.get("actions_mn2") or {})


def test_award_rejects_guest():
    from backend.services.agent_crypto_rewards_service import award_agent_action

    r = award_agent_action(
        "default_user",
        "routed_chat",
        reference="test-guest-1",
        success=True,
    )
    assert r.get("success") is False


def test_award_mn2_idempotent(monkeypatch):
    import tempfile
    from backend.services import unified_points_database as upd
    from backend.services.agent_crypto_rewards_service import award_agent_action
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    base = tempfile.mkdtemp(prefix="agent-reward-test-")
    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    db = upd.UnifiedPointsDatabase(base_dir=base)
    monkeypatch.setattr(upd, "unified_points_db", db)

    daily = os.path.join(base, "agent_crypto_daily.json")
    monkeypatch.setattr(
        "backend.services.agent_crypto_rewards_service._DAILY_FILE",
        daily,
    )

    r1 = award_agent_action(
        "agent_reward_user",
        "routed_chat",
        reference="trace-abc-1",
        success=True,
    )
    assert r1.get("success") is True
    assert float(r1.get("mn2_awarded") or 0) > 0

    r2 = award_agent_action(
        "agent_reward_user",
        "routed_chat",
        reference="trace-abc-1",
        success=True,
    )
    assert r2.get("duplicate") is True or float(r2.get("mn2_awarded") or 0) == 0


def test_task_kinds_include_taaft_inspired():
    from backend.services.agent_ai_router import TASK_ROUTING_TABLE

    for kind in ("log_triage", "support_copilot", "pricing_brain", "debugger_challenge"):
        assert kind in TASK_ROUTING_TABLE
