"""Tests for the Crash game: pure engine, provably-fair RNG, and routes."""
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


# --------------------------------------------------------------------------- #
# Pure crash engine
# --------------------------------------------------------------------------- #

def test_crash_point_bounds_and_monotonicity():
    from backend.services.engines import crash

    # Always >= 1.00.
    assert crash.crash_point(0.0) >= 1.0
    assert crash.crash_point(0.5) >= 1.0
    # Higher random float => higher (or equal) bust point.
    assert crash.crash_point(0.9) >= crash.crash_point(0.1)


def test_crash_point_rtp_converges():
    """Average min(bust, target) / target should approach (1 - house_edge)."""
    from backend.services.engines import crash

    house_edge = 0.03
    target = 2.0
    n = 20000
    total_return = 0.0
    for i in range(n):
        r = (i + 0.5) / n  # deterministic uniform sweep over (0, 1)
        bust = crash.crash_point(r, house_edge)
        if bust >= target:
            total_return += target  # cashed out at target
    rtp = total_return / n
    assert abs(rtp - (1 - house_edge)) < 0.01


def test_multiplier_curve_grows_with_time():
    from backend.services.engines import crash

    assert crash.multiplier_at(0) == 1.0
    # Default growth reaches ~2x at 5s.
    assert abs(crash.multiplier_at(5) - 2.0) < 0.05
    assert crash.multiplier_at(10) > crash.multiplier_at(5)


def test_settle_win_and_loss():
    from backend.services.engines import crash

    # Reached 1.5x with a bust at 3.0 -> win at the reachable multiplier.
    won = crash.settle(bust=3.0, elapsed_seconds=crash.seconds_for_multiplier(1.5))
    assert won["won"] is True
    assert won["multiplier"] >= 1.0

    # Bust at 1.0 (instant) -> any cash-out loses.
    lost = crash.settle(bust=1.0, elapsed_seconds=5.0)
    assert lost["won"] is False
    assert lost["multiplier"] == 0.0


# --------------------------------------------------------------------------- #
# Provably-fair RNG
# --------------------------------------------------------------------------- #

def test_hmac_float_is_deterministic_and_in_range():
    from backend.services import casino_rng

    a = casino_rng.hmac_float("server-seed", "client-seed", 1)
    b = casino_rng.hmac_float("server-seed", "client-seed", 1)
    assert a == b
    assert 0.0 <= a < 1.0
    assert casino_rng.hmac_float("server-seed", "client-seed", 2) != a


def test_verify_reproduces_outcome():
    from backend.services import casino_rng

    proof = casino_rng.verify("abc123", "player", 7)
    assert proof["float"] == casino_rng.hmac_float("abc123", "player", 7)
    assert proof["server_seed_hash"] == __import__("hashlib").sha256(b"abc123").hexdigest()


def test_rotate_reveals_matching_seed(tmp_path, monkeypatch):
    import hashlib
    from backend.services import casino_rng

    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path / "logs"))
    state = casino_rng.public_state("user-x")
    committed_hash = state["server_seed_hash"]

    rotated = casino_rng.rotate("user-x")
    revealed_seed = rotated["revealed"]["server_seed"]
    # The previously committed hash must match the now-revealed seed.
    assert hashlib.sha256(revealed_seed.encode()).hexdigest() == committed_hash
    # A fresh server seed hash is now committed.
    assert rotated["server_seed_hash"] != committed_hash


# --------------------------------------------------------------------------- #
# Routes (start + cash out)
# --------------------------------------------------------------------------- #

def _crash_app(tmp_path, monkeypatch):
    from flask import Flask
    import backend.services.casino_service as casino
    from backend.routes.casino_routes import casino_bp

    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path / "logs"))
    cfg = tmp_path / "casino_config.json"
    cfg.write_text(
        '{"currency":"coins","min_bet":5,"max_bet":500,"max_bets_per_day":50,'
        '"games":{"crash":{"label":"Crash","house_edge":0.03,'
        '"growth_per_second":0.13863,"max_round_seconds":60,"max_auto_cashout":100,'
        '"rtp_estimate":97.0}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    app.register_blueprint(casino_bp)
    return app


def test_crash_start_then_cashout_win(tmp_path, monkeypatch):
    app = _crash_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 100, "mn2_balance": 0}}
    mock_points.add_points.return_value = {"success": True}

    # Force a high bust so an immediate cash-out wins.
    fake_draw = {"float": 0.99, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value=fake_draw):
                start = client.post("/api/casino/play/crash", json={"user_id": "u1", "bet": 10})
                start_data = start.get_json()
                assert start.status_code == 200
                assert start_data["success"] is True
                round_id = start_data["round_id"]

                cashout = client.post(
                    "/api/casino/play/crash/cashout",
                    json={"user_id": "u1", "round_id": round_id, "multiplier": 1.0},
                )
    data = cashout.get_json()
    assert cashout.status_code == 200
    assert data["success"] is True
    assert data["outcome"] == "win"
    assert data["bust"] >= 2.0


