"""Wave 3 casino ideas — crash crew, clip cards, duels, spectator, coupons, battle pass."""
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _wave3_app(tmp_path, monkeypatch):
    from flask import Flask
    import backend.services.casino_service as casino
    from backend.routes.casino_routes import casino_bp

    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path / "logs"))
    cfg = tmp_path / "casino_config.json"
    cfg.write_text(
        '{"currency":"coins","min_bet":5,"max_bet":500,"max_bets_per_day":50,'
        '"games":{"crash":{"label":"Crash","house_edge":0.03,'
        '"growth_per_second":0.13863,"max_round_seconds":60,"max_auto_cashout":100,'
        '"rtp_estimate":97.0},'
        '"plinko":{"label":"Plinko","rows":8,"risk_tables":{"medium":[5.6,2.1,1.1,1,0.5,1,1.1,2.1,5.6]}},'
        '"mines":{"label":"Mines","tiles":25,"default_mines":3,"min_mines":1,"max_mines":24,"house_edge":0.01}},'
        '"crash_crew":{"enabled":true,"lobby_seconds":30,"min_players":2,"max_players":6},'
        '"mines_duel":{"enabled":true,"tiles":25,"mines":3},'
        '"casino_battle_pass":{"enabled":true,"xp_per_bet_coin":1,"xp_per_tier":100},'
        '"streak_shield":{"enabled":true,"shields_per_week":1,"refund_pct":50,"currency":"coins"},'
        '"lab_coupons":{"enabled":true,"codes":{"LAB-FREEBET":{"type":"free_daily_bet","uses":1}}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg))

    bp_state = tmp_path / "logs" / "shop_monetization" / "battle_pass.json"
    bp_state.parent.mkdir(parents=True, exist_ok=True)
    bp_state.write_text('{"users":{}}', encoding="utf-8")

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    app.register_blueprint(casino_bp)
    return app


def test_crash_crew_create_join_launch_cashout(tmp_path, monkeypatch):
    app = _wave3_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000, "mn2_balance": 0}}
    mock_points.add_points.return_value = {"success": True}
    fake_draw = {"float": 0.99, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value=fake_draw):
                created = client.post(
                    "/api/casino/crash-crew/create",
                    json={"user_id": "host1", "bet": 10},
                )
                assert created.status_code == 200
                room_id = created.get_json()["room"]["room_id"]

                joined = client.post(
                    "/api/casino/crash-crew/join",
                    json={"user_id": "guest1", "room_id": room_id},
                )
                assert joined.status_code == 200

                launched = client.post(
                    "/api/casino/crash-crew/launch",
                    json={"user_id": "host1", "room_id": room_id},
                )
                assert launched.status_code == 200
                assert launched.get_json()["room"]["status"] == "live"

                cashout = client.post(
                    "/api/casino/crash-crew/cashout",
                    json={"user_id": "host1", "room_id": room_id, "multiplier": 1.0},
                )
    data = cashout.get_json()
    assert data["success"] is True
    assert data["game"] == "crash_crew"
    assert data["outcome"] in ("win", "loss")


def test_plinko_battle_higher_bin_wins(tmp_path, monkeypatch):
    app = _wave3_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    mock_points.add_points.return_value = {"success": True}
    draws = [
        {"float": 0.1, "server_seed_hash": "h1", "client_seed": "c1", "nonce": 1},
        {"float": 0.9, "server_seed_hash": "h2", "client_seed": "c2", "nonce": 2},
    ]

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", side_effect=draws):
                created = client.post(
                    "/api/casino/duels/plinko-battle/create",
                    json={"user_id": "p1", "bet": 10, "risk": "medium"},
                )
                assert created.status_code == 200
                duel_id = created.get_json()["duel"]["duel_id"]
                accepted = client.post(
                    "/api/casino/duels/plinko-battle/accept",
                    json={"user_id": "p2", "duel_id": duel_id},
                )
    data = accepted.get_json()
    assert data["success"] is True
    assert data["winner_id"] == "p2"
    assert data["details"]["acceptor"]["bin"] >= data["details"]["challenger"]["bin"]


