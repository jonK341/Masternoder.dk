"""
Unit tests for Shop V9.2 monetization service.

State is isolated per-test via MASTERNODER_LOG_DIR (tmp), and all balance
operations are routed through an in-memory fake points DB so the tests never
touch real unified_points stores or require a Flask app context.
"""
import shutil
import tempfile

import pytest

from backend.services import shop_monetization_service as mon


class FakePointsDB:
    def __init__(self):
        self.coins = {}
        self.mn2 = {}
        self.boosters = []
        self.game_time = 0

    def set_coins(self, uid, n):
        self.coins[uid] = int(n)

    def get_all_points(self, user_id="default_user"):
        return {
            "success": True,
            "user_id": user_id,
            "points": {
                "coins": int(self.coins.get(user_id, 0)),
                "mn2_balance": float(self.mn2.get(user_id, 0)),
            },
        }

    def add_points(self, user_id, point_type, amount, source="system", metadata=None):
        if point_type == "coins":
            self.coins[user_id] = int(self.coins.get(user_id, 0)) + int(amount)
        elif point_type == "mn2_balance":
            self.mn2[user_id] = float(self.mn2.get(user_id, 0)) + float(amount)
        return {"success": True}

    def add_booster(self, user_id, booster_id, duration_minutes, name=""):
        self.boosters.append((user_id, booster_id, duration_minutes))
        return {"success": True}

    def add_game_time_minutes(self, user_id, minutes):
        self.game_time += int(minutes)
        return {"success": True}


@pytest.fixture
def fake_db(monkeypatch):
    tmp_dir = tempfile.mkdtemp(prefix="shopmon_test_")
    monkeypatch.setenv("MASTERNODER_LOG_DIR", tmp_dir)
    db = FakePointsDB()
    monkeypatch.setattr(mon, "_points_db", lambda: db)
    try:
        yield db
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_config_present():
    cfg = mon.get_config()
    assert cfg.get("vip_pass")
    assert cfg.get("mystery_boxes")
    assert cfg.get("spin_wheel")


def test_vip_activation_and_daily_claim(fake_db):
    uid = "tester1"
    status = mon.get_vip_status(uid)
    assert status["active"] is False

    mon.activate_vip(uid, days=30)
    status = mon.get_vip_status(uid)
    assert status["active"] is True
    assert status["discount_pct"] >= 0
    assert status["can_claim_daily"] is True

    result = mon.claim_vip_daily(uid)
    assert result["success"] is True
    assert result["coins_granted"] >= 0
    assert fake_db.coins.get(uid, 0) == result["coins_granted"]

    # Second claim same day is blocked.
    again = mon.claim_vip_daily(uid)
    assert again["success"] is False


def test_vip_discount_applies_to_box_price(fake_db):
    uid = "tester_vip"
    boxes_no_vip = mon.list_mystery_boxes(uid)
    base = boxes_no_vip[0]["price_coins"]
    assert boxes_no_vip[0]["effective_price_coins"] == base

    mon.activate_vip(uid, days=30)
    boxes_vip = mon.list_mystery_boxes(uid)
    assert boxes_vip[0]["effective_price_coins"] <= base


def test_open_mystery_box_charges_and_rewards(fake_db):
    uid = "boxer"
    boxes = mon.list_mystery_boxes(uid)
    box = boxes[0]
    fake_db.set_coins(uid, box["price_coins"] + 1000)
    before = fake_db.coins[uid]

    result = mon.open_mystery_box(uid, box["id"], payment_method="coins")
    assert result["success"] is True
    assert result["reward"]["type"] in {"coins", "booster", "loyalty", "item", "nothing", "game_time"}
    # Net coins change = -price + (reward coins if any)
    reward_coins = result["reward"].get("amount", 0) if result["reward"]["type"] == "coins" else 0
    assert fake_db.coins[uid] == before - result["price_paid_coins"] + reward_coins


def test_open_mystery_box_insufficient_coins(fake_db):
    uid = "broke"
    boxes = mon.list_mystery_boxes(uid)
    fake_db.set_coins(uid, 0)
    result = mon.open_mystery_box(uid, boxes[0]["id"], payment_method="coins")
    assert result["success"] is False


def test_spin_wheel_free_then_paid(fake_db):
    uid = "spinner"
    status = mon.get_spin_status(uid)
    assert status["free_available"] is True

    free = mon.spin_wheel(uid, paid=False)
    assert free["success"] is True
    assert free["free_spin"] is True

    # Non-VIP gets a single free spin/day; next free attempt should fall through
    # to paid and fail without coins.
    status2 = mon.get_spin_status(uid)
    assert status2["free_available"] is False

    fake_db.set_coins(uid, status2["spin_cost_coins"] + 10)
    paid = mon.spin_wheel(uid, paid=True)
    assert paid["success"] is True
    assert paid["free_spin"] is False
    assert paid["price_paid_coins"] == status2["spin_cost_coins"]


def test_gifting_transfers_coins(fake_db):
    sender, recipient = "alice", "bob"
    fake_db.set_coins(sender, 500)
    result = mon.gift_coins(sender, recipient, 200)
    assert result["success"] is True
    assert fake_db.coins[sender] == 300
    assert fake_db.coins[recipient] == 200

    gifts = mon.list_gifts(sender)
    assert len(gifts["sent"]) == 1


def test_gifting_validation(fake_db):
    fake_db.set_coins("alice", 5)
    # below minimum
    assert mon.gift_coins("alice", "bob", 1)["success"] is False
    # self gift
    assert mon.gift_coins("alice", "alice", 50)["success"] is False
    # insufficient
    assert mon.gift_coins("alice", "bob", 50)["success"] is False