def test_crash_instant_bust_is_loss(tmp_path, monkeypatch):
    app = _crash_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 100}}
    mock_points.add_points.return_value = {"success": True}

    fake_draw = {"float": 0.0, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value=fake_draw):
                start = client.post("/api/casino/play/crash", json={"user_id": "u2", "bet": 10})
                round_id = start.get_json()["round_id"]
                cashout = client.post(
                    "/api/casino/play/crash/cashout",
                    json={"user_id": "u2", "round_id": round_id, "multiplier": 5.0},
                )
    data = cashout.get_json()
    assert data["success"] is True
    assert data["outcome"] == "loss"
    assert data["payout"] == 0


def test_crash_single_active_round_enforced(tmp_path, monkeypatch):
    app = _crash_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 100}}
    mock_points.add_points.return_value = {"success": True}
    fake_draw = {"float": 0.99, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value=fake_draw):
                client.post("/api/casino/play/crash", json={"user_id": "u3", "bet": 10})
                second = client.post("/api/casino/play/crash", json={"user_id": "u3", "bet": 10})
    data = second.get_json()
    assert second.status_code == 400
    assert data["code"] == "CRASH_ROUND_ACTIVE"


def _plinko_app(tmp_path, monkeypatch):
    from flask import Flask
    import backend.services.casino_service as casino
    from backend.routes.casino_routes import casino_bp

    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path / "logs"))
    cfg = tmp_path / "casino_config.json"
    cfg.write_text(
        '{"currency":"coins","min_bet":5,"max_bet":500,"max_bets_per_day":50,'
        '"games":{"plinko":{"label":"Plinko","rows":12,"rtp_estimate":99.0,'
        '"risk_tables":{'
        '"low":[10,3,1.6,1.4,1.1,1,0.5,1,1.1,1.4,1.6,3,10],'
        '"medium":[33,11,4,2,1.1,0.6,0.3,0.6,1.1,2,4,11,33],'
        '"high":[170,24,8.1,2,0.7,0.2,0.2,0.2,0.7,2,8.1,24,170]}}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    app.register_blueprint(casino_bp)
    return app


def test_plinko_path_is_deterministic_and_binomial_bin():
    from backend.services.engines import plinko

    table = [0] * 13
    # rand_float ~1.0 -> all right moves -> last bin (12).
    res_hi = plinko.play(0.9999999, 12, [float(i) for i in range(13)])
    assert res_hi["bin"] == 12
    assert res_hi["path"].count("R") == 12
    # rand_float 0.0 -> all left moves -> bin 0.
    res_lo = plinko.play(0.0, 12, [float(i) for i in range(13)])
    assert res_lo["bin"] == 0
    assert set(res_lo["path"]) == {"L"}


def test_plinko_rtp_within_band():
    from backend.services.engines import plinko

    tables = {
        "low": [10, 3, 1.6, 1.4, 1.1, 1, 0.5, 1, 1.1, 1.4, 1.6, 3, 10],
        "medium": [33, 11, 4, 2, 1.1, 0.6, 0.3, 0.6, 1.1, 2, 4, 11, 33],
        "high": [170, 24, 8.1, 2, 0.7, 0.2, 0.2, 0.2, 0.7, 2, 8.1, 24, 170],
    }
    for table in tables.values():
        rtp = plinko.rtp(12, table)
        assert 0.95 <= rtp <= 1.0


def test_plinko_route_pays_table_multiplier(tmp_path, monkeypatch):
    app = _plinko_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    mock_points.add_points.return_value = {"success": True}

    # float ~1.0 -> bin 12 -> high-edge multiplier; assert big win on high risk.
    fake_draw = {"float": 0.9999999, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}
    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value=fake_draw):
                resp = client.post(
                    "/api/casino/play/plinko",
                    json={"user_id": "p1", "bet": 10, "risk": "high"},
                )
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["details"]["bin"] == 12
    assert data["details"]["multiplier"] == 170
    assert data["outcome"] == "win"
    assert data["payout"] == 1700


