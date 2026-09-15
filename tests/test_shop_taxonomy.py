#!/usr/bin/env python3
"""Shop taxonomy: inventory/catalog subcategory classification."""
import os
import sys
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
os.chdir(BASE)


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


if __name__ == "__main__":
    unittest.main()
