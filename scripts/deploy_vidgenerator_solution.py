#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Vidgenerator Solution - unified routes, battle, video generator, navigation
Uploads changed files and restarts services on masternoder.dk

AUTO-UPGRADE: backend/routes/*.py and backend/services/register_intelligence/*.py
are included via glob - new route files are deployed automatically, no list edits needed.
At startup, register_blueprints discovers and registers all blueprints.
"""
import os
import sys
import time
import glob
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html"


def _build_files_to_deploy():
    """Build deploy list: explicit files + auto-included backend routes and register_intelligence."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(base)
    files = [
        "src/app/__init__.py",
        "backend/route_loader.py",
        "wsgi.py",
        "backend/middleware/auto_fix_404_middleware.py",
        "logs/path_corrector/path_mappings.json",
        "backend/services/video_generator_service.py",
        "backend/services/generator_context_service.py",
        "backend/services/generator_agent_connections.py",
        "data/content_categories.json",
        "data/communication_psychology_theories.json",
        "data/star_map.json",
        "backend/services/communication_psychology_service.py",
        "backend/services/agent_ai_intelligence.py",
        "backend/services/ai_content_generator.py",
        "backend/services/ai_skill_implementations.py",
        "backend/services/llm_service.py",
        "backend/services/modelslab_video_service.py",
        "backend/services/stability_image_service.py",
        "backend/services/tts_service.py",
        "backend/services/unified_points_database.py",
        "backend/services/unified_points_database_enhanced.py",
        "backend/services/unified_points_trigger_integration.py",
        "backend/services/user_onboarding.py",
        "backend/services/trophies_db_service.py",
        "backend/services/agent_trigger_system.py",
        "backend/services/points_db_service.py",
        "backend/register_blueprints.py",
        # Auto-include ALL backend routes (new route files deployed without editing this list)
        *[p.replace(os.sep, "/") for p in glob.glob("backend/routes/*.py")],
        *[p.replace(os.sep, "/") for p in glob.glob("backend/services/register_intelligence/*.py")],
        # Lab, generator, trophies, static assets
        "vidgenerator/wsgi.py",
        "vidgenerator/lab/index.html",
        "vidgenerator/generator/index.html",
        "vidgenerator/trophies/index.html",
        "vidgenerator/profile/index.html",
    "vidgenerator/service-worker.js",
    "vidgenerator/static/js/service-worker-gatherer.js",
    "vidgenerator/static/js/toast-notifications.js",
    "vidgenerator/static/js/error-manager.js",
    "vidgenerator/static/js/theme-timeline.js",
    "vidgenerator/static/js/unified-generator-battle.js",
    "vidgenerator/static/js/hypnotic-point-counters.js",
    "vidgenerator/static/js/trigger-based-actions.js",
    "vidgenerator/static/js/comprehensive-loading-fix.js",
    "vidgenerator/static/js/universal-auto-save-status.js",
    "vidgenerator/static/js/point-system-save-manager.js",
    # Navigation favorites
    "vidgenerator/static/js/navigation-toolbar.js",
    "vidgenerator/static/css/navigation-toolbar.css",
    # Theme assets (fix 404)
    "vidgenerator/static/css/themes/professor-a-plus.css",
    "vidgenerator/static/js/effects/professor-a-plus-effects.js",
    "vidgenerator/static/img/pages/default-bg.jpg",
        # Server-side script: run on server to apply route updates (after git pull, etc.)
        "scripts/production_apply_routes.sh",
        # Communication psychology (DB migration + trophy seed — run on server if needed)
        "scripts/communication_psychology_migration.py",
        "scripts/seed_communication_psychology_trophies.py",
    ]
    return files


def run():
    ssh = None
    sftp = None
    try:
        print("=" * 70)
        print("DEPLOY VIDGENERATOR SOLUTION")
        print("=" * 70)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print()

        import paramiko

        # Connect
        print("[1/5] Connecting...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print("  [OK] Connected")
        print()

        # Upload only changed files (compare local hash vs remote hash)
        print("[2/5] Checking for changed files...")
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        orig_cwd = os.getcwd()
        os.chdir(base)
        files_to_deploy = _build_files_to_deploy()
        total_candidates = len(files_to_deploy)
        print(f"  Candidates: {total_candidates} files")

        import hashlib

        def _normalize(data: bytes) -> bytes:
            """Strip CRLF/BOM differences so Windows vs Linux files compare equal."""
            return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n").lstrip(b"\xef\xbb\xbf")

        def _local_hash(path):
            try:
                with open(path, "rb") as f:
                    return hashlib.md5(_normalize(f.read())).hexdigest()
            except Exception:
                return None

        def _remote_hash(sftp_conn, path):
            try:
                with sftp_conn.file(path, "rb") as f:
                    return hashlib.md5(_normalize(f.read())).hexdigest()
            except Exception:
                return None

        deployed = 0
        skipped = 0
        for local in files_to_deploy:
            if not os.path.exists(local):
                continue
            remote = f"{REMOTE_BASE}/{local.replace(os.sep, '/')}"
            lh = _local_hash(local)
            rh = _remote_hash(sftp, remote)
            if lh and lh == rh:
                skipped += 1
                continue
            remote_dir = os.path.dirname(remote)
            try:
                ssh.exec_command(f"mkdir -p '{remote_dir}'", timeout=5)
                time.sleep(0.1)
            except Exception:
                pass
            try:
                with open(local, "rb") as f:
                    content = f.read()
                is_binary = local.endswith((".jpg", ".png", ".gif", ".ico", ".woff", ".woff2", ".ttf"))
                if not is_binary:
                    content = _normalize(content)
                with sftp.file(remote, "wb") as rf:
                    rf.write(content)
                print(f"  [OK] {local}")
                deployed += 1
            except Exception as e:
                print(f"  [ERROR] {local}: {e}")
        os.chdir(orig_cwd)
        sftp.close()
        print(f"  [SUMMARY] {deployed} changed, {skipped} unchanged (skipped)")
        print()

        # Clear Python cache
        print("[3/5] Clearing cache...")
        ssh.exec_command(
            f"find {REMOTE_BASE} -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null || true",
            timeout=30,
        )
        ssh.exec_command(
            f"find {REMOTE_BASE} -type f -name '*.pyc' -delete 2>/dev/null || true",
            timeout=30,
        )
        print("  [OK] Cache cleared")
        print()

        # Setup generator no-cache (nginx proxy with Cache-Control: no-store)
        print("[4/5] Setting up generator no-cache (nginx)...")
        try:
            import subprocess
            r = subprocess.run(
                [sys.executable, os.path.join(base, "scripts", "setup_generator_no_cache.py")],
                cwd=base,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if r.returncode == 0:
                print("  [OK] Generator page will not be cached")
            else:
                print("  [WARN] No-cache setup skipped or failed (deploy continues)")
        except Exception as e:
            print("  [WARN] No-cache setup:", e, "(deploy continues)")

        # Setup nginx API proxy (fixes 404 for /api/* and /vidgenerator/api/*)
        print("[4b/5] Setting up nginx API proxy...")
        try:
            import subprocess
            r = subprocess.run(
                [sys.executable, os.path.join(base, "scripts", "setup_nginx_api_proxy.py")],
                cwd=base,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if r.returncode == 0:
                print("  [OK] API proxy configured")
            else:
                print("  [WARN] API proxy setup failed:", r.stderr or r.stdout, "(deploy continues)")
        except Exception as e:
            print("  [WARN] API proxy setup:", e, "(deploy continues)")

        # Ensure Flask routes registered (vidgenerator wsgi + uwsgi pythonpath)
        print("[4c/5] Ensuring Flask routes registered...")
        try:
            import subprocess
            r = subprocess.run(
                [sys.executable, os.path.join(base, "scripts", "ensure_flask_routes_registered.py")],
                cwd=base,
                capture_output=True,
                text=True,
                timeout=90,
            )
            if r.returncode == 0:
                print("  [OK] Flask routes fix applied")
            else:
                print("  [WARN]", (r.stderr or r.stdout or "")[:150])
        except Exception as e:
            print("  [WARN]", str(e)[:80])

        # Restart services
        print("[5/5] Restarting services...")
        wait_s = 6
        ssh.exec_command("systemctl restart python-proxy 2>&1 || systemctl restart python-proxy.service 2>&1 || true", timeout=20)
        time.sleep(wait_s)
        ssh.exec_command("systemctl restart uwsgi-vidgenerator 2>&1 || true", timeout=20)
        time.sleep(wait_s)
        ssh.exec_command("systemctl restart uwsgi 2>&1 || true", timeout=20)
        time.sleep(3)
        ssh.exec_command("systemctl reload nginx 2>&1 || systemctl restart nginx 2>&1 || true", timeout=15)
        print("  [OK] Services restarted")
        print()
        print("=" * 70)
        print("DEPLOY COMPLETE")
        print("=" * 70)
        print("Verify: https://masternoder.dk/vidgenerator/ (Ctrl+F5)")
        print()
        print("If browser still shows old UI (no reboot needed):")
        print("  python scripts/apply_updates.py")
        print()
        print("On-server apply (e.g. after git pull):")
        print("  ssh root@masternoder.dk 'cd /var/www/html && bash scripts/production_apply_routes.sh'")
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
