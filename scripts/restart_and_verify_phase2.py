"""
Restart production services and verify phase2 endpoints.
Run this after deploy_phase2_patch.py if connection/auth interrupted.
"""
import os
import paramiko

HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USER = os.getenv("DEPLOY_USER", "root")
PASS = os.getenv("DEPLOY_PASS", "")


def sh(ssh, cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode("utf-8", errors="ignore").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="ignore").strip()
    return out, err


def main():
    if not PASS:
        raise SystemExit("DEPLOY_PASS is required")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=30)
    try:
        commands = [
            "systemctl restart python-proxy 2>&1 || systemctl restart python-proxy.service 2>&1 || true",
            "systemctl restart uwsgi-vidgenerator 2>&1 || true",
            "systemctl restart uwsgi 2>&1 || true",
            "systemctl reload nginx 2>&1 || true",
        ]
        for cmd in commands:
            out, err = sh(ssh, cmd, timeout=120)
            print(f"[CMD] {cmd}")
            if out:
                print(f"  OUT: {out[:200]}")
            if err:
                print(f"  ERR: {err[:200]}")

        for service in ("python-proxy", "uwsgi-vidgenerator", "uwsgi", "nginx"):
            out, _ = sh(ssh, f"systemctl is-active {service} 2>&1", timeout=10)
            print(f"[STATUS] {service}: {out}")

        checks = [
            "curl -s -o /dev/null -w '%{http_code}' 'https://masternoder.dk/vidgenerator/api/errors/stats?days=7'",
            "curl -s -o /dev/null -w '%{http_code}' 'https://masternoder.dk/vidgenerator/api/errors/list?limit=5'",
            "curl -s -o /dev/null -w '%{http_code}' 'https://masternoder.dk/api/points/get-all-connected?user_id=test'",
            "curl -s -o /dev/null -w '%{http_code}' 'https://masternoder.dk/api/points/analytics?user_id=test'",
            "curl -s -o /dev/null -w '%{http_code}' 'https://masternoder.dk/api/game/hunters/level?user_id=test'",
        ]
        for c in checks:
            out, err = sh(ssh, c, timeout=30)
            print(f"[CHECK] {c}")
            print(f"  HTTP: {out or err}")
    finally:
        ssh.close()


if __name__ == "__main__":
    main()

