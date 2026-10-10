"""Wave 4 casino ideas — syndicate, duels, BJ bracket, wheel raid, roulette side bets, rake, podcast, hub."""
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _wave4_app(tmp_path, monkeypatch):
    from flask import Flask
    import backend.services.casino_service as casino
    from backend.routes.casino_routes import casino_bp

    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path / "logs"))
    cfg = tmp_path / "casino_config.json"
    cfg.write_text(
        '{"currency":"coins","min_bet":5,"max_bet":500,"max_bets_per_day":50,'
        '"tournaments":{"enabled":true,"scoring":"net","prize_split":[0.5,0.3,0.2],'
        '"auto_recreate":false,"templates":[]},'
        '"jackpot":{"enabled":true,"rails":{"coins":{"seed":100,"contribution_rate":0.01,'
        '"win_chance":0,"reseed":100}}},'
        '"games":{"wheel":{"risk_tables":{"low":[{"multiplier":1.2,"weight":1}]}},'
        '"keno":{"pool":40,"draw":10,"max_spots":6,'
        '"pay_table":{"1":{"1":3.8},"2":{"2":16.5}}},'
        '"roulette":{"pockets":37},'
        '"blackjack":{"blackjack_payout":1.5,"hit_soft_17":true}},'
        '"keno_syndicate":{"enabled":true,"min_players":2,"max_players":4,"default_stake":10},'
        '"roulette_side_bets":{"enabled":true,"hot_numbers":[7,17,23],'
        '"cold_numbers":[0,13,26],"hot_payout":8.0,"cold_payout":8.0,"max_fraction_of_main":0.5},'
        '"blackjack_tournaments":{"enabled":true,"buy_in":10,"house_seed":100,"bracket_size":2,"currency":"coins"},'
        '"wheel_raid":{"enabled":true,"spin_threshold":3,"bonus_seed_coins":50,"bonus_seed_mn2":0,'
        '"bonus_seed_usd":0,"award_last_spinner_pct":0.1},'
        '"podcast_tournament_bonus":{"enabled":true,"bonus_coins_per_bet":5,"coins_only":true},'
        '"trophy_rake_rebate":{"enabled":true,"max_rebate_pct":0.12,'
        '"tiers":[{"min_trophies":0,"rebate_pct":0.02},{"min_trophies":5,"rebate_pct":0.05}]},'
        '"pvp":{"rake_percent":5}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    app.register_blueprint(casino_bp)
    return app


def test_keno_syndicate_draw_splits(tmp_path, monkeypatch):
    app = _wave4_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    mock_points.add_points.return_value = {"success": True}
    fake_draw = {"float": 0.42, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value=fake_draw):
                created = client.post(
                    "/api/casino/keno-syndicate/create",
                    json={"user_id": "host", "stake": 10},
                )
                assert created.status_code == 200
                sid = created.get_json()["syndicate"]["syndicate_id"]
                joined = client.post(
                    "/api/casino/keno-syndicate/join",
                    json={"user_id": "guest", "syndicate_id": sid, "spots": [4, 5, 6]},
                )
                assert joined.status_code == 200
                drawn = client.post(
                    "/api/casino/keno-syndicate/draw",
                    json={"user_id": "host", "syndicate_id": sid},
                )
    data = drawn.get_json()
    assert data["success"] is True
    assert data["syndicate"]["status"] == "drawn"
    assert "result" in data


def test_duel_invite_token_resolve(tmp_path, monkeypatch):
    app = _wave4_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    mock_points.add_points.return_value = {"success": True}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            created = client.post(
                "/api/casino/duels/create",
                json={"user_id": "challenger", "bet": 10, "game": "coin_flip", "choice": "heads"},
            )
            body = created.get_json()
            assert body["success"] is True
            token = body["invite_token"]
            assert token
            resolved = client.get(f"/api/casino/duels/invite/{token}")
    data = resolved.get_json()
    assert data["success"] is True
    assert data["duel"]["duel_id"] == body["duel"]["duel_id"]
    assert "invite_url" in data


def test_blackjack_tournament_bracket(tmp_path, monkeypatch):
    app = _wave4_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    mock_points.add_points.return_value = {"success": True}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            open_t = client.get("/api/casino/blackjack-tournaments/open")
            tid = open_t.get_json()["tournament"]["tournament_id"]
            client.post(
                "/api/casino/blackjack-tournaments/join",
                json={"user_id": "bj-a", "tournament_id": tid},
            )
            finished = client.post(
                "/api/casino/blackjack-tournaments/join",
                json={"user_id": "bj-b", "tournament_id": tid},
            )
    data = finished.get_json()
    assert data["success"] is True
    t = data["tournament"]
    assert t["status"] == "ended"
    assert t["winner_id"] in ("bj-a", "bj-b")


def test_wheel_raid_threshold(tmp_path, monkeypatch):
    app = _wave4_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    mock_points.add_points.return_value = {"success": True}
    fake_draw = {"float": 0.1, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value=fake_draw):
                for _ in range(3):
                    client.post(
                        "/api/casino/play/wheel",
                        json={"user_id": "wheel-u", "bet": 5, "risk": "low"},
                    )
                status = client.get("/api/casino/wheel-raid/status")
    data = status.get_json()
    assert data["success"] is True
    assert data["spin_count"] == 0
    assert data["raids_triggered"] >= 1


def test_roulette_side_bet_hot(tmp_path, monkeypatch):
    app = _wave4_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    mock_points.add_points.return_value = {"success": True}
    fake_draw = {"float": 7 / 37.0, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value=fake_draw):
                resp = client.post(
                    "/api/casino/play/roulette",
                    json={
                        "user_id": "roulette-u",
                        "bet": 10,
                        "bet_type": "red",
                        "side_bet": {"type": "hot", "amount": 5},
                    },
                )
    data = resp.get_json()
    assert data["success"] is True
    assert data["details"]["side_bet"]["type"] == "hot"


def test_trophy_rake_rebate_progress(tmp_path, monkeypatch):
    app = _wave4_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 500}, "systems": {"trophies_collected": 2}}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            resp = client.get("/api/casino/trophy-rake-rebate/progress?user_id=trophy-u")
    data = resp.get_json()
    assert data["success"] is True
    assert data["trophies"] == 2
    assert data["current_rebate_pct"] == 0.02
    assert data["progress_pct"] >= 0


def test_podcast_bonus_status(tmp_path, monkeypatch):
    app = _wave4_app(tmp_path, monkeypatch)
    with app.test_client() as client:
        resp = client.get("/api/casino/podcast-bonus/status?podcast_active=true")
    data = resp.get_json()
    assert data["success"] is True
    assert data["enabled"] is True
    assert data["bonus_coins_per_bet"] == 5


def test_global_hub_node_report(tmp_path, monkeypatch):
    app = _wave4_app(tmp_path, monkeypatch)
    payload = {
        "node_id": "affiliate-demo",
        "label": "Demo node",
        "period": "today",
        "currency": "coins",
        "leaderboard": [{"user_id": "remote-u", "net": 50, "bets": 3, "wins": 2, "wagered": 100}],
    }
    with app.test_client() as client:
        resp = client.post("/api/casino/global/hub-node", json=payload)
        listed = client.get("/api/casino/global/hub-nodes")
    assert resp.get_json()["success"] is True
    nodes = listed.get_json()
    assert nodes["success"] is True
    assert nodes["node_count"] >= 1
