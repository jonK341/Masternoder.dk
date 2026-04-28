#!/usr/bin/env python3
"""
Fix 502 Bad Gateway - SQLite database permissions and env setup.
Root cause: sqlalchemy.exc.OperationalError: unable to open database file
"""
import os
import sys
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE = "/var/www/html"
DB_PATH = "/var/www/html/vidgenerator/documentaries.db"
INSTANCE_DB = "/var/www/html/instance/database.db"

def run(ssh, cmd, timeout=20):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace").strip()
    err = stderr.read().decode(errors="replace").strip()
    return out, err

def main():
    try:
        import paramiko
    except ImportError:
        print("pip install paramiko")
        sys.exit(1)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    print("=" * 60)
    print("FIX 502 - DATABASE & PERMISSIONS")
    print("=" * 60)

    # 1. Ensure .env exists with DATABASE_URL
    print("\n[1] Ensure .env with DATABASE_URL")
    env_path = f"{REMOTE}/vidgenerator/.env"
    run(ssh, f"test -f {env_path} && echo exists || echo missing")
    out, _ = run(ssh, f"grep DATABASE_URL {env_path} 2>/dev/null || echo 'not found'")
    print(f"  {env_path}: {out[:80] if out else 'no DATABASE_URL'}")

    if "DATABASE_URL" not in (out or ""):
        # sqlite://// for absolute path (4 slashes)
        run(ssh, f"echo 'DATABASE_URL=sqlite:///{DB_PATH}' >> {env_path}")
        print("  Added DATABASE_URL to .env")

    # 2. Ensure database directory and file exist, fix permissions
    print("\n[2] Database path and permissions")
    run(ssh, f"mkdir -p {os.path.dirname(DB_PATH)}")
    run(ssh, f"touch {DB_PATH}")
    run(ssh, f"chown www-data:www-data {DB_PATH}")
    run(ssh, f"chmod 664 {DB_PATH}")
    run(ssh, f"chown -R www-data:www-data {os.path.dirname(DB_PATH)}")
    print(f"  {DB_PATH} - exists, www-data:www-data, 664")

    # Also ensure instance/database.db (app default when DATABASE_URL unset) exists and is writable
    run(ssh, f"mkdir -p {REMOTE}/instance")
    run(ssh, f"chmod 775 {REMOTE}/instance")
    run(ssh, f"touch {REMOTE}/instance/database.db 2>/dev/null || true")
    run(ssh, f"chown -R www-data:www-data {REMOTE}/instance")
    run(ssh, f"chmod 664 {REMOTE}/instance/database.db 2>/dev/null || true")
    print(f"  {REMOTE}/instance + instance/database.db - exists, www-data, writable")

    # 3. Add env to uwsgi.ini so DATABASE_URL is always set (backup if .env not loaded)
    print("\n[3] Add env to uwsgi.ini")
    uwsgi_ini = f"{REMOTE}/vidgenerator/uwsgi.ini"
    out, _ = run(ssh, f"grep -c 'env.*DATABASE' {uwsgi_ini} 2>/dev/null || echo 0")
    if "0" in out or not out:
        run(ssh, f"echo 'env = DATABASE_URL=sqlite:///{DB_PATH}' >> {uwsgi_ini}")
        print("  Added env DATABASE_URL to uwsgi.ini")
    else:
        print("  env DATABASE_URL already in uwsgi.ini")

    # 4. Restart uwsgi-vidgenerator (single service, see docs/DEPLOYMENT_PLAN.md)
    print("\n[4] Restart uwsgi-vidgenerator")
    run(ssh, "systemctl stop uwsgi-vidgenerator 2>/dev/null; systemctl stop uwsgi 2>/dev/null || true", timeout=10)
    time.sleep(3)
    run(ssh, "systemctl start uwsgi-vidgenerator", timeout=10)
    time.sleep(6)
    out, _ = run(ssh, "systemctl is-active uwsgi-vidgenerator")
    print(f"  uwsgi-vidgenerator: {out}")

    # 5. Quick test
    print("\n[5] Quick curl test")
    out, _ = run(ssh, "curl -s -o /dev/null -w '%{http_code}' --max-time 15 http://127.0.0.1:5000/ 2>/dev/null || echo 'timeout'")
    print(f"  Port 5000: HTTP {out}")

    ssh.close()
    print("\n" + "=" * 60)
    print("DONE - Check https://masternoder.dk/ and https://masternoder.dk/generator")
    print("=" * 60)

if __name__ == "__main__":
    main()