def test_loyalty_accrual_and_redeem(fake_db, fake_catalog):
    uid = "loyal"
    # Accrue via box opens
    boxes = mon.list_mystery_boxes(uid)
    fake_db.set_coins(uid, 100000)
    for _ in range(20):
        mon.open_mystery_box(uid, boxes[-1]["id"], payment_method="coins")
    loyalty = mon.get_loyalty(uid)
    assert loyalty["points"] > 0

    rewards = loyalty["rewards"]
    assert rewards
    cheapest = min(rewards, key=lambda r: r.get("cost_points", 10**9))
    if loyalty["points"] >= cheapest["cost_points"]:
        before = loyalty["points"]
        res = mon.redeem_loyalty(uid, cheapest["id"])
        assert res["success"] is True
        assert mon.get_loyalty(uid)["points"] == before - cheapest["cost_points"]


def test_accrue_purchase_loyalty_awards_points(fake_db):
    uid = "spender"
    res = mon.accrue_purchase_loyalty(uid, 1000)
    assert res["earned"] > 0
    assert mon.get_loyalty(uid)["points"] == res["earned"]


def test_accrue_purchase_loyalty_noop_for_guest(fake_db):
    assert mon.accrue_purchase_loyalty("default_user", 1000)["earned"] == 0
    assert mon.accrue_purchase_loyalty("", 1000)["earned"] == 0
    assert mon.accrue_purchase_loyalty("u", 0)["earned"] == 0


def test_featured_listing_requires_ownership(fake_db):
    assert mon.get_featured_listing_ids() == []
    result = mon.feature_listing("someone", "nonexistent-listing")
    assert result["success"] is False


_FAKE_CATALOG = [
    {"id": "shop-1", "name": "Galaxy Dark", "category": "themes", "price": 100, "icon": "🎨", "rarity": "rare"},
    {"id": "shop-2", "name": "XP Booster", "category": "boosts", "price": 60, "icon": "⚡", "rarity": "common"},
    {"id": "shop-3", "name": "Battle Ticket", "category": "battle", "price": 200, "icon": "🎫", "rarity": "rare"},
    {"id": "shop-4", "name": "Avatar Frame", "category": "cosmetic", "price": 40, "icon": "🖼️", "rarity": "common"},
]


@pytest.fixture
def fake_catalog(monkeypatch):
    from backend.routes import shop_routes

    monkeypatch.setattr(shop_routes, "_get_shop_items", lambda: [dict(i) for i in _FAKE_CATALOG])
    return _FAKE_CATALOG


def test_flash_sales_shape(fake_db, fake_catalog):
    data = mon.get_flash_sales()
    assert "sales" in data
    assert isinstance(data["sales"], list)
    assert len(data["sales"]) >= 1
    for sale in data["sales"]:
        assert sale["deal_price"] <= sale["original_price"]
        assert 0 < sale["discount_pct"] <= 60


def test_flash_sales_rotation_is_stable_within_window(fake_db, fake_catalog):
    first = mon.get_flash_sales()
    second = mon.get_flash_sales()
    assert [s["item_id"] for s in first["sales"]] == [s["item_id"] for s in second["sales"]]


def test_overview_aggregates(fake_db, fake_catalog):
    uid = "viewer"
    fake_db.set_coins(uid, 1000)
    ov = mon.get_overview(uid)
    assert "vip" in ov and "loyalty" in ov and "spin" in ov
    assert "top25" in ov
    assert ov["coin_balance"] == 1000


# --------------------------- Top 25 collection ---------------------------

@pytest.fixture
def fake_inventory(monkeypatch):
    """In-memory inventory backing shop_db_service.get_inventory / add_to_inventory."""
    from backend.services import shop_db_service

    store = {}

    def _get_inventory(user_id):
        return [{"item_id": iid, "quantity": q} for iid, q in store.get(user_id, {}).items()]

    def _add_to_inventory(user_id, item_id, item_name, quantity, purchase_id=None):
        store.setdefault(user_id, {})[item_id] = store.get(user_id, {}).get(item_id, 0) + int(quantity)
        return True

    monkeypatch.setattr(shop_db_service, "get_inventory", _get_inventory, raising=False)
    monkeypatch.setattr(shop_db_service, "add_to_inventory", _add_to_inventory, raising=False)
    return store


def _own_top25(store, uid, count):
    store.setdefault(uid, {})
    for n in range(1, count + 1):
        store[uid][f"top25-{n:02d}"] = 1


def test_top25_status_incomplete(fake_db, fake_inventory):
    uid = "collector"
    _own_top25(fake_inventory, uid, 10)
    st = mon.get_top25_status(uid)
    assert st["owned_count"] == 10
    assert st["total"] == 25
    assert st["complete"] is False
    assert st["claimable"] is False


def test_top25_claim_requires_full_set(fake_db, fake_inventory):
    uid = "collector2"
    _own_top25(fake_inventory, uid, 24)
    res = mon.claim_top25_completion(uid)
    assert res["success"] is False


def test_top25_claim_grants_reward_once(fake_db, fake_inventory):
    uid = "collector3"
    _own_top25(fake_inventory, uid, 25)
    st = mon.get_top25_status(uid)
    assert st["complete"] is True and st["claimable"] is True

    res = mon.claim_top25_completion(uid)
    assert res["success"] is True
    assert fake_db.coins.get(uid, 0) >= 5000
    # Trophy landed in inventory.
    assert "top25-collector-trophy" in fake_inventory.get(uid, {})

    # Second claim is blocked.
    again = mon.claim_top25_completion(uid)
    assert again["success"] is False
    assert mon.get_top25_status(uid)["claimed"] is True


def test_top25_claim_guest_blocked(fake_db, fake_inventory):
    assert mon.claim_top25_completion("default_user")["success"] is False
    assert mon.claim_top25_completion("")["success"] is False
