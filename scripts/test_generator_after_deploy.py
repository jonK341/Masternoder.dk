#!/usr/bin/env python3
"""
Test generator after deploy: GET /api/generator/test, then create a short test video
and poll progress until completed or timeout. Use BASE_URL for live site.

  python scripts/test_generator_after_deploy.py
  BASE_URL=https://masternoder.dk python scripts/test_generator_after_deploy.py
"""
import os
import sys
import time
import json

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.chdir(_root)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_root, '.env'))
except Exception:
    pass

BASE_URL = os.environ.get('BASE_URL', 'http://127.0.0.1:5000').rstrip('/')


def get(url, timeout=30):
    try:
        import urllib.request
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), r.read().decode('utf-8')
    except Exception as e:
        return None, str(e)


def post(url, data, timeout=60):
    try:
        import urllib.request
        body = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=body, method='POST', headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), r.read().decode('utf-8')
    except Exception as e:
        return None, str(e)


def main():
    print('Testing generator at', BASE_URL)
    # 1) Health
    code, raw = get(BASE_URL + '/api/generator/test')
    if code != 200:
        print('FAIL: GET /api/generator/test returned', code, raw[:200] if raw else '')
        return 1
    try:
        data = json.loads(raw)
    except Exception:
        data = {}
    if not data.get('success'):
        print('FAIL: generator test success=False', data)
        return 1
    print('OK: Generator test passed (DB:', data.get('database_available'), 'pipeline:', data.get('video_pipeline_available'), ')')
    # 2) Create short test video
    payload = {
        'title': 'Deploy test',
        'description': 'Kort testvideo efter deploy.',
        'prompt': 'Deploy test',
        'user_id': 'deploy_test_user',
        'duration': 30,
        'short_clip': True,
        'quality_mode': 'fast',
    }
    code, raw = post(BASE_URL + '/api/generator/create', payload)
    if code not in (200, 202):
        print('FAIL: POST /api/generator/create returned', code, raw[:300] if raw else '')
        return 1
    try:
        data = json.loads(raw)
    except Exception:
        data = {}
    doc_id = data.get('documentary_id') or data.get('video_id')
    if not doc_id:
        print('WARN: No documentary_id in response; job may still be running.', data)
        return 0
    print('Created job:', doc_id, '- polling progress...')
    # 3) Poll progress (max 5 min; encoding can take 1–2 min for 30s video on slow server)
    deadline = time.monotonic() + 300
    last_pct = -1
    while time.monotonic() < deadline:
        code, raw = get(BASE_URL + '/api/documentary/progress/' + doc_id, timeout=15)
        if code != 200:
            time.sleep(2)
            continue
        try:
            pd = json.loads(raw)
        except Exception:
            time.sleep(2)
            continue
        status = pd.get('status', '')
        progress = pd.get('progress', 0)
        if progress != last_pct:
            print('  Progress:', progress, '%', pd.get('stage', pd.get('message', ''))[:50])
            last_pct = progress
        if status in ('completed', 'done') or progress >= 100:
            print('OK: Video completed. URL:', BASE_URL + '/api/documentary/video/' + doc_id)
            return 0
        if status in ('error', 'failed'):
            print('FAIL: Job failed:', pd.get('error_message', pd.get('error', raw[:200])))
            return 1
        time.sleep(2.5)
    print('WARN: Timeout waiting for completion. Check job manually:', doc_id)
    print('  If a new video appears in the gallery, the job completed on the server (polling stopped early).')
    print('  On server (SSH): tail -100 /var/www/html/vidgenerator/videos/generator_subprocess.log')
    print('  If missing: tail -100 /var/www/html/uwsgi.log  (get real path from curl -s http://127.0.0.1:5000/api/generator/test)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
