#!/usr/bin/env python3
"""
Start the Flask server and run the hard test generator script.
Use when you want one command to: start server -> wait for ready -> run full generation test.

  python scripts/run_generation_and_test.py
  python scripts/run_generation_and_test.py --no-start   # only run test (server must be running)
  python scripts/run_generation_and_test.py --poll 90

Run from project root.
"""
import os
import sys
import subprocess
import time
import argparse

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_root)
sys.path.insert(0, _root)

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")


def wait_for_server(timeout=30, interval=1.0):
    try:
        import requests
    except ImportError:
        print("Install requests: pip install requests")
        return False
    deadline = time.monotonic() + timeout
    api_base = BASE_URL.rstrip("/") + "/vidgenerator"
    url = api_base + "/api/generator/test"
    while time.monotonic() < deadline:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200 and (r.json() or {}).get("success"):
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def main():
    ap = argparse.ArgumentParser(description="Start server and run hard test generator")
    ap.add_argument("--no-start", action="store_true", help="Do not start server; only run test (server must be running)")
    ap.add_argument("--poll", type=int, default=120, help="Max seconds to poll for video completion")
    ap.add_argument("--wait", type=int, default=30, help="Max seconds to wait for server to be ready")
    args = ap.parse_args()

    server_proc = None
    if not args.no_start:
        print("Starting Flask server...")
        try:
            server_proc = subprocess.Popen(
                [sys.executable, "run.py"],
                cwd=_root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            print(f"Failed to start server: {e}")
            return 2
        print(f"Server PID {server_proc.pid}; waiting up to {args.wait}s for ready...")
        if not wait_for_server(timeout=args.wait):
            print("Server did not become ready in time.")
            if server_proc:
                server_proc.terminate()
            return 2
        print("Server is ready.\n")

    try:
        cmd = [sys.executable, os.path.join(_root, "scripts", "hard_test_generator_urls.py"), "--poll", str(args.poll)]
        code = subprocess.call(cmd, cwd=_root)
        return code
    finally:
        if server_proc and server_proc.poll() is None:
            server_proc.terminate()
            print("\nServer stopped.")


if __name__ == "__main__":
    sys.exit(main())