def test_mines_duel_mine_hit_loses(tmp_path, monkeypatch):
    app = _wave3_app(tmp_path, monkeypatch)
    from backend.services.engines import mines as mines_engine

    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    mock_points.add_points.return_value = {"success": True}
    proof = {"float": 0.42, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}
    positions = mines_engine.mine_positions(0.42, 25, 3)
    safe_tile = next(i for i in range(25) if i not in positions)
    bomb_tile = positions[0]

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value=proof):
                created = client.post(
                    "/api/casino/duels/mines/create",
                    json={"user_id": "m-host", "bet": 10},
                )
                duel_id = created.get_json()["duel"]["duel_id"]
                client.post(
                    "/api/casino/duels/mines/accept",
                    json={"user_id": "m-guest", "duel_id": duel_id},
                )
                client.post(
                    "/api/casino/duels/mines/pick",
                    json={"user_id": "m-host", "duel_id": duel_id, "tile": safe_tile},
                )
                boom = client.post(
                    "/api/casino/duels/mines/pick",
                    json={"user_id": "m-guest", "duel_id": duel_id, "tile": bomb_tile},
                )
    data = boom.get_json()
    assert data["success"] is True
    assert data["winner_id"] == "m-host"
    assert data.get("hit_mine") is True


def test_spectator_feed(tmp_path, monkeypatch):
    app = _wave3_app(tmp_path, monkeypatch)
    import backend.services.casino_agents_service as agents

    agents._log_spectator_event(
        "casino_kelly_agent",
        "casino_kelly_user",
        {"name": "Kelly Optimizer"},
        {"game": "dice", "bet": 10, "currency": "coins", "spectator_line": "Sizing down after a streak."},
        {"outcome": "win", "net": 5},
        dry_run=False,
    )
    with app.test_client() as client:
        resp = client.get("/api/casino/agents/spectate?limit=5")
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert len(data["events"]) >= 1
    assert data["events"][0]["spectator_line"]


def test_streak_shield_refunds_once(tmp_path, monkeypatch):
    app = _wave3_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 500}}
    mock_points.add_points.return_value = {"success": True}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            st = client.get("/api/casino/streak-shield?user_id=shield-u")
            assert st.get_json()["shields_remaining"] == 1

            first = client.post(
                "/api/casino/streak-shield/apply",
                json={"user_id": "shield-u", "bet": 20, "currency": "coins"},
            )
            assert first.status_code == 200
            assert first.get_json()["refund"] == 10

            second = client.post(
                "/api/casino/streak-shield/apply",
                json={"user_id": "shield-u", "bet": 20, "currency": "coins"},
            )
    assert second.status_code == 400
    assert second.get_json()["error"] == "no_shields_left"


def test_big_win_svg_route(tmp_path, monkeypatch):
    app = _wave3_app(tmp_path, monkeypatch)
    with app.test_client() as client:
        resp = client.get(
            "/api/casino/share/big-win/card.svg?game=crash&net=250&currency=coins&mult=4.5&user_id=u-svg"
        )
    assert resp.status_code == 200
    assert resp.mimetype == "image/svg+xml"
    body = resp.get_data(as_text=True)
    assert "BIG WIN CLIP" in body
    assert "Crash" in body


def test_lab_coupon_redeem_free_bet(tmp_path, monkeypatch):
    app = _wave3_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 500}}
    mock_points.add_points.return_value = {"success": True}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            resp = client.post(
                "/api/casino/coupons/redeem-lab",
                json={"user_id": "coupon-u", "code": "LAB-FREEBET"},
            )
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["type"] == "free_daily_bet"


def test_battle_pass_xp_on_bet(tmp_path, monkeypatch):
    app = _wave3_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 500}}
    mock_points.add_points.return_value = {"success": True}
    fake_draw = {"float": 0.1, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value=fake_draw):
                play = client.post(
                    "/api/casino/play/coin-flip",
                    json={"user_id": "bp-u", "bet": 10, "choice": "heads"},
                )
    assert play.status_code == 200
    from backend.services.battle_pass_service import _load_state

    row = (_load_state().get("users") or {}).get("bp-u") or {}
    assert int(row.get("xp") or 0) >= 10
    assert float(row.get("casino_bet_volume") or 0) >= 10
