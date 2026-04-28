#!/usr/bin/env python3
"""
Test and debug key URLs for root-first setup (masternoder.dk at /, /generator, redirects).

Local warnings (non-blocking): "No module named 'bs4'" -> pip install beautifulsoup4 (or pip install -r requirements.txt).

Usage:
  # Test local app (Flask test client)
  python scripts/test_and_debug_urls.py

  # Test live site via HTTP (from a machine that can reach the server)
  python scripts/test_and_debug_urls.py --live

  # Restart uWSGI on server, then test live URLs (fix 502 / timeouts then verify)
  python scripts/test_and_debug_urls.py --live --reboot

  # Test live with custom base URL
  BASE_URL=https://masternoder.dk python scripts/test_and_debug_urls.py --live
"""
import io
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BASE_URL = os.environ.get("BASE_URL", "https://masternoder.dk").rstrip("/")
TIMEOUT = int(os.environ.get("LIVE_TIMEOUT", "20"))


def test_live():
    """Curl live/base URL and report status + redirect."""
    try:
        import urllib.request
        import urllib.error
        import ssl
    except ImportError:
        print("Use Python 3 with urllib.request for --live")
        return 2

    ctx = ssl.create_default_context()
    urls = [
        ("/", "root"),
        ("/generator", "generator"),
        ("/vidgenerator", "vidgenerator (expect 301 to /)"),
        ("/vidgenerator/generator", "vidgenerator/generator (expect 301 to /generator)"),
        ("/static/css/modern-design-system.css", "static asset"),
        ("/api/health", "API health"),
    ]
    print(f"Testing {BASE_URL} (timeout={TIMEOUT}s)")
    print("=" * 60)
    all_ok = True
    for path, label in urls:
        url = BASE_URL + path
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MasternoderUrlTest/1.0"})
            r = urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx)
            code = r.getcode()
            loc = r.headers.get("Location", "")
            if loc:
                print(f"  {path:45} -> {code} -> {loc}")
            else:
                print(f"  {path:45} -> {code} OK")
        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location", "")
            if e.code in (301, 302, 307, 308) and loc:
                print(f"  {path:45} -> {e.code} -> {loc}")
            else:
                print(f"  {path:45} -> {e.code} FAIL")
                all_ok = False
        except urllib.error.URLError as e:
            reason = str(e.reason) if e.reason else str(e)
            if "timed out" in reason.lower() or "timeout" in reason.lower():
                print(f"  {path:45} -> READ TIMEOUT (server did not respond in {TIMEOUT}s)")
                print("       Hint: server may be down, overloaded, or nginx/uWSGI misconfigured. Check SERVER_QUICK_REFERENCE.md")
            else:
                print(f"  {path:45} -> ERROR: {e}")
            all_ok = False
        except (OSError, TimeoutError) as e:
            if "timed out" in str(e).lower() or "timeout" in str(e).lower():
                print(f"  {path:45} -> READ TIMEOUT (server did not respond in {TIMEOUT}s)")
                print("       Hint: server may be down, overloaded, or nginx/uWSGI misconfigured. Check SERVER_QUICK_REFERENCE.md")
            else:
                print(f"  {path:45} -> ERROR: {e}")
            all_ok = False
        except Exception as e:
            print(f"  {path:45} -> ERROR: {e}")
            all_ok = False
    print("=" * 60)
    if not all_ok:
        print("If timeouts persist: ensure uWSGI and nginx are running on the server; disk space and worker count can affect response time.")
    return 0 if all_ok else 1


def test_local():
    """Use Flask test client to verify routes."""
    sys.path.insert(0, str(PROJECT_ROOT))
    os.chdir(PROJECT_ROOT)
    # Ensure instance dir exists before any app code runs (avoids "unable to open database file")
    (PROJECT_ROOT / "instance").mkdir(exist_ok=True)
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    # Suppress blueprint/SQLite/bs4 startup messages during import
    _saved_stdout, _saved_stderr = sys.stdout, sys.stderr
    try:
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        from run import app
    except Exception as e:
        sys.stdout, sys.stderr = _saved_stdout, _saved_stderr
        print(f"Failed to load app: {e}")
        return 2
    finally:
        sys.stdout, sys.stderr = _saved_stdout, _saved_stderr

    with app.test_client() as c:
        cases = [
            ("/", 200, None, "root"),
            ("/generator", 200, None, "generator"),
            ("/vidgenerator", 301, "/", "vidgenerator -> /"),
            ("/vidgenerator/", 301, "/", "vidgenerator/ -> /"),
            ("/vidgenerator/generator", 301, "/generator", "vidgenerator/generator -> /generator"),
            ("/static/css/modern-design-system.css", (200, 404), None, "static (200 or 404)"),
        ]
        print("Local Flask test client")
        print("=" * 60)
        all_ok = True
        for path, expect_code, expect_location, label in cases:
            r = c.get(path)
            codes = (expect_code,) if isinstance(expect_code, int) else expect_code
            loc = r.headers.get("Location")
            ok = r.status_code in codes and (expect_location is None or loc == expect_location)
            if not ok:
                all_ok = False
            loc_str = f" -> {loc}" if loc else ""
            status = "OK" if ok else "FAIL"
            print(f"  {path:45} {r.status_code}{loc_str:30} [{status}] {label}")
        print("=" * 60)
        return 0 if all_ok else 1


def main():
    if "--live" not in sys.argv:
        return test_local()
    if "--reboot" in sys.argv:
        script_dir = Path(__file__).resolve().parent
        restart_script = script_dir / "restart_uwsgi_fix_502.py"
        if not restart_script.exists():
            print("restart_uwsgi_fix_502.py not found; run --live without --reboot")
            return 2
        print("Running: python scripts/restart_uwsgi_fix_502.py")
        print("(Then live URL tests will run.)\n")
        rc = subprocess.call(
            [sys.executable, str(restart_script)],
            cwd=PROJECT_ROOT,
            timeout=300,
        )
        if rc != 0:
            print(f"\nRestart script exited with {rc}; continuing with URL tests anyway.")
    return test_live()


if __name__ == "__main__":
    sys.exit(main())
