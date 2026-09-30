"""High-value bridge product: cross-quests, fused leaderboard, market fan-out."""
import pytest
from unittest.mock import patch


@pytest.fixture
def bridge_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import agent_marketplace_service as mkt
    from backend.services import exchange_rental_service as rent
    from backend.services import exchange_casino_quest_service as quests
    from backend.services import exchange_casino_leaderboard_service as lb

    data = tmp_path / "crypto_exchange"
    (data / "user_agents").mkdir(parents=True)
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit.jsonl"))
    monkeypatch.setattr(mkt, "_USER_AGENTS_DIR", str(data / "user_agents"))
    monkeypatch.setattr(rent, "_RENTALS_PATH", str(data / "rentals.jsonl"))
    monkeypatch.setattr(quests, "_STATE_DIR", str(data / "quests"))
    monkeypatch.setattr(lb, "_STATE_PATH", str(data / "leaderboard.json"))

    coins = {"u1": 1000.0}
    bal = {"u1": 5000.0}
    monkeypatch.setattr(ex, "_get_quote_balance", lambda uid, q: float(bal.get(uid, 0.0)))
    monkeypatch.setattr(ex, "_adjust_quote_balance",
                        lambda uid, q, delta, source, meta=None: bal.__setitem__(uid, bal.get(uid, 0.0) + float(delta)))

    class FakeDB:
        def get_all_points(self, uid):
            return {"success": True, "points": {"coins": coins.get(uid, 0), "mn2_balance": bal.get(uid, 0)}}

        def add_points(self, user_id, point_type, amount, source="", metadata=None):
            if point_type == "coins":
                coins[user_id] = coins.get(user_id, 0) + float(amount)
            return {"success": True}

    monkeypatch.setattr("backend.services.unified_points_database.unified_points_db", FakeDB())
    try:
        from backend.services import exchange_trust_service as trust
        monkeypatch.setattr(trust, "check_activation", lambda *a, **k: {"allowed": True})
        monkeypatch.setattr(trust, "_POLICY_PATH", str(data / "trust.json"))
        ex._write_json(str(data / "trust.json"), {"require_manual_activation": False})
    except Exception:
        pass
    return {"quests": quests, "lb": lb, "rent": rent, "coins": coins}


def test_cross_quest_rent_completes(bridge_env):
    quests = bridge_env["quests"]
    rent = bridge_env["rent"]
    before = bridge_env["coins"]["u1"]
    rent.rent_agent("u1", "rent_starter_7d")
    st = quests.quest_status("u1")
    rent_q = next(q for q in st["quests"] if q["id"] == "xcq-rent-bot")
    assert rent_q["completed"] is True
    assert bridge_env["coins"]["u1"] > before


def test_cross_quest_mn2_wins_progress(bridge_env):
    quests = bridge_env["quests"]
    for _ in range(3):
        quests.record_bridge_action("u1", "casino_mn2_win")
    st = quests.quest_status("u1")
    win_q = next(q for q in st["quests"] if q["id"] == "xcq-mn2-wins-3")
    assert win_q["completed"] is True


def test_fused_leaderboard_scores(bridge_env):
    lb = bridge_env["lb"]
    lb.record_trader_profit("u1", 5.0)
    lb.record_highroller_net("u1", 0.2)
    lb.record_rental_start("u1")
    board = lb.weekly_leaderboard(user_id="u1")
    assert board["success"] is True
    assert board["your_rank"]["score"] > 0


def test_market_fanout_bridge_combined_embed():
    from backend.services import market_discord_fanout as mdf

    rental = {"type": "exchange_rental_start", "payload": {"name": "Pro Bot", "days": 7, "price_mn2": 120}}
    win = {"type": "casino_mn2_big_win", "payload": {"net": 1.5, "game": "dice"}}
    embed = mdf._embed_bridge_combined(rental, win)
    assert "Pro Bot" in embed["embeds"][0]["description"]
    assert "1.5000 MN2" in embed["embeds"][0]["description"]


def test_market_fanout_rental_event():
    from backend.services import market_discord_fanout as mdf

    row = {"type": "exchange_rental_start", "payload": {"name": "Elite", "days": 3, "price_mn2": 95}}
    embed = mdf._embed_for_event(row)
    assert embed is not None
    assert "Elite" in embed["embeds"][0]["description"]
