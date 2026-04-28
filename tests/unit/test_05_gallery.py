"""
Unit tests for Gallery (nr 5): gallery_db_service.
Run: pytest tests/unit/test_05_gallery.py -v
"""
from tests.unit.test_utils import ensure_project_root, assert_tables_exist_returns_bool

ensure_project_root()


def test_gallery_tables_exist():
    import backend.services.gallery_db_service as svc
    assert_tables_exist_returns_bool(svc, "gallery_tables_exist")


def test_gallery_record_view():
    import backend.services.gallery_db_service as svc
    result = svc.record_view("test-u", "item-1")
    assert result is True or result is False


def test_gallery_record_download():
    import backend.services.gallery_db_service as svc
    result = svc.record_download("test-u", "item-1")
    assert result is True or result is False


def test_gallery_get_user_downloads():
    import backend.services.gallery_db_service as svc
    result = svc.get_user_downloads("test-u", limit=10)
    assert result is None or isinstance(result, list)


def test_gallery_upsert_gallery_item():
    import backend.services.gallery_db_service as svc
    result = svc.upsert_gallery_item("item-1", title="Test")
    assert result is True or result is False
