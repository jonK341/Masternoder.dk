#!/usr/bin/env python3
"""
Set lazy-apps = false in uwsgi.ini on the server so workers load at startup.
After this, the site will respond immediately after restart (no 1–3 min wait per worker).
Uses more RAM (all workers load the app at once).

Run from your PC:  python scripts/disable_lazy_apps.py
Then restart:       python fix_502.py   or on server:  sudo systemctl restart uwsgi-vidgenerator
"""
import os
import sys

SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = "root"
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
UWSGI_INI = "/var/www/html/vidgenerator/uwsgi.ini"

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

    def run(cmd, timeout=15):
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
        err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
        return out, err

    # Set lazy-apps = false (comment out lazy-apps = true or replace)
    run(f"sed -i 's/^lazy-apps = true/lazy-apps = false/' {UWSGI_INI}")
    run(f"sed -i 's/^#lazy-apps = false/lazy-apps = false/' {UWSGI_INI}")
    out, _ = run(f"grep -n lazy-apps {UWSGI_INI}")
    print("uwsgi.ini lazy-apps setting:")
    print(out or "(no lazy-apps line)")
    ssh.close()
    print("\nRestart uWSGI so the change takes effect:")
    print("  python fix_502.py   or on server:  sudo systemctl restart uwsgi-vidgenerator")
    print("After restart the app will load at startup; first request will respond without long wait.")

if __name__ == "__main__":
    main()
