#!/usr/bin/env python3
"""
Warm up uWSGI workers so the site responds right after a restart.

With lazy-apps = true, each worker loads the app on its first request (can take 3–4 min).
This script sends several requests to localhost:5000 so workers load; then browsing the site
gets a response without waiting.

Run from your PC after restarting uwsgi-vidgenerator:
  python scripts/warm_up_workers.py

On the server you can do the same with:
  for i in 1 2 3 4; do curl -s -m 240 -o /dev/null -w "Worker $i: HTTP %{http_code}\n" http://127.0.0.1:5000/; done
"""
import os
import sys

SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = "root"
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
CURL_TIMEOUT = 240  # seconds per request (first load can take 3–4 min with 123 blueprints)
NUM_REQUESTS = 4    # match typical uwsgi processes = 4

def main():
    try:
        import paramiko
    except ImportError:
        print("Install paramiko: pip install paramiko")
        sys.exit(1)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    except Exception as e:
        print(f"[ERROR] SSH failed: {e}")
        sys.exit(1)

    print("Warming up uWSGI workers (each request may take 1–3 min until worker is loaded)...")
    print(f"Sending {NUM_REQUESTS} requests to http://127.0.0.1:5000/ with {CURL_TIMEOUT}s timeout each.\n")

    for i in range(1, NUM_REQUESTS + 1):
        stdin, stdout, stderr = ssh.exec_command(
            f"curl -s -m {CURL_TIMEOUT} -o /dev/null -w '%{{http_code}}' http://127.0.0.1:5000/ 2>/dev/null || echo '000'",
            timeout=CURL_TIMEOUT + 10,
        )
        try:
            raw = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
            code = raw[-3:] if len(raw) >= 3 and raw[-3:].isdigit() else (raw[:3] if raw and raw[:3].isdigit() else "000")
        except Exception:
            code = "000"
        if code == "200":
            print(f"  Request {i}: HTTP {code} (worker ready)")
        else:
            print(f"  Request {i}: HTTP {code} (timeout or not ready)")

    ssh.close()
    print("\nDone. Try https://masternoder.dk/ and https://masternoder.dk/generator in your browser.")
    print("If still no response, run: python scripts/investigate_502.py")

if __name__ == "__main__":
    main()
