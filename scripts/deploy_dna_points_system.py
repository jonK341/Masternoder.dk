#!/usr/bin/env python3
"""
Deploy DNA Tech + Unified Points (/api/points/all) system
Deploys backend services/routes and the unified dashboard UI changes.
"""
import os
import time
from datetime import datetime

import paramiko

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

FILES_TO_DEPLOY = [
    "backend/register_blueprints.py",
    "backend/services/unified_points_database.py",
    "backend/routes/points_routes.py",
    "backend/services/unified_points_trigger_integration.py",
    "backend/services/agent_trigger_system.py",
    "backend/services/dna_manipulation_system.py",
    "backend/routes/dna_monster_calendar_routes.py",
    "vidgenerator/static/js/unified-point-counters.js",
    "vidgenerator/unified_dashboard/index.html",
    "178_systems_config.json",
]


def main():
    print("=" * 70)
    print("DNA Tech + Unified Points - Production Deployment")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    ssh = None
    sftp = None
    try:
        print("[1/5] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()

        print("[2/5] Deploying files...")
        sftp = ssh.open_sftp()
        deployed = 0
        for local_file in FILES_TO_DEPLOY:
            if not os.path.exists(local_file):
                print(f"  [SKIP] {local_file} (not found)")
                continue

            remote_file = f"/var/www/html/vidgenerator/{local_file}"
            remote_dir = os.path.dirname(remote_file)
            ssh.exec_command(f"mkdir -p {remote_dir} 2>&1 || true", timeout=10)
            ssh.exec_command(f"cp {remote_file} {remote_file}.backup.$(date +%Y%m%d_%H%M%S) 2>&1 || true", timeout=10)

            with open(local_file, "r", encoding="utf-8") as f:
                content = f.read()
            with sftp.file(remote_file, "w") as rf:
                rf.write(content)

            print(f"  [OK] {local_file}")
            deployed += 1
        print(f"  [SUMMARY] {deployed} files deployed")
        print()

        print("[3/5] Clearing cache...")
        ssh.exec_command("find /var/www/html/vidgenerator -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true", timeout=30)
        ssh.exec_command("find /var/www/html/vidgenerator -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()

        print("[4/5] Restarting services...")
        ssh.exec_command("systemctl restart uwsgi-vidgenerator 2>&1 || true", timeout=30)
        ssh.exec_command("systemctl restart python-proxy 2>&1 || true", timeout=30)
        time.sleep(12)
        print("  [OK] Restart commands sent")
        print()

        print("[5/5] Quick verification...")
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator && systemctl is-active python-proxy", timeout=30)
        status = stdout.read().decode("utf-8", errors="ignore").strip()
        if status:
            print(f"  [STATUS]\n{status}")
        else:
            print("  [WARN] Could not read service status")

        print()
        print("=" * 70)
        print("Deployment complete.")
        print("=" * 70)
        print("Next: test endpoints:")
        print("  - GET  https://masternoder.dk/vidgenerator/api/points/all?user_id=default_user")
        print("  - POST https://masternoder.dk/vidgenerator/api/dna/manipulate")
        print("  - POST https://masternoder.dk/vidgenerator/api/dna/clone")
        print()

    finally:
        try:
            if sftp:
                sftp.close()
        except Exception:
            pass
        try:
            if ssh:
                ssh.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()

