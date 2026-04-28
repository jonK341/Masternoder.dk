#!/usr/bin/env python3
"""
Diagnose and fix uwsgi.service on the server.
Run from your machine: python scripts/diagnose_uwsgi_server.py
"""
import paramiko
import os
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def run(ssh, cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    return out, err


def main():
    fix = "--fix" in sys.argv
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
    except Exception as e:
        print(f"[ERROR] SSH failed: {e}")
        return 1

    print("=" * 60)
    print("UWSGI SERVER DIAGNOSTIC")
    print("=" * 60)

    # 1. How is uwsgi started?
    print("\n[1] How uwsgi service is started:")
    out, _ = run(ssh, "systemctl cat uwsgi 2>/dev/null || true")
    if out:
        for line in out.splitlines()[:25]:
            print(f"  {line}")
    else:
        out, _ = run(ssh, "head -60 /etc/init.d/uwsgi 2>/dev/null || true")
        if out:
            print("  (from /etc/init.d/uwsgi)")
            for line in out.splitlines()[:40]:
                print(f"  {line}")
        else:
            print("  (could not read service or init script)")

    # 2. What configs does it use?
    print("\n[2] /etc/uwsgi/apps-enabled/:")
    out, _ = run(ssh, "ls -la /etc/uwsgi/apps-enabled/ 2>/dev/null || echo '(dir missing or empty)'")
    print(f"  {out}")

    # 3. Does vidgenerator uwsgi.ini exist?
    print("\n[3] Vidgenerator uwsgi.ini:")
    out, _ = run(ssh, "test -f /var/www/html/vidgenerator/uwsgi.ini && echo 'exists' || echo 'MISSING'")
    print(f"  {out}")

    # 4. Find uwsgi binary (venv often has none; system /usr/bin/uwsgi is common)
    uwsgi_bin, _ = run(ssh, "test -x /var/www/html/vidgenerator/.venv/bin/uwsgi && echo /var/www/html/vidgenerator/.venv/bin/uwsgi || echo /usr/bin/uwsgi")
    uwsgi_bin = uwsgi_bin.strip() or "/usr/bin/uwsgi"
    print(f"\n[4] Running uwsgi by hand (using {uwsgi_bin}):")
    cmd = (
        f"cd /var/www/html/vidgenerator && "
        f"timeout 6 sudo -u www-data {uwsgi_bin} "
        "--ini /var/www/html/vidgenerator/uwsgi.ini 2>&1 || true"
    )
    out, err = run(ssh, cmd, timeout=10)
    combined = (out + "\n" + err).strip()
    if combined:
        for line in combined.splitlines()[:30]:
            print(f"  {line}")
    else:
        print("  (no output captured)")

    # 5. Fix: ensure apps-enabled symlink
    if fix:
        print("\n[FIX] Ensuring /etc/uwsgi/apps-enabled/vidgenerator.ini symlink...")
        run(ssh, "mkdir -p /etc/uwsgi/apps-enabled")
        run(ssh, "ln -sf /var/www/html/vidgenerator/uwsgi.ini /etc/uwsgi/apps-enabled/vidgenerator.ini")
        out, _ = run(ssh, "ls -la /etc/uwsgi/apps-enabled/")
        print(f"  {out}")
        print("  Then run: sudo systemctl start uwsgi-vidgenerator   (or from PC: python scripts/ensure_site_up.py)")
    else:
        print("\n[FIX] To create symlink and prepare for start, run this script with --fix:")
        print("  python scripts/diagnose_uwsgi_server.py --fix")

    ssh.close()
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