def test_plinko_rejects_bad_risk(tmp_path, monkeypatch):
    app = _plinko_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            resp = client.post(
                "/api/casino/play/plinko",
                json={"user_id": "p2", "bet": 10, "risk": "insane"},
            )
    assert resp.status_code == 400
    assert "risk must be one of" in resp.get_json()["error"]


def test_fairness_seed_and_verify_endpoints(tmp_path, monkeypatch):
    app = _crash_app(tmp_path, monkeypatch)
    with app.test_client() as client:
        seed = client.get("/api/casino/fairness/seed?user_id=u4")
        seed_data = seed.get_json()
        assert seed.status_code == 200
        assert seed_data["success"] is True
        assert "server_seed_hash" in seed_data

        verify = client.post(
            "/api/casino/fairness/verify",
            json={"server_seed": "abc", "client_seed": "xyz", "nonce": 3},
        )
        vdata = verify.get_json()
    assert verify.status_code == 200
    assert vdata["success"] is True
    assert 0.0 <= vdata["float"] < 1.0
    assert vdata["crash_bust"] >= 1.0


# --------------------------------------------------------------------------- #
# Wheel engine + route
# --------------------------------------------------------------------------- #

def test_wheel_spin_is_deterministic_and_weighted():
    from backend.services.engines import wheel

    segs = [
        {"multiplier": 0, "weight": 8},
        {"multiplier": 1.7, "weight": 4},
        {"multiplier": 2, "weight": 2},
        {"multiplier": 4, "weight": 1},
    ]
    assert wheel.spin(0.0, segs)["index"] == 0
    assert wheel.spin(0.99, segs)["index"] == 3  # last (4x) segment
    assert wheel.spin(0.99, segs)["multiplier"] == 4


def test_wheel_rtp_within_band():
    from backend.services.engines import wheel

    tables = {
        "low": [
            {"multiplier": 0, "weight": 4}, {"multiplier": 1.2, "weight": 6},
            {"multiplier": 1.5, "weight": 3}, {"multiplier": 2, "weight": 1},
        ],
        "medium": [
            {"multiplier": 0, "weight": 8}, {"multiplier": 1.7, "weight": 4},
            {"multiplier": 2, "weight": 2}, {"multiplier": 4, "weight": 1},
        ],
        "high": [
            {"multiplier": 0, "weight": 62}, {"multiplier": 2, "weight": 3},
            {"multiplier": 9.9, "weight": 1}, {"multiplier": 49.5, "weight": 1},
        ],
    }
    for segs in tables.values():
        assert 0.95 <= wheel.rtp(segs) <= 1.0


