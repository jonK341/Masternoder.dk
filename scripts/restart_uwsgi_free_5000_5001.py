#!/usr/bin/env python3
"""
On the server: stop both uWSGI units, free TCP 5000 and 5001, start them again.

Usage:
  python scripts/restart_uwsgi_free_5000_5001.py

Uses DEPLOY_HOST / DEPLOY_USER / DEPLOY_PASS (same as deploy.py).
"""
import os
import sys
import time

SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

try:
    import paramiko
except ImportError:
    print("Install paramiko: pip install paramiko")
    sys.exit(1)


def run(ssh, cmd, timeout=30):
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    return out, err


def main():
    print("=" * 60)
    print("Restart uWSGI: free :5000 and :5001, start both backends")
    print("=" * 60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=45)
    except Exception as e:
        print("[ERROR] SSH:", e)
        return 1

    print("\n[1] Before (listeners on 5000 / 5001)")
    out, _ = run(ssh, "ss -tlnp 2>/dev/null | grep -E ':5000 |:5001 ' || true", 10)
    print(out or "  (none)")

    print("\n[2] Stop systemd units (may take up to ~2 min — TimeoutStopSec on uwsgi)")
    run(
        ssh,
        "systemctl stop uwsgi-vidgenerator-5001 2>/dev/null; "
        "systemctl stop uwsgi-vidgenerator 2>/dev/null; "
        "systemctl stop uwsgi 2>/dev/null; true",
        180,
    )
    time.sleep(2)

    print("\n[3] Kill stray uwsgi / free ports")
    run(ssh, "pkill -9 -f '[u]wsgi' 2>/dev/null || true", 10)
    time.sleep(1)
    run(ssh, "fuser -k 5000/tcp 2>/dev/null || true", 10)
    run(ssh, "fuser -k 5001/tcp 2>/dev/null || true", 10)
    time.sleep(2)
    out, _ = run(ssh, "ss -tlnp 2>/dev/null | grep -E ':5000 |:5001 ' || true", 10)
    if out:
        print("  WARN still listening:", out[:300])
        run(ssh, "for p in $(ss -tlnp 2>/dev/null | grep -E ':5000 |:5001 ' | sed -n 's/.*pid=\\([0-9]*\\).*/\\1/p'); do kill -9 $p 2>/dev/null; done", 10)
        time.sleep(1)
    else:
        print("  [OK] Ports 5000 and 5001 are free")

    print("\n[4] Start uwsgi-vidgenerator (5000), then uwsgi-vidgenerator-5001 (5001)")
    run(ssh, "systemctl start uwsgi-vidgenerator", 120)
    time.sleep(3)
    run(ssh, "systemctl start uwsgi-vidgenerator-5001", 120)

    print("\n[5] Wait for workers (up to ~3 min)...")
    ok5000 = ok5001 = False
    for i in range(36):
        st0, _ = run(ssh, "systemctl is-active uwsgi-vidgenerator 2>&1", 10)
        st1, _ = run(ssh, "systemctl is-active uwsgi-vidgenerator-5001 2>&1", 10)
        c0, _ = run(
            ssh,
            "curl -s -o /dev/null -w '%{http_code}' --max-time 8 http://127.0.0.1:5000/ 2>/dev/null",
            15,
        )
        c1, _ = run(
            ssh,
            "curl -s -o /dev/null -w '%{http_code}' --max-time 8 http://127.0.0.1:5001/ 2>/dev/null",
            15,
        )
        print(f"  t={i * 5}s  5000:{st0} http={c0 or '---'}  |  5001:{st1} http={c1 or '---'}")
        if c0 and len(c0) == 3 and c0.startswith("2"):
            ok5000 = True
        if c1 and len(c1) == 3 and c1.startswith("2"):
            ok5001 = True
        if ok5000 and ok5001:
            break
        time.sleep(5)

    print("\n[6] Summary")
    out, _ = run(ssh, "ss -tlnp 2>/dev/null | grep -E ':5000 |:5001 ' || true", 10)
    print(out or "  (no listeners)")
    if not ok5001:
        print(
            "\n[WARN] Port 5001 did not return HTTP 200. Check: "
            "journalctl -u uwsgi-vidgenerator-5001 -n 50  and  tail /var/www/html/uwsgi_5001.log"
        )
    ssh.close()
    print("\nDone.")
    return 0 if (ok5000 and ok5001) else 1


if __name__ == "__main__":
    sys.exit(main())
