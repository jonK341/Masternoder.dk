#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Upload, deploy, and update — intelligence + layout changes.
Single connection: upload files, run migration, clear cache, restart services.
"""
import os
import sys
import time
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html"

FILES_TO_DEPLOY = [
    "migrations/hunters_star_map_ground_level.py",
    "backend/services/unified_points_trigger_integration.py",
    "backend/services/agent_techs/agent_electric_magnet.py",
    "backend/services/agent_techs/agent_event_tracker.py",
    "backend/routes/hunters_game.py",
    "backend/routes/agent_event_tracker_routes.py",
    "backend/routes/agent_electric_magnet_routes.py",
    "backend/routes/star_map_routes.py",
    "backend/routes/gallery_routes.py",
    "backend/routes/shop_routes.py",
    "backend/routes/all_page_routes.py",
    "backend/register_blueprints.py",
    "data/star_map.json",
    "data/hunters_rulebook_v2.json",
    "data/config_3d_monitor.json",
    "vidgenerator/trophies/index.html",
    "vidgenerator/profile/index.html",
    "vidgenerator/debugger/index.html",
    "vidgenerator/shop/index.html",
    "vidgenerator/gallery/index.html",
    "vidgenerator/generator/index.html",
    "vidgenerator/battle/index.html",
    "vidgenerator/social/index.html",
    "vidgenerator/unified_dashboard/index.html",
    "vidgenerator/lab/index.html",
    "vidgenerator/static/css/navigation-toolbar.css",
    "vidgenerator/static/css/page-layout-metrics.css",
    "vidgenerator/static/js/navigation-toolbar.js",
    "logs/agent_triggers/triggers.json",
    "docs/PLAN.md",
    "docs/PLATFORM_TODO.md",
    "scripts/deploy_upload_update.py",
    "scripts/fix_gateways.py",
]


def run():
    ssh = None
    sftp = None
    try:
        print("=" * 70)
        print("UPLOAD, DEPLOY & UPDATE")
        print("=" * 70)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print()

        # Connect
        print("[1/5] Connecting...")
        ssh = __import__("paramiko").SSHClient()
        ssh.set_missing_host_key_policy(__import__("paramiko").AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print("  [OK] Connected")
        print()

        # Upload
        print("[2/5] Uploading files...")
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(base)
        deployed = 0
        for local in FILES_TO_DEPLOY:
            if not os.path.exists(local):
                print(f"  [SKIP] {local} (missing)")
                continue
            remote = f"{REMOTE_BASE}/{local.replace(os.sep, '/')}"
            remote_dir = os.path.dirname(remote)
            try:
                ssh.exec_command(f"mkdir -p '{remote_dir}'", timeout=5)
                time.sleep(0.2)
            except Exception:
                pass
            try:
                with open(local, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                with sftp.file(remote, "w") as rf:
                    rf.write(content)
                print(f"  [OK] {local}")
                deployed += 1
            except Exception as e:
                print(f"  [ERROR] {local}: {e}")
        sftp.close()
        print(f"  [SUMMARY] {deployed} files uploaded")
        print()

        # Migration
        print("[3/5] Running migration...")
        migration = f"{REMOTE_BASE}/migrations/hunters_star_map_ground_level.py"
        stdin, stdout, stderr = ssh.exec_command(
            f"cd {REMOTE_BASE} && python3 {migration} 2>&1",
            timeout=120,
        )
        out = (stdout.read() or b"") + (stderr.read() or b"")
        text = out.decode("utf-8", errors="replace").strip()
        for line in text.splitlines():
            print(f"  {line}")
        if "ERROR" not in text and "Migration failed" not in text:
            print("  [OK] Migration run complete")
        else:
            print("  [WARN] Migration failed on server (app layout). Run manually from app root if needed.")
        print()

        # Clear cache
        print("[4/5] Clearing cache...")
        ssh.exec_command(
            f"find {REMOTE_BASE} -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null || true",
            timeout=30,
        )
        ssh.exec_command(
            f"find {REMOTE_BASE} -type f -name '*.pyc' -delete 2>/dev/null || true",
            timeout=30,
        )
        ssh.exec_command("rm -rf /var/cache/nginx/* 2>/dev/null || true", timeout=10)
        print("  [OK] Cache cleared")
        print()

        # Fix gateways (avoid 502): restart upstream first, then nginx reload
        print("[5/5] Fix gateways (restart upstream, then nginx)...")
        wait_s = 8
        # Python-proxy (Flask :5000) first
        ssh.exec_command("systemctl restart python-proxy 2>&1 || systemctl restart python-proxy.service 2>&1 || true", timeout=20)
        time.sleep(wait_s)
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active python-proxy 2>&1 || systemctl is-active python-proxy.service 2>&1", timeout=5)
        s = (stdout.read() or b"").decode().strip()
        print(f"  python-proxy: {s or 'unknown'}")
        # uwsgi-vidgenerator
        ssh.exec_command("systemctl restart uwsgi-vidgenerator 2>&1 || true", timeout=20)
        time.sleep(wait_s)
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator 2>&1", timeout=5)
        s = (stdout.read() or b"").decode().strip()
        print(f"  uwsgi-vidgenerator: {s or 'unknown'}")
        if s != "active":
            time.sleep(5)
            ssh.exec_command("systemctl start uwsgi-vidgenerator 2>&1 || true", timeout=10)
            time.sleep(3)
        # uwsgi (main)
        ssh.exec_command("systemctl restart uwsgi 2>&1 || true", timeout=20)
        time.sleep(3)
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi 2>&1", timeout=5)
        print(f"  uwsgi: {(stdout.read() or b'').decode().strip() or 'unknown'}")
        # Wait for upstream :5000
        for _ in range(6):
            stdin, stdout, stderr = ssh.exec_command(
                "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/ 2>/dev/null || echo 000", timeout=10
            )
            out = (stdout.read() or b"").decode().strip()
            if out and out != "000":
                try:
                    c = int(out)
                    if 200 <= c < 600 or c in (301, 302):
                        print("  [OK] Upstream :5000 responding")
                        break
                except Exception:
                    pass
            time.sleep(3)
        else:
            print("  [WARN] Upstream :5000 not ready; continuing.")
        # Nginx reload (no full restart to avoid brief 502)
        ssh.exec_command("nginx -t 2>&1 || true", timeout=10)
        ssh.exec_command("systemctl reload nginx 2>&1 || systemctl restart nginx 2>&1 || true", timeout=15)
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active nginx 2>&1", timeout=5)
        print(f"  nginx: {(stdout.read() or b'').decode().strip() or 'unknown'}")
        print("  [OK] Gateway fix complete")
        print()
        print("=" * 70)
        print("UPLOAD, DEPLOY & UPDATE COMPLETE")
        print("=" * 70)
        print("Verify: https://masternoder.dk/vidgenerator/ (Ctrl+F5)")
        print()
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass
        return False


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
