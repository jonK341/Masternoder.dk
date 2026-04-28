"""
Deploy phase-2 backend patch files to production and restart services.
"""
import os
import paramiko

HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USER = os.getenv("DEPLOY_USER", "root")
PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

FILES = [
    "backend/register_blueprints.py",
    "backend/routes/error_logging_routes.py",
    "backend/routes/points_routes.py",
    "backend/routes/missing_endpoints_routes.py",
    "backend/routes/hunters_game.py",
    "backend/routes/agent_automation_routes.py",
    "backend/services/agent_automation.py",
    "backend/services/agent_activation_system.py",
]


def sh(ssh, cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode("utf-8", errors="ignore").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="ignore").strip()
    return out, err


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=30)
    sftp = ssh.open_sftp()

    try:
        for f in FILES:
            remote = f"/var/www/html/{f.replace(os.sep, '/')}"
            remote_dir = remote.rsplit("/", 1)[0]
            sh(ssh, f"mkdir -p {remote_dir}")
            with open(f, "r", encoding="utf-8") as fh:
                content = fh.read()
            with sftp.open(remote, "w") as rf:
                rf.write(content)
            print(f"[OK] uploaded {f}")

        commands = [
            "find /var/www/html -name '*.pyc' -delete 2>/dev/null || true",
            "find /var/www/html -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true",
            "systemctl restart python-proxy 2>&1 || systemctl restart python-proxy.service 2>&1 || true",
            "systemctl restart uwsgi-vidgenerator 2>&1 || true",
            "systemctl restart uwsgi 2>&1 || true",
            "systemctl reload nginx 2>&1 || true",
        ]
        for cmd in commands:
            out, err = sh(ssh, cmd, timeout=90)
            print(f"[CMD] {cmd}")
            if out:
                print(f"  OUT: {out[:180]}")
            if err:
                print(f"  ERR: {err[:180]}")

        for service in ("python-proxy", "uwsgi-vidgenerator", "uwsgi", "nginx"):
            out, _ = sh(ssh, f"systemctl is-active {service} 2>&1", timeout=10)
            print(f"[STATUS] {service}: {out}")

        print("[DONE] phase-2 patch deployed")
    finally:
        sftp.close()
        ssh.close()


if __name__ == "__main__":
    main()

