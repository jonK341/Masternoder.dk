"""
Unit tests for Trophies (nr 3): trophies_db_service.
Run: pytest tests/unit/test_03_trophies.py -v
"""
from tests.unit.test_utils import ensure_project_root, assert_tables_exist_returns_bool

ensure_project_root()


def test_trophies_tables_exist():
    import backend.services.trophies_db_service as svc
    assert_tables_exist_returns_bool(svc, "trophies_tables_exist")


def test_trophies_get_trophy_definitions():
    import backend.services.trophies_db_service as svc
    result = svc.get_trophy_definitions()
    assert isinstance(result, list)


def test_trophies_get_user_trophies():
    import backend.services.trophies_db_service as svc
    result = svc.get_user_trophies("test-user")
    assert isinstance(result, list)


def test_trophies_award_trophy():
    import backend.services.trophies_db_service as svc
    result = svc.award_trophy(user_id="test-user", trophy_id=1)
    assert result is True or result is False
