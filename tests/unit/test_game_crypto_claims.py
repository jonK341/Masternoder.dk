"""Battle + Star Map crypto claims via game_mn2_rewards."""
import json
import os
import tempfile

import pytest
from flask import Flask


@pytest.fixture
def points_db(tmp_path, monkeypatch):
    from backend.services import unified_points_database as upd
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    monkeypatch.setattr(upd, "_IDEMPOTENCY_CACHE", {})
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path))
    monkeypatch.setattr(upd, "unified_points_db", db)
    return db


@pytest.fixture
def activity_log(tmp_path, monkeypatch):
    import backend.services.activity_events_service as aes

    path = tmp_path / "activity_events.jsonl"
    monkeypatch.setattr(aes, "_LOG_PATH", str(path))
    return path


@pytest.fixture
def battle_state_file(monkeypatch):
    f = tempfile.NamedTemporaryFile(prefix="battle_v2_", suffix=".json", delete=False)
    path = f.name
    f.close()
    os.unlink(path)
    import backend.routes.battle_routes as br

    monkeypatch.setattr(br, "_battle_v2_state_path", lambda: path)
    return path


@pytest.fixture
def starmap_crypto_file(monkeypatch):
    f = tempfile.NamedTemporaryFile(prefix="starmap_crypto_", suffix=".json", delete=False)
    path = f.name
    f.close()
    os.unlink(path)
    import backend.routes.star_map_routes as sm

    monkeypatch.setattr(sm, "STAR_MAP_25_CRYPTO_PATH", path)
    return path


def test_battle_crypto_claim_uses_game_mn2_rewards(
    monkeypatch, points_db, activity_log, battle_state_file
):
    import backend.routes.battle_routes as br

    monkeypatch.setattr(
        br,
        "_battle_crypto_progress",
        lambda user_id: {"matches": 5, "win_streak": 0, "season_score": 0, "clans": 0, "shards": 0},
    )
    monkeypatch.setattr("backend.services.mn2_ledger.append_entry", lambda *a, **k: {"success": True})
    monkeypatch.setattr("backend.routes.social_routes.push_activity", lambda *a, **k: None)

    body, status = br._claim_battle_crypto("player_battle", "duel_hash")
    assert status == 200
    assert body.get("success") is True
    bal = points_db.get_all_points("player_battle")
    assert float(bal["points"]["mn2_balance"]) > 0

    rows = activity_log.read_text(encoding="utf-8").strip().splitlines()
    assert rows
    event = json.loads(rows[-1])
    assert event.get("type") == "game_mn2_reward"
    assert event.get("user_id") == "player_battle"


def test_battle_crypto_claim_idempotent(
    monkeypatch, points_db, activity_log, battle_state_file
):
    import backend.routes.battle_routes as br

    monkeypatch.setattr(
        br,
        "_battle_crypto_progress",
        lambda user_id: {"matches": 5, "win_streak": 0, "season_score": 0, "clans": 0, "shards": 0},
    )
    monkeypatch.setattr("backend.services.mn2_ledger.append_entry", lambda *a, **k: {"success": True})
    monkeypatch.setattr("backend.routes.social_routes.push_activity", lambda *a, **k: None)

    body1, status1 = br._claim_battle_crypto("player_battle_idem", "duel_hash")
    assert status1 == 200
    amount1 = float(body1["claim"]["amount_mn2"])

    body2, status2 = br._claim_battle_crypto("player_battle_idem", "duel_hash")
    assert status2 == 429
    assert body2.get("error") == "cooldown"

    bal = points_db.get_all_points("player_battle_idem")
    assert float(bal["points"]["mn2_balance"]) == pytest.approx(amount1, rel=1e-6)


def test_starmap_crypto_claim_uses_game_mn2_rewards(
    monkeypatch, points_db, activity_log, starmap_crypto_file
):
    import backend.routes.star_map_routes as sm

    monkeypatch.setattr(
        sm,
        "_starmap25_crypto_progress",
        lambda user_id: {
            "investigated": 3,
            "secured": 1,
            "placements": 2,
            "max_level_reached": 2,
        },
    )
    monkeypatch.setattr("backend.services.mn2_ledger.append_entry", lambda *a, **k: {"success": True})
    monkeypatch.setattr("backend.routes.social_routes.push_activity", lambda *a, **k: None)

    body, status = sm._claim_starmap25_crypto("player_starmap", "cartographer_hash")
    assert status == 200
    assert body.get("success") is True
    bal = points_db.get_all_points("player_starmap")
    assert float(bal["points"]["mn2_balance"]) > 0

    rows = activity_log.read_text(encoding="utf-8").strip().splitlines()
    assert rows
    event = json.loads(rows[-1])
    assert event.get("type") == "game_mn2_reward"
    assert event.get("user_id") == "player_starmap"


def test_battle_crypto_claim_route(monkeypatch, points_db, activity_log, battle_state_file):
    from backend.routes.battle_routes import battle_bp

    import backend.routes.battle_routes as br

    monkeypatch.setattr(
        br,
        "_battle_crypto_progress",
        lambda user_id: {"matches": 5, "win_streak": 0, "season_score": 0, "clans": 0, "shards": 0},
    )
    monkeypatch.setattr("backend.services.mn2_ledger.append_entry", lambda *a, **k: {"success": True})
    monkeypatch.setattr("backend.routes.social_routes.push_activity", lambda *a, **k: None)

    app = Flask(__name__)
    app.register_blueprint(battle_bp)
    client = app.test_client()
    r = client.post(
        "/api/battle/crypto/claim",
        json={"user_id": "route_player", "option_id": "duel_hash"},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
