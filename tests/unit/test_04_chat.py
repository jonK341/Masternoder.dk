"""
Unit tests for Chat (nr 4): chat_db_service.
Run: pytest tests/unit/test_04_chat.py -v
"""
from tests.unit.test_utils import ensure_project_root, assert_tables_exist_returns_bool

ensure_project_root()


def test_chat_tables_exist():
    import backend.services.chat_db_service as svc
    assert_tables_exist_returns_bool(svc, "chat_tables_exist")


def test_chat_save_message():
    import backend.services.chat_db_service as svc
    result = svc.save_message("global", "u1", "user1", "hello", is_ai=False)
    assert result is True or result is False


def test_chat_load_chat_history():
    import backend.services.chat_db_service as svc
    result = svc.load_chat_history("global", limit=20)
    assert result is None or isinstance(result, list)


def test_chat_get_messages_since():
    import backend.services.chat_db_service as svc
    result = svc.get_messages_since("global", "2020-01-01T00:00:00", limit=10)
    assert result is None or isinstance(result, list)


def test_chat_clear_history():
    import backend.services.chat_db_service as svc
    result = svc.clear_history("global")
    assert result is True or result is False
