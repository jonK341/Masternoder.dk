#!/usr/bin/env python3
"""
Start systemd unit uwsgi-vidgenerator-5001 on the server (works even if disabled for boot).

Uses DEPLOY_HOST / DEPLOY_USER / DEPLOY_PASS (same as deploy.py).

Usage:
  python scripts/start_uwsgi_5001.py

Override: DEPLOY_HOST, DEPLOY_USER, DEPLOY_PASS, SYSTEMD_UNIT (default: uwsgi-vidgenerator-5001)
"""
import os
import sys

# Avoid UnicodeEncodeError on Windows consoles when printing systemd output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Systemd unit name — must match server (see systemd/uwsgi-vidgenerator-5001.service)
SYSTEMD_UNIT = os.environ.get("SYSTEMD_UNIT", "uwsgi-vidgenerator-5001")

SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

try:
    import paramiko
except ImportError:
    print("Install paramiko: pip install paramiko")
    sys.exit(1)


def run(ssh, cmd, timeout=120):
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    return out, err


def main():
    unit = SYSTEMD_UNIT
    print(f"SSH {SERVER_USER}@{SERVER_HOST} — systemd unit: {unit}")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=45)
    except Exception as e:
        print("[ERROR] SSH:", e)
        return 1

    # Clear stuck "activating (auto-restart)" / failed state before start
    out, err = run(
        ssh,
        f"systemctl show {unit} -p Id,FragmentPath,ExecStart,ActiveState,UnitFileState 2>&1; "
        f"echo '--- reset-failed ---'; systemctl reset-failed {unit} 2>&1; "
        f"echo '--- start ---'; systemctl start {unit} 2>&1; "
        f"sleep 2; "
        f"echo '--- ss listen (uwsgi-vidgenerator-5001) ---'; "
        f"ss -tlnp | grep uwsgi-vidgenerator-5001 || echo 'Port 5001 is free'; "
        f"echo '--- is-active ---'; systemctl is-active {unit} 2>&1; "
        f"echo '--- status ---'; systemctl status {unit} --no-pager -l 2>&1 | head -45",
        180,
    )
    print(out)
    if err:
        print(err, file=sys.stderr)

    active, _ = run(ssh, f"systemctl is-active {unit} 2>&1", 10)
    ok = active.strip() == "active"

    if not ok:
        print(f"\n--- [{unit}] not active — journal (last 40 lines) ---", file=sys.stderr)
        jout, _ = run(
            ssh,
            f"journalctl -u {unit} -n 40 --no-pager 2>&1",
            60,
        )
        print(jout, file=sys.stderr)
        print(f"\n--- uwsgi_5001.log (last 35 lines, if present) ---", file=sys.stderr)
        log_out, _ = run(
            ssh,
            "tail -n 35 /var/www/html/uwsgi_5001.log 2>&1 || true",
            30,
        )
        print(log_out, file=sys.stderr)

    ssh.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
