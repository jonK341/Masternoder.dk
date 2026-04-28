"""
Unit tests for Points (nr 6): points_db_service.
Run: pytest tests/unit/test_06_points.py -v
"""
from tests.unit.test_utils import ensure_project_root, assert_tables_exist_returns_bool

ensure_project_root()


def test_points_analytics_tables_exist():
    import backend.services.points_db_service as svc
    assert_tables_exist_returns_bool(svc, "points_analytics_tables_exist")


def test_points_point_transactions_exist():
    import backend.services.points_db_service as svc
    assert_tables_exist_returns_bool(svc, "point_transactions_exist")


def test_points_get_analytics_daily():
    import backend.services.points_db_service as svc
    result = svc.get_analytics_daily("test-u", days=7)
    assert result is None or isinstance(result, list)


def test_points_refresh_daily_aggregates():
    import backend.services.points_db_service as svc
    result = svc.refresh_daily_aggregates(days=7)
    assert result is True or result is False


def test_points_get_analytics_summary():
    import backend.services.points_db_service as svc
    result = svc.get_analytics_summary("test-u", days=30)
    assert result is None or isinstance(result, dict)
