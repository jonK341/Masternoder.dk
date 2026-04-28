#!/usr/bin/env python3
"""
Hard reset for port 5000: kill every process using 5000 or running uwsgi/start-stop-daemon
so that "Unit process X remains running after unit stopped" does not block a clean start.

Usage:
  python scripts/reset_port_5000.py         # kill only, port 5000 freed
  python scripts/reset_port_5000.py --start # kill then start uwsgi (same as fix_502 flow)
"""
import os
import sys
import time
import argparse

SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

try:
    import paramiko
except ImportError:
    print("Install paramiko: pip install paramiko")
    sys.exit(1)


def run(ssh, cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    try:
        out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
        err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    except Exception:
        out, err = "", ""
    return out, err


def main():
    ap = argparse.ArgumentParser(description="Hard reset port 5001 (kill all uwsgi / port 5001); optional --start uwsgi")
    ap.add_argument("--start", action="store_true", help="After reset, start uwsgi and verify")
    args = ap.parse_args()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

    print("=== RESET PORT 5001 (kill all app processes) ===\n")

    # 1. Stop services (they may leave children running – we kill those next)
    for svc in ["uwsgi", "uwsgi-vidgenerator", "python-proxy", "vidgenerator-gunicorn"]:
        run(ssh, f"systemctl stop {svc} 2>/dev/null || true")
    time.sleep(2)

    # 2. Kill by port first so nothing keeps 5000
    run(ssh, "fuser -k 5001/tcp 2>/dev/null || true")
    #run(ssh, "fuser -k 5003/tcp 2>/dev/null || true")
    time.sleep(1)

    # 3. Kill every uwsgi and start-stop-daemon (LSB script leaves these running)
    run(ssh, "pkill -9 -f uwsgi-vidgenerator-5001 2>/dev/null || true")
    #run(ssh, "pkill -9 -f 'start-stop-daemon.*uwsgi' 2>/dev/null || true")
    #run(ssh, "pkill -9 -f gunicorn 2>/dev/null || true")
    time.sleep(2)

    # 4. Again free port and kill any restarted by systemd
    run(ssh, "fuser -k 5001/tcp 2>/dev/null || true")
    # run(ssh, "fuser -k 5003/tcp 2>/dev/null || true")
    run(ssh, "pkill -9 -f uwsgi-vidgenerator-5001 2>/dev/null || true")
    time.sleep(2)

    # 5. Verify port 5000 is free
    out, _ = run(ssh, "ss -tlnp 2>/dev/null | grep -E ':5000 |:5003 ' || true")
    if out.strip():
        print("  WARN: Port still in use, forcing again:")
        run(ssh, "fuser -k 5001/tcp 2>/dev/null || true")
        run(ssh, "pkill -9 -f uwsgi-vidgenerator-5001 2>/dev/null || true")
        time.sleep(1)
        out, _ = run(ssh, "ss -tlnp 2>/dev/null | grep ':5001 ' || true")
    if out.strip():
        print("  Port 5001 still in use:", out[:200])
    else:
        print("  Port 5001 (and 5003) is free.\n")

    if not args.start:
        ssh.close()
        print("Done. Start app with: python scripts/ensure_site_up.py  or  python fix_502.py")
        return

    # 6. Start uwsgi-vidgenerator (single service; see docs/DEPLOYMENT_PLAN.md)
    print("=== Starting uwsgi-vidgenerator-5001 ===\n")
    run(ssh, "systemctl start uwsgi-vidgenerator-5001", timeout=25)
    time.sleep(5)
    out, _ = run(ssh, "ss -tlnp 2>/dev/null | grep 5001 || true")
    print("  Port 5001:", out.strip() if out else "(nothing)")
    out, _ = run(ssh, "curl -s -m 8 -o /dev/null -w '%{http_code}' http://127.0.0.1:5001/ 2>/dev/null || true")
    print("  HTTP :5001:", out if out else "timeout")
    run(ssh, "systemctl reload nginx 2>/dev/null || true")
    ssh.close()
    print("\nDone. If still 502, run: python scripts/ensure_site_up.py")


if __name__ == "__main__":
    main()