def _games_app(tmp_path, monkeypatch):
    from flask import Flask
    import backend.services.casino_service as casino
    from backend.routes.casino_routes import casino_bp

    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path / "logs"))
    cfg = tmp_path / "casino_config.json"
    cfg.write_text(
        '{"currency":"coins","min_bet":5,"max_bet":500,"max_bets_per_day":50,'
        '"games":{'
        '"wheel":{"label":"Wheel","rtp_estimate":98.0,"risk_tables":{'
        '"medium":[{"multiplier":0,"weight":8},{"multiplier":1.7,"weight":4},'
        '{"multiplier":2,"weight":2},{"multiplier":4,"weight":1}]}},'
        '"mines":{"label":"Mines","tiles":25,"default_mines":3,"min_mines":1,'
        '"max_mines":24,"house_edge":0.01,"max_round_seconds":7200,"rtp_estimate":99.0}'
        '}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    app.register_blueprint(casino_bp)
    return app


def test_wheel_route_pays_landed_multiplier(tmp_path, monkeypatch):
    app = _games_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    mock_points.add_points.return_value = {"success": True}
    fake_draw = {"float": 0.99, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value=fake_draw):
                resp = client.post(
                    "/api/casino/play/wheel",
                    json={"user_id": "w1", "bet": 10, "risk": "medium"},
                )
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["details"]["multiplier"] == 4
    assert data["outcome"] == "win"
    assert data["payout"] == 40


# --------------------------------------------------------------------------- #
# Mines engine + route
# --------------------------------------------------------------------------- #

def test_mines_layout_deterministic_and_multiplier_grows():
    from backend.services.engines import mines

    a = mines.mine_positions(0.42, 25, 3)
    b = mines.mine_positions(0.42, 25, 3)
    assert a == b
    assert len(a) == 3
    assert len(set(a)) == 3
    assert all(0 <= p < 25 for p in a)

    assert mines.multiplier(25, 3, 0) == 1.0
    assert mines.multiplier(25, 3, 2) > mines.multiplier(25, 3, 1) > 1.0


def test_mines_reveal_safe_then_cashout_wins(tmp_path, monkeypatch):
    from backend.services.engines import mines as mines_engine

    app = _games_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    mock_points.add_points.return_value = {"success": True}
    fake_draw = {"float": 0.42, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}

    positions = mines_engine.mine_positions(0.42, 25, 3)
    safe_tile = next(i for i in range(25) if i not in positions)

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value=fake_draw):
                start = client.post("/api/casino/play/mines", json={"user_id": "m1", "bet": 10, "mines": 3})
                round_id = start.get_json()["round_id"]
                reveal = client.post(
                    "/api/casino/play/mines/reveal",
                    json={"user_id": "m1", "round_id": round_id, "tile": safe_tile},
                )
                reveal_data = reveal.get_json()
                cashout = client.post(
                    "/api/casino/play/mines/cashout",
                    json={"user_id": "m1", "round_id": round_id},
                )
    assert reveal_data["success"] is True
    assert reveal_data["hit_mine"] is False
    assert reveal_data["multiplier"] > 1.0
    cdata = cashout.get_json()
    assert cdata["success"] is True
    assert cdata["outcome"] == "win"
    assert cdata["payout"] > 10


def test_mines_hitting_mine_loses(tmp_path, monkeypatch):
    from backend.services.engines import mines as mines_engine

    app = _games_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    mock_points.add_points.return_value = {"success": True}
    fake_draw = {"float": 0.42, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}

    positions = mines_engine.mine_positions(0.42, 25, 3)
    mine_tile = positions[0]

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value=fake_draw):
                start = client.post("/api/casino/play/mines", json={"user_id": "m2", "bet": 10, "mines": 3})
                round_id = start.get_json()["round_id"]
                reveal = client.post(
                    "/api/casino/play/mines/reveal",
                    json={"user_id": "m2", "round_id": round_id, "tile": mine_tile},
                )
    data = reveal.get_json()
    assert data["success"] is True
    assert data["hit_mine"] is True
    assert data["outcome"] == "loss"
    assert data["payout"] == 0


def test_mines_single_active_round_enforced(tmp_path, monkeypatch):
    app = _games_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    mock_points.add_points.return_value = {"success": True}
    fake_draw = {"float": 0.42, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}

    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value=fake_draw):
                client.post("/api/casino/play/mines", json={"user_id": "m3", "bet": 10, "mines": 3})
                second = client.post("/api/casino/play/mines", json={"user_id": "m3", "bet": 10, "mines": 3})
    data = second.get_json()
    assert second.status_code == 400
    assert data["code"] == "MINES_ROUND_ACTIVE"


# --------------------------------------------------------------------------- #
# Progressive jackpot
# --------------------------------------------------------------------------- #

_JACKPOT_CFG = (
    '{"currency":"coins","min_bet":5,"max_bet":500,"max_bets_per_day":50,'
    '"games":{"dice":{"label":"Dice"}},'
    '"jackpot":{"enabled":true,"slot_jackpot_symbol_awards":true,"rails":{'
    '"coins":{"seed":1000,"contribution_rate":0.01,"win_chance":0.0008,"reseed":1000}}}}'
)


def _jackpot_env(tmp_path, monkeypatch):
    import backend.services.casino_service as casino

    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path / "logs"))
    cfg = tmp_path / "casino_config.json"
    cfg.write_text(_JACKPOT_CFG, encoding="utf-8")
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg))


