import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _app(tmp_path, monkeypatch):
    from flask import Flask
    import backend.services.casino_service as casino
    from backend.routes.casino_routes import casino_bp

    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path / "logs"))
    cfg = tmp_path / "casino_config.json"
    cfg.write_text(
        '{"currency":"coins","min_bet":5,"max_bet":500,"max_bets_per_day":50,'
        '"daily_quests":[{"id":"place_3_bets","title":"High roller","description":"3 bets",'
        '"metric":"bets","target":3,"reward_coins":15}],'
        '"games":{"coin_flip":{"label":"Coin flip","payout_multiplier":1.9,"choices":["heads","tails"]},'
        '"dice":{"label":"Dice","payout_multiplier":4,"sides":6},'
        '"rps_bet":{"label":"RPS","payout_multiplier":2,"choices":["rock","paper","scissors"]},'
        '"rps_distribution":{"label":"Meta","payout_multiplier":2.2,"choices":["rock","paper","scissors"]},'
        '"slot_classic":{"label":"Classic","symbols":["7","bar","cherry"],"paytable":{"default_three":5,"default_two":1.2}}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    app.register_blueprint(casino_bp)
    return app


def test_casino_health_endpoint(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    with app.test_client() as client:
        resp = client.get("/api/casino/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["service"] == "casino"
    assert body["status"] == "healthy"
    assert "timestamp" in body


def test_casino_marketing_endpoint(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    with app.test_client() as client:
        resp = client.get("/api/casino/marketing")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body.get("brand") == "MasterNoder2 Casino"
    assert "tags" in body and len(body["tags"]) >= 15
    assert body.get("banner", {}).get("png") == "/static/img/casino/banner-masternoder2-casino.png"


def test_casino_config_and_balance(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 100}}

    with app.test_client() as client:
        with patch("backend.services.casino_service.unified_points_db", mock_points, create=True):
            with patch("backend.services.unified_points_database.unified_points_db", mock_points):
                cfg = client.get("/api/casino/settings")
                bal = client.get("/api/casino/balance?user_id=user-a")

    assert cfg.status_code == 200
    assert cfg.get_json()["success"] is True
    assert "coin_flip" in cfg.get_json()["games"]
    assert bal.status_code == 200
    bal_json = bal.get_json()
    assert bal_json["balance"] == 100
    assert "disclaimer" in bal_json
    assert "coin_flip" in bal_json["games"]


def test_activity_stats_endpoint(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    with app.test_client() as client:
        resp = client.get("/api/casino/activity-stats?days=5&currency=coins")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["days"] == 5
    assert len(body["daily"]) == 5
    assert "bets" in body["daily"][0]


def test_coin_flip_deducts_and_pays(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 100, "mn2_balance": 0}}
    mock_points.add_points.return_value = {"success": True}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_service.random.choice", return_value="heads"):
                response = client.post("/api/casino/play/coin-flip", json={
                    "user_id": "user-a",
                    "bet": 10,
                    "choice": "heads",
                })

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["outcome"] == "win"
    assert data["payout"] == 19
    assert mock_points.add_points.call_count >= 2


def test_insufficient_coins_rejected(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1}}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            response = client.post("/api/casino/play/dice", json={
                "user_id": "user-a",
                "bet": 10,
                "guess": 3,
            })

    assert response.status_code == 400
    assert response.get_json()["error"] == "Insufficient coins"


def test_rps_distribution_and_quests(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 100}}
    mock_points.add_points.return_value = {"success": True}

    battle_state = tmp_path / "battle_v2_state.json"
    battle_state.write_text(
        json.dumps({
            "users": {
                "u1": {
                    "telemetry": [
                        {"battle_mode": "rps", "opponent_move": "rock"},
                        {"battle_mode": "rps", "opponent_move": "rock"},
                        {"battle_mode": "rps", "opponent_move": "paper"},
                    ]
                }
            }
        }),
        encoding="utf-8",
    )

    import backend.services.casino_service as casino

    monkeypatch.setattr(casino, "_BATTLE_V2_PATH", str(battle_state))

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            dist = client.get("/api/casino/battle-rps-distribution")
            assert dist.status_code == 200
            dist_json = dist.get_json()
            assert dist_json["total"] == 3
            assert dist_json["counts"]["rock"] == 2

            with patch("backend.services.casino_service._weighted_rps_move", return_value="rock"):
                play = client.post("/api/casino/play/rps-distribution", json={
                    "user_id": "user-meta",
                    "bet": 10,
                    "prediction": "rock",
                })
            assert play.status_code == 200
            assert play.get_json()["outcome"] == "win"

            quests = client.get("/api/casino/quests?user_id=user-meta")
            assert quests.status_code == 200
            quest_rows = quests.get_json()["quests"]
            assert quest_rows[0]["progress"] >= 1

            lb = client.get("/api/casino/leaderboard?period=today")
            assert lb.status_code == 200
            assert any(row["user_id"] == "user-meta" for row in lb.get_json()["leaderboard"])


def test_wave1_rarity_window_rank_and_bonuses(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    import backend.services.casino_service as casino

    now = datetime.now(timezone.utc)
    battle_state = tmp_path / "battle_v2_state.json"
    battle_state.write_text(
        json.dumps({
            "users": {
                "u1": {
                    "telemetry": [
                        {"battle_mode": "rps", "opponent_move": "rock", "created_at": now.isoformat()},
                        {"battle_mode": "rps", "opponent_move": "rock", "created_at": now.isoformat()},
                        {"battle_mode": "rps", "opponent_move": "paper", "created_at": now.isoformat()},
                    ]
                }
            }
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(casino, "_BATTLE_V2_PATH", str(battle_state))
    monkeypatch.setattr(
        casino,
        "_load_config",
        lambda: {
            "daily_quests": [{"id": "q1", "metric": "bets", "target": 1, "reward_coins": 5}],
            "battle_meta": {
                "window_hours": 24,
                "max_events": 50,
                "rarity_base_multiplier": 2.0,
                "rarity_min_multiplier": 1.8,
                "rarity_max_multiplier": 3.5,
            },
            "quest_streaks": {
                "daily_all_claimed_bonus": 10,
                "streak_3_day_bonus": 25,
                "streak_days_required": 3,
            },
            "games": {"rps_distribution": {"payout_multiplier": 2.2, "choices": ["rock", "paper", "scissors"]}},
        },
    )

    dist = casino.get_battle_rps_distribution()
    assert dist["total"] == 3
    assert dist["window_hours"] == 24
    assert dist["payout_multipliers"]["paper"] >= dist["payout_multipliers"]["rock"]

    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 100}}
    mock_points.add_points.return_value = {"success": True}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_service._weighted_rps_move", return_value="rock"):
                play = client.post("/api/casino/play/rps-distribution", json={
                    "user_id": "rank-user",
                    "bet": 10,
                    "prediction": "rock",
                })
            assert play.status_code == 200
            body = play.get_json()
            assert body["outcome"] == "win"
            assert body["details"]["multiplier"] >= 1.8

            lb = client.get("/api/casino/leaderboard?period=today&user_id=rank-user")
            assert lb.status_code == 200
            lb_json = lb.get_json()
            assert lb_json["your_rank"]["user_id"] == "rank-user"
            assert "win_rate" in lb_json["your_rank"]
            assert "roi" in lb_json["your_rank"]
            assert lb_json["leaderboard"][0]["win_rate"] >= 0

            quests = client.get("/api/casino/quests?user_id=rank-user")
            assert "bonuses" in quests.get_json()


def test_wave2_free_bet_double_bests(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 100}}
    mock_points.add_points.return_value = {"success": True}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_service.random.choice", return_value="heads"):
                free = client.post("/api/casino/play/free-daily-bet", json={
                    "user_id": "w2-user",
                    "choice": "heads",
                })
            assert free.status_code == 200
            free_json = free.get_json()
            assert free_json["game"] == "free_daily_bet"
            assert free_json["outcome"] == "win"

            free2 = client.post("/api/casino/play/free-daily-bet", json={
                "user_id": "w2-user",
                "choice": "heads",
            })
            assert free2.status_code == 400

            with patch("backend.services.casino_service.random.choice", return_value="heads"):
                win = client.post("/api/casino/play/coin-flip", json={
                    "user_id": "w2-user",
                    "bet": 10,
                    "choice": "heads",
                })
            win_json = win.get_json()
            assert win_json.get("can_double") is True

            with patch("backend.services.casino_service.random.random", return_value=0.1):
                dbl = client.post("/api/casino/double-or-nothing", json={
                    "user_id": "w2-user",
                    "bet_id": win_json["bet_id"],
                })
            assert dbl.status_code == 200
            assert dbl.get_json()["game"] == "double_or_nothing"

            bests = client.get("/api/casino/personal-bests?user_id=w2-user")
            assert bests.status_code == 200
            assert bests.get_json()["total_bets"] >= 2

            hof = client.get("/api/casino/hall-of-fame")
            assert hof.status_code == 200

            quests = client.get("/api/casino/quests?user_id=w2-user")
            assert "weekly" in quests.get_json()
            assert "free_daily_bet" in quests.get_json()


def test_wave3_new_games_and_meta_filters(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    import backend.services.casino_service as casino

    now = datetime.now(timezone.utc)
    battle_state = tmp_path / "battle_v2_state.json"
    battle_state.write_text(
        json.dumps({
            "users": {
                "u1": {
                    "telemetry": [
                        {
                            "battle_mode": "rps",
                            "opponent_move": "scissors",
                            "player_move": "rock",
                            "difficulty": "hard",
                            "result": "win",
                            "created_at": now.isoformat(),
                        },
                        {
                            "battle_mode": "skirmish",
                            "difficulty": "easy",
                            "result": "loss",
                            "created_at": now.isoformat(),
                        },
                        {
                            "battle_mode": "rps",
                            "opponent_move": "rock",
                            "player_move": "rock",
                            "difficulty": "hard",
                            "result": "draw",
                            "created_at": now.isoformat(),
                        },
                    ]
                }
            }
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(casino, "_BATTLE_V2_PATH", str(battle_state))

    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 200}}
    mock_points.add_points.return_value = {"success": True}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            dual = client.get("/api/casino/battle-rps-distribution?player_move=rock&difficulty=hard")
            assert dual.status_code == 200
            dual_json = dual.get_json()
            assert dual_json["source"] in ("dual_signal", "battle_telemetry", "uniform_fallback")
            assert dual_json["player_move"] == "rock"

            outcome_dist = client.get("/api/casino/battle-outcome-distribution?difficulty=easy")
            assert outcome_dist.status_code == 200
            assert "percentages" in outcome_dist.get_json()

            with patch("backend.services.casino_service.random.uniform", return_value=2.2):
                with patch("backend.services.casino_service.random.choice", return_value="heads"):
                    mystery = client.post("/api/casino/play/mystery-coin-flip", json={
                        "user_id": "w3-user",
                        "bet": 10,
                        "choice": "heads",
                    })
            assert mystery.status_code == 200
            assert mystery.get_json()["game"] == "mystery_coin_flip"
            assert mystery.get_json()["details"]["multiplier"] == 2.2

            with patch("backend.services.casino_service.random.choice", side_effect=["7", "7", "star"]):
                scratch = client.post("/api/casino/play/scratch-card", json={
                    "user_id": "w3-user",
                    "bet": 10,
                })
            assert scratch.status_code == 200
            assert scratch.get_json()["outcome"] == "win"
            assert scratch.get_json()["details"]["match_label"] == "2-match"

            with patch("backend.services.casino_service._weighted_outcome_pick", return_value="win"):
                outcome = client.post("/api/casino/play/battle-outcome", json={
                    "user_id": "w3-user",
                    "bet": 10,
                    "prediction": "win",
                    "difficulty": "hard",
                })
            assert outcome.status_code == 200
            assert outcome.get_json()["outcome"] == "win"


def test_wave4_counter_house_mn2(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    import backend.services.casino_service as casino

    cfg_path = tmp_path / "casino_config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg["real_money"] = {"enabled": True, "rails": ["mn2"], "mn2_min_bet": 0.05, "mn2_max_bet": 1.0}
    cfg["games"]["rps_counter_pick"] = {"payout_multiplier": 2.0, "choices": ["rock", "paper", "scissors"]}
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg_path))

    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 100, "mn2_balance": 1.0}}
    mock_points.add_points.return_value = {"success": True}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            bal = client.get("/api/casino/balance?user_id=w4-user")
            assert bal.get_json()["real_money"]["enabled"] is True

            hint = client.get("/api/casino/counter-pick-hint")
            assert hint.status_code == 200
            assert "counter_pick" in hint.get_json()

            with patch("backend.services.casino_service._weighted_rps_move", return_value="scissors"):
                counter = client.post("/api/casino/play/rps-counter-pick", json={
                    "user_id": "w4-user",
                    "bet": 0.1,
                    "choice": "rock",
                    "currency": "mn2",
                })
            assert counter.status_code == 200
            assert counter.get_json()["currency"] == "mn2"

            house = client.get("/api/casino/house-stats?user_id=w4-user&currency=mn2")
            assert house.status_code == 200
            assert "house_net" in house.get_json()

            social = client.get("/api/casino/social-mini-board?user_id=w4-user")
            assert social.status_code == 200


def test_paypal_usd_stake_and_capture(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    import backend.services.casino_service as casino

    cfg_path = tmp_path / "casino_config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg["real_money"] = {
        "enabled": True,
        "rails": ["mn2", "paypal"],
        "paypal_min_bet": 0.5,
        "paypal_max_bet": 25.0,
        "paypal_deposit_packs": [{"id": "casino_usd_5", "label": "$5", "amount_usd": 5.0}],
    }
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg_path))

    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 100, "casino_fiat_balance": 10.0}}
    mock_points.add_points.return_value = {"success": True}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            packs = client.get("/api/casino/paypal/deposit-packs")
            assert packs.status_code == 200
            assert len(packs.get_json().get("packs") or []) >= 1

            with patch("backend.services.paypal_service.capture_order", return_value={
                "success": True, "amount": 5.0, "capture_id": "cap1", "currency": "USD",
            }):
                casino._save_paypal_deposits({
                    "pending": {"ord1": {"user_id": "pp-user", "pack_id": "casino_usd_5", "amount_usd": 5.0}},
                    "captured": {},
                })
                cap = client.post("/api/casino/paypal/capture", json={
                    "user_id": "pp-user",
                    "order_id": "ord1",
                    "pack_id": "casino_usd_5",
                })
            assert cap.status_code == 200
            assert cap.get_json()["amount_usd"] == 5.0

            with patch("backend.services.casino_service.random.choice", return_value="heads"):
                usd_bet = client.post("/api/casino/play/coin-flip", json={
                    "user_id": "pp-user",
                    "bet": 1.0,
                    "choice": "heads",
                    "currency": "usd",
                })
            assert usd_bet.status_code == 200
            assert usd_bet.get_json()["currency"] == "usd"


