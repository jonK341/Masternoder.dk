"""Agent rental, skill add-ons, and exchange shop."""
import pytest
from datetime import datetime, timedelta, timezone


@pytest.fixture
def rs_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import agent_marketplace_service as mkt
    from backend.services import exchange_rental_service as rent
    from backend.services import exchange_shop_service as shop

    data = tmp_path / "crypto_exchange"
    (data / "user_agents").mkdir(parents=True)
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(mkt, "_USER_AGENTS_DIR", str(data / "user_agents"))
    monkeypatch.setattr(rent, "_RENTALS_PATH", str(data / "rental_history.jsonl"))
    monkeypatch.setattr(shop, "_STATE_DIR", str(data / "exchange_shop"))
    monkeypatch.setattr(shop, "_PURCHASES_PATH", str(data / "shop_purchases.jsonl"))
    try:
        from backend.services import exchange_trust_service as trust
        monkeypatch.setattr(trust, "_POLICY_PATH", str(data / "trust_policy.json"))
        ex._write_json(str(data / "trust_policy.json"), {"require_manual_activation": False, "suspended_users": []})
        monkeypatch.setattr(trust, "check_activation", lambda *a, **k: {"allowed": True})
    except Exception:
        pass

    bal = {"u1": 5000.0}
    coins = {"u1": 1000.0}
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
    return {"ex": ex, "mkt": mkt, "rent": rent, "shop": shop, "bal": bal, "coins": coins}


def test_rent_agent_and_add_skill(rs_env):
    rent = rs_env["rent"]
    r = rent.rent_agent("u1", "rent_starter_7d")
    assert r["success"] is True
    assert r["agent"]["rented"] is True
    aid = r["agent"]["agent_id"]
    add = rent.add_skill_addon("u1", aid, "addon_kelly")
    assert add["success"] is True
    assert "kelly_sizing" in add["effective_skills"]
    tick = rs_env["mkt"].run_user_agent_tick("u1", aid)
    assert tick["success"] is True


def test_rental_expired_blocks_tick(rs_env):
    rent = rs_env["rent"]
    mkt = rs_env["mkt"]
    r = rent.rent_agent("u1", "rent_starter_7d")
    aid = r["agent"]["agent_id"]
    data = mkt._read_user_agents("u1")
    data["agents"][aid]["expires_at"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat().replace("+00:00", "Z")
    mkt._write_user_agents("u1", data)
    tick = mkt.run_user_agent_tick("u1", aid)
    assert tick["success"] is False
    assert tick["error"] == "rental_expired"


def test_shop_reward_chest(rs_env):
    shop = rs_env["shop"]
    before = rs_env["bal"]["u1"]
    res = shop.purchase_item("u1", "ex_reward_starter_chest")
    assert res["success"] is True
    assert rs_env["bal"]["u1"] > before - 30  # spent 30, got 5 back


def test_convert_rental_to_purchase(rs_env):
    rent = rs_env["rent"]
    mkt = rs_env["mkt"]
    r = rent.rent_agent("u1", "rent_starter_7d")
    aid = r["agent"]["agent_id"]
    before = rs_env["bal"]["u1"]
    conv = rent.convert_rental_to_purchase("u1", aid)
    assert conv["success"] is True
    assert conv["spent_mn2"] == pytest.approx(205.0)  # 250 buy - 45 rental
    assert rs_env["bal"]["u1"] == pytest.approx(before - 205.0)
    agent = mkt._read_user_agents("u1")["agents"][aid]
    assert agent.get("rented") is False
    assert "expires_at" not in agent


def test_shop_profit_boost_multiplier(rs_env):
    shop = rs_env["shop"]
    shop.purchase_item("u1", "ex_profit_boost_24h")
    assert shop.profit_multiplier("u1") == pytest.approx(1.25)


def test_rental_catalog_has_images(rs_env):
    cat = rs_env["rent"].rental_catalog()
    assert cat["success"] is True
    assert len(cat["rentals"]) >= 3
    assert all(r.get("image") for r in cat["rentals"])


def test_auto_renew_extends_rental(rs_env):
    rent = rs_env["rent"]
    r = rent.rent_agent("u1", "rent_starter_7d", auto_renew=True)
    aid = r["agent"]["agent_id"]
    mkt = rs_env["mkt"]
    data = mkt._read_user_agents("u1")
    data["agents"][aid]["expires_at"] = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat().replace("+00:00", "Z")
    mkt._write_user_agents("u1", data)
    before = rs_env["bal"]["u1"]
    res = rent.try_auto_renew("u1", aid)
    assert res["success"] is True
    assert rs_env["bal"]["u1"] < before
    tick = mkt.run_user_agent_tick("u1", aid)
    assert tick["success"] is True


def test_rental_completion_casino_bonus(rs_env):
    rent = rs_env["rent"]
    mkt = rs_env["mkt"]
    from datetime import datetime, timedelta, timezone
    r = rent.rent_agent("u1", "rent_starter_7d")
    aid = r["agent"]["agent_id"]
    data = mkt._read_user_agents("u1")
    data["agents"][aid]["expires_at"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat().replace("+00:00", "Z")
    mkt._write_user_agents("u1", data)
    before = rs_env["coins"]["u1"]
    claim = rent.claim_rental_reward("u1", aid)
    assert claim["success"] is True
    assert claim.get("casino_coins_bonus", 0) >= 50
    assert rs_env["coins"]["u1"] > before


def test_shop_linked_in_main_catalog(rs_env):
    from backend.services.exchange_shop_service import shop_items_for_catalog

    items = shop_items_for_catalog()
    ids = {i["id"] for i in items}
    assert "ex_profit_boost_24h" in ids
    assert "ex_skill_pack_arb" not in ids
    assert all(i.get("delivery") == "exchange_shop" for i in items)
