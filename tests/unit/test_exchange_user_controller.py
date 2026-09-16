"""Tests for exchange user controller (multi-rail checkout + cash-out)."""
import pytest


@pytest.fixture
def ctrl_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import agent_marketplace_service as mkt
    from backend.services import exchange_rental_service as rent
    from backend.services import exchange_shop_service as shop
    from backend.services import exchange_user_controller_service as ctrl

    data = tmp_path / "crypto_exchange"
    (data / "user_agents").mkdir(parents=True)
    (data / "exchange_shop").mkdir(parents=True)
    (data / "exchange_controller").mkdir(parents=True)
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(mkt, "_USER_AGENTS_DIR", str(data / "user_agents"))
    monkeypatch.setattr(rent, "_RENTALS_PATH", str(data / "rental_history.jsonl"))
    monkeypatch.setattr(shop, "_STATE_DIR", str(data / "exchange_shop"))
    monkeypatch.setattr(ctrl, "_STATE_DIR", str(data / "exchange_controller"))
    monkeypatch.setattr(ctrl, "_PAYPAL_ORDERS", str(data / "controller_paypal.json"))
    try:
        from backend.services import exchange_trust_service as trust
        monkeypatch.setattr(trust, "check_activation", lambda *a, **k: {"allowed": True})
        ex._write_json(str(data / "trust_policy.json"), {"require_manual_activation": False})
        monkeypatch.setattr(trust, "_POLICY_PATH", str(data / "trust_policy.json"))
    except Exception:
        pass

    bal = {"u1": 5000.0}
    coins = {"u1": 50000.0}
    monkeypatch.setattr(ex, "_get_quote_balance", lambda uid, q: float(bal.get(uid, 0.0)))
    monkeypatch.setattr(ex, "_adjust_quote_balance",
                        lambda uid, q, delta, source, meta=None: bal.__setitem__(uid, bal.get(uid, 0.0) + float(delta)))

    class FakeDB:
        def get_all_points(self, uid):
            return {"success": True, "points": {"coins": coins.get(uid, 0), "mn2_balance": bal.get(uid, 0)}}

        def add_points(self, user_id, point_type, amount, source="", metadata=None):
            if point_type == "coins":
                coins[user_id] = coins.get(user_id, 0) + float(amount)
            elif point_type == "mn2_balance":
                bal[user_id] = bal.get(user_id, 0) + float(amount)
            return {"success": True}

    monkeypatch.setattr("backend.services.unified_points_database.unified_points_db", FakeDB())
    return {"ctrl": ctrl, "mkt": mkt, "rent": rent, "bal": bal, "coins": coins}


def test_controller_rent_with_coins(ctrl_env):
    ctrl = ctrl_env["ctrl"]
    before_coins = ctrl_env["coins"]["u1"]
    res = ctrl.checkout("u1", "rent", "rent_starter_7d", payment_method="coins")
    assert res["success"] is True
    assert ctrl_env["coins"]["u1"] < before_coins


def test_controller_addon_with_mn2(ctrl_env):
    ctrl = ctrl_env["ctrl"]
    rent = ctrl_env["rent"]
    r = rent.rent_agent("u1", "rent_starter_7d")
    aid = r["agent"]["agent_id"]
    before = ctrl_env["bal"]["u1"]
    res = ctrl.checkout("u1", "addon", "addon_kelly", payment_method="mn2", agent_id=aid)
    assert res["success"] is True
    assert ctrl_env["bal"]["u1"] < before


def test_cash_out_to_casino_coins(ctrl_env):
    ctrl = ctrl_env["ctrl"]
    mkt = ctrl_env["mkt"]
    r = ctrl_env["rent"].rent_agent("u1", "rent_starter_7d")
    data = mkt._read_user_agents("u1")
    data["agents"][r["agent"]["agent_id"]]["realized_profit_usd"] = 25.0
    mkt._write_user_agents("u1", data)
    before = ctrl_env["coins"]["u1"]
    out = ctrl.cash_out_profit("u1", 5.0, destination="casino_coins")
    assert out["success"] is True
    assert ctrl_env["coins"]["u1"] > before


def test_controller_catalog_has_prices(ctrl_env):
    cat = ctrl_env["ctrl"].catalog_for_controller()
    assert cat["success"] is True
    assert len(cat["rentals"]) >= 1
    assert "price_usd" in cat["rentals"][0]
