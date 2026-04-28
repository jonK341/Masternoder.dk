#!/usr/bin/env python3
"""
Check API latency from the server (avoids timeouts from restricted networks).
SSHs to the server and curls http://127.0.0.1:5000/api/health with timing.

  python scripts/check_latency_from_server.py

Use when requests to https://masternoder.dk from your/agent network time out
but you want to know if the app is responding on the box.
"""
import os
import sys

SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
# Curl format: http_code, time_total (seconds), time_connect, time_starttransfer
CURL_CMD = (
    "curl -s -o /dev/null -w '%{http_code}\\n%{time_total}\\n%{time_connect}\\n%{time_starttransfer}' "
    "--max-time 60 http://127.0.0.1:5000/api/health"
)


def main():
    try:
        import paramiko
    except ImportError:
        print("Install paramiko: pip install paramiko")
        sys.exit(1)

    print("Connecting to", SERVER_HOST, "...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
    stdin, stdout, stderr = ssh.exec_command(CURL_CMD, timeout=65)
    out = (stdout.read() or b"").decode().strip()
    err = (stderr.read() or b"").decode().strip()
    ssh.close()

    if err and "curl" not in err.lower():
        print("Stderr:", err)

    lines = [x.strip() for x in out.splitlines() if x.strip()]
    if len(lines) >= 2:
        code = lines[0]
        time_total = float(lines[1]) if lines[1].replace(".", "").isdigit() else 0
        time_connect = float(lines[2]) if len(lines) > 2 and lines[2].replace(".", "").replace("-", "").isdigit() else None
        time_ttfb = float(lines[3]) if len(lines) > 3 and lines[3].replace(".", "").replace("-", "").isdigit() else None
        ms = round(time_total * 1000)
        print("API health (from server 127.0.0.1:5000):")
        print("  HTTP status:", code)
        print("  Latency:    ", ms, "ms  (total)", round(time_total, 3), "s")
        if time_connect is not None:
            print("  Connect:    ", round(time_connect * 1000), "ms")
        if time_ttfb is not None:
            print("  TTFB:       ", round(time_ttfb * 1000), "ms")
        if code != "200":
            sys.exit(1)
    else:
        print("Unexpected output:", out or "(empty)")
        sys.exit(1)


if __name__ == "__main__":
    main()
