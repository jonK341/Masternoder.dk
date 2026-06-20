"""Tier B product bundles — on-ramp+hosting, auction fee, copy-trading, casino MN2 buy-in."""
from __future__ import annotations

import os
import shutil
import tempfile

import pytest

from backend.services.monetization_config_service import reload_monetization_config
from backend.services.tier_b_monetization_service import (
    get_auction_fee_info,
    get_copy_trading_premium_status,
    get_onramp_hosting_offer,
    purchase_copy_trading_premium,
)
from backend.services.battle_pass_service import record_battle_pass_action, get_battle_pass_status
from backend.services import shop_monetization_service as mon
from backend.services import battle_pass_service as bp_mod
from backend.services import casino_service as casino_mod


class FakePointsDB:
    def __init__(self):
        self.balances = {}

    def _key(self, user_id, point_type):
        return (user_id, point_type)

    def set_balance(self, uid, point_type, amount):
        self.balances[self._key(uid, point_type)] = amount

    def get_all_points(self, user_id="default_user"):
        coins = int(self.balances.get(self._key(user_id, "coins"), 0))
        mn2 = float(self.balances.get(self._key(user_id, "mn2_balance"), 0))
        fiat = float(self.balances.get(self._key(user_id, "casino_fiat_balance"), 0))
        return {
            "success": True,
            "user_id": user_id,
            "points": {"coins": coins, "mn2_balance": mn2, "casino_fiat_balance": fiat},
        }

    def add_points(self, user_id, point_type, amount, source="system", metadata=None):
        k = self._key(user_id, point_type)
        if point_type == "coins":
            self.balances[k] = int(self.balances.get(k, 0)) + int(amount)
        else:
            self.balances[k] = float(self.balances.get(k, 0)) + float(amount)
        return {"success": True}


@pytest.fixture
def tier_b_env(monkeypatch):
    reload_monetization_config()
    tmp_dir = tempfile.mkdtemp(prefix="tier_b_test_")
    bp_path = os.path.join(tmp_dir, "battle_pass.json")
    ct_path = os.path.join(tmp_dir, "copy_trading_premium.json")
    monkeypatch.setattr(bp_mod, "_STATE", bp_path)
    db = FakePointsDB()
    monkeypatch.setattr(mon, "_points_db", lambda: db)
    import backend.services.unified_points_database as updb

    monkeypatch.setattr(updb, "unified_points_db", db)

    def _fake_charge(uid, amount, payment_method="coins", source="", metadata=None):
        snap = db.get_all_points(uid)
        bal = int((snap.get("points") or {}).get("coins") or 0)
        if bal < int(amount):
            return False, "insufficient_coins"
        db.add_points(uid, "coins", -int(amount), source=source)
        return True, None

    monkeypatch.setattr(mon, "_charge", _fake_charge)
    try:
        yield db
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_onramp_hosting_offer_shape():
    reload_monetization_config()
    out = get_onramp_hosting_offer("u_tier_b")
    assert out["success"] is True
    assert len(out["steps"]) == 2
    assert out["promo_code"]


def test_auction_fee_enforced():
    reload_monetization_config()
    out = get_auction_fee_info()
    assert out["success"] is True
    assert out["fee_rate"] == 0.05
    assert out["enforced"] is True


def test_battle_pass_quest_completion(tier_b_env):
    reload_monetization_config()
    out = record_battle_pass_action("u_quest", "shop_purchase")
    assert out["success"] is True
    assert out.get("xp_granted", 0) >= 75
    st = get_battle_pass_status("u_quest")
    done = [q for q in (st.get("quests") or []) if q.get("id") == "bp-shop-1"]
    assert done and done[0].get("completed") is True


def test_copy_trading_premium_coins(tier_b_env):
    reload_monetization_config()
    tier_b_env.set_balance("u_ct", "coins", 1000)
    st = get_copy_trading_premium_status("u_ct")
    assert st["success"] is True
    assert st["active"] is False
    buy = purchase_copy_trading_premium("u_ct", source="shop_coins")
    assert buy["success"] is True
    st2 = get_copy_trading_premium_status("u_ct")
    assert st2["active"] is True


def test_mn2_buyin_packs(tier_b_env):
    reload_monetization_config()
    packs = casino_mod.get_mn2_buyin_packs()
    assert packs["success"] is True
    assert any(p["id"] == "casino_mn2_starter" for p in packs.get("packs") or [])
    tier_b_env.set_balance("u_casino", "mn2_balance", 50.0)
    pack = next(p for p in packs["packs"] if p["id"] == "casino_mn2_starter")
    out = casino_mod.purchase_mn2_buyin_pack("u_casino", pack["id"])
    assert out["success"] is True
    snap = tier_b_env.get_all_points("u_casino")
    assert float(snap["points"]["casino_fiat_balance"]) == float(pack["casino_usd_credit"])
