"""Trader level-gated strategy unlocks (Phase 4 polish)."""


def test_unlocked_strategies_by_level():
    from backend.services.agent_trader_service import unlocked_strategies, resolve_strategy, size_multiplier

    assert unlocked_strategies(1) == ["market_maker"]
    assert "momentum" in unlocked_strategies(2)
    assert "sniper" in unlocked_strategies(4)
    assert "sniper" not in unlocked_strategies(3)

    r = resolve_strategy("trader_agent_1", "sniper")
    # agent_1 bootstrap level is 1 → sniper downgrades
    assert r["strategy"] == "market_maker"
    assert r["downgraded"] is True

    assert size_multiplier(1) == 0.5
    assert size_multiplier(4) == 1.25


def test_trader_skillset_profiles():
    from backend.services.agent_skillset import AgentSkillset
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as td:
        sk = AgentSkillset(base_dir=td)
        out = sk.ensure_trader_skills_per_agent(count=6)
        assert out.get("success") is True
        agents = sk.skillsets.get("agents") or {}
        assert "trader_agent_1" in agents
        profiles = agents["trader_agent_1"].get("trader_skill_profiles") or []
        assert len(profiles) >= 6
