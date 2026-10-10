"""Tests for hunter level MN2 milestone rewards."""
import json
import os
import shutil
import pytest


@pytest.fixture
def level_crypto_env(monkeypatch):
    from backend.services import game_level_crypto_service as glcs
    from backend.services import unified_points_database as upd
    from contextlib import contextmanager

    base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".pytest-tmp", "game-level-crypto")
    if os.path.isdir(base):
        shutil.rmtree(base, ignore_errors=True)
    os.makedirs(base, exist_ok=True)

    cfg = {
        "currency": "MN2",
        "levels": [
            {"level": 1, "mn2": 0.0001, "label": "Welcome"},
            {"level": 5, "mn2": 0.0005, "label": "Tier 5"},
        ],
    }
    cfg_path = os.path.join(base, "game_level_crypto.json")
    state_path = os.path.join(base, "game_level_crypto_state.json")
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f)

    monkeypatch.setattr(glcs, "_CONFIG_PATH", cfg_path)
    monkeypatch.setattr(glcs, "_STATE_PATH", state_path)
    monkeypatch.setattr(glcs, "_CONFIG_CACHE", None)

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    db = upd.UnifiedPointsDatabase(base_dir=os.path.join(base, "points"))
    monkeypatch.setattr(upd, "unified_points_db", db)
    monkeypatch.setattr("backend.services.mn2_ledger.append_entry", lambda *a, **k: {"success": True})
    monkeypatch.setattr("backend.services.activity_events_service.emit", lambda *a, **k: {"success": True})

    def _level(_user_id):
        return {"current_level": 5, "current_xp": 0}

    monkeypatch.setattr("backend.routes.hunters_game.get_user_level_info", _level)
    yield glcs, db


def test_level_rewards_status_ready_count(level_crypto_env):
    glcs, _db = level_crypto_env
    status = glcs.level_rewards_status("player_a")
    assert status["current_level"] == 5
    assert status["claimable_count"] == 2
    ready = [r for r in status["levels"] if r["ready"]]
    assert len(ready) == 2


def test_claim_level_reward(level_crypto_env):
    glcs, db = level_crypto_env
    body, code = glcs.claim_level_reward("player_a", 1)
    assert code == 200
    assert body["success"] is True
    bal = db.get_all_points("player_a")
    assert float(bal["points"]["mn2_balance"]) == pytest.approx(0.0001, rel=1e-6)

    body2, code2 = glcs.claim_level_reward("player_a", 1)
    assert code2 == 409
    assert body2.get("duplicate") is True


def test_claim_locked_level(level_crypto_env, monkeypatch):
    glcs, _db = level_crypto_env
    monkeypatch.setattr(
        "backend.routes.hunters_game.get_user_level_info",
        lambda _uid: {"current_level": 2},
    )
    body, code = glcs.claim_level_reward("player_b", 5)
    assert code == 400
    assert "not reached" in body.get("error", "").lower()
