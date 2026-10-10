"""Generator P0: cross-worker progress via sidecar before in-memory job."""
from __future__ import annotations

import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


@pytest.fixture
def videos_tmp(monkeypatch, tmp_path):
    monkeypatch.setattr(
        'backend.services.video_generator_service.VIDEOS_DIR',
        str(tmp_path),
        raising=False,
    )
    return tmp_path


def test_get_video_job_prefers_sidecar_over_memory(videos_tmp):
    from backend.routes import generator_shared as gs

    doc_id = 'sidecar-pref-1'
    gs.reset_engine_for_test()
    gs.set_video_job(doc_id, {
        'id': doc_id,
        'status': 'processing',
        'progress': 5,
        'message': 'old worker',
        'updated_at': '2020-01-01T00:00:00Z',
    })
    sidecar_path = videos_tmp / f'{doc_id}.status.json'
    sidecar_path.write_text(
        json.dumps({
            'id': doc_id,
            'status': 'processing',
            'progress': 72,
            'message': 'Encoding video',
            'updated_at': '2030-01-01T00:00:00Z',
        }),
        encoding='utf-8',
    )

    job = gs.get_video_job(doc_id)
    assert job is not None
    assert job['progress'] == 72
    assert job['message'] == 'Encoding video'


def test_documentary_progress_uses_sidecar_without_memory_job(videos_tmp):
    from flask import Flask

    doc_id = 'sidecar-only-2'
    sidecar_path = videos_tmp / f'{doc_id}.status.json'
    sidecar_path.write_text(
        json.dumps({
            'id': doc_id,
            'status': 'processing',
            'progress': 40,
            'message': 'Building segments',
            'updated_at': '2030-06-01T12:00:00Z',
        }),
        encoding='utf-8',
    )

    from backend.routes.generator_routes import generator_bp

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(generator_bp)
    with app.test_client() as client:
        r = client.get(f'/api/documentary/progress/{doc_id}')
    assert r.status_code == 200
    data = r.get_json()
    assert data.get('success') is True
    assert data.get('progress') == 40
    assert data.get('status') == 'processing'
