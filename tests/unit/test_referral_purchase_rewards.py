"""Tier C1/C2 — referral purchase rewards and upsell suggestions."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def referral_social(tmp_path, monkeypatch):
    social_path = tmp_path / "social_structure.json"
    social_path.write_text(
        json.dumps(
            {
                "referrals": {
                    "codes": {"REF123": {"user_id": "referrer-1"}},
                    "signups": [
                        {
                            "id": "sig-1",
                            "referrer_user_id": "referrer-1",
                            "referred_user_id": "buyer-1",
                            "code": "REF123",
                        }
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    import backend.services.referral_purchase_rewards_service as svc

    monkeypatch.setattr(svc, "_SOCIAL_PATH", str(social_path))
    return social_path


def test_classify_purchase_kinds():
    from backend.services.referral_purchase_rewards_service import classify_purchase

    assert classify_purchase(item_id="coin-pack-500", is_coin_pack=True) == "coin_pack"
    assert classify_purchase(item_id="mnq_host_1", product="mn2_masternode_hosting") == "hosting"
    assert classify_purchase(item_id="bundle-mn2-starter") == "bundle"
    assert classify_purchase(item_id="booster-staking-150-7d") == "shop_item"


def test_referrer_rewarded_once(referral_social, monkeypatch):
    from backend.services import referral_purchase_rewards_service as svc

    awarded = []

    class FakePoints:
        def add_points(self, user_id, point_type, amount, source=None, metadata=None):
            awarded.append((user_id, point_type, amount, source, metadata))
            return {"success": True}

    monkeypatch.setattr(
        "backend.services.unified_points_database.unified_points_db",
        FakePoints(),
    )
    monkeypatch.setattr("backend.routes.social_routes.push_activity", lambda *a, **k: None)

    first = svc.maybe_reward_referrer(
        "buyer-1",
        purchase_kind="coin_pack",
        item_id="coin-pack-100",
        order_id="ord-1",
        amount_usd=9.99,
    )
    second = svc.maybe_reward_referrer(
        "buyer-1",
        purchase_kind="hosting",
        item_id="mnq_host_1",
        order_id="ord-2",
    )

    assert first["rewarded"] is True
    assert first["referrer_coins"] == 100
    assert second["rewarded"] is False
    assert second.get("duplicate") is True
    assert len(awarded) == 1

    saved = json.loads(Path(referral_social).read_text(encoding="utf-8"))
    row = saved["referrals"]["signups"][0]
    assert row.get("purchase_rewarded_at")
    assert row.get("purchase_reward_coins") == 100


def test_no_referrer_is_noop(monkeypatch):
    from backend.services import referral_purchase_rewards_service as svc

    monkeypatch.setattr(svc, "_load_social", lambda: {"referrals": {"signups": []}})
    out = svc.maybe_reward_referrer("solo-user", purchase_kind="coin_pack")
    assert out["rewarded"] is False
    assert out.get("reason") == "no_referrer"


def test_upsell_suggestions():
    from backend.services.shop_upsell_service import upsell_suggestions

    coin = upsell_suggestions(item_id="coin-pack-100", coins_granted=100, purchase_kind="coin_pack")
    assert any("bundle" in (r.get("title") or "").lower() for r in coin)
    assert len(coin) <= 3

    host = upsell_suggestions(item_id="mnq_host", purchase_kind="hosting")
    assert any("staking" in (r.get("title") or "").lower() for r in host)

    big = upsell_suggestions(item_id="coin-pack-500", coins_granted=600, purchase_kind="coin_pack")
    assert big[0]["title"].startswith("VIP")
