import json
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_validate_plan_clamps_bet_and_game():
    from backend.services.casino_agent_llm_planner import _validate_plan

    policy = {"min_bet": 5, "max_bet": 100, "allowed_games": ["dice", "coin_flip"], "currency": "coins"}
    plan = _validate_plan({"game": "invalid", "bet": 9999, "params": {"guess": 99}}, policy)
    assert plan["game"] in ("dice", "coin_flip")
    assert 5 <= plan["bet"] <= 100
    assert 1 <= plan["params"]["guess"] <= 6


def test_extract_json_from_markdown_wrapper():
    from backend.services.casino_agent_llm_planner import _extract_json

    raw = 'Here is the plan:\n```json\n{"game":"dice","bet":25,"confidence":0.8,"reasoning":"test","params":{"guess":3}}\n```'
    parsed = _extract_json(raw)
    assert parsed is not None
    assert parsed["game"] == "dice"
    assert parsed["bet"] == 25


def test_plan_bet_uses_llm_when_available(tmp_path, monkeypatch):
    monkeypatch.setenv("CASINO_AGENT_LLM", "1")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    from backend.services import casino_agent_llm_planner as planner
    from backend.services import llm_service

    mock_resp = llm_service.LLMResponse(
        success=True,
        content=json.dumps({
            "game": "coin_flip",
            "bet": 20,
            "confidence": 0.77,
            "reasoning": "Rank 12 — small coin flip to grind net.",
            "spectator_line": "Kelly sees fifty-fifty and likes the odds.",
            "params": {"choice": "heads"},
        }),
        provider="groq",
        model="llama-3.3-70b-versatile",
    )

    model = {
        "name": "Kelly Optimizer",
        "strategy": "kelly_flat",
        "task_kind": "casino_bet_plan",
        "llm_task_type": "reason",
        "skills": ["kelly_sizing"],
    }
    policy = {"min_bet": 5, "max_bet": 200, "allowed_games": ["dice", "coin_flip"], "currency": "coins", "leaderboard_period": "week"}
    agent = {}

    with patch.object(planner, "_BRAIN_LOG", str(tmp_path / "brain.jsonl")):
        with patch("backend.services.casino_agent_llm_planner.casino.get_leaderboard", return_value={"leaderboard": []}):
            with patch("backend.services.casino_agent_llm_planner.casino.get_history", return_value={"history": []}):
                with patch("backend.services.casino_agent_llm_planner.casino.get_balance", return_value={"bets_today": 1}):
                    with patch("backend.services.casino_agent_llm_planner.casino._user_balance", return_value=1000.0):
                        with patch("backend.services.agent_ai_router.routed_chat", return_value=(mock_resp, {"trace_id": "t1", "task_kind": "casino_bet_plan"})):
                            result = planner.plan_bet(
                                agent_id="casino_kelly_agent",
                                user_id="casino_kelly_user",
                                model=model,
                                agent=agent,
                                policy=policy,
                                heuristic_plan={"game": "dice", "bet": 10},
                            )

    assert result["success"] is True
    assert result["used_ai"] is True
    assert result["plan"]["game"] == "coin_flip"
    assert result["plan"]["bet"] == 20
    assert "Kelly" in result["plan"]["reasoning"] or result["plan"]["reasoning"]


def test_resolve_plan_falls_back_without_llm(tmp_path, monkeypatch):
    monkeypatch.setenv("CASINO_AGENT_LLM", "0")
    from backend.services import casino_agents_service as svc

    model = {"strategy": "kelly_flat", "preferred_games": ["dice"]}
    pol = {"min_bet": 5, "max_bet": 50, "allowed_games": ["dice"], "currency": "coins"}
    agent = {}

    with patch.object(svc.casino, "_user_balance", return_value=500.0):
        with patch.object(svc.casino, "get_public_config", return_value={"min_bet": 5, "max_bet": 500}):
            resolved = svc._resolve_plan("casino_kelly_agent", "u1", model, agent, pol, 1.0)

    assert resolved["success"] is True
    assert resolved["used_ai"] is False
    assert resolved["plan"]["source"] == "heuristic"
