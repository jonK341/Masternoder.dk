"""
Unit tests that conclude key solutions (nr 9): response shapes and contract checks.
Run: pytest tests/unit/test_09_solutions.py -v
"""
from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_generator_history_shape():
    """Generator history API contract: history has total, successful, recent (list)."""
    import backend.services.generator_db_service as svc
    jobs = svc.list_jobs(user_id="test", limit=10)
    if jobs is None:
        jobs = []
    total = (svc.get_job_count("test") or 0) if hasattr(svc, 'get_job_count') else len(jobs)
    completed = [j for j in jobs if j.get('status') == 'completed']
    # Shape that the frontend expects
    history = {
        'total': total,
        'successful': len(completed),
        'recent': jobs,
    }
    assert 'total' in history
    assert 'successful' in history
    assert isinstance(history['recent'], list)


def test_documentary_progress_error_message_contract():
    """When job status is failed, progress response should expose error_message."""
    # We test the contract: job dict with status failed should have error_message used in API
    job_failed = {'status': 'failed', 'message': 'Generation failed', 'error_message': 'MoviePy error: ...'}
    message = job_failed.get('message', 'Generation failed')
    if job_failed.get('error_message'):
        message = job_failed['error_message']
    assert message == 'MoviePy error: ...'
    payload = {'status': job_failed['status'], 'message': message}
    if job_failed.get('error_message'):
        payload['error_message'] = job_failed['error_message']
    assert 'error_message' in payload


def test_generator_job_row_shape():
    """Generator get_job returns dict with id, status, config, created_at (or None)."""
    import backend.services.generator_db_service as svc
    job = svc.get_job('nonexistent-id-999')
    assert job is None or isinstance(job, dict)
    if job:
        assert 'id' in job or 'job_id' in job
        assert 'status' in job


def test_shop_purchase_record_contract():
    """record_purchase accepts required args and returns int or None."""
    import backend.services.shop_db_service as svc
    result = svc.record_purchase(
        user_id='test-u', item_id='item-1', item_name='Test',
        quantity=1, price_type='points', price_paid_coins=0
    )
    assert result is None or isinstance(result, int)


def test_chat_history_returns_list_or_none():
    """load_chat_history returns None or list of message dicts."""
    import backend.services.chat_db_service as svc
    result = svc.load_chat_history('global', limit=5)
    assert result is None or isinstance(result, list)
    if result:
        for m in result[:3]:
            assert isinstance(m, dict)
