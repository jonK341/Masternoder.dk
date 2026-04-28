"""
Unit tests for Battle (nr 2): battle_db_service.
Run: pytest tests/unit/test_02_battle.py -v
"""
import os
import tempfile

import pytest

from tests.unit.test_utils import ensure_project_root, assert_tables_exist_returns_bool, assert_returns_safe_or_typed

ensure_project_root()


@pytest.fixture
def isolated_battle_social_state(monkeypatch):
    """Avoid polluting repo data/battle_social_state.json across test runs."""
    import backend.services.battle_social_store as bss

    f = tempfile.NamedTemporaryFile(prefix="battle_soc_", suffix=".json", delete=False)
    path = f.name
    f.close()
    v2f = tempfile.NamedTemporaryFile(prefix="battle_v2_", suffix=".json", delete=False)
    v2path = v2f.name
    v2f.close()
    try:
        os.unlink(path)
    except OSError:
        pass
    try:
        os.unlink(v2path)
    except OSError:
        pass
    monkeypatch.setattr(bss, "_state_path", lambda: path)
    import backend.routes.battle_routes as br
    monkeypatch.setattr(br, "_battle_v2_state_path", lambda: v2path)
    yield
    try:
        if os.path.isfile(path):
            os.unlink(path)
    except OSError:
        pass
    try:
        if os.path.isfile(v2path):
            os.unlink(v2path)
    except OSError:
        pass


def _stub_llm_complete(monkeypatch):
    def fake_complete(**kwargs):
        class R:
            success = False
            content = None

        return R()

    monkeypatch.setattr("backend.services.llm_service.complete", fake_complete)


def _stub_battle_quick_extras(monkeypatch):
    """Avoid LLM, DB XP, and noisy side effects during route tests."""
    _stub_llm_complete(monkeypatch)
    v2f = tempfile.NamedTemporaryFile(prefix="battle_v2_quick_", suffix=".json", delete=False)
    v2path = v2f.name
    v2f.close()
    try:
        os.unlink(v2path)
    except OSError:
        pass
    import backend.routes.battle_routes as br
    monkeypatch.setattr(br, "_battle_v2_state_path", lambda: v2path)
    monkeypatch.setattr(
        "backend.routes.hunters_game.award_xp",
        lambda *a, **k: {"success": False, "error": "stubbed"},
    )

    def _noop(*_a, **_k):
        return None

    monkeypatch.setattr("backend.services.ai_user_controller.on_user_activity", _noop)
    monkeypatch.setattr("backend.routes.social_routes.push_activity", _noop)
    import backend.services.unified_points_sync as ups_mod

    monkeypatch.setattr(ups_mod.unified_points_sync_device, "record_domain_sync", lambda *a, **k: None)


def test_battle_tables_exist():
    import backend.services.battle_db_service as svc
    assert_tables_exist_returns_bool(svc, "battle_tables_exist")


def test_battle_record_battle():
    import backend.services.battle_db_service as svc
    result = svc.record_battle(
        user_id="test-u", battle_id="b1", opponent_type="ai",
        difficulty="balanced", result="win", points_delta=10
    )
    assert result is None or isinstance(result, (int, type(None)))


def test_battle_get_battle_history():
    import backend.services.battle_db_service as svc
    result = svc.get_battle_history("test-u", limit=10)
    assert isinstance(result, list)


def test_battle_get_battle_leaderboard():
    import backend.services.battle_db_service as svc
    result = svc.get_battle_leaderboard(limit=5)
    assert isinstance(result, list)


def _battle_app():
    from flask import Flask
    app = Flask(__name__)
    app.config["TESTING"] = True
    from backend.routes.battle_routes import battle_bp
    app.register_blueprint(battle_bp)
    return app


def test_battle_fantasy_tournaments_and_legacy_alias(isolated_battle_social_state):
    app = _battle_app()
    with app.test_client() as c:
        r = c.get("/api/battle/fantasy/tournaments?status=open")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("success") is True
        assert isinstance(data.get("tournaments"), list)
        assert len(data["tournaments"]) >= 1

        r2 = c.get("/api/battle/tournaments?status=open")
        assert r2.status_code == 200
        assert r2.get_json() == data


