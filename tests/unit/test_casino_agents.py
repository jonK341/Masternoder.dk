import json
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _app(tmp_path, monkeypatch):
    from flask import Flask
    from backend.routes.agent_casino_routes import agent_casino_bp

    monkeypatch.setenv("AGENT_CASINO_SECRET", "test-casino-secret")
    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path / "logs"))
    agents_path = tmp_path / "casino_agents.json"
    models_path = tmp_path / "casino_agent_models.json"
    models_path.write_text(
        json.dumps({
            "models": {
                "casino_kelly_agent": {
                    "name": "Kelly Optimizer",
                    "strategy": "kelly_flat",
                    "skills": ["kelly_sizing", "play_dice"],
                    "preferred_games": ["dice"],
                    "bet_fraction": 0.05,
                    "currency": "coins",
                    "task_kind": "casino_bet_plan",
                }
            }
        }),
        encoding="utf-8",
    )
    agents_path.write_text(
        json.dumps({
            "casino_kelly_agent": {
                "user_id": "casino_kelly_user",
                "model_id": "casino_kelly_agent",
                "policy": {"enabled": True, "min_bet": 5, "max_bet": 50},
            }
        }),
        encoding="utf-8",
    )

    import backend.services.casino_agents_service as svc
    monkeypatch.setattr(svc, "_AGENTS_FILE", str(agents_path))
    monkeypatch.setattr(svc, "_MODELS_PATH", str(models_path))

    app = Flask(__name__)
    app.register_blueprint(agent_casino_bp)
    return app


def test_casino_agent_models_and_list(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    with app.test_client() as client:
        models = client.get("/api/agent/casino/models")
        agents = client.get("/api/agent/casino/agents")
    assert models.status_code == 200
    assert models.get_json()["count"] == 1
    assert agents.status_code == 200
    assert agents.get_json()["count"] == 1
    assert agents.get_json()["agents"][0]["agent_id"] == "casino_kelly_agent"


def test_casino_agent_run_requires_auth(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    with app.test_client() as client:
        denied = client.post("/api/agent/casino/run-all", json={})
        assert denied.status_code == 403


def test_casino_agent_run_all_dry(tmp_path, monkeypatch):
    monkeypatch.setenv("CASINO_AGENT_LLM", "0")
    app = _app(tmp_path, monkeypatch)
    mock_play = MagicMock(return_value={"success": True, "outcome": "loss", "net": -5, "bet_id": "b1"})
    mock_coins = MagicMock(return_value=1000.0)
    mock_balance = MagicMock(return_value=995.0)
    heuristic = {"game": "dice", "bet": 25, "currency": "coins", "params": {"guess": 3}, "source": "heuristic"}

    with app.test_client() as client:
        with patch("backend.services.casino_agents_service._resolve_plan", return_value={"success": True, "plan": heuristic, "used_ai": False}):
            with patch("backend.services.casino_agents_service.casino.play_dice", mock_play):
                with patch("backend.services.casino_agents_service.casino._user_coins", mock_coins):
                    with patch("backend.services.casino_agents_service.casino._user_balance", mock_balance):
                        with patch("backend.services.casino_agents_service.casino.get_public_config", return_value={"min_bet": 5, "max_bet": 500, "games": {"dice": {"sides": 6}}}):
                            with patch("backend.services.casino_agents_service.casino.get_balance", return_value={"success": True, "balance": 995}):
                                with patch("backend.services.casino_agents_service.agent_db_service", create=True):
                                    resp = client.post(
                                        "/api/agent/casino/run-all",
                                        json={"dry_run": False},
                                        headers={"X-Agent-Casino-Key": "test-casino-secret"},
                                    )
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["ran"] == 1
    mock_play.assert_called_once()


def test_casino_ai_router_task_kinds():
    from backend.services.agent_ai_router import TASK_ROUTING_TABLE

    assert "casino_bet_plan" in TASK_ROUTING_TABLE
    assert TASK_ROUTING_TABLE["casino_bet_plan"]["agent_id"] == "casino_kelly_agent"


def test_agent_skillset_casino_models(tmp_path, monkeypatch):
    monkeypatch.setenv('AGENT_SKILLSET_LITE_INIT', '1')
    import sys
    sys.modules.pop('backend.services.agent_skillset', None)
    models_path = tmp_path / "data" / "casino_agent_models.json"
    models_path.parent.mkdir(parents=True)
    models_path.write_text(
        json.dumps({"models": {"casino_kelly_agent": {"name": "Kelly", "skills": ["kelly_sizing"], "strategy": "kelly_flat"}}}),
        encoding="utf-8",
    )
    from backend.services.agent_skillset import AgentSkillset
    sk = AgentSkillset.__new__(AgentSkillset)
    sk.base_dir = str(tmp_path)
    sk.skillsets = {"agents": {}}
    saved = []
    sk.save_skillsets = lambda: saved.append(True)
    result = sk.ensure_casino_agent_skillsets()
    assert result["success"] is True
    assert "casino_kelly_agent" in sk.skillsets["agents"]
    assert "kelly_sizing" in sk.skillsets["agents"]["casino_kelly_agent"]["skills"]
