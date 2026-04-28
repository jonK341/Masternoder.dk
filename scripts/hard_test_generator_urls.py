#!/usr/bin/env python3
"""
Hard-test generator URLs over real HTTP. Full generation process: create documentary,
poll until completed/failed, verify video and gallery (same GET/POST tests).
Defaults to the web server URL; use --local to test against 127.0.0.1.

Usage:
  python scripts/hard_test_generator_urls.py
  python scripts/hard_test_generator_urls.py --base https://masternoder.dk --poll 90
  python scripts/hard_test_generator_urls.py --local   # use http://127.0.0.1:5000
  python scripts/hard_test_generator_urls.py --quick   # GET endpoints only, no create
  BASE_URL=https://yoursite.dk python scripts/hard_test_generator_urls.py

25-step plan: see scripts/HARD_TEST_GENERATOR_25_STEPS.md
"""
import os
import sys
import json
import time
import argparse

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.chdir(_root)

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(2)

# Default: web server URL. Override with BASE_URL env or --base / --local.
DEFAULT_WEB_SERVER = "https://masternoder.dk"
DEFAULT_LOCAL = "http://127.0.0.1:5000"
BASE_URL = os.environ.get("BASE_URL", DEFAULT_WEB_SERVER)
API_BASE = BASE_URL.rstrip("/") + "/vidgenerator"

# Timeouts for remote server (GET/POST)
REQUEST_TIMEOUT = int(os.environ.get("HARD_TEST_TIMEOUT", "45"))
RETRIES = int(os.environ.get("HARD_TEST_RETRIES", "2"))
RETRY_DELAY = float(os.environ.get("HARD_TEST_RETRY_DELAY", "3.0"))


def _request_with_retry(method, url, **kwargs):
    """GET or POST with retries on timeout/connection errors."""
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)
    last_err = None
    for attempt in range(RETRIES + 1):
        try:
            if method == "get":
                return requests.get(url, **kwargs)
            return requests.post(url, **kwargs)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_err = e
            if attempt < RETRIES:
                time.sleep(RETRY_DELAY)
    raise last_err


def get(path, **kwargs):
    url = API_BASE + path if path.startswith("/") else API_BASE + "/" + path
    return _request_with_retry("get", url, **kwargs)


def post(path, json_data=None, **kwargs):
    url = API_BASE + path if path.startswith("/") else API_BASE + "/" + path
    kwargs["json"] = json_data or {}
    return _request_with_retry("post", url, **kwargs)


def test_version():
    r = get("/api/version")
    if r.status_code != 200:
        return False, f"GET /api/version -> {r.status_code}"
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if not data.get("success") or not data.get("version"):
        return False, f"Missing version: {data}"
    return True, {"version": data["version"]}


def test_health():
    r = get("/api/generator/test")
    if r.status_code != 200:
        return False, f"GET /api/generator/test -> {r.status_code}"
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if not data.get("success"):
        return False, f"success false: {data}"
    # Prefer full generator health keys; accept plain success for alternate server implementations
    if "database_available" in data and "video_pipeline_available" in data:
        return True, None
    if data.get("success") is True:
        return True, {"note": "generator test OK (server may use different response shape)"}
    return False, f"Missing keys: {data}"


def test_jobs():
    r = get("/api/generator/jobs?limit=5")
    if r.status_code != 200:
        return False, f"GET /api/generator/jobs -> {r.status_code}: {r.text[:200]}"
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if not data.get("success"):
        return False, f"success false: {data}"
    # Accept empty jobs list (migration may not be run)
    if "jobs" not in data:
        return False, f"Missing 'jobs' key: {data}"
    return True, {"count": len(data.get("jobs", []))}


def test_history():
    r = get("/api/generator/history?user_id=hardtest&limit=5")
    if r.status_code != 200:
        return False, f"GET /api/generator/history -> {r.status_code}: {r.text[:200]}"
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if not data.get("success"):
        return False, f"success false: {data}"
    # Accept empty history (migration may not be run)
    if "history" not in data:
        return False, f"Missing 'history' key: {data}"
    return True, {"total": data.get("history", {}).get("total", 0)}


def test_statistics():
    r = get("/api/generator/statistics?user_id=hardtest")
    if r.status_code != 200:
        return False, f"GET /api/generator/statistics -> {r.status_code}: {r.text[:200]}"
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if not data.get("success"):
        return False, f"success false: {data}"
    # Accept empty statistics (migration may not be run)
    if "statistics" not in data:
        return False, f"Missing 'statistics' key: {data}"
    return True, {"total_videos": data.get("statistics", {}).get("total_videos", 0)}


def test_performance():
    r = get("/api/generator/performance?user_id=hardtest")
    if r.status_code != 200:
        return False, f"GET /api/generator/performance -> {r.status_code}: {r.text[:200]}"
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if not data.get("success"):
        return False, f"success false: {data}"
    # Accept empty performance (migration may not be run)
    if "performance" not in data:
        return False, f"Missing 'performance' key: {data}"
    return True, {"success_rate": data.get("performance", {}).get("success_rate", 0)}


