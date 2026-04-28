#!/usr/bin/env python3
"""Test key API URLs from the server (127.0.0.1:5000) via SSH. Use to see if 502/slow is server or network."""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE, ".env"))
except ImportError:
    pass
SERVER_PASS = os.environ.get("DEPLOY_PASS", "")

# Key URLs that the front page needs (same paths as test_url_timing.py)
URLS = [
    ("/vidgenerator/api/frontpage/init", "GET"),
    ("/vidgenerator/api/stats/summary", "GET"),
    ("/vidgenerator/api/points/all", "GET"),
    ("/vidgenerator/api/health", "GET"),
    ("/vidgenerator/", "GET"),
]

def main():
    try:
        import paramiko
    except ImportError:
        print("Install paramiko: pip install paramiko")
        sys.exit(1)
    passwd = SERVER_PASS or (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
    if not passwd:
        print("Set DEPLOY_PASS in .env or environment")
        sys.exit(1)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=passwd, timeout=15)

    print("Testing URLs from server (127.0.0.1:5000)")
    print("=" * 60)
    base = "http://127.0.0.1:5000"
    # One SSH command: run all curls with 5s timeout each
    parts = []
    for path, _ in URLS:
        url = base + path
        parts.append(f'curl -s -o /dev/null -w "%{{http_code}} {path} %{{time_total}}s\\n" -m 5 "{url}" 2>/dev/null || echo "FAIL {path}"')
    cmd = " ; ".join(parts)
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=40)
    out = stdout.read().decode(errors="replace").strip()
    err = stderr.read().decode(errors="replace").strip()
    for line in out.splitlines():
        print(" ", line)
    if err:
        print("  STDERR:", err)
    ssh.close()
    print("=" * 60)
    print("Done. 200 = OK; 502/000/FAIL = backend or timeout.")

if __name__ == "__main__":
    main()