def test_jackpot_contributes_and_reconciles(tmp_path, monkeypatch):
    _jackpot_env(tmp_path, monkeypatch)
    from backend.services import casino_jackpot

    # Force the must-drop roll to never fire so we only measure contributions.
    monkeypatch.setattr("backend.services.casino_jackpot.random.random", lambda: 1.0)

    row = {"user_id": "j1", "game": "dice", "bet": 100, "currency": "coins", "details": {}}
    award = casino_jackpot.on_bet(row)
    assert award is None

    pools = casino_jackpot.public_pools()
    # seed 1000 + 1% of 100 = 1001.
    assert pools["enabled"] is True
    assert abs(pools["pools"]["coins"]["pool"] - 1001.0) < 1e-6

    rec = casino_jackpot.reconcile()
    assert rec["ok"] is True
    assert rec["rails"]["coins"]["ok"] is True


def test_jackpot_slot_symbol_awards_and_reseeds(tmp_path, monkeypatch):
    _jackpot_env(tmp_path, monkeypatch)
    from backend.services import casino_jackpot

    mock_points = MagicMock()
    mock_points.add_points.return_value = {"success": True}

    row = {
        "user_id": "j2", "game": "slot_classic", "bet": 10,
        "currency": "coins", "details": {"match": "jackpot"},
    }
    with patch("backend.services.unified_points_database.unified_points_db", mock_points):
        award = casino_jackpot.on_bet(row)

    # Pool was 1000 + 0.1 contribution; coins floor to 1000 awarded.
    assert award is not None
    assert award["currency"] == "coins"
    assert award["amount"] == 1000
    # Player was actually credited the jackpot.
    assert mock_points.add_points.called
    # Pool re-seeded to ~reseed (1000) plus the rounding remainder.
    pools = casino_jackpot.public_pools()
    assert pools["pools"]["coins"]["pool"] >= 1000.0
    assert pools["pools"]["coins"]["win_count"] == 1

    rec = casino_jackpot.reconcile()
    assert rec["ok"] is True


def test_jackpot_pools_route(tmp_path, monkeypatch):
    from flask import Flask
    from backend.routes.casino_routes import casino_bp

    _jackpot_env(tmp_path, monkeypatch)

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    app.register_blueprint(casino_bp)

    with app.test_client() as client:
        resp = client.get("/api/casino/jackpots?user_id=u1")
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["enabled"] is True
    # Real-money rails are off in this config, so only coins should show.
    assert "coins" in data["pools"]
    assert data["pools"]["coins"]["pool"] >= 1000.0


# --------------------------------------------------------------------------- #
# Keno
# --------------------------------------------------------------------------- #

_KENO_PAY = {
    "1": {"1": 3.8}, "2": {"2": 16.5}, "3": {"2": 5.5, "3": 16.5},
    "4": {"3": 20, "4": 60}, "5": {"3": 7.5, "4": 30, "5": 120},
    "6": {"4": 27, "5": 135, "6": 680},
}


def test_keno_draw_is_deterministic_and_distinct():
    from backend.services.engines import keno

    a = keno.draw_numbers(0.4242, 40, 10)
    b = keno.draw_numbers(0.4242, 40, 10)
    assert a == b
    assert len(a) == 10
    assert len(set(a)) == 10
    assert all(1 <= n <= 40 for n in a)
    # Different float -> (almost surely) different draw.
    assert keno.draw_numbers(0.7777, 40, 10) != a


def test_keno_rtp_within_band():
    from backend.services.engines import keno

    for s in range(1, 7):
        rtp = keno.rtp(s, _KENO_PAY, 40, 10)
        assert 0.90 <= rtp <= 0.98, (s, rtp)


def _games2_app(tmp_path, monkeypatch):
    from flask import Flask
    import backend.services.casino_service as casino
    from backend.routes.casino_routes import casino_bp
    import json as _json

    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path / "logs"))
    cfg = tmp_path / "casino_config.json"
    cfg.write_text(_json.dumps({
        "currency": "coins", "min_bet": 5, "max_bet": 500, "max_bets_per_day": 50,
        "games": {
            "keno": {"label": "Keno", "pool": 40, "draw": 10, "max_spots": 6, "pay_table": _KENO_PAY},
            "hilo": {"label": "Hi-Lo", "ranks": 13, "house_edge": 0.02, "max_round_seconds": 7200},
            "roulette": {"label": "Roulette", "pockets": 37},
        },
        "tournaments": {
            "enabled": True, "scoring": "net", "prize_split": [0.5, 0.3, 0.2], "auto_recreate": True,
            "templates": [{"id": "daily_coins", "name": "Daily Coin Cup", "currency": "coins",
                           "buy_in": 50, "house_seed": 2000, "duration_hours": 24}],
        },
    }), encoding="utf-8")
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    app.register_blueprint(casino_bp)
    return app


