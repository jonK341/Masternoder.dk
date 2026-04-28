#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix 502 Bad Gateway: ensure upstream (python-proxy, uwsgi) is up before nginx.
Order: python-proxy restart -> uwsgi-vidgenerator stop then start -> uwsgi restart -> nginx reload.
(uwsgi-vidgenerator uses stop/start because restart hangs on deactivating.)
"""
import os
import sys
import time

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
UPSTREAM_PORT = 5000
WAIT_AFTER_RESTART = 8
WAIT_UPSTREAM_RETRIES = 6
UPSTREAM_RETRY_DELAY = 3


def _sh(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    return out, err


def _sh_bg(ssh, cmd, wait_sec=15):
    """Run command in background on server so SSH read does not block."""
    ssh.exec_command(f"nohup bash -c '{cmd}' </dev/null >/dev/null 2>&1 &")
    time.sleep(wait_sec)


def _wait_upstream(ssh):
    """Check that something is listening on UPSTREAM_PORT (curl ok or ss)."""
    for _ in range(WAIT_UPSTREAM_RETRIES):
        out, _ = _sh(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:{UPSTREAM_PORT}/ 2>/dev/null || echo 000", timeout=10)
        if out and out != "000":
            try:
                c = int(out)
                if 200 <= c < 600 or c in (301, 302):
                    return True
            except Exception:
                pass
        out2, _ = _sh(ssh, f"ss -ltn 2>/dev/null | grep ':{UPSTREAM_PORT}' || true", timeout=5)
        if out2 and f":{UPSTREAM_PORT}" in out2:
            return True
        time.sleep(UPSTREAM_RETRY_DELAY)
    return False


def run():
    ssh = None
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    except Exception as e:
        print(f"[ERROR] Connect failed: {e}")
        return False

    try:
        print("=" * 60)
        print("FIX GATEWAYS (502 Bad Gateway)")
        print("=" * 60)

        # 1. Restart python-proxy first (Flask on :5000)
        print("[1/4] Restarting python-proxy...")
        _sh_bg(ssh, "systemctl restart python-proxy 2>&1 || systemctl restart python-proxy.service 2>&1 || true", wait_sec=WAIT_AFTER_RESTART + 5)
        out, _ = _sh(ssh, "systemctl is-active python-proxy 2>&1 || systemctl is-active python-proxy.service 2>&1", timeout=5)
        print(f"  python-proxy: {out.strip() or 'unknown'}")

        # 2. Stop then start uwsgi-vidgenerator (restart hangs on deactivating)
        print("[2/4] Stopping uwsgi-vidgenerator...")
        _sh_bg(ssh, "systemctl stop uwsgi-vidgenerator 2>&1 || true", wait_sec=5)
        for i in range(24):
            out, _ = _sh(ssh, "systemctl is-active uwsgi-vidgenerator 2>&1", timeout=5)
            out = (out or "").strip()
            print(f"  Status: {out}")
            if out in ("inactive", "failed", ""):
                break
            time.sleep(5)
        else:
            print("  [WARN] Unit still not inactive after 2 min; starting anyway.")
        time.sleep(2)
        print("  Starting uwsgi-vidgenerator...")
        _sh_bg(ssh, "systemctl start uwsgi-vidgenerator 2>&1 || true", wait_sec=15)
        for _ in range(6):
            out, _ = _sh(ssh, "systemctl is-active uwsgi-vidgenerator 2>&1", timeout=5)
            out = (out or "").strip()
            print(f"  Status: {out}")
            if out == "active":
                break
            time.sleep(5)
        print(f"  uwsgi-vidgenerator: {out.strip() or 'unknown'}")

        # 3. Optional: uwsgi (main)
        print("[3/4] Restarting uwsgi (main)...")
        _sh_bg(ssh, "systemctl restart uwsgi 2>&1 || true", wait_sec=10)
        out, _ = _sh(ssh, "systemctl is-active uwsgi 2>&1", timeout=5)
        print(f"  uwsgi: {out.strip() or 'unknown'}")

        # 4. Wait for upstream :5000 then reload nginx
        print("[4/4] Waiting for upstream :5000...")
        if _wait_upstream(ssh):
            print("  [OK] Upstream responding")
        else:
            print("  [WARN] Upstream may not be ready; continuing anyway.")

        print("      Reloading nginx...")
        _sh(ssh, "nginx -t 2>&1", timeout=10)
        _sh(ssh, "systemctl reload nginx 2>&1 || systemctl restart nginx 2>&1 || true", timeout=30)
        out, _ = _sh(ssh, "systemctl is-active nginx 2>&1", timeout=5)
        print(f"  nginx: {out.strip() or 'unknown'}")

        print("=" * 60)
        print("GATEWAY FIX COMPLETE")
        print("=" * 60)
        print("Verify: https://masternoder.dk/vidgenerator/ (Ctrl+F5)")
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