def test_slot_classic_spin(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 200}}
    mock_points.add_points.return_value = {"success": True}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_service.random.uniform", return_value=0.01):
                response = client.post("/api/casino/play/slot-classic", json={
                    "user_id": "slot-user",
                    "bet": 10,
                    "currency": "coins",
                })
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["game"] == "slot_classic"
    assert len(data.get("details", {}).get("reels") or []) == 3
    assert "symbol_display" in data.get("details", {})


def test_list_slots_and_generic_play(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    import backend.services.casino_service as casino

    cfg_path = tmp_path / "casino_config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg["games"]["slot_neon"] = {
        "label": "Neon Pulse",
        "symbols": ["neon", "bolt"],
        "weights": {"neon": 1, "bolt": 2},
        "paytable": {"default_three": 5.0, "default_two": 1.2, "three": {"neon": 10.0}},
    }
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg_path))

    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 200}}
    mock_points.add_points.return_value = {"success": True}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            listing = client.get("/api/casino/slots")
            assert listing.status_code == 200
            slots = listing.get_json().get("slots") or []
            assert any(s["id"] == "slot_neon" for s in slots)

            with patch("backend.services.casino_service.random.uniform", return_value=0.01):
                spin = client.post("/api/casino/play/slot", json={
                    "user_id": "slot-user2",
                    "slot_id": "slot_neon",
                    "bet": 10,
                })
            assert spin.status_code == 200
            assert spin.get_json()["game"] == "slot_neon"