def test_keno_route_pays_table_multiplier(tmp_path, monkeypatch):
    from backend.services.engines import keno
    app = _games2_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    mock_points.add_points.return_value = {"success": True}

    fake = {"float": 0.4242, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}
    drawn = keno.draw_numbers(0.4242, 40, 10)
    spots = drawn[:3]  # force 3 hits on a 3-spot ticket -> 16.5x
    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value=fake):
                resp = client.post("/api/casino/play/keno",
                                   json={"user_id": "k1", "bet": 10, "spots": spots})
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["details"]["hits"] == 3
    assert data["details"]["multiplier"] == 16.5
    assert data["payout"] == 165


def test_keno_rejects_too_many_spots(tmp_path, monkeypatch):
    app = _games2_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            resp = client.post("/api/casino/play/keno",
                               json={"user_id": "k2", "bet": 10, "spots": [1, 2, 3, 4, 5, 6, 7]})
    assert resp.status_code == 400
    assert "at most" in resp.get_json()["error"]


# --------------------------------------------------------------------------- #
# Roulette
# --------------------------------------------------------------------------- #

def test_roulette_engine_pockets_and_evaluate():
    from backend.services.engines import roulette

    assert roulette.spin(0.0) == 0
    assert roulette.spin(0.9999999) == 36
    assert roulette.color(0) == "green"
    assert roulette.evaluate(17, "straight", 17) == 36.0
    assert roulette.evaluate(18, "straight", 17) == 0.0
    assert roulette.evaluate(0, "red") == 0.0  # zero loses outside bets
    assert roulette.evaluate(1, "red") == 2.0
    assert roulette.evaluate(2, "even") == 2.0
    assert roulette.evaluate(20, "high") == 2.0
    assert roulette.evaluate(5, "dozen", 1) == 3.0
    assert roulette.evaluate(36, "column", 3) == 3.0


def test_roulette_rtp_is_european_edge():
    from backend.services.engines import roulette

    for bt, sel in [("straight", 7), ("red", None), ("even", None), ("dozen", 2), ("column", 1)]:
        assert abs(roulette.rtp(bt, sel) - 36 / 37) < 1e-9


def test_roulette_route_pays_straight(tmp_path, monkeypatch):
    app = _games2_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    mock_points.add_points.return_value = {"success": True}

    # float -> pocket 17
    fake = {"float": 17.5 / 37, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}
    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value=fake):
                resp = client.post("/api/casino/play/roulette",
                                   json={"user_id": "r1", "bet": 10, "bet_type": "straight", "selection": 17})
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["details"]["pocket"] == 17
    assert data["outcome"] == "win"
    assert data["payout"] == 360


# --------------------------------------------------------------------------- #
# Hi-Lo
# --------------------------------------------------------------------------- #

def test_hilo_engine_fair_multipliers_and_wins():
    from backend.services.engines import hilo

    assert hilo.card_from_float(0.0) == 1
    assert hilo.card_from_float(0.9999999) == 13
    # Fair: P(win) * step_multiplier == (1 - edge)
    for c in range(1, 14):
        for d in ("higher", "lower"):
            p = hilo.win_probability(c, d)
            assert abs(p * hilo.step_multiplier(c, d, 0.02) - 0.98) < 0.02
    assert hilo.wins(5, 9, "higher") is True
    assert hilo.wins(5, 2, "higher") is False
    assert hilo.wins(5, 5, "lower") is True  # ties win for the chosen side


