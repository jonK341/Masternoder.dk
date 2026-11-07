"""Roster recap: which agents can run, and which sites fold into a shorter map."""
from backend.services.agent_roster import (
    activate_existing,
    build_recap,
    classify_agents,
    classify_sites,
    discover_site_pages,
    nav_paths_from_source,
)


def test_nav_paths_from_toolbar_source():
    source = """
    { name: 'Game', url: APP_BASE + '/game', id: 'game' },
    { name: 'Create App', url: APP_BASE + '/create-app', id: 'create_app' },
    """
    assert nav_paths_from_source(source) == ["create-app", "game"]


def test_classify_agents_splits_ready_idle_unused_and_aliases():
    catalog = {
        "content_generator_agent": {"name": "Content Generator Agent"},
        "automation": {"name": "Automation"},
        "scanner_agent": {"name": "Scanner Agent"},
        "content_ai_agent": {"name": "Content AI Agent"},
        "llm_orchestrator_agent": {"name": "LLM Orchestrator Agent"},
    }
    probes = {
        "content_generator_agent": {"loadable": True, "running": None, "startable": False},
        "automation": {"loadable": True, "running": False, "startable": True},
        "llm_orchestrator_agent": {"loadable": False, "error": "import failed", "startable": False},
    }
    aliases = {"content_ai_agent": "content_generator_agent"}

    rows = classify_agents(catalog, probes, aliases)
    by_id = {row["agent_id"]: row for row in rows}

    assert by_id["content_generator_agent"]["state"] == "active"
    assert by_id["automation"]["state"] == "idle"
    assert by_id["scanner_agent"]["state"] == "unused"
    assert by_id["content_ai_agent"]["state"] == "alias"
    assert by_id["content_ai_agent"]["alias_of"] == "content_generator_agent"
    assert by_id["llm_orchestrator_agent"]["state"] == "blocked"


def test_activate_existing_registers_ready_agents_and_starts_idle_loops_once():
    class Loop:
        def __init__(self):
            self.running = False
            self.starts = 0
            self.primed = 0
            self.activations = {"auto_activations": [{"id": "auto_health_check"}], "last_activations": {}}

        def start(self):
            self.starts += 1
            self.running = True

        def prime_schedules(self):
            self.primed += 1
            self.activations["last_activations"]["auto_health_check"] = "stamped"

    class Ready:
        def get_status(self):
            return {"level": 3}

    loop = Loop()
    ready = Ready()

    class Controller:
        def __init__(self):
            self.agents = {}
            self.data = {}
            self.saved = 0

        def save_data(self):
            self.saved += 1

    controller = Controller()
    probes = {
        "content_generator_agent": {
            "loadable": True,
            "running": None,
            "startable": False,
            "instance": ready,
            "controller_key": "content_generator",
            "name": "Content Generator Agent",
        },
        "activation": {
            "loadable": True,
            "running": False,
            "startable": True,
            "instance": loop,
            "controller_key": "activation",
            "name": "Activation",
        },
        "scanner_agent": {"loadable": False, "startable": False, "name": "Scanner Agent"},
    }

    held = activate_existing(probes, controller=controller, start_loops=False)
    assert held["started"] == []
    assert loop.starts == 0
    assert "content_generator_agent" in controller.agents
    assert controller.agents["content_generator"] is controller.agents["content_generator_agent"]
    assert "activation" not in controller.agents

    started = activate_existing(probes, controller=controller, start_loops=True)
    assert started["started"] == ["activation"]
    assert loop.starts == 1
    assert loop.primed == 1
    assert loop.activations["last_activations"]["auto_health_check"] == "stamped"
    assert controller.agents["activation"].get_status()["running"] is True

    again = activate_existing(probes, controller=controller, start_loops=True)
    assert again["started"] == []
    assert loop.starts == 1
    assert "scanner_agent" in started["skipped"]


def test_classify_sites_keeps_nav_folds_duplicates_and_archives_lore():
    pages = [
        "generator",
        "points",
        "metal",
        "discord/verify",
        "vidgenerator/generator",
        "editor",
    ]
    nav = ["generator", "profile", "game"]
    result = classify_sites(pages, nav)

    assert result["linked"] == ["generator"]
    folded = {row["path"]: row["into"] for row in result["folded"]}
    assert folded["points"] == "profile"
    assert folded["editor"] == "generator"
    assert result["archived"] == ["metal"]
    assert result["keep"] == ["discord/verify"]
    assert result["mirrors"] == [{"path": "vidgenerator/generator", "of": "generator"}]
    assert "editor" not in result["keep"]
    assert "points" not in result["keep"]


def test_recap_counts_match_classified_rows():
    catalog = {
        "content_generator_agent": {"name": "Content"},
        "automation": {"name": "Automation"},
        "scanner_agent": {"name": "Scanner"},
        "content_ai_agent": {"name": "Content AI"},
    }
    probes = {
        "content_generator_agent": {"loadable": True, "running": None, "startable": False, "name": "Content"},
        "automation": {"loadable": True, "running": False, "startable": True, "name": "Automation"},
    }
    recap = build_recap(
        catalog,
        probes,
        {"content_ai_agent": "content_generator_agent"},
        ["generator", "points", "metal"],
        ["generator", "profile"],
    )
    assert recap["counts"] == {"active": 1, "idle": 1, "unused": 1, "alias": 1, "blocked": 0}
    assert recap["sites"]["counts"]["folded"] == 1
    assert recap["sites"]["counts"]["archived"] == 1
    assert recap["sites"]["counts"]["linked"] == 1


def test_roster_route_returns_recap(monkeypatch):
    from flask import Flask

    from backend.routes.agent_profile_routes import agent_profile_bp

    monkeypatch.setattr(
        "backend.services.agent_roster.live_recap",
        lambda: {"success": True, "counts": {"active": 1}},
    )
    app = Flask(__name__)
    app.register_blueprint(agent_profile_bp)
    response = app.test_client().get("/api/agents/roster")
    assert response.status_code == 200
    assert response.get_json()["counts"]["active"] == 1


def test_discover_site_pages_reads_index_titles(tmp_path):
    page = tmp_path / "lab"
    page.mkdir()
    (page / "index.html").write_text("<html><title>Lab - MasterNoder</title></html>", encoding="utf-8")
    nested = tmp_path / "backend" / "skip"
    nested.mkdir(parents=True)
    (nested / "index.html").write_text("<title>Skip</title>", encoding="utf-8")

    found = discover_site_pages(tmp_path)
    assert found == [{"path": "lab", "title": "Lab - MasterNoder"}]
