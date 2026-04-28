"""shop_api_line_checks helpers — kind_ok + JSON load."""
from __future__ import annotations

from tests.unit.test_utils import ensure_project_root

ensure_project_root()

from backend.services.shop_api_line_checks import (  # noqa: E402
    kind_ok,
    load_shop_v4_api_line_checks,
)


def test_load_shop_v4_api_line_checks_has_ten_entries():
    data = load_shop_v4_api_line_checks()
    assert isinstance(data.get("checks"), list)
    assert len(data["checks"]) == 10


def test_load_shop_v4_api_line_checks_falls_back_when_file_missing():
    data = load_shop_v4_api_line_checks("missing-shop-api-line-checks.json")
    assert data.get("source") == "built_in_fallback"
    assert isinstance(data.get("checks"), list)
    assert len(data["checks"]) == 10


def test_kind_shop_items_ok_empty_list():
    assert kind_ok("shop_items_ok", {"success": True, "items": []}) is True


def test_kind_shop_items_ok_missing_items_with_success():
    assert kind_ok("shop_items_ok", {"success": True}) is True


def test_kind_shop_items_ok_explicit_failure():
    assert kind_ok("shop_items_ok", {"success": False, "items": []}) is False


def test_kind_payment_health_ok():
    assert kind_ok("payment_health_ok", {"success": True, "mn2_daemon": {}, "paypal": {}}) is True
    assert kind_ok("payment_health_ok", {"success": True}) is False
