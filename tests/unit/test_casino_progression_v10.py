"""Casino v10 progression — levels, walk, trophies."""
from __future__ import annotations

import os
import tempfile

import pytest


@pytest.fixture
def progression_state(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, "users.json")
        import backend.services.casino_progression_service as svc

        monkeypatch.setattr(svc, "_STATE_PATH", state_path)
        yield svc


def test_level_up_and_claim(progression_state):
    svc = progression_state
    svc.add_casino_xp("casino_u1", 400, source="bet")
    st = svc.get_user_progression("casino_u1")
    assert st["success"] is True
    assert st["level"] >= 2
    out = svc.claim_level_reward("casino_u1", 2)
    assert out["success"] is True
    assert out.get("reward_coins") == 25


def test_walk_complete_requires_agent_when_configured(progression_state):
    svc = progression_state
    cfg = svc._load_config()
    steps = cfg.get("daily_walk") or []
    agent_step = next((s for s in steps if s.get("assign_agent")), None)
    assert agent_step is not None
    blocked = svc.complete_walk_step("walk_u", agent_step["id"])
    assert blocked["success"] is False
    svc.assign_walk_agent("walk_u", agent_step["agent_pool"][0])
    ok = svc.complete_walk_step("walk_u", agent_step["id"])
    assert ok["success"] is True


def test_trophy_first_win(progression_state):
    svc = progression_state
    svc.record_casino_metric("trophy_u", "wins", 1)
    st = svc.get_user_progression("trophy_u")
    assert "trophy_first_win" in (st.get("trophies_earned") or [])
