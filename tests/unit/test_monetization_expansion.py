"""Top-10 monetization expansion services."""
from __future__ import annotations

import os
import shutil
import tempfile

import pytest

from backend.services.monetization_config_service import reload_monetization_config
from backend.services.shop_checkout_promo_service import validate_checkout_promo
from backend.services.monetization_priority_service import queue_priority_bonus
from backend.services.scr_checkout_service import list_scr_checkout_skus
from backend.services.generator_premium_checkout_service import quote_premium_render
from backend.services.battle_pass_service import get_battle_pass_status, purchase_battle_pass_premium
from backend.services.generator_api_key_service import create_api_key, resolve_api_key
from backend.services import shop_monetization_service as mon
from backend.services import battle_pass_service as bp_mod


class FakePointsDB:
    def __init__(self):
        self.coins = {}

    def set_coins(self, uid, n):
        self.coins[uid] = int(n)

    def get_all_points(self, user_id="default_user"):
        return {
            "success": True,
            "user_id": user_id,
            "points": {"coins": int(self.coins.get(user_id, 0)), "mn2_balance": 0.0},
        }

    def add_points(self, user_id, point_type, amount, source="system", metadata=None):
        if point_type == "coins":
            self.coins[user_id] = int(self.coins.get(user_id, 0)) + int(amount)
        return {"success": True}


@pytest.fixture
def battle_pass_shop_db(monkeypatch):
    tmp_dir = tempfile.mkdtemp(prefix="bp_test_")
    state_path = os.path.join(tmp_dir, "battle_pass.json")
    monkeypatch.setattr(bp_mod, "_STATE", state_path)
    db = FakePointsDB()
    monkeypatch.setattr(mon, "_points_db", lambda: db)
    try:
        yield db
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_promo_validate():
    reload_monetization_config()
    out = validate_checkout_promo("WELCOME10", "u1", amount_usd=10.0)
    assert out["success"] is True
    assert out["discount_percent"] == 10
    assert out["amount_usd_discounted"] == 9.0


def test_scr_skus_list():
    reload_monetization_config()
    out = list_scr_checkout_skus()
    assert out["success"] is True
    assert any(s["id"] == "scr-studio-90d-500" for s in out["skus"])


def test_premium_quote():
    q = quote_premium_render("u1", {"quality_mode": "studio", "duration": 200})
    assert q["success"] is True
    assert q["premium_required"] is True
    assert q["price_usd"] >= 0.99


def test_battle_pass_config():
    reload_monetization_config()
    out = get_battle_pass_status("u_bp")
    assert out["success"] is True
    assert out.get("season_id")


def test_battle_pass_coin_purchase_deducts(battle_pass_shop_db):
    reload_monetization_config()
    uid = "bp_buyer"
    status = get_battle_pass_status(uid)
    price = int(status.get("price_coins") or 0)
    assert price > 0
    battle_pass_shop_db.set_coins(uid, price + 500)
    before = battle_pass_shop_db.coins[uid]

    out = purchase_battle_pass_premium(uid, source="shop_coins")
    assert out["success"] is True
    paid = int(out["price_paid_coins"] or 0)
    assert paid > 0
    assert battle_pass_shop_db.coins[uid] == before - paid + int(out.get("granted_coins") or 0)

    again = purchase_battle_pass_premium(uid, source="shop_coins")
    assert again.get("already_owned") is True


def test_battle_pass_insufficient_coins(battle_pass_shop_db):
    reload_monetization_config()
    out = purchase_battle_pass_premium("broke_bp", source="shop_coins")
    assert out["success"] is False
    assert "insufficient" in (out.get("error") or "").lower()


def test_battle_pass_paypal_skips_coin_charge(battle_pass_shop_db):
    reload_monetization_config()
    uid = "bp_paypal"
    battle_pass_shop_db.set_coins(uid, 0)
    out = purchase_battle_pass_premium(uid, source="paypal")
    assert out["success"] is True
    assert out.get("price_paid_coins") is None
    assert battle_pass_shop_db.coins[uid] == int(out.get("granted_coins") or 0)


def test_api_key_roundtrip(monkeypatch):
    monkeypatch.setenv("GENERATOR_API_KEY_SECRET", "test-secret")
    created = create_api_key(org_label="acme", user_id="u_api", label="test")
    assert created["success"] is True
    row = resolve_api_key(created["api_key"])
    assert row is not None
    assert row.get("org_label") == "acme"


def test_queue_priority_bonus():
    b = queue_priority_bonus("default_user")
    assert b == 0
