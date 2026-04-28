"""
Unit tests for Shop (nr 7): shop_db_service.
Run: pytest tests/unit/test_07_shop.py -v
"""
from tests.unit.test_utils import ensure_project_root, assert_tables_exist_returns_bool

ensure_project_root()


def test_shop_tables_exist():
    import backend.services.shop_db_service as svc
    assert_tables_exist_returns_bool(svc, "shop_tables_exist")


def test_shop_get_shop_items_from_db():
    import backend.services.shop_db_service as svc
    result = svc.get_shop_items_from_db()
    assert result is None or isinstance(result, list)


def test_shop_record_purchase():
    import backend.services.shop_db_service as svc
    result = svc.record_purchase(
        user_id="test-u", item_id="item-1", item_name="Test Item",
        quantity=1, price_type="points", price_paid_coins=0
    )
    assert result is None or isinstance(result, int)


def test_shop_add_to_inventory():
    import backend.services.shop_db_service as svc
    result = svc.add_to_inventory("test-u", "item-1", "Test", 1)
    assert result is True or result is False


def test_shop_get_purchases():
    import backend.services.shop_db_service as svc
    result = svc.get_purchases("test-u", limit=10)
    assert isinstance(result, list)


def test_shop_get_inventory():
    import backend.services.shop_db_service as svc
    result = svc.get_inventory("test-u")
    assert isinstance(result, list)


def test_shop_get_analytics_popular_items():
    import backend.services.shop_db_service as svc
    result = svc.get_analytics_popular_items(limit=5)
    assert isinstance(result, list)


def test_shop_get_analytics_revenue_by_item():
    import backend.services.shop_db_service as svc
    result = svc.get_analytics_revenue_by_item()
    assert isinstance(result, list)


def test_shop_get_analytics_revenue_by_category():
    import backend.services.shop_db_service as svc
    result = svc.get_analytics_revenue_by_category(days=7)
    assert isinstance(result, list)


def test_shop_get_analytics_user_spending():
    import backend.services.shop_db_service as svc
    result = svc.get_analytics_user_spending("test-u")
    assert isinstance(result, dict)


def test_shop_get_analytics_refund_stats():
    import backend.services.shop_db_service as svc
    result = svc.get_analytics_refund_stats()
    assert isinstance(result, dict)