def test_battle_fantasy_tournament_join_url_and_legacy_body(isolated_battle_social_state):
    app = _battle_app()
    with app.test_client() as c:
        tid = "tour_alpha"
        r = c.post(
            f"/api/battle/fantasy/tournaments/{tid}/join",
            json={},
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body.get("success") is True
        assert body.get("participants") == 1

        r2 = c.post(
            "/api/battle/tournament/join",
            json={"tournament_id": tid},
        )
        assert r2.status_code == 200
        body2 = r2.get_json()
        assert body2.get("success") is True
        assert body2.get("participants") == 1


def test_rps_outcome_rules():
    from backend.routes import battle_routes as br
    assert br._rps_outcome("rock", "scissors") == "win"
    assert br._rps_outcome("rock", "paper") == "loss"
    assert br._rps_outcome("rock", "rock") == "draw"


def test_battle_quick_rps_win(monkeypatch):
    _stub_battle_quick_extras(monkeypatch)
    from backend.routes import battle_routes as br
    monkeypatch.setattr(br, "_pick_ai_rps_move", lambda pm, d: "scissors")
    app = _battle_app()
    with app.test_client() as c:
        r = c.post(
            "/api/battle/quick",
            json={"user_id": "battle-rps-user", "player_move": "rock", "opponent_type": "ai", "difficulty": "balanced"},
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("success") is True
        assert data.get("result") == "win"
        assert data.get("player_move") == "rock"
        assert data.get("ai_move") == "scissors"
        assert data.get("battle_mode") == "rps"

        progress = c.get("/api/battle/progress?user_id=battle-rps-user")
        assert progress.status_code == 200
        p = progress.get_json()["progress"]
        assert p["season"]["current"]["matches"] >= 1
        assert p["telemetry"]["event_count"] >= 1
        assert p["resources"]["balances"]["shards"] >= 2
        assert p["crypto"]["implementation_status"] == "internal_mn2_balance_claims"


def test_battle_quick_skirmish_balanced_loss(monkeypatch):
    _stub_battle_quick_extras(monkeypatch)
    from backend.routes import battle_routes as br
    monkeypatch.setattr(br.random, "random", lambda: 0.65)
    app = _battle_app()
    with app.test_client() as c:
        r = c.post(
            "/api/battle/quick",
            json={"opponent_type": "ai", "difficulty": "balanced"},
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("success") is True
        assert data.get("result") == "loss"
        assert data.get("battle_mode") == "skirmish"


def test_battle_quick_invalid_stance_falls_back_to_skirmish(monkeypatch):
    _stub_battle_quick_extras(monkeypatch)
    from backend.routes import battle_routes as br
    monkeypatch.setattr(br.random, "random", lambda: 0.65)
    app = _battle_app()
    with app.test_client() as c:
        r = c.post(
            "/api/battle/quick",
            json={"player_move": "lizard", "opponent_type": "ai", "difficulty": "balanced"},
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("battle_mode") == "skirmish"
        assert "player_move" not in data


def test_battle_season_leaderboard(isolated_battle_social_state):
    app = _battle_app()
    with app.test_client() as c:
        r = c.get("/api/battle/season/current_season/leaderboard?limit=5")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("success") is True
        assert data.get("season_id") == "current_season"
        assert "leaderboard" in data


def test_battle_progress_is_user_scoped(isolated_battle_social_state):
    app = _battle_app()
    with app.test_client() as c:
        clan_join = c.post(
            "/api/battle/clans/clan_vanguard/join",
            json={"user_id": "battle-v2-user", "agent_id": "agent_alpha"},
        )
        assert clan_join.status_code == 200
        joined = clan_join.get_json()
        assert joined.get("user_id") == "battle-v2-user"
        assert joined.get("membership_id") == "battle-v2-user:agent_alpha"

        progress = c.get("/api/battle/progress?user_id=battle-v2-user&history_limit=3")
        assert progress.status_code == 200
        data = progress.get_json()
        assert data.get("success") is True
        assert data.get("user_id") == "battle-v2-user"
        assert "progress" in data
        assert "missing_for_v2" in data
        assert data["progress"]["social"]["joined_clans"][0]["id"] == "clan_vanguard"


def test_battle_stub_endpoints_minimal():
    app = _battle_app()
    with app.test_client() as c:
        r = c.get("/api/battle/fantasy/resources")
        assert r.status_code == 200
        d = r.get_json()
        assert d.get("implementation_status") == "user_ledger"
        assert "energy" in (d.get("resources") or {})

        r2 = c.get("/api/battle/intelligence/statistics")
        assert r2.status_code == 200
        assert r2.get_json().get("implementation_status") == "minimal"

        r3 = c.get("/api/battle/pvp/trophies")
        assert r3.status_code == 200
        t = r3.get_json().get("trophies") or []
        assert len(t) >= 1
        assert "earned" in t[0]


def test_battle_quick_includes_skirmish_note(monkeypatch):
    _stub_battle_quick_extras(monkeypatch)
    app = _battle_app()
    with app.test_client() as c:
        r = c.post("/api/battle/quick", json={"opponent_type": "ai", "difficulty": "balanced"})
        data = r.get_json()
        assert data.get("instant_skirmish_note")



def test_battle_quick_rps_pvp_queue_opponent_move(monkeypatch):
    _stub_battle_quick_extras(monkeypatch)
    from backend.routes import battle_routes as br
    monkeypatch.setattr(br, "_pick_ai_rps_move", lambda pm, d: "scissors")
    app = _battle_app()
    with app.test_client() as c:
        r = c.post(
            "/api/battle/quick",
            json={"player_move": "rock", "opponent_type": "player", "difficulty": "balanced"},
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("success") is True
        assert data.get("result") == "win"
        assert data.get("battle_mode") == "rps_pvp"
        assert data.get("opponent_type") == "player"
        assert data.get("opponent_move") == "scissors"
        assert "ai_move" not in data


def test_battle_quick_player_queue_skirmish_uses_weights(monkeypatch):
    _stub_battle_quick_extras(monkeypatch)
    from backend.routes import battle_routes as br
    monkeypatch.setattr(br.random, "random", lambda: 0.65)
    app = _battle_app()
    with app.test_client() as c:
        r = c.post("/api/battle/quick", json={"opponent_type": "player", "difficulty": "balanced"})
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("result") == "loss"
        assert data.get("battle_mode") == "skirmish"
        assert data.get("opponent_type") == "player"
