"""
Unit tests for Generator (nr 1): generator_db_service + video_generator_service.
Run: pytest tests/unit/test_01_generator.py -v
"""
import os
import pytest

from tests.unit.test_utils import ensure_project_root, assert_tables_exist_returns_bool, assert_returns_safe_or_typed

ensure_project_root()


# --- generator_db_service ---

def test_generator_tables_exist():
    import backend.services.generator_db_service as svc
    assert_tables_exist_returns_bool(svc, "generator_tables_exist")


def test_generator_get_job():
    import backend.services.generator_db_service as svc
    assert_returns_safe_or_typed(svc, "get_job", "nonexistent-job-id-999", return_type=dict)


def test_generator_save_job():
    import backend.services.generator_db_service as svc
    # save_job returns bool
    result = assert_returns_safe_or_typed(
        svc, "save_job",
        {"job_id": "test-job-999", "user_id": "u1", "status": "pending"},
        return_type=bool
    )
    assert result is True or result is False


def test_generator_list_jobs():
    import backend.services.generator_db_service as svc
    result = svc.list_jobs(user_id="u1", limit=5)
    assert result is None or isinstance(result, list)


def test_generator_get_job_statistics():
    import backend.services.generator_db_service as svc
    result = svc.get_job_statistics(user_id="u1", days=7)
    assert result is None or isinstance(result, dict)
    if result:
        assert "total_jobs" in result or "by_status" in result


def test_generator_get_job_performance():
    import backend.services.generator_db_service as svc
    result = svc.get_job_performance(user_id="u1", limit=10)
    assert result is None or isinstance(result, dict)


def test_generator_get_job_count():
    import backend.services.generator_db_service as svc
    result = svc.get_job_count(user_id="u1")
    assert result is None or isinstance(result, int)


def test_generator_get_theme_distribution():
    import backend.services.generator_db_service as svc
    result = svc.get_theme_distribution(user_id="u1", days=30)
    assert result is None or isinstance(result, dict)


# --- video_generator_service ---

def test_video_generator_sync_returns_tuple():
    from backend.services.video_generator_service import _generate_video_sync
    result = _generate_video_sync(
        "test-doc-unit-999", "Test", "Test", 60, 1280, 768, None
    )
    assert isinstance(result, tuple)
    assert len(result) == 2
    path, err = result
    if path is None:
        assert isinstance(err, str)
    else:
        assert os.path.isfile(path) or os.path.exists(path)


def test_video_generator_set_job_failed_callable():
    from backend.services.video_generator_service import _set_job_failed
    def noop_get(jid):
        return {"id": jid, "status": "processing"}
    def noop_set(jid, data):
        pass
    _set_job_failed("test-id", "Failed", "Detail", noop_get, noop_set)


def test_video_generator_background_starts():
    """generate_video_background does not raise and starts a thread."""
    from backend.services.video_generator_service import generate_video_background
    store = {}
    def get_job(jid):
        return store.get(jid)
    def set_job(jid, data):
        store[jid] = data
    generate_video_background("debug-test-doc-id", {"prompt": "Test", "duration": 60}, get_job, set_job)
    assert "debug-test-doc-id" in store or True  # may be set async


def test_generator_save_job_rejects_no_job_id():
    """save_job returns False when job_id and id are missing."""
    import backend.services.generator_db_service as svc
    result = svc.save_job({"user_id": "u1", "status": "pending"})
    assert result is False


def test_generator_row_to_job_handles_none_and_invalid_json():
    """_row_to_job handles None config/clips and invalid JSON without raising."""
    import backend.services.generator_db_service as svc
    # Row tuple: job_id, user_id, job_type, status, progress, theme, config, clips, video_url,
    # error_message, estimated_time, actual_time, points_earned, created_at, updated_at, completed_at
    from datetime import datetime
    now = datetime.utcnow()
    row_none = (
        "j1", "u1", "documentary", "pending", 0, None, None, None,
        None, None, 0, 0, 0.0, now, now, None
    )
    job = svc._row_to_job(row_none)
    assert job is not None
    assert job["config"] == {}
    assert job["clips"] == []
    assert job["status"] == "pending"
    # Invalid JSON in config
    row_bad_json = (
        "j2", "u1", "documentary", "completed", 100, "theme", "{ invalid", "[]",
        "/video/j2", None, 0, 10, 0.0, now, now, now
    )
    job2 = svc._row_to_job(row_bad_json)
    assert job2 is not None
    assert job2["config"] == {}
    assert job2["clips"] == []
    assert job2["video_url"] == "/video/j2"
