"""Unit tests for shop serial metadata (numbers, classes, keys)."""
import pytest

from backend.services.shop_serial_service import (
    build_serial_key,
    enrich_shop_items_serial,
    serial_class_for_category,
    serial_class_summary,
)


def test_serial_class_for_category():
    assert serial_class_for_category("themes") == ("THM", "Themes")
    assert serial_class_for_category("BOOSTS") == ("BST", "Boosts")
    assert serial_class_for_category("unknown") == ("OTH", "Other")


def test_build_serial_key_stable():
    k1 = build_serial_key("THM", 42, "shop-42")
    k2 = build_serial_key("THM", 42, "shop-42")
    assert k1 == k2
    assert k1.startswith("MN2-THM-000042-")
    assert len(k1.split("-")) >= 4


def test_enrich_shop_items_serial_order_and_keys():
    items = [
        {"id": "shop-2", "category": "themes", "name": "B"},
        {"id": "shop-1", "category": "boosts", "name": "A"},
        {"id": "shop-best-agent-offer", "category": "premium", "name": "Agent"},
    ]
    enrich_shop_items_serial(items)
    # shop-1 should be serial 1, shop-2 serial 2, special id last
    by_id = {i["id"]: i for i in items}
    assert by_id["shop-1"]["serial_no"] == 1
    assert by_id["shop-2"]["serial_no"] == 2
    assert by_id["shop-best-agent-offer"]["serial_no"] == 3
    assert by_id["shop-1"]["serial_class"] == "BST"
    assert "serial_key" in by_id["shop-1"] and len(by_id["shop-1"]["serial_key"]) >= 18


def test_serial_class_summary():
    items = [
        {"serial_class": "THM", "serial_class_label": "Themes"},
        {"serial_class": "THM", "serial_class_label": "Themes"},
        {"serial_class": "BST", "serial_class_label": "Boosts"},
    ]
    s = serial_class_summary(items)
    assert any(x["code"] == "THM" and x["count"] == 2 for x in s)
    assert any(x["code"] == "BST" and x["count"] == 1 for x in s)
