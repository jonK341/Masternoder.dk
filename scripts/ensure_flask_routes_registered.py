#!/usr/bin/env python3
"""
Ensure uwsgi-vidgenerator loads from project root so all Flask routes (missing_endpoints, etc.) are registered.
- Deploys vidgenerator/wsgi.py that adds /var/www/html to sys.path
- Updates uwsgi pythonpath to include /var/www/html
- Restarts uwsgi-vidgenerator
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
    print("ENSURE FLASK ROUTES REGISTERED")
    print("=" * 60)

    # 1. Find uwsgi config for vidgenerator
    uwsgi_cfgs = [
        "/etc/uwsgi/apps-enabled/vidgenerator.ini",
        "/etc/uwsgi/apps-available/vidgenerator.ini",
        "/etc/uwsgi/vidgenerator.ini",
        f"{REMOTE_BASE}/vidgenerator/uwsgi.ini",
    ]
    cfg_path = None
    for p in uwsgi_cfgs:
        if "ok" in sh(ssh, f"test -f {p} && echo ok || true"):
            cfg_path = p
            break

    if cfg_path:
        print(f"\n[1] Found uwsgi config: {cfg_path}")
        cfg = sh(ssh, f"cat {cfg_path}")
        import re
        # Ensure pythonpath includes project root (so backend.*, src.* import correctly)
        if "pythonpath" in cfg.lower():
            new_cfg = re.sub(
                r"pythonpath\s*=\s*[^\n]+",
                f"pythonpath = {REMOTE_BASE}",
                cfg,
                count=1,
                flags=re.I
            )
        else:
            new_cfg = cfg.rstrip() + f"\npythonpath = {REMOTE_BASE}\n"

        if new_cfg != cfg:
            sh(ssh, f"cp {cfg_path} {cfg_path}.bak 2>/dev/null || true")
            sftp = ssh.open_sftp()
            with sftp.open(cfg_path, "w") as f:
                f.write(new_cfg)
            sftp.close()
            print(f"  Set pythonpath = {REMOTE_BASE}")
        else:
            print(f"  pythonpath already correct")
    else:
        print("\n[1] No uwsgi vidgenerator config found")

    # 2. Clear Python cache
    print("\n[2] Clear Python cache")
    sh(ssh, f"find {REMOTE_BASE} -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null; find {REMOTE_BASE} -name '*.pyc' -delete 2>/dev/null; echo done")

    # 2b. Ensure python-proxy has PYTHONPATH (it may serve port 5000)
    proxy_env_dir = "/etc/systemd/system/python-proxy.service.d"
    proxy_env_file = f"{proxy_env_dir}/environment.conf"
    sh(ssh, f"mkdir -p {proxy_env_dir}", timeout=5)
    proxy_override = f"""[Service]
Environment="PYTHONPATH={REMOTE_BASE}"
"""
    try:
        sftp = ssh.open_sftp()
        with sftp.open(proxy_env_file, "w") as f:
            f.write(proxy_override)
        sftp.close()
        print(f"\n  Set PYTHONPATH for python-proxy: {proxy_env_file}")
        sh(ssh, "systemctl daemon-reload 2>&1")
    except Exception as ex:
        print(f"\n  [WARN] Could not write python-proxy env: {ex}")

    # 3. Restart uwsgi-vidgenerator (stop then start - restart can hang)
    print("\n[3] Restart uwsgi-vidgenerator")
    import time
    sh(ssh, "systemctl stop uwsgi-vidgenerator 2>&1 || true", timeout=15)
    time.sleep(3)
    sh(ssh, "systemctl start uwsgi-vidgenerator 2>&1 || true", timeout=15)
    time.sleep(5)

    # 3b. Restart python-proxy (Flask on port 5000)
    print("\n[3b] Restart python-proxy")
    sh(ssh, "systemctl restart python-proxy 2>&1 || systemctl restart python-proxy.service 2>&1 || true", timeout=15)
    time.sleep(5)

    # 4. Test routes
    print("\n[4] Test routes on :5000")
    for path in ["/api/unified/status", "/api/generator/test", "/api/monetization/top-50",
                 "/api/progression/all/default_user", "/api/notifications/count", "/api/debug/routes"]:
        code = sh(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'http://127.0.0.1:5000{path}' 2>/dev/null")
        print(f"  {path}: {code}")

    ssh.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
