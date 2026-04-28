#!/usr/bin/env python3
"""
Fix 404 for /api/unified/status etc.
Diagnose showed: 127.0.0.1:5000 returns 404 for /api/unified/status but 200 for /api/generator/test.
The app on 5000 has generator routes but not unified. Likely cause: uwsgi/pythonpath or import path
doesn't include project root, so backend.routes.missing_endpoints may fail to load some routes.
Fix: Ensure PYTHONPATH includes /var/www/html and clear caches, then restart.
"""
import os
import sys

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html"


def sh(ssh, cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    return out + ("\n" + err if err else "")


def main():
    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

    print("=" * 60)
    print("FIX SERVER ROUTES 404")
    print("=" * 60)

    # 1. Verify missing_endpoints has unified route
    print("\n[1] Check if unified route exists in file on server:")
    out = sh(ssh, f"grep -n 'unified/status' {REMOTE_BASE}/backend/routes/missing_endpoints_routes.py 2>/dev/null | head -3")
    print(out or "  File not found or no match")

    # 2. Test route registration
    print("\n[2] Test route registration:")
    out = sh(ssh, f"cd {REMOTE_BASE} && PYTHONPATH={REMOTE_BASE} python3 -B -c 'from src.app import create_app; a=create_app(); u=[str(r) for r in a.url_map.iter_rules() if \"unified\" in str(r)]; print(len(u), \"unified routes\")' 2>&1")
    print(f"  {out}")

    # 3. Fix uwsgi env if needed - add PYTHONPATH to systemd service
    print("\n[3] Check uwsgi-vidgenerator service env:")
    out = sh(ssh, "systemctl show uwsgi-vidgenerator -p Environment 2>/dev/null")
    print(f"  {out}")

    # 4. Add env file or override for uwsgi to set PYTHONPATH
    env_dir = "/etc/systemd/system/uwsgi-vidgenerator.service.d"
    env_file = f"{env_dir}/environment.conf"
    print("\n[4] Ensure PYTHONPATH in uwsgi-vidgenerator:")
    sh(ssh, f"mkdir -p {env_dir}", timeout=5)
    override = f"""[Service]
Environment="PYTHONPATH={REMOTE_BASE}"
"""
    sftp = ssh.open_sftp()
    try:
        with sftp.open(env_file, "w") as f:
            f.write(override)
        print(f"  Wrote {env_file}")
    except Exception as e:
        print(f"  Could not write: {e}")
    sftp.close()

    # 5. Clear Python cache
    print("\n[5] Clear Python cache:")
    sh(ssh, f"find {REMOTE_BASE} -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null; find {REMOTE_BASE} -name '*.pyc' -delete 2>/dev/null; echo done")

    # 6. Restart services (use fix_gateways order)
    print("\n[6] Restart services...")
    sh(ssh, "systemctl daemon-reload 2>&1")
    sh(ssh, "systemctl restart python-proxy 2>&1 || systemctl restart python-proxy.service 2>&1 || true", timeout=15)
    import time
    time.sleep(10)
    sh(ssh, "systemctl stop uwsgi-vidgenerator 2>&1 || true", timeout=10)
    time.sleep(3)
    sh(ssh, "systemctl start uwsgi-vidgenerator 2>&1 || true", timeout=15)
    time.sleep(5)
    sh(ssh, "systemctl restart uwsgi 2>&1 || true", timeout=10)
    time.sleep(3)
    sh(ssh, "systemctl reload nginx 2>&1 || true", timeout=10)

    # 7. Test
    print("\n[7] Test after restart:")
    for path in ["/api/unified/status", "/api/generator/test"]:
        code = sh(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'http://127.0.0.1:5000{path}' 2>/dev/null")
        print(f"  {path}: {code}")

    ssh.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
