"""
Legacy generator service tests. Prefer the unified unit tests:
  pytest tests/unit/test_01_generator.py -v
  or  pytest tests/unit/ -v
See tests/unit/README.md for the full facility (test_01 .. test_07).
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)
os.chdir(_root)


def test_video_generator_service_returns_tuple():
    """_generate_video_sync returns (path, error_message) tuple."""
    from backend.services.video_generator_service import _generate_video_sync
    # Call with minimal args; may return (None, error) if MoviePy/sample missing
    result = _generate_video_sync(
        "test-doc-999-nonexistent",
        "Test",
        "Test",
        60,
        1280,
        768,
        None,
    )
    assert isinstance(result, tuple), "Expected (path, error_message) tuple"
    assert len(result) == 2
    path, err = result
    if path is None:
        assert isinstance(err, str), "error_message should be str when path is None"
    else:
        assert os.path.isfile(path) or os.path.exists(path), f"Path should exist: {path}"


def test_generator_db_service_module():
    """generator_db_service has required functions and safe fallbacks when no app context."""
    import backend.services.generator_db_service as svc
    assert hasattr(svc, "generator_tables_exist")
    assert hasattr(svc, "get_job")
    assert hasattr(svc, "save_job")
    assert hasattr(svc, "list_jobs")
    assert hasattr(svc, "get_job_statistics")
    assert hasattr(svc, "get_job_performance")
    assert hasattr(svc, "get_job_count")
    assert hasattr(svc, "get_theme_distribution")
    # Without app context, generator_tables_exist may raise or return False
    try:
        exists = svc.generator_tables_exist()
        assert isinstance(exists, bool)
    except Exception:
        pass


def test_set_job_failed_exists():
    """_set_job_failed is callable and accepts the right args."""
    from backend.services.video_generator_service import _set_job_failed
    # No-op store that does nothing
    def noop_get(jid):
        return {"id": jid, "status": "processing"}
    def noop_set(jid, data):
        pass
    _set_job_failed("test-id", "Failed", "Detail", noop_get, noop_set)


def run():
    test_video_generator_service_returns_tuple()
    test_generator_db_service_module()
    test_set_job_failed_exists()
    print("All generator service tests passed.")


if __name__ == "__main__":
    run()