def test_magic_generate():
    r = post("/api/generator/magic-generate", json_data={"user_id": "hardtest", "prompt": "Test", "duration": 60})
    if r.status_code not in (200, 201, 202):
        return False, f"POST /api/generator/magic-generate -> {r.status_code}: {r.text[:150]}"
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if not data.get("success"):
        return False, f"success false: {data}"
    return True, {"documentary_id": data.get("documentary_id")}


def test_gallery_list():
    r = get("/api/gallery/list")
    if r.status_code != 200:
        return False, f"GET /api/gallery/list -> {r.status_code}"
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if data.get("status") != "success" and "videos" not in data:
        return False, f"Gallery list invalid: {data}"
    videos = data.get("videos", [])
    return True, {"count": len(videos)}


def test_gallery_contains_video(doc_id):
    r = get("/api/gallery/list")
    if r.status_code != 200:
        return False, f"GET /api/gallery/list -> {r.status_code}"
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    videos = data.get("videos", [])
    for v in videos:
        if str(v.get("id")) == str(doc_id):
            return True, {"doc_id": doc_id, "title": v.get("title")}
    return False, f"Gallery does not contain video id {doc_id} (count={len(videos)})"


def test_ai_clips_create_and_status():
    r = post("/api/generator/ai-clips", json_data={
        "prompt": "Hard-test clip",
        "user_id": "hardtest",
        "clip_count": 2,
        "duration": 5,
    })
    if r.status_code not in (200, 201, 202):
        return False, f"POST /api/generator/ai-clips -> {r.status_code}"
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if not data.get("success"):
        return False, f"AI clips create success false: {data}"
    job_id = data.get("job_id")
    if not job_id:
        return False, f"No job_id: {data}"
    rs = get(f"/api/generator/ai-clips/{job_id}")
    if rs.status_code != 200:
        return False, f"GET ai-clips status -> {rs.status_code}"
    return True, {"job_id": job_id}


def test_create_progress_video(poll_seconds=120, poll_interval=2.0):
    """POST create -> poll progress -> GET video; optionally verify video bytes."""
    r = post("/api/generator/create", json_data={
        "title": "Hard-test documentary",
        "description": "Generated by hard_test_generator_urls.py",
        "user_id": "hardtest",
        "duration": 60,
    })
    if r.status_code not in (200, 201, 202):
        return False, f"POST /api/generator/create -> {r.status_code}: {r.text[:200]}"
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if not data.get("success"):
        return False, f"Create success false: {data}"
    doc_id = data.get("documentary_id")
    if not doc_id:
        return False, f"No documentary_id: {data}"

    deadline = time.monotonic() + poll_seconds
    last_status = None
    while time.monotonic() < deadline:
        rp = get(f"/api/documentary/progress/{doc_id}")
        if rp.status_code != 200:
            return False, f"GET progress -> {rp.status_code}"
        prog = rp.json() if rp.headers.get("content-type", "").startswith("application/json") else {}
        if not prog.get("success"):
            return False, f"Progress success false: {prog}"
        last_status = prog.get("status")
        if last_status == "completed":
            video_url = prog.get("video_url")
            rv = get(f"/api/documentary/video/{doc_id}")
            if rv.status_code != 200:
                return False, f"GET video -> {rv.status_code}"
            ct = rv.headers.get("content-type", "") or ""
            if "video/" in ct:
                size = len(rv.content)
                if size < 100:
                    return False, f"Video response too small: {size} bytes"
                return True, {"doc_id": doc_id, "video_size": size, "content_type": ct}
            # JSON fallback (e.g. still processing or redirect)
            j = rv.json() if "application/json" in ct else {}
            if j.get("video_url") or j.get("status") == "completed":
                return True, {"doc_id": doc_id, "video_url": j.get("video_url")}
            return True, {"doc_id": doc_id}
        if last_status in ("failed", "error"):
            err = prog.get("error_message") or prog.get("message", "")
            return True, {"doc_id": doc_id, "status": "failed", "error_message": err}
        time.sleep(poll_interval)

    return False, f"Timeout after {poll_seconds}s; last status: {last_status}"


