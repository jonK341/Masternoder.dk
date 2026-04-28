#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Sync Changes — upload edited sync files and restart Flask.
Files: unified_points_sync, communication_psychology, dna, user_engagement,
       agent_db_service, missing_endpoints_routes, docs, data, migration script.
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
    # Sync device + DB migration
    "backend/services/unified_points_sync.py",
    "scripts/sync_database_migration.py",
    # Domain sync integrations
    "backend/services/communication_psychology_service.py",
    "backend/services/dna_manipulation_system.py",
    "backend/services/user_engagement.py",
    "backend/services/agent_db_service.py",
    "backend/routes/missing_endpoints_routes.py",
    # Docs
    "docs/SYNC_AND_AGENT_KNOWLEDGE.md",
    "docs/TSS_AI_IMPLEMENTATION_GUIDE.md",
    "docs/LOADING_AND_VIDGENERATOR_STATE.md",
    # Data
    "data/rulebook_v16_sync.json",
]


def run():
    ssh = None
    sftp = None
    try:
        print("=" * 70)
        print("DEPLOY SYNC CHANGES — Upload & Restart Flask")
        print("=" * 70)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print()

        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(base)

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
        deployed = 0
        for local in FILES_TO_DEPLOY:
            if not os.path.exists(local):
                print(f"  [SKIP] {local} (missing)")
                continue
            remote = f"{REMOTE_BASE}/{local.replace(os.sep, '/')}"
            remote_dir = os.path.dirname(remote)
            try:
                ssh.exec_command(f"mkdir -p '{remote_dir}'", timeout=5)
                time.sleep(0.1)
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

        # Run sync migration (optional, may fail if DB path differs)
        print("[3/5] Running sync database migration...")
        migration = f"{REMOTE_BASE}/scripts/sync_database_migration.py"
        stdin, stdout, stderr = ssh.exec_command(
            f"cd {REMOTE_BASE} && python3 {migration} 2>&1",
            timeout=60,
        )
        out = (stdout.read() or b"") + (stderr.read() or b"")
        text = out.decode("utf-8", errors="replace").strip()
        for line in text.splitlines()[-15:]:  # last 15 lines
            print(f"  {line}")
        if "unable to open database" in text.lower():
            print("  [INFO] DB path may differ on server; sync will use JSON fallback.")
        else:
            print("  [OK] Migration attempted")
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
        print("  [OK] Cache cleared")
        print()

        # Restart services
        print("[5/5] Restarting Flask services...")
        services = ["python-proxy", "uwsgi-vidgenerator", "uwsgi"]
        for svc in services:
            ssh.exec_command(f"systemctl restart {svc} 2>&1 || true", timeout=15)
            time.sleep(3)
        time.sleep(5)
        for svc in services:
            stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {svc} 2>&1", timeout=5)
            status = (stdout.read() or b"").decode().strip()
            print(f"  {svc}: {status or 'unknown'}")
        print("  [OK] Restart complete")
        print()

        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print("Verify: https://masternoder.dk/vidgenerator/api/sync/status")
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
