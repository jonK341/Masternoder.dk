#!/usr/bin/env python3
"""
Run all bottleneck-reduction steps in order (see docs/PORT_5000_BOTTLENECK_AND_SOLUTIONS.md).

  1. Add swap on server (if missing) so more workers don't trigger OOM.
  2. Patch nginx to use upstream flask_backend (5000 + 5001).
  3. Deploy and start second uWSGI backend on port 5001.
  4. Deploy updated systemd units (LITE_APP=1, main + 5001) and restart uwsgi-vidgenerator.

Run from your PC:  python scripts/run_bottleneck_fixes.py

Optional:  --skip-swap   skip adding swap (if you already have enough).
"""
import base64
import os
import subprocess
import sys

try:
    import paramiko
except ImportError:
    print("Install paramiko: pip install paramiko")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def run_script(name, *args):
    path = os.path.join(SCRIPT_DIR, name)
    if not os.path.isfile(path):
        print(f"[SKIP] {name} not found")
        return 0
    r = subprocess.run([sys.executable, path] + list(args), cwd=PROJECT_ROOT, timeout=120)
    return r.returncode


def run(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode(errors="replace").strip()
    err = (stderr.read() or b"").decode(errors="replace").strip()
    return out, err


def main():
    skip_swap = "--skip-swap" in sys.argv
    print("=" * 60)
    print("Run all bottleneck fixes (swap, nginx upstream, second backend, restart)")
    print("=" * 60)

    if not skip_swap:
        print("\n[1/4] Add swap on server (if missing)...")
        if run_script("server_add_swap.py") != 0:
            print("  [WARN] server_add_swap.py failed; continue anyway.")
    else:
        print("\n[1/4] Skip swap (--skip-swap).")

    print("\n[2/4] Nginx: add upstream flask_backend (5000 + 5001)...")
    if run_script("enable_nginx_upstream.py") != 0:
        print("[ERROR] enable_nginx_upstream.py failed.")
        return 1

    print("\n[3/4] Deploy and start second backend (port 5001)...")
    if run_script("enable_second_backend.py") != 0:
        print("[WARN] enable_second_backend.py failed; 5000-only will still work.")

    print("\n[4/4] Deploy updated systemd units and restart uwsgi-vidgenerator...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    except Exception as e:
        print(f"[ERROR] SSH failed: {e}")
        return 1

    for unit_name in ("uwsgi-vidgenerator.service", "uwsgi-vidgenerator-5001.service"):
        unit_path = os.path.join(PROJECT_ROOT, "systemd", unit_name)
        if os.path.isfile(unit_path):
            with open(unit_path, "r", encoding="utf-8") as f:
                content = f.read()
            b64 = base64.b64encode(content.encode()).decode()
            remote = f"/etc/systemd/system/{unit_name}"
            run(ssh, f"echo '{b64}' | base64 -d > {remote}", timeout=10)
            print(f"  Deployed {unit_name}")

    run(ssh, "systemctl daemon-reload", timeout=10)
    # Restart can take 60–90s+ while workers load (TimeoutStartSec=300 on the unit)
    print("  Restarting uwsgi-vidgenerator (may take 1–2 min)...")
    run(ssh, "systemctl restart uwsgi-vidgenerator", timeout=180)
    run(ssh, "systemctl start uwsgi-vidgenerator-5001 2>/dev/null || true", timeout=60)
    run(ssh, "systemctl reload nginx 2>&1 || true", timeout=10)

    out, _ = run(ssh, "systemctl is-active uwsgi-vidgenerator 2>/dev/null || true")
    print(f"  uwsgi-vidgenerator (5000): {out}")
    out2, _ = run(ssh, "systemctl is-active uwsgi-vidgenerator-5001 2>/dev/null || true")
    print(f"  uwsgi-vidgenerator-5001:   {out2}")

    ssh.close()
    print()
    print("Done. Test: https://masternoder.dk/ and check logs if needed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
