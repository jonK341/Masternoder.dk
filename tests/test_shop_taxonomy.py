#!/usr/bin/env python3
"""Shop taxonomy: inventory/catalog subcategory classification."""
import os
import sys
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
os.chdir(BASE)


UPGRADE_ITEM_IDS = (
    "shop-taxonomy-navigator",
    "agent-settlement-cron-badge",
    "agent-shop-finish-token",
    "mn2-daemon-health-probe",
    "rented-mn-uptime-pass-7d",
    "instant-mn2-reward-chest",
    "multi-wallet-ledger-ribbon",
    "profile-subtab-unlock-flair",
    "casino-subtab-chip-pack",
    "agent-tx-cron-scheduler",
    "mn2-wallet-api-shield",
    "settlement-finish-bundle",
)


class TestShopTaxonomy(unittest.TestCase):
    def test_super_stack_is_stacks(self):
        from backend.services.shop_taxonomy_service import classify_item
        row = classify_item(item_id="shop-super-stack-core", name="Super Stack Core", category="inventory")
        self.assertEqual(row["subcategory"], "stacks")
        self.assertEqual(row["parent"], "ops")

    def test_star_map_is_maps(self):
        from backend.services.shop_taxonomy_service import classify_item
        row = classify_item(item_id="star-map", name="Star Map — 7 Nearest Stars", category="inventory")
        self.assertEqual(row["subcategory"], "maps")

    def test_booster_is_boosts(self):
        from backend.services.shop_taxonomy_service import classify_item
        row = classify_item(item_id="booster-1", name="Booster Pack #1", category="boosts")
        self.assertEqual(row["subcategory"], "boosts")
        self.assertEqual(row["parent"], "play")

    def test_enrich_rows_adds_subcategory(self):
        from backend.services.shop_taxonomy_service import enrich_rows
        rows = enrich_rows(
            [{"item_id": "x", "item_name": "DNA Test Kit", "quantity": 2}],
            {"x": {"id": "x", "name": "DNA Test Kit", "category": "inventory", "icon": "🧬"}},
        )
        self.assertEqual(rows[0]["subcategory"], "kits")
        self.assertEqual(rows[0]["icon"], "🧬")

    def test_taxonomy_navigator_is_ops_kits(self):
        from backend.services.shop_taxonomy_service import classify_item
        row = classify_item(
            item_id="shop-taxonomy-navigator",
            name="Shop Taxonomy Navigator",
            category="inventory",
        )
        self.assertEqual(row["parent"], "ops")
        self.assertEqual(row["subcategory"], "kits")

    def test_mn2_daemon_probe_is_wallet(self):
        from backend.services.shop_taxonomy_service import classify_item
        row = classify_item(
            item_id="mn2-daemon-health-probe",
            name="MN2 Daemon Health Probe",
            category="mn2_services",
        )
        self.assertEqual(row["parent"], "wallet")
        self.assertEqual(row["subcategory"], "wallet")

    def test_coin_pack_special_subcats(self):
        from backend.services.shop_taxonomy_service import special_subcategory_for
        self.assertEqual(
            special_subcategory_for("coin_packs", {"id": "coin-pack-s", "price_usd": 0.99, "coins_granted": 100}),
            "starter",
        )
        self.assertEqual(
            special_subcategory_for(
                "coin_packs",
                {"id": "coin-pack-m", "price_usd": 4.99, "coins_granted": 500, "featured": True},
            ),
            "value",
        )
        self.assertEqual(
            special_subcategory_for("coin_packs", {"id": "coin-pack-l", "price_usd": 9.99, "coins_granted": 2000}),
            "whale",
        )

    def test_mn2_service_special_subcats(self):
        from backend.services.shop_taxonomy_service import special_subcategory_for
        self.assertEqual(
            special_subcategory_for("mn2_services", {"service_id": "masternode_hosting", "name": "Hosting"}),
            "hosting",
        )
        self.assertEqual(
            special_subcategory_for("mn2_services", {"service_id": "staking", "name": "Staking Pool"}),
            "staking",
        )
        self.assertEqual(
            special_subcategory_for("mn2_services", {"service_id": "p2p", "name": "P2P MN2 Marketplace"}),
            "market",
        )
        self.assertEqual(
            special_subcategory_for("mn2_services", {"service_id": "onramp", "name": "PayPal On-Ramp"}),
            "wallet",
        )
        self.assertEqual(
            special_subcategory_for("mn2_services", {"service_id": "proof_of_reserves", "name": "Proof of Reserves"}),
            "reports",
        )

    def test_tx_subcategory(self):
        from backend.services.shop_taxonomy_service import tx_subcategory_for
        self.assertEqual(tx_subcategory_for("deposit"), "deposit")
        self.assertEqual(tx_subcategory_for("withdraw"), "withdraw")
        self.assertEqual(tx_subcategory_for("shop_spend"), "spend")
        self.assertEqual(tx_subcategory_for("reward_credit"), "reward")
        self.assertEqual(tx_subcategory_for("unknown-xyz"), "other")

    def test_casino_and_exchange_parents(self):
        from backend.services.shop_taxonomy_service import casino_parent_for, exchange_parent_for
        self.assertEqual(casino_parent_for("avatar"), "look")
        self.assertEqual(casino_parent_for("booster"), "play")
        self.assertEqual(casino_parent_for("vip_flair"), "vip")
        self.assertEqual(exchange_parent_for("rental"), "rent")
        self.assertEqual(exchange_parent_for("skill"), "play")
        self.assertEqual(exchange_parent_for("fee"), "ops")

    def test_profile_and_nav_groups(self):
        from backend.services.shop_taxonomy_service import nav_group_for, profile_hub_parent_for
        self.assertEqual(profile_hub_parent_for("shop"), "market")
        self.assertEqual(profile_hub_parent_for("wallet"), "market")
        self.assertEqual(profile_hub_parent_for("overview"), "you")
        self.assertEqual(profile_hub_parent_for("battle"), "play")
        self.assertEqual(nav_group_for("shop"), "market")
        self.assertEqual(nav_group_for("battle"), "play")
        self.assertEqual(nav_group_for("debugger"), "ops")

    def test_taxonomy_payload_includes_new_tables(self):
        from backend.services.shop_taxonomy_service import taxonomy_payload
        payload = taxonomy_payload()
        self.assertIn("parents", payload)
        self.assertIn("special_groups", payload)
        self.assertIn("coin_packs", payload["special_groups"])
        self.assertIn("profile_hub_parents", payload)
        self.assertIn("nav_groups", payload)
        self.assertIn("tx_subcategories", payload)
        self.assertIn("casino_parents", payload)
        self.assertIn("exchange_parents", payload)