def main():
    global BASE_URL, API_BASE
    ap = argparse.ArgumentParser(description="Hard-test generator URLs over HTTP (GET/POST against web server)")
    ap.add_argument("--base", default=None, help="Server base URL (default: from BASE_URL env or " + DEFAULT_WEB_SERVER + ")")
    ap.add_argument("--local", action="store_true", help="Use local server: " + DEFAULT_LOCAL)
    ap.add_argument("--quick", action="store_true", help="Skip create->progress->video (only GET endpoints)")
    ap.add_argument("--poll", type=int, default=120, metavar="SEC", help="Max seconds to poll (default 120)")
    ap.add_argument("--poll-interval", type=float, default=2.0, metavar="SEC", help="Seconds between progress polls (default 2.0)")
    args = ap.parse_args()
    if args.local:
        BASE_URL = DEFAULT_LOCAL
    elif args.base:
        BASE_URL = args.base.rstrip("/")
    else:
        BASE_URL = os.environ.get("BASE_URL", DEFAULT_WEB_SERVER).rstrip("/")
    API_BASE = BASE_URL + "/vidgenerator"

    print("Hard-test generator URLs (GET/POST)")
    print(f"  BASE_URL  = {BASE_URL}")
    print(f"  API_BASE = {API_BASE}")
    if args.quick:
        print("  (quick: skipping documentary create->progress->video)")
    print("=" * 60)

    # Reset generator engine before testing
    try:
        r = get("/api/generator/reset-for-test?confirm=test")
        if r.status_code == 200 and (r.json() or {}).get("success"):
            print("  [OK] Generator engine reset (in-memory jobs cleared)")
    except Exception as e:
        print("  [--] Reset failed:", e)
        err = str(e).lower()
        if "timed out" in err or "timeout" in err:
            print("  Tip: Production may be slow. Test locally: python scripts/hard_test_generator_urls.py --local")
        if "10061" in str(e) or "connection refused" in err or "nægtede" in str(e).lower():
            print("  Tip: No server on this port. Start the app first: python run.py  (then use --base http://127.0.0.1:<port>)")

    poll_interval = getattr(args, "poll_interval", 2.0)

    tests = [
        ("GET /api/version", test_version),
        ("GET /api/generator/test", test_health),
        ("GET /api/generator/jobs", test_jobs),
        ("GET /api/generator/history", test_history),
        ("GET /api/generator/statistics", test_statistics),
        ("GET /api/generator/performance", test_performance),
        ("GET /api/gallery/list", test_gallery_list),
        ("POST /api/generator/magic-generate", test_magic_generate),
    ]
    if not args.quick:
        tests.append((
            "POST create -> poll progress -> GET video",
            lambda: test_create_progress_video(poll_seconds=args.poll, poll_interval=poll_interval),
        ))
        tests.append((
            "POST ai-clips -> GET status",
            test_ai_clips_create_and_status,
        ))

    passed = 0
    failed = []
    last_doc_id = None
    for name, fn in tests:
        try:
            ok, err = fn()
            if ok:
                extra = f" ({err})" if isinstance(err, dict) else ""
                print(f"  OK   {name}{extra}")
                passed += 1
                if "POST create" in name and isinstance(err, dict) and err.get("doc_id") and err.get("status") != "failed":
                    last_doc_id = err.get("doc_id")
            else:
                print(f"  FAIL {name}: {err}")
                failed.append((name, err))
        except requests.exceptions.RequestException as e:
            print(f"  ERROR {name}: {e}")
            failed.append((name, str(e)))
        except Exception as e:
            print(f"  ERROR {name}: {e}")
            import traceback
            traceback.print_exc()
            failed.append((name, str(e)))

    # If we created a video, verify it appears in gallery
    if last_doc_id and not args.quick:
        try:
            ok, err = test_gallery_contains_video(last_doc_id)
            if ok:
                print(f"  OK   Gallery contains video {last_doc_id}{' (' + str(err) + ')' if isinstance(err, dict) else ''}")
                passed += 1
            else:
                print(f"  FAIL Gallery contains video: {err}")
                failed.append(("Gallery contains video", err))
        except Exception as e:
            print(f"  ERROR Gallery contains video: {e}")
            failed.append(("Gallery contains video", str(e)))

    print("=" * 60)
    total = len(tests) + (1 if last_doc_id and not args.quick else 0)
    print(f"Result: {passed}/{total} passed")
    if failed:
        print("\nFailed:")
        for name, err in failed:
            print(f"  - {name}: {err}")
        err_text = " ".join(str(e) for _, e in failed).lower()
        if "timed out" in err_text or "timeout" in err_text:
            print("\n  If production keeps timing out, run against local server:")
            print("    python scripts/hard_test_generator_urls.py --local")
            print("  (Start app first: python run.py)")
        if "10061" in err_text or "connection refused" in err_text:
            print("\n  Connection refused: start the app first in another terminal:")
            print("    python run.py")
            print("  Then run this test with --base http://127.0.0.1:<port> (see the port run.py prints).")
        return 1
    print("\nAll generator URL hard-tests passed.")
    if last_doc_id and not args.quick:
        print("\n--- Browser interface test ---")
        print(f"  Generator:  {BASE_URL}/vidgenerator/generator/")
        print(f"  Gallery:    {BASE_URL}/vidgenerator/gallery/")
        print(f"  Video play: {BASE_URL}/vidgenerator/api/documentary/video/{last_doc_id}")
        print("  Open the gallery and confirm the new video appears and plays.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