def test_hilo_start_guess_win_then_cashout(tmp_path, monkeypatch):
    from backend.services.engines import hilo
    app = _games2_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    mock_points.add_points.return_value = {"success": True}

    # first card from 0.0 -> 1; next from 0.99 -> 13 ; "higher" wins
    draws = [
        {"float": 0.0, "server_seed_hash": "h", "client_seed": "c", "nonce": 1},
        {"float": 0.99, "server_seed_hash": "h", "client_seed": "c", "nonce": 2},
    ]
    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", side_effect=draws):
                start = client.post("/api/casino/play/hilo", json={"user_id": "h1", "bet": 10}).get_json()
                rid = start["round_id"]
                guess = client.post("/api/casino/play/hilo/guess",
                                    json={"user_id": "h1", "round_id": rid, "direction": "higher"}).get_json()
                cash = client.post("/api/casino/play/hilo/cashout",
                                   json={"user_id": "h1", "round_id": rid}).get_json()
    assert start["card"] == 1
    assert guess["success"] is True and guess["busted"] is False
    expected_mult = hilo.step_multiplier(1, "higher", 0.02, 13)
    assert abs(guess["multiplier"] - expected_mult) < 1e-6
    assert cash["success"] is True
    assert cash["outcome"] in ("win", "draw")
    assert abs(cash["multiplier"] - expected_mult) < 1e-6


def test_hilo_wrong_guess_busts(tmp_path, monkeypatch):
    app = _games2_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    mock_points.add_points.return_value = {"success": True}

    # first card 13 (0.99), guess higher, next card 1 (0.0) -> 1 >= 13 false -> bust
    draws = [
        {"float": 0.99, "server_seed_hash": "h", "client_seed": "c", "nonce": 1},
        {"float": 0.0, "server_seed_hash": "h", "client_seed": "c", "nonce": 2},
    ]
    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", side_effect=draws):
                start = client.post("/api/casino/play/hilo", json={"user_id": "h2", "bet": 10}).get_json()
                rid = start["round_id"]
                guess = client.post("/api/casino/play/hilo/guess",
                                    json={"user_id": "h2", "round_id": rid, "direction": "higher"}).get_json()
    assert start["card"] == 13
    assert guess["success"] is True
    assert guess["busted"] is True
    assert guess["outcome"] == "loss"


def test_hilo_single_active_round_enforced(tmp_path, monkeypatch):
    app = _games2_app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 1000}}
    mock_points.add_points.return_value = {"success": True}
    fake = {"float": 0.3, "server_seed_hash": "h", "client_seed": "c", "nonce": 1}
    with app.test_client() as client:
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            with patch("backend.services.casino_rng.draw", return_value=fake):
                client.post("/api/casino/play/hilo", json={"user_id": "h3", "bet": 10})
                second = client.post("/api/casino/play/hilo", json={"user_id": "h3", "bet": 10})
    data = second.get_json()
    assert second.status_code == 400
    assert data["code"] == "HILO_ROUND_ACTIVE"


# --------------------------------------------------------------------------- #
# Tournaments
# --------------------------------------------------------------------------- #

def test_tournament_join_score_finalize_and_reconcile(tmp_path, monkeypatch):
    app = _games2_app(tmp_path, monkeypatch)  # sets _CONFIG_PATH + log dir
    from backend.services import casino_service, casino_tournaments

    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"points": {"coins": 100000}}
    mock_points.add_points.return_value = {"success": True}

    with patch("backend.services.unified_points_database.unified_points_db", mock_points):
        # Auto-create the daily coins tournament.
        listing = casino_service.list_tournaments("u1")
        assert listing["enabled"] is True
        tid = listing["tournaments"][0]["id"]

        assert casino_service.join_tournament("u1", tid)["success"] is True
        assert casino_service.join_tournament("u2", tid)["success"] is True
        # Re-join should be rejected.
        assert casino_service.join_tournament("u1", tid)["success"] is False

        # Score via the ledger hook surrogate.
        casino_tournaments.record_bet({"user_id": "u1", "currency": "coins", "net": 500, "bet": 100})
        casino_tournaments.record_bet({"user_id": "u2", "currency": "coins", "net": 100, "bet": 100})

        # Force the window closed, then finalize on next read.
        state = casino_tournaments._load_state()
        from datetime import datetime, timezone, timedelta
        state[tid]["end_at"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        casino_tournaments._save_state(state)

        final = casino_service.get_tournament(tid, "u1")["tournament"]
        assert final["status"] == "ended"
        # u1 led on net, so rank 1 with the biggest prize.
        assert final["results"][0]["user_id"] == "u1"
        # pool = 2000 seed + 50 + 50 buy-ins = 2100 ; 50% to first.
        assert final["results"][0]["prize"] == 1050

        rec = casino_service.reconcile_tournaments()
        assert rec["ok"] is True