class TestShopUpgradeWave(unittest.TestCase):
    def test_seed_includes_upgrade_wave_ids(self):
        from backend.routes.shop_routes import _seed_shop_items
        ids = {i.get("id") for i in _seed_shop_items()}
        missing = [iid for iid in UPGRADE_ITEM_IDS if iid not in ids]
        self.assertEqual(missing, [], f"seed catalog missing upgrade items: {missing}")

    def test_get_shop_items_merges_mn2_services_and_upgrade_wave(self):
        from unittest.mock import patch
        from backend.routes import shop_routes

        fake_db = [{"id": "legacy-theme", "name": "Legacy", "category": "themes", "price": 10}]
        with patch.object(shop_routes, "get_coin_pack_map", return_value={}), patch.object(
            shop_routes, "get_mn2_pack_map", return_value={}
        ), patch(
            "backend.services.shop_db_service.get_shop_items_from_db", return_value=list(fake_db)
        ):
            items = shop_routes._get_shop_items()
        ids = {i.get("id") for i in items}
        self.assertIn("legacy-theme", ids)
        self.assertIn("svc-mn2-masternode-hosting", ids)
        self.assertIn("shop-taxonomy-navigator", ids)
        self.assertIn("settlement-finish-bundle", ids)
        hosting = next(i for i in items if i.get("id") == "svc-mn2-masternode-hosting")
        self.assertEqual(hosting.get("category"), "mn2_services")


if __name__ == "__main__":
    unittest.main()
